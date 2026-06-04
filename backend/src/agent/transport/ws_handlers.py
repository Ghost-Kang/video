"""WS inbound message handlers — 一个 type 一个 handler,HANDLERS dict 注册 (Pydantic model + handler fn) pair。

handler 签名:`async def handle_xxx(ctx: WSCtx, msg: XxxMsg) -> None`
- msg 已被 ws_server.dispatch 校验过,handler 拿到的是 typed Pydantic 实例
- 全部从 `ctx.ws` 发送响应,统一走 `send_json`

`auth` 由 ws_server 直接处理(它要拿 user_id 才能构造 ctx),不入 HANDLERS。
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Awaitable, Callable

from agent import store  # 通过 module 访问,方便 test monkeypatch
from agent.cascade import cost_guard  # B3 — enqueue-time generation cost guard
from agent.cascade import events as cascade_events  # module 访问,test 可 patch emit
from agent.cascade import storage as cascade_storage  # module 访问,test 可 patch
from agent.cascade.event_names import EventName
from agent.cascade.failures import HardFailure
from agent.config import IMAGE_GEN_PROVIDER
from agent.tools import canvas as canvas_tools
from agent.transport import agent_runner, run_state  # module 访问同理
from agent.transport.context import WSCtx, canvas_data, send_json
from agent.transport.ws_messages import (
    INBOUND_MODELS,
    CreateEdgeMsg,
    DeleteEdgeMsg,
    DeleteSessionMsg,
    DeleteSessionsMsg,
    ExecuteNodeMsg,
    GetSessionStateMsg,
    ListNodeVersionsMsg,
    ListSessionsMsg,
    OptimizePromptMsg,
    RegenerateNodeMsg,
    RegenerateScriptNodeMsg,
    CancelGenerationMsg,
    ReorderEdgeMsg,
    RestoreNodeVersionMsg,
    SeedCanvasMsg,
    ReviewDecisionMsg,
    ReviewNodeMsg,
    UpdateNodeStatusMsg,
    UpdatePositionMsg,
    UserMessageMsg,
)

_THREAD_RUN_LOCKS: dict[str, asyncio.Lock] = {}
_MAX_THREAD_LOCKS = 512


def _get_thread_run_lock(thread_id: str) -> asyncio.Lock:
    """Per-thread run lock with a bound on dict growth.

    Previously `setdefault` grew this dict forever (one entry per thread_id
    ever seen) — a slow leak over long uptime. When we exceed the cap we drop
    currently-unlocked entries (an unlocked asyncio.Lock has no holder and no
    waiters, so removing it is safe).
    """
    lock = _THREAD_RUN_LOCKS.get(thread_id)
    if lock is None:
        if len(_THREAD_RUN_LOCKS) >= _MAX_THREAD_LOCKS:
            for k in [k for k, l in _THREAD_RUN_LOCKS.items() if not l.locked()]:
                del _THREAD_RUN_LOCKS[k]
        lock = asyncio.Lock()
        _THREAD_RUN_LOCKS[thread_id] = lock
    return lock


async def _run_agent_serialized(ctx: WSCtx, msg: UserMessageMsg) -> None:
    """Run one Director turn at a time per thread.

    Users can double-send or reconnect/autosend quickly. Without this guard,
    two `run_agent` tasks for the same thread race over the same LangGraph
    checkpoint and can duplicate expensive upstream analysis calls.
    """
    lock = _get_thread_run_lock(msg.thread_id)
    async with lock:
        await agent_runner.run_agent(
            ctx.user_id,
            ctx.pool,
            msg.thread_id,
            msg.content,
            ctx.ws,
            selected_niche=msg.selected_niche,
        )


async def _resume_agent_serialized(ctx: WSCtx, msg: ReviewDecisionMsg) -> None:
    """Resume a paused (awaiting-review) Director turn under the SAME per-thread
    lock as run_agent. The lock serializes a resume against a concurrent
    user_message so they never drive the same LangGraph checkpoint at once (a
    double-click resume / race would otherwise corrupt the paused state)."""
    lock = _get_thread_run_lock(msg.thread_id)
    async with lock:
        await agent_runner.resume_agent(
            ctx.user_id,
            ctx.pool,
            msg.thread_id,
            msg.decisions,
            ctx.ws,
            interrupt_id=msg.interrupt_id,
        )


# ---------- session ----------


async def handle_list_sessions(ctx: WSCtx, msg: ListSessionsMsg) -> None:
    # store.* is synchronous sqlite3 — offload so it doesn't block the loop.
    sessions = await asyncio.to_thread(store.list_sessions, ctx.user_id)
    await send_json(ctx.ws, type="session_list", sessions=sessions)


async def handle_delete_session(ctx: WSCtx, msg: DeleteSessionMsg) -> None:
    def _work() -> list:
        store.delete_session(ctx.user_id, msg.thread_id)
        return store.list_sessions(ctx.user_id)

    sessions = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="session_list", sessions=sessions)


async def handle_delete_sessions(ctx: WSCtx, msg: DeleteSessionsMsg) -> None:
    # Bulk soft-delete in one transaction, then a SINGLE session_list push with
    # the final state. Avoids the per-session round-trip race where a mid-state
    # session_list re-added not-yet-deleted sessions on the client.
    def _work() -> list:
        store.delete_sessions(ctx.user_id, msg.thread_ids)
        return store.list_sessions(ctx.user_id)

    sessions = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="session_list", sessions=sessions)


async def _resolve_run_status(thread_id: str, msgs: list[dict]) -> tuple[str, dict | None]:
    """Authoritative run lifecycle for reconnect resume (W5D4 P0-B).

    Reads the persisted `run_lifecycle` row (DB-backed, survives restart) — no
    more inferring from the chat-history tail. Boot-time reconciliation already
    flipped any process-death `running` rows to `failed`, so a `running` we see
    here is genuinely in-flight in THIS process. As a last-resort defense against
    a task that died without marking, a `running` row older than the run ceiling
    is reported `stale` so the client stops spinning. No row → `idle`."""
    st = await run_state.load(thread_id)
    if st is None:
        return "idle", None
    if st["status"] == "running":
        # Defensive: a same-process run shows in the cache with a real monotonic
        # updated_at; if it's wall-clock-older than the ceiling, treat as stale.
        age = time.time() - st.get("updated_at", time.time())
        if age > agent_runner.RUN_TURN_TIMEOUT_S + 30:
            return "stale", {
                "code": "S11_INTERNAL_ERROR",
                "hint": "上次处理像是中断了,重试一下或换一条链接。",
                "actions": ["RETRY_SAME_URL", "RETRY_WITH_NEW_URL"],
                "request_id": "",
            }
    return st["status"], st["failure"]


async def handle_get_session_state(ctx: WSCtx, msg: GetSessionStateMsg) -> None:
    print(f"[请求] get_session_state thread={msg.thread_id}")

    def _work() -> tuple[list, dict | None]:
        store.ensure_session_exists(ctx.user_id, msg.thread_id)
        msgs = store.get_messages(ctx.user_id, msg.thread_id)
        canvas = canvas_data(msg.thread_id)
        return msgs, canvas

    msgs, canvas = await asyncio.to_thread(_work)
    run_status, failure = await _resolve_run_status(msg.thread_id, msgs)
    print(f"[请求] 返回 msgs={len(msgs)} canvas={canvas is not None} run_status={run_status}")
    await send_json(
        ctx.ws,
        type="session_state",
        thread_id=msg.thread_id,
        messages=msgs,
        canvas=canvas,
        run_status=run_status,
        failure=failure,
    )
    # W5D4 — replay this thread's analysis/rewrite so a reloaded finished
    # session shows its cards instead of an empty panel. analysis_returned /
    # rewrite_returned are the same frames the cascade tool pushes live, so the
    # frontend renders them through its existing handlers (zero UI change).
    await _replay_results(ctx, msg.thread_id)
    # P2 — if the run is paused at a review gate, re-push the approval card so a
    # reconnect (or reload) re-shows it instead of leaving the user stuck.
    if run_status == "awaiting_review":
        await _maybe_replay_review(ctx, msg.thread_id)


async def _maybe_replay_review(ctx: WSCtx, thread_id: str) -> None:
    """Reconnect replay of the pending review card. The review payload lives in the
    LangGraph checkpoint (single source of truth); pool the agent, read it via
    aget_state, and re-push `review_required`. Best-effort — never blocks
    session_state. If no interrupt is pending (already resumed), do nothing."""
    try:
        entry = await ctx.pool.get(ctx.user_id, thread_id)
        snap = await entry["agent"].aget_state(entry["config"])
        if snap.interrupts:
            intr = snap.interrupts[0]
            frame = agent_runner._build_review_frame(thread_id, intr.value, intr.id or "")
            await send_json(ctx.ws, **frame)
    except Exception as exc:  # best-effort; replay never blocks session_state
        print(f"[replay] review for thread={thread_id} failed: {exc}")


async def _replay_results(ctx: WSCtx, thread_id: str) -> None:
    """Re-push stored analysis_returned / rewrite_returned for a thread."""
    try:
        analysis_id, rewrite_id = await cascade_storage.load_pointers(
            ctx.user_id, thread_id
        )
    except Exception as exc:  # best-effort; replay never blocks session_state
        print(f"[replay] load_pointers failed thread={thread_id}: {exc}")
        return

    if analysis_id:
        try:
            contract = await cascade_storage.load_analysis(analysis_id)
            if contract is not None:
                await send_json(
                    ctx.ws,
                    type="analysis_returned",
                    thread_id=thread_id,
                    analysis=contract.model_dump(mode="json"),
                )
        except Exception as exc:
            print(f"[replay] analysis {analysis_id} failed: {exc}")

    if rewrite_id:
        try:
            result_json = await cascade_storage.load_rewrite_by_id(rewrite_id)
            if result_json:
                rewrite = json.loads(result_json)
                await send_json(
                    ctx.ws,
                    type="rewrite_returned",
                    thread_id=thread_id,
                    analysis_id=rewrite.get("analysis_id", analysis_id or ""),
                    rewrite=rewrite,
                )
        except Exception as exc:
            print(f"[replay] rewrite {rewrite_id} failed: {exc}")

        # 视频闭环:重放已生成的草稿图 / 逐镜视频 / 整片(都已落 /media 持久)。
        # 必须在 rewrite_returned 之后(前端先建好 rewriteShots,再被这些帧 patch)。
        try:
            for a in await cascade_storage.load_shot_assets(rewrite_id):
                if a.get("image_url"):
                    await send_json(
                        ctx.ws,
                        type="shot_first_frame_returned",
                        thread_id=thread_id,
                        rewrite_id=rewrite_id,
                        shot_index=a["shot_index"],
                        image_url=a["image_url"],
                    )
                if a.get("video_url"):
                    await send_json(
                        ctx.ws,
                        type="shot_video_returned",
                        thread_id=thread_id,
                        rewrite_id=rewrite_id,
                        shot_index=a["shot_index"],
                        video_url=a["video_url"],
                    )
            film_url = await cascade_storage.load_film(rewrite_id)
            if film_url:
                await send_json(
                    ctx.ws,
                    type="film_returned",
                    thread_id=thread_id,
                    rewrite_id=rewrite_id,
                    film_url=film_url,
                )
        except Exception as exc:
            print(f"[replay] shot assets {rewrite_id} failed: {exc}")


# ---------- canvas edges ----------
#
# Each handler bundles set_thread_id + mutation + canvas snapshot into one
# `asyncio.to_thread` call. set_thread_id is a ContextVar; to_thread copies the
# current context into the worker thread, so the set and the subsequent reads
# stay consistent within the same thread. Keeps synchronous sqlite3 off the
# event loop.


async def handle_reorder_edge(ctx: WSCtx, msg: ReorderEdgeMsg) -> None:
    def _work() -> dict | None:
        canvas_tools.set_thread_id(msg.thread_id)
        canvas_tools.reorder_edge(msg.edge_id, msg.direction)
        return canvas_data(msg.thread_id)

    snapshot = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)


async def handle_create_edge(ctx: WSCtx, msg: CreateEdgeMsg) -> None:
    def _work() -> tuple[dict, dict | None]:
        canvas_tools.set_thread_id(msg.thread_id)
        result = canvas_tools.create_canvas_edge(msg.source, msg.target)
        snapshot = canvas_data(msg.thread_id) if "error" not in result else None
        return result, snapshot

    result, snapshot = await asyncio.to_thread(_work)
    if "error" not in result:
        await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)
    else:
        print(f"[边] 创建失败: {result['error']}")


async def handle_delete_edge(ctx: WSCtx, msg: DeleteEdgeMsg) -> None:
    def _work() -> tuple[dict, dict | None]:
        canvas_tools.set_thread_id(msg.thread_id)
        result = canvas_tools.delete_canvas_edge(msg.edge_id)
        snapshot = canvas_data(msg.thread_id) if "deleted" in result else None
        return result, snapshot

    result, snapshot = await asyncio.to_thread(_work)
    if "deleted" in result:
        await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)
    else:
        print(f"[边] 删除失败: {result.get('error')}")


# ---------- canvas nodes ----------


async def handle_update_position(ctx: WSCtx, msg: UpdatePositionMsg) -> None:
    def _work() -> None:
        canvas_tools.set_thread_id(msg.thread_id)
        node = canvas_tools._load_node(msg.node_id)
        if node:
            node["x"] = msg.x
            node["y"] = msg.y
            canvas_tools._upsert_node(node)

    await asyncio.to_thread(_work)


async def handle_review_node(ctx: WSCtx, msg: ReviewNodeMsg) -> None:
    def _work() -> dict | None:
        canvas_tools.set_thread_id(msg.thread_id)
        if msg.action == "approve":
            canvas_tools.approve_node(msg.node_id)
        elif msg.action == "reject":
            canvas_tools.reject_node(msg.node_id, msg.feedback or "")
        return canvas_data(msg.thread_id)

    snapshot = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)


async def handle_execute_node(ctx: WSCtx, msg: ExecuteNodeMsg) -> None:
    provider = msg.image_gen_provider or IMAGE_GEN_PROVIDER
    print(
        f"[执行] execute_node node={msg.node_id} type={msg.node_type} provider={provider} prompt={msg.description[:50]}..."
    )

    # B3 — enqueue-time cost guard for the generation leg. Charged ONCE here
    # (retries go through schedule_generation_retry, not this path, so they don't
    # re-charge). user_id is server-derived from the authenticated ctx, NOT the
    # client payload — a caller can't rotate identity to evade the spend cap.
    # run_id keyed by thread_id (the run unit at this layer). Over-cap → refuse
    # before enqueue so the worker never spends. Only media nodes cost money.
    if msg.node_type in ("image", "video"):
        predicted = cost_guard.predict_generation_cost(
            msg.node_type,
            n_images=1 if msg.node_type == "image" else 0,
            video_seconds=float(msg.duration) if (msg.node_type == "video" and msg.duration) else 0.0,
        )
        try:
            await cost_guard.cost_guard(ctx.user_id, msg.thread_id, predicted)
        except HardFailure as exc:
            await send_json(
                ctx.ws,
                type="analysis_failed",
                thread_id=msg.thread_id,
                code=exc.code.value,
                hint=exc.hint or "生成预算超限,请稍后再试或联系我们。",
                actions=list(exc.actions) or ["REPORT"],
                request_id=exc.request_id,
                stage="generation",
            )
            return

    def _work() -> dict | None:
        canvas_tools.set_thread_id(msg.thread_id)
        result = canvas_tools.execute_node(msg.node_id, msg.node_type, msg.description, provider)
        if "_pending_submit" in result:
            # 媒体节点:入队让 worker 处理
            canvas_tools.enqueue_generation(msg.node_id)
            if msg.node_type == "video":
                canvas_tools._update_node_result(msg.node_id, {
                    "prompt": msg.description,
                    "duration": msg.duration if msg.duration is not None else 5,
                    "resolution": msg.resolution or "720p",
                    "generate_audio": msg.generate_audio if msg.generate_audio is not None else True,
                })
        return canvas_data(msg.thread_id)

    snapshot = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)


async def handle_regenerate_node(ctx: WSCtx, msg: RegenerateNodeMsg) -> None:
    """time-travel 回溯(P2 slice-2)— 重生节点:快照旧版 → 清 + 入队 → 标脏下游。
    媒体节点走与 execute_node 同一道 enqueue-time cost guard(server-derived user_id,
    不可绕);worker 重生时按边读父节点最新 result 作参考,下游自动反映新上游。"""

    def _load() -> dict | None:
        canvas_tools.set_thread_id(msg.thread_id)
        return canvas_tools._load_node(msg.node_id)

    node = await asyncio.to_thread(_load)
    if node is None:
        # 节点不存在:回推当前快照即可,不报错(可能已被删/陈旧点击)。
        snapshot = await asyncio.to_thread(canvas_data, msg.thread_id)
        await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)
        return

    node_type = node.get("type")
    # 媒体节点重生要花钱 → enqueue 前 cost guard(同 execute_node)。文字节点免费,跳过。
    if node_type in ("image", "video"):
        # 重生用节点已存的时长(video),没有就按 5s 估;图按 1 张。
        video_seconds = 0.0
        if node_type == "video":
            video_seconds = float((node.get("result") or {}).get("duration") or 5)
        predicted = cost_guard.predict_generation_cost(
            node_type,
            n_images=1 if node_type == "image" else 0,
            video_seconds=video_seconds,
        )
        try:
            await cost_guard.cost_guard(ctx.user_id, msg.thread_id, predicted)
        except HardFailure as exc:
            await send_json(
                ctx.ws,
                type="analysis_failed",
                thread_id=msg.thread_id,
                code=exc.code.value,
                hint=exc.hint or "生成预算超限,请稍后再试或联系我们。",
                actions=list(exc.actions) or ["REPORT"],
                request_id=exc.request_id,
                stage="generation",
            )
            return

    def _work() -> dict | None:
        canvas_tools.set_thread_id(msg.thread_id)
        canvas_tools.regenerate_node(msg.node_id)
        return canvas_data(msg.thread_id)

    snapshot = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)


async def handle_list_node_versions(ctx: WSCtx, msg: ListNodeVersionsMsg) -> None:
    """time-travel 回溯(P2 slice-2b)— 只读拉取节点的产物版本快照,回 node_versions_returned。
    user_id 走连接 auth 时设的 ContextVar(to_thread 复制上下文),不可由客户端伪造。"""

    def _work() -> list[dict]:
        canvas_tools.set_thread_id(msg.thread_id)
        return canvas_tools.list_versions(msg.node_id)

    versions = await asyncio.to_thread(_work)
    await send_json(
        ctx.ws,
        type="node_versions_returned",
        thread_id=msg.thread_id,
        node_id=msg.node_id,
        versions=versions,
    )


async def handle_restore_node_version(ctx: WSCtx, msg: RestoreNodeVersionMsg) -> None:
    """time-travel 回溯(P2 slice-2c)— 回滚节点到某旧版:快照当前 → 换回旧产物 → 标脏下游。
    回 canvas_updated(节点新产物 + 下游 needs_regen)+ node_versions_returned(列表已含刚
    归档的当前,免得 NodeVersionHistory 因 asset_status 没变而漏掉新版)。不调模型 → 无 cost guard。"""

    def _work() -> tuple[dict | None, list[dict]]:
        canvas_tools.set_thread_id(msg.thread_id)
        canvas_tools.restore_node_version(msg.node_id, msg.version_seq)
        return canvas_data(msg.thread_id), canvas_tools.list_versions(msg.node_id)

    snapshot, versions = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)
    await send_json(
        ctx.ws,
        type="node_versions_returned",
        thread_id=msg.thread_id,
        node_id=msg.node_id,
        versions=versions,
    )


async def handle_regenerate_script_node(ctx: WSCtx, msg: RegenerateScriptNodeMsg) -> None:
    """time-travel 回溯(P2 slice-2d)— 重生 script(策划书)节点:快照旧内容 + 标脏下游,
    再触发 Director 按 feedback 重写(脚本无生成 worker → 走 agent,不入生成队列)。

    回 canvas_updated(下游 needs_regen)+ node_versions_returned(含刚归档的旧内容);
    Director 异步 update_canvas_node 写新内容后,再经 agent 流 + canvas_updated 推回。"""
    # 与 user_message 同:审核闸门待决时拒绝(喂新输入会丢掉被拦的工具调用)。
    st = run_state.get(msg.thread_id)
    if st is not None and st.get("status") == "awaiting_review":
        await send_json(
            ctx.ws,
            type="error",
            code="review_pending",
            message="有一步生成在等你确认,先点「确认生成」或「先不生成」再继续。",
        )
        return

    def _work() -> tuple[dict | None, dict | None, list[dict]]:
        canvas_tools.set_thread_id(msg.thread_id)
        regenerated = canvas_tools.regenerate_script_node(msg.node_id)
        return regenerated, canvas_data(msg.thread_id), canvas_tools.list_versions(msg.node_id)

    regenerated, snapshot, versions = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)
    if regenerated is None:
        # 非 script / 无内容 —— 不是可重写脚本,不触发 Director。
        return
    await send_json(
        ctx.ws,
        type="node_versions_returned",
        thread_id=msg.thread_id,
        node_id=msg.node_id,
        versions=versions,
    )

    # 触发 Director 重写(异步,与 user_message 同一条 per-thread serialized agent 路径)。
    fb = (msg.feedback or "").strip()
    fb_clause = f"用户的修改反馈:{fb}" if fb else "参考当前分析与上游,产出一版更有钩子的策划书"
    instruction = (
        f"【重写策划书】{fb_clause}。请用 update_canvas_node 更新策划书节点 {msg.node_id} 的"
        f"完整内容(description=新的完整策划书 Markdown)。用户已在画布上点「重生」授权,"
        f"直接重写、不必再向用户确认。"
    )
    synth = UserMessageMsg(type="user_message", thread_id=msg.thread_id, content=instruction)
    asyncio.create_task(_run_agent_serialized(ctx, synth))


async def handle_seed_canvas(ctx: WSCtx, msg: SeedCanvasMsg) -> None:
    """canvas 统筹 P0 桥 — 「在画布上做我的版本」:在**空画布**上 seed 创作起点,让用户从爆点
    分析顺势进画布。带 analysis_summary 时先 seed「📊 这条为什么火」只读参考节点(confirmed,
    内容=分析摘要),再 seed「✍️ 我的策划书」创作锚(reviewing,空)并连一条边,用户进画布就
    看到「为什么火」的依据;不带摘要就只 seed 策划书节点。幂等:画布已有任何节点就不重复 seed。
    纯脚手架,不调模型、不触发 Director —— 用户给改写方向后既有锚点级联(director.md §2-6)接手。"""

    def _work() -> dict | None:
        canvas_tools.set_thread_id(msg.thread_id)
        if not canvas_tools._load_all_nodes():  # 空画布才 seed
            summary = (msg.analysis_summary or "").strip()
            parent_ids = None
            if summary:
                # 📊 爆点分析参考(confirmed,只读)—— 给用户看「为什么火」,也给 Director 当上下文。
                ref = canvas_tools.create_canvas_node("script", "📊 这条为什么火", description=summary)
                canvas_tools.update_canvas_node(ref["id"], node_status="confirmed", confirmed=True)
                parent_ids = [ref["id"]]
            # ✍️ 我的策划书 = 创作锚(reviewing,空,Director 把改写写进这里)。
            canvas_tools.create_canvas_node("script", "✍️ 我的策划书", description="", parent_ids=parent_ids)
        return canvas_data(msg.thread_id)

    snapshot = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)


async def handle_cancel_generation(ctx: WSCtx, msg: CancelGenerationMsg) -> None:
    """逐镜取消(P2 ③)— 取消一个在途的媒体生成。置 cancelled(worker 回写被取消守卫拦下)
    + asset_status 回 idle,回推 canvas_updated。不在途/节点不存在 → 回推当前快照即可。"""

    def _work() -> dict | None:
        canvas_tools.set_thread_id(msg.thread_id)
        canvas_tools.cancel_node_generation(msg.node_id)
        return canvas_data(msg.thread_id)

    snapshot = await asyncio.to_thread(_work)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)


async def handle_update_node_status(ctx: WSCtx, msg: UpdateNodeStatusMsg) -> None:
    print(f"[状态] update_node_status node={msg.node_id} → {msg.node_status}")

    def _work() -> tuple[dict | None, dict | None]:
        canvas_tools.set_thread_id(msg.thread_id)
        canvas_tools.update_canvas_node(msg.node_id, node_status=msg.node_status)
        updated = canvas_tools._load_node(msg.node_id)
        return canvas_data(msg.thread_id), updated

    snapshot, updated = await asyncio.to_thread(_work)
    print(f"[状态] 确认 node={msg.node_id} node_status={updated.get('node_status') if updated else 'NOT FOUND'}")
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=snapshot)


async def handle_optimize_prompt(ctx: WSCtx, msg: OptimizePromptMsg) -> None:
    print(f"[润色] optimize_prompt node={msg.node_id} feedback={msg.feedback[:50]}...")
    canvas_tools.set_thread_id(msg.thread_id)
    optimized = await agent_runner.optimize_prompt(msg.node_id, msg.prompt, msg.feedback)
    print(f"[润色] 完成 node={msg.node_id} optimized={optimized[:80]}...")
    await send_json(
        ctx.ws,
        type="prompt_optimized",
        thread_id=msg.thread_id,
        node_id=msg.node_id,
        optimized_prompt=optimized,
    )


# ---------- agent ----------


async def handle_user_message(ctx: WSCtx, msg: UserMessageMsg) -> None:
    print(f"[用户] thread={msg.thread_id} niche={msg.selected_niche} {msg.content[:80]}...")
    # P2 — refuse a new message while a review gate is pending on this thread.
    # Feeding fresh {messages:[...]} input to a graph paused at an interrupt
    # silently DISCARDS the pending gated tool call (and a later 确认生成 no-ops).
    # The frontend scrim already blocks this in the UI; this is defense-in-depth
    # for non-UI paths (a second tab, a queued/reconnect resend). Cache-only read
    # (sync, hot-path cheap): an awaiting_review thread is recent + in cache.
    st = run_state.get(msg.thread_id)
    if st is not None and st.get("status") == "awaiting_review":
        await send_json(
            ctx.ws,
            type="error",
            code="review_pending",
            message="有一步生成在等你确认,先点「确认生成」或「先不生成」再继续。",
        )
        return
    # 仅在用户带 niche 时记一条 telemetry — 让 /admin/events 能看到 WS 字段
    # 真的端到端打通了(不依赖 LLM 走到 rewrite 才能验证)。emit 失败不应阻塞
    # 用户消息流(telemetry 是 best-effort)。
    if msg.selected_niche is not None:
        try:
            await cascade_events.emit(
                EventName.NICHE_SELECTED,
                user_id=ctx.user_id,
                run_id=None,
                payload={"niche": msg.selected_niche, "thread_id": msg.thread_id},
            )
        except Exception as exc:
            print(f"[telemetry] niche_selected emit failed: {exc}")
    asyncio.create_task(_run_agent_serialized(ctx, msg))
    await send_json(ctx.ws, type="processing", thread_id=msg.thread_id)


async def handle_review_decision(ctx: WSCtx, msg: ReviewDecisionMsg) -> None:
    """P2 审核闸门 — 用户对暂停的生成做了 approve/edit/reject 决策 → resume graph。
    与 user_message 一样:后台 task 串行执行(同线程锁),立即回 processing。"""
    print(f"[审核] review_decision thread={msg.thread_id} decisions={len(msg.decisions)}")
    asyncio.create_task(_resume_agent_serialized(ctx, msg))
    await send_json(ctx.ws, type="processing", thread_id=msg.thread_id)


# ---------- registry ----------

HandlerFn = Callable[[WSCtx, Any], Awaitable[None]]

# (model class, handler) — ws_server dispatch 查这个表,先验证再调用 handler
HANDLERS: dict[str, tuple[type, HandlerFn]] = {
    "list_sessions": (ListSessionsMsg, handle_list_sessions),
    "delete_session": (DeleteSessionMsg, handle_delete_session),
    "delete_sessions": (DeleteSessionsMsg, handle_delete_sessions),
    "get_session_state": (GetSessionStateMsg, handle_get_session_state),
    "reorder_edge": (ReorderEdgeMsg, handle_reorder_edge),
    "create_edge": (CreateEdgeMsg, handle_create_edge),
    "delete_edge": (DeleteEdgeMsg, handle_delete_edge),
    "update_position": (UpdatePositionMsg, handle_update_position),
    "review_node": (ReviewNodeMsg, handle_review_node),
    "execute_node": (ExecuteNodeMsg, handle_execute_node),
    "update_node_status": (UpdateNodeStatusMsg, handle_update_node_status),
    "optimize_prompt": (OptimizePromptMsg, handle_optimize_prompt),
    "regenerate_node": (RegenerateNodeMsg, handle_regenerate_node),
    "list_node_versions": (ListNodeVersionsMsg, handle_list_node_versions),
    "restore_node_version": (RestoreNodeVersionMsg, handle_restore_node_version),
    "regenerate_script_node": (RegenerateScriptNodeMsg, handle_regenerate_script_node),
    "seed_canvas": (SeedCanvasMsg, handle_seed_canvas),
    "cancel_generation": (CancelGenerationMsg, handle_cancel_generation),
    "review_decision": (ReviewDecisionMsg, handle_review_decision),
    "user_message": (UserMessageMsg, handle_user_message),
}


# sanity-check:确保 HANDLERS 与 INBOUND_MODELS 的 non-auth 部分对齐
_expected_keys = set(INBOUND_MODELS) - {"auth"}
_handler_keys = set(HANDLERS)
assert _expected_keys == _handler_keys, (
    f"HANDLERS / INBOUND_MODELS drift: missing handlers={_expected_keys - _handler_keys}, "
    f"extra handlers={_handler_keys - _expected_keys}"
)
