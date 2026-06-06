"""LangGraph agent 调度 — 把 user message 喂给 deepagent,流式回推。

ws_handlers 里 `user_message` handler 调度此函数;`optimize_prompt` 单独走 LLM
直调,绕开主 agent 流程。
"""

from __future__ import annotations

import asyncio
from typing import Optional

from langchain_core.messages import AIMessageChunk, ToolMessage
from langgraph.types import Command
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from agent.cascade.rewrite_service import Niche
from agent.llm_factory import get_chat_model
from agent.pool import AgentPool
from agent.store import save_message
from agent.tools import canvas as canvas_tools
from agent.transport import notify, run_state
from agent.transport.context import canvas_data
from agent.transport.runtime_ctx import RUN_CTX, set_run_ctx

# W5D4 — hard ceiling on a single Director turn (seconds). A hung upstream model
# call otherwise leaves the run task — and the thread run-state — pending forever
# (the "stuck at 95%" root cause). asyncio.timeout raises TimeoutError on expiry,
# which the handler below classifies as S7_UPSTREAM_TIMEOUT.
RUN_TURN_TIMEOUT_S = 180


def extract_text(content) -> str:
    """从 LangChain message content 中抽出纯文本(string 或 part list)。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return str(content)


# --- 审核闸门(LangGraph interrupt) — canvas 统筹 P2 slice-1 ---------------------
#
# When CANVAS_INTERRUPT_GATE is on, the Director's costly generation tools pause
# (HumanInTheLoopMiddleware → interrupt) BEFORE executing. We detect the pause via
# `aget_state(config).interrupts` after the stream, push a `review_required` frame,
# persist `awaiting_review`, and resume on the user's decision (resume_agent below).
#
# Explicit user clicks (CardStack 的 [generate_*] / [compose_film] 标记) mean the
# user ALREADY consented — auto-approve them so the gate never double-confirms a
# button press; only *autonomous* generation surfaces a review.

# Markers a frontend control prepends when the user explicitly clicks 生成/合成.
# Match on lstrip().startswith so a selected_niche prefix never hides them (the
# niche prefix is only added for onboarding turns, which are never gen markers).
_EXPLICIT_GEN_MARKERS = (
    "[generate_first_frame:",
    "[generate_shot_video:",
    "[compose_film]",
)
# Safety bound on auto-approve gate cycles within one explicit-click turn — stops a
# runaway agent that keeps proposing gated tools from looping forever.
_MAX_AUTO_RESUMES = 12


def _is_explicit_generation(content: str) -> bool:
    s = (content or "").lstrip()
    return any(s.startswith(m) for m in _EXPLICIT_GEN_MARKERS)


def _review_label(name: str, args: dict) -> str:
    """Friendly Chinese label for a gated tool call (shown on the review card).

    Cost copy mirrors the cascade tool docstrings (PREDICT_* constants); kept here
    so the user sees what they're approving without the frontend hardcoding它。"""
    shot = args.get("shot_index")
    if name == "cascade_generate_first_frame":
        return f"生成镜头 {shot} 的草稿图（约 ¥1.5）" if shot is not None else "生成草稿图（约 ¥1.5）"
    if name == "cascade_generate_shot_video":
        return f"把镜头 {shot} 生成视频（约 ¥1.5）" if shot is not None else "生成镜头视频（约 ¥1.5）"
    if name == "cascade_compose_film":
        return "合成整片（免费）"
    return f"执行 {name}"


def _build_review_frame(thread_id: str, hitl: dict, interrupt_id: str = "") -> dict:
    """HITLRequest(action_requests + review_configs)→ review_required WS 帧。

    One `review` per gated tool call, IN ORDER — the frontend builds its
    `decisions` array in the same order, and HumanInTheLoopMiddleware requires
    len(decisions) == #gated calls.

    `interrupt_id` binds this review round to its LangGraph interrupt. The frontend
    echoes it back in review_decision; resume_agent only applies a decision when it
    matches the currently-pending interrupt — so a stale/duplicate decision for an
    already-resolved gate can't be applied to the NEXT chained gate (review #3)."""
    action_requests = hitl.get("action_requests", []) or []
    review_configs = hitl.get("review_configs", []) or []
    allowed_by_name = {
        rc.get("action_name"): rc.get("allowed_decisions", []) for rc in review_configs
    }
    reviews = []
    for ar in action_requests:
        name = ar.get("name", "")
        args = ar.get("args", {}) or {}
        reviews.append({
            "tool": name,
            "label": _review_label(name, args),
            "args": args,
            "allowed_decisions": allowed_by_name.get(name) or ["approve", "reject"],
        })
    headline = reviews[0]["label"] if len(reviews) == 1 else f"导演想执行 {len(reviews)} 步生成"
    return {
        "type": "review_required",
        "thread_id": thread_id,
        "reviews": reviews,
        "summary": f"待你确认：{headline}",
        "interrupt_id": interrupt_id,
    }


async def _stream_once(agent, agent_input, config, user_id: str, thread_id: str, ws) -> str:
    """One astream pass (initial input OR Command resume). Pushes agent_stream
    frames, returns the text accumulated in THIS pass (caller sums across passes)."""
    full = ""
    async for chunk in agent.astream(
        agent_input, config=config, stream_mode="messages", version="v2",
    ):
        msg, meta = chunk["data"]

        if isinstance(msg, AIMessageChunk) and msg.tool_calls:
            for tc in msg.tool_calls:
                await notify.send_to_user(
                    user_id,
                    {
                        "type": "agent_stream",
                        "thread_id": thread_id,
                        "event": "tool_call",
                        "name": tc.get("name", ""),
                        "args": str(tc.get("args", {})),
                    },
                    fallback_ws=ws,
                )

        elif isinstance(msg, AIMessageChunk) and msg.content and not isinstance(msg, ToolMessage):
            token = extract_text(msg.content)
            if token and not full.endswith(token):
                full += token
                await notify.send_to_user(
                    user_id,
                    {"type": "agent_stream", "thread_id": thread_id, "event": "text", "content": token},
                    fallback_ws=ws,
                )
    return full


async def _drive_turn(
    agent, initial_input, config, user_id: str, thread_id: str, ws, *, auto_approve: bool
) -> tuple[str, Optional[dict]]:
    """Drive a graph turn through any interrupt gate(s).

    Returns (full_reply, pending_review):
    - pending_review None → the turn ran to completion (no gate, or flag off).
    - pending_review dict → the graph is PAUSED at an autonomous gate; the dict is
      the `review_required` frame body to push. The caller persists awaiting_review
      and returns without marking done.

    auto_approve=True (explicit user-click turn) → gates auto-approve and never
    surface; False → the first autonomous gate pauses for human review."""
    full_reply = ""
    agent_input = initial_input
    for _ in range(_MAX_AUTO_RESUMES + 1):
        full_reply += await _stream_once(agent, agent_input, config, user_id, thread_id, ws)
        snap = await agent.aget_state(config)
        if not snap.interrupts:
            return full_reply, None  # turn complete
        intr = snap.interrupts[0]
        if not auto_approve:
            return full_reply, _build_review_frame(thread_id, intr.value, intr.id or "")
        # explicit user click → approve the gate(s) without a human round-trip.
        n = len(intr.value.get("action_requests", []) or []) or 1
        agent_input = Command(resume={"decisions": [{"type": "approve"}] * n})
    # Exhausted the auto-resume budget — a runaway gate loop. Surface the latest
    # gate for human review rather than spin forever.
    snap = await agent.aget_state(config)
    if snap.interrupts:
        intr = snap.interrupts[0]
        return full_reply, _build_review_frame(thread_id, intr.value, intr.id or "")
    return full_reply, None


async def _handle_run_exception(e: Exception, user_id: str, thread_id: str, ws, *, site: str) -> None:
    """Classify + record + surface a terminal turn failure (shared by run_agent /
    resume_agent). W5D3/W5D4 invariants preserved verbatim:

    - Don't leak the raw exception into the WS push or the persisted chat line.
    - mark_failed so a reconnecting client (get_session_state) can replay it — the
      live analysis_failed frame often never lands (the dying WS is usually what
      triggered the failure).
    - Full traceback → events.db (observability), best-effort.
    """
    print(f"[错误] thread={thread_id} {e}")
    import traceback as _tb
    from agent.cascade.event_names import EventName as _EN
    from agent.cascade.events import emit as _emit
    from agent.cascade.failures import HardFailure as _HF, FailureCode as _FC, RECOVERY_HINTS as _HINTS, RECOVERY_ACTIONS as _ACTIONS

    # Compute the sanitized user-facing hint from the failure taxonomy.
    if isinstance(e, _HF):
        code_val = e.code.value
        hint_val = e.hint
        actions_val = e.actions
        request_id_val = e.request_id
    else:
        if type(e).__name__ == "TimeoutError" or "timeout" in str(e).lower():
            code_val = _FC.S7_UPSTREAM_TIMEOUT.value
        elif isinstance(e, (ConnectionError, OSError)) or "refus" in str(e).lower() or "rate" in str(e).lower():
            code_val = _FC.S8_UPSTREAM_REFUSED.value
        else:
            # Unexpected internal error (programming bug / unclassified) — don't
            # mislabel our own bug as "upstream refused". Full traceback is
            # captured in the uncaught_exception event below.
            code_val = _FC.S11_INTERNAL_ERROR.value
        hint_val = _HINTS.get(code_val, "处理出错,请重试或换一条链接。")
        actions_val = _ACTIONS.get(code_val, ["REPORT"])
        request_id_val = ""

    await run_state.mark_failed(thread_id, {
        "code": code_val,
        "hint": hint_val or "处理出错,请重试",
        "actions": actions_val,
        "request_id": request_id_val,
    })

    # Persist sanitized hint (raw traceback still lands in events.db below).
    await asyncio.to_thread(
        save_message, user_id, thread_id, "agent", hint_val or "处理出错,请重试"
    )

    # W5D2 observability — persist the full traceback to events.db so
    # /admin/events can surface it. Best-effort; observability errors
    # never swallow the real error.
    try:
        await _emit(
            _EN.UNCAUGHT_EXCEPTION,
            user_id=user_id,
            run_id=None,
            payload={
                "site": site,
                "exc_type": type(e).__name__,
                "message": str(e)[:500],
                "traceback": _tb.format_exc()[:4000],
                "thread_id": thread_id,
            },
        )
    except Exception:
        pass

    # Push structured analysis_failed WS frame so frontend ChatPanel flips into
    # `failed` state directly. W5D4 P0-A — via live registry so a reconnect during
    # the failing run still receives it.
    try:
        await notify.send_to_user(
            user_id,
            {
                "type": "analysis_failed",
                "thread_id": thread_id,
                "code": code_val,
                "hint": hint_val,
                "actions": actions_val,
                "request_id": request_id_val,
                "stage": "analysis",
            },
            fallback_ws=ws,
        )
    except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
        pass


async def _emit_todos(agent, config, user_id: str, thread_id: str, ws) -> None:
    """write_todos → 画布进度(P2 ③):读 Director agent state 的 todos,推 `todos_updated`
    给前端进度条。Director 用 deepagents 自带的 `write_todos`(TodoListMiddleware)规划多步
    创作(策划书→角色→场景→宫格→视频→合成),todos 存在 LangGraph state["todos"](每项
    {content, status: pending|in_progress|completed})。best-effort:读 state / 推帧失败都不挡主
    流程;todos 空(本轮没规划)不推,避免清掉前端已显示的进度。"""
    try:
        state = await agent.aget_state(config)
        todos = (getattr(state, "values", None) or {}).get("todos") or []
    except Exception:  # pragma: no cover - defensive
        return
    if not todos:
        return
    try:
        await notify.send_to_user(
            user_id,
            {"type": "todos_updated", "thread_id": thread_id, "todos": todos},
            fallback_ws=ws,
        )
    except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
        pass


async def run_agent(
    user_id: str,
    pool: AgentPool,
    thread_id: str,
    user_content: str,
    ws,
    selected_niche: Optional[Niche] = None,
) -> None:
    """后台执行 agent。出错时推 analysis_failed + canvas_updated 而非 raw exception。

    `selected_niche` 来自前端 onboarding 选择;非 None 时,我们在 user content
    最前面注入一行 `[selected_niche: <id>]` 标记,Director prompt 已经知道如何
    解析这个标记并跳过 "你想选哪个赛道?" 的追问。保留原文给画布消息历史,
    所以 store 里仍存原始 user_content,标记只进 agent stream。
    """
    # W5D3 — defensive ContextVar cleanup. PEP 567 + asyncio.create_task each
    # snapshot the parent Context, so two concurrent run_agent tasks already
    # see isolated RUN_CTX values without this reset. The reset is hygiene
    # (avoids holding the ws reference for one extra GC cycle), not concurrency
    # safety. We capture the token before try so it's in scope for finally.
    # Per-run cost cap needs a real run_id. mark_running bumps + returns the
    # run_seq (run_state.py); mint run_id = f"{thread_id}#{run_seq}" and store it
    # on the run ctx so every tool descendant (cost_guard + GENERATION_COST emit)
    # attributes spend to THIS turn. Until 2026-06-06 run_id was hardcoded None →
    # _run_cost(None)≈0 → the ¥/run cap was a silent no-op (audit #1-7 根因 A).
    # mark_running must run BEFORE set_run_ctx — the ctx dict is frozen at set time.
    run_seq = await run_state.mark_running(user_id, thread_id)  # W5D4 P0-B — persisted lifecycle
    _run_ctx = {
        "user_id": user_id,
        "thread_id": thread_id,
        "ws": ws,
        "run_id": f"{thread_id}#{run_seq}",
        "tool_failure": None,  # W5D4 B5 — a tool that catches HardFailure sets this
    }
    _ctx_token = set_run_ctx(_run_ctx)
    reply = ""
    failed = False  # W5D3 CR-P1: explicit flag replaces magic-string sentinel.
    awaiting_review = False  # P2 — graph paused at an autonomous review gate.
    entry = None  # set after pool.get; guarded at the bottom for the todos emit.
    try:
        # agent 的 tool call 通过 ContextVar 读写正确的用户/会话数据
        canvas_tools.set_user_id(user_id)
        canvas_tools.set_thread_id(thread_id)
        await asyncio.to_thread(save_message, user_id, thread_id, "user", user_content)
        entry = await pool.get(user_id, thread_id)

        # 注入 niche 标记 — 不污染存储,只在喂给 LLM 的 turn 加 prefix。
        agent_input_content = (
            f"[selected_niche: {selected_niche}]\n\n{user_content}"
            if selected_niche
            else user_content
        )

        # W5D4 — bound the whole streamed turn. If the upstream model stalls,
        # asyncio.timeout fires TimeoutError instead of hanging this task (and
        # the thread's run-state) indefinitely; the except below classifies it
        # as S7_UPSTREAM_TIMEOUT and pushes a recoverable failure.
        # P2 — _drive_turn streams + walks any interrupt gate. Explicit 生成 clicks
        # auto-approve (user already consented); autonomous generation pauses.
        async with asyncio.timeout(RUN_TURN_TIMEOUT_S):
            full_reply, pending_review = await _drive_turn(
                entry["agent"],
                {"messages": [{"role": "user", "content": agent_input_content}]},
                entry["config"],
                user_id,
                thread_id,
                ws,
                auto_approve=_is_explicit_generation(user_content),
            )

        # W5D4 B5 — a non-gated tool may have caught a HardFailure, pushed
        # analysis_failed, set tool_failure on the run ctx, and returned an error
        # dict to the LLM (the stream then ends normally). That failure is TERMINAL
        # and WINS over a pending review: marking awaiting_review would clear the
        # failure payload (mark_awaiting_review sets failure=NULL) and a reconnect
        # would replay a review card for a turn whose earlier stage actually failed
        # (review finding #1). So check tool_failure FIRST, before the review gate.
        tool_failure = _run_ctx.get("tool_failure")
        if tool_failure is not None:
            failed = True  # bottom pushes canvas_updated, not agent_response
            reply = full_reply or "（未生成回复）"
            await asyncio.to_thread(save_message, user_id, thread_id, "agent", reply)
            await run_state.mark_failed(thread_id, tool_failure)
        elif pending_review is not None:
            # Graph paused at an autonomous review gate. Persist awaiting_review +
            # push the review card; do NOT mark done — the turn resumes on the
            # user's decision (resume_agent). reconnect replays the card.
            awaiting_review = True
            reply = full_reply or "（待你确认后继续）"
            await asyncio.to_thread(save_message, user_id, thread_id, "agent", reply)
            await run_state.mark_awaiting_review(thread_id)
            await notify.send_to_user(user_id, pending_review, fallback_ws=ws)
        else:
            reply = full_reply or "（未生成回复）"
            await asyncio.to_thread(save_message, user_id, thread_id, "agent", reply)
            await run_state.mark_done(thread_id)  # terminal success, reconnect-visible
    except Exception as e:
        failed = True
        await _handle_run_exception(e, user_id, thread_id, ws, site="agent_runner.run_agent")
    finally:
        # Defensive cleanup (see top-of-function note about ContextVar semantics).
        try:
            RUN_CTX.reset(_ctx_token)
        except (ValueError, LookupError):
            pass

    # W5D3 CR-P1 — explicit failed flag replaces the magic-string sentinel.
    # When the agent failed, frontend already got `analysis_failed`; we still
    # push canvas snapshot to keep canvas/anchor state consistent, then return
    # without sending `agent_response` (which would carry the failure hint
    # again and confuse the chat history). awaiting_review is the same: the
    # review card was already pushed, so we only sync canvas (no agent_response,
    # which would read as a finished turn).
    # Canvas snapshot is synchronous sqlite3 — read it off the event loop.
    snapshot = await asyncio.to_thread(canvas_data, thread_id)
    if failed or awaiting_review:
        try:
            await notify.send_to_user(
                user_id,
                {"type": "canvas_updated", "thread_id": thread_id, "canvas": snapshot},
                fallback_ws=ws,
            )
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass
    else:
        try:
            await notify.send_to_user(
                user_id,
                {"type": "agent_response", "thread_id": thread_id, "content": reply, "canvas": snapshot},
                fallback_ws=ws,
            )
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass

    # write_todos → 画布进度(P2 ③):本轮结束推 Director 的规划 todos(若有)。
    if entry is not None:
        await _emit_todos(entry["agent"], entry["config"], user_id, thread_id, ws)


async def resume_agent(
    user_id: str,
    pool: AgentPool,
    thread_id: str,
    decisions: list[dict],
    ws,
    interrupt_id: str = "",
) -> None:
    """Resume a paused (awaiting-review) Director turn with the human decisions.

    `decisions`: HITL Decision dicts (approve/edit/reject), IN THE SAME ORDER as the
    `review_required.reviews` — HumanInTheLoopMiddleware requires the count to match
    the #gated tool calls. Mirrors run_agent's ctx / lifecycle / failure handling
    but feeds Command(resume=...) and never auto-approves (a resume may hit the NEXT
    gate → pause again for review).

    `interrupt_id`: the review round this decision was made for (review #3 fix). If
    given and it does NOT match the currently-pending interrupt, the decision is
    STALE (its gate was already resolved and a different gate is now pending) — we
    drop it and re-push the current review rather than applying it to the wrong
    tool calls. Empty = legacy/no-binding → resume whatever's pending."""
    # Real run_id for the per-run cost cap (see run_agent). A resume mints a fresh
    # run_seq; for an interrupt-gated generation both the cost_guard check and the
    # GENERATION_COST emit run inside THIS resumed frame, so they share this id.
    run_seq = await run_state.mark_running(user_id, thread_id)  # back to running while resuming
    _run_ctx = {
        "user_id": user_id,
        "thread_id": thread_id,
        "ws": ws,
        "run_id": f"{thread_id}#{run_seq}",
        "tool_failure": None,
    }
    _ctx_token = set_run_ctx(_run_ctx)
    reply = ""
    failed = False
    awaiting_review = False
    entry = None  # set after pool.get; guarded at the bottom for the todos emit.
    try:
        canvas_tools.set_user_id(user_id)
        canvas_tools.set_thread_id(thread_id)
        entry = await pool.get(user_id, thread_id)

        # Guard against a double-click / stale resume: only resume if a gate is
        # actually pending. Without this, astream(Command(resume=...)) on a thread
        # with no interrupt re-runs the last user turn from the checkpoint.
        snap = await entry["agent"].aget_state(entry["config"])
        if not snap.interrupts:
            await run_state.mark_done(thread_id)
            snapshot = await asyncio.to_thread(canvas_data, thread_id)
            try:
                await notify.send_to_user(
                    user_id,
                    {"type": "canvas_updated", "thread_id": thread_id, "canvas": snapshot},
                    fallback_ws=ws,
                )
            except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
                pass
            return

        # review #3 — stale-decision guard. A pending gate exists, but if this
        # decision was made for a DIFFERENT (already-resolved) gate, applying it
        # here would approve/reject the wrong tool calls. Re-push the current
        # review and drop the stale decision; keep the thread awaiting_review.
        current_id = snap.interrupts[0].id or ""
        if interrupt_id and current_id and interrupt_id != current_id:
            await run_state.mark_awaiting_review(thread_id)
            try:
                await notify.send_to_user(
                    user_id,
                    _build_review_frame(thread_id, snap.interrupts[0].value, current_id),
                    fallback_ws=ws,
                )
            except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
                pass
            return

        async with asyncio.timeout(RUN_TURN_TIMEOUT_S):
            full_reply, pending_review = await _drive_turn(
                entry["agent"],
                Command(resume={"decisions": decisions}),
                entry["config"],
                user_id,
                thread_id,
                ws,
                auto_approve=False,
            )

        if pending_review is not None:
            awaiting_review = True
            reply = full_reply or "（待你确认后继续）"
            await asyncio.to_thread(save_message, user_id, thread_id, "agent", reply)
            await run_state.mark_awaiting_review(thread_id)
            await notify.send_to_user(user_id, pending_review, fallback_ws=ws)
        else:
            reply = full_reply or "（已按你的选择继续）"
            await asyncio.to_thread(save_message, user_id, thread_id, "agent", reply)
            tool_failure = _run_ctx.get("tool_failure")
            if tool_failure is not None:
                await run_state.mark_failed(thread_id, tool_failure)
            else:
                await run_state.mark_done(thread_id)
    except Exception as e:
        failed = True
        await _handle_run_exception(e, user_id, thread_id, ws, site="agent_runner.resume_agent")
    finally:
        try:
            RUN_CTX.reset(_ctx_token)
        except (ValueError, LookupError):
            pass

    snapshot = await asyncio.to_thread(canvas_data, thread_id)
    if failed or awaiting_review:
        try:
            await notify.send_to_user(
                user_id,
                {"type": "canvas_updated", "thread_id": thread_id, "canvas": snapshot},
                fallback_ws=ws,
            )
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass
    else:
        try:
            await notify.send_to_user(
                user_id,
                {"type": "agent_response", "thread_id": thread_id, "content": reply, "canvas": snapshot},
                fallback_ws=ws,
            )
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass

    # write_todos → 画布进度(P2 ③):审核续跑(级联推进)后也同步规划 todos。
    if entry is not None:
        await _emit_todos(entry["agent"], entry["config"], user_id, thread_id, ws)


async def optimize_prompt(node_id: str, prompt: str, feedback: str) -> str:
    """LLM 优化图片 prompt,不经过主 agent 流程。同步写回 node.description。"""
    model = get_chat_model()
    system = "你是一位专业的 AI 绘画提示词优化师。根据用户的反馈优化提示词，只返回优化后的提示词，不要加任何解释或前缀。"
    user = f"当前提示词：\n{prompt}\n\n用户反馈：\n{feedback}\n\n请输出优化后的提示词："
    # await ainvoke — `.invoke()` is a blocking network call; on the asyncio
    # event loop it would stall ALL websocket/HTTP handling for the duration.
    result = await model.ainvoke(
        [{"role": "system", "content": system}, {"role": "user", "content": user}]
    )
    optimized = result.content if hasattr(result, "content") else str(result)

    # Canvas DAO is synchronous sqlite3 — offload so the load/upsert doesn't
    # block the event loop either.
    def _persist() -> None:
        node = canvas_tools._load_node(node_id)
        if node:
            node["description"] = optimized
            canvas_tools._upsert_node(node)
            print(f"[润色] 已更新节点 description node={node_id}")

    await asyncio.to_thread(_persist)
    return optimized
