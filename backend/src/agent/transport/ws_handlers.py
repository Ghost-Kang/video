"""WS inbound message handlers — 一个 type 一个 handler,HANDLERS dict 注册 (Pydantic model + handler fn) pair。

handler 签名:`async def handle_xxx(ctx: WSCtx, msg: XxxMsg) -> None`
- msg 已被 ws_server.dispatch 校验过,handler 拿到的是 typed Pydantic 实例
- 全部从 `ctx.ws` 发送响应,统一走 `send_json`

`auth` 由 ws_server 直接处理(它要拿 user_id 才能构造 ctx),不入 HANDLERS。
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from agent import store  # 通过 module 访问,方便 test monkeypatch
from agent.cascade import events as cascade_events  # module 访问,test 可 patch emit
from agent.cascade.event_names import EventName
from agent.config import IMAGE_GEN_PROVIDER
from agent.tools import canvas as canvas_tools
from agent.transport import agent_runner  # module 访问同理
from agent.transport.context import WSCtx, canvas_data, send_json
from agent.transport.ws_messages import (
    INBOUND_MODELS,
    CreateEdgeMsg,
    DeleteEdgeMsg,
    DeleteSessionMsg,
    ExecuteNodeMsg,
    GetSessionStateMsg,
    ListSessionsMsg,
    OptimizePromptMsg,
    ReorderEdgeMsg,
    ReviewNodeMsg,
    UpdateNodeStatusMsg,
    UpdatePositionMsg,
    UserMessageMsg,
)


# ---------- session ----------


async def handle_list_sessions(ctx: WSCtx, msg: ListSessionsMsg) -> None:
    sessions = store.list_sessions(ctx.user_id)
    await send_json(ctx.ws, type="session_list", sessions=sessions)


async def handle_delete_session(ctx: WSCtx, msg: DeleteSessionMsg) -> None:
    store.delete_session(ctx.user_id, msg.thread_id)
    sessions = store.list_sessions(ctx.user_id)
    await send_json(ctx.ws, type="session_list", sessions=sessions)


async def handle_get_session_state(ctx: WSCtx, msg: GetSessionStateMsg) -> None:
    store.ensure_session_exists(ctx.user_id, msg.thread_id)
    print(f"[请求] get_session_state thread={msg.thread_id}")
    msgs = store.get_messages(ctx.user_id, msg.thread_id)
    canvas = canvas_data(msg.thread_id)
    print(f"[请求] 返回 msgs={len(msgs)} canvas={canvas is not None}")
    await send_json(
        ctx.ws,
        type="session_state",
        thread_id=msg.thread_id,
        messages=msgs,
        canvas=canvas,
    )


# ---------- canvas edges ----------


async def handle_reorder_edge(ctx: WSCtx, msg: ReorderEdgeMsg) -> None:
    canvas_tools.set_thread_id(msg.thread_id)
    canvas_tools.reorder_edge(msg.edge_id, msg.direction)
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=canvas_data(msg.thread_id))


async def handle_create_edge(ctx: WSCtx, msg: CreateEdgeMsg) -> None:
    canvas_tools.set_thread_id(msg.thread_id)
    result = canvas_tools.create_canvas_edge(msg.source, msg.target)
    if "error" not in result:
        await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=canvas_data(msg.thread_id))
    else:
        print(f"[边] 创建失败: {result['error']}")


async def handle_delete_edge(ctx: WSCtx, msg: DeleteEdgeMsg) -> None:
    canvas_tools.set_thread_id(msg.thread_id)
    result = canvas_tools.delete_canvas_edge(msg.edge_id)
    if "deleted" in result:
        await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=canvas_data(msg.thread_id))
    else:
        print(f"[边] 删除失败: {result.get('error')}")


# ---------- canvas nodes ----------


async def handle_update_position(ctx: WSCtx, msg: UpdatePositionMsg) -> None:
    canvas_tools.set_thread_id(msg.thread_id)
    node = canvas_tools._load_node(msg.node_id)
    if node:
        node["x"] = msg.x
        node["y"] = msg.y
        canvas_tools._upsert_node(node)


async def handle_review_node(ctx: WSCtx, msg: ReviewNodeMsg) -> None:
    canvas_tools.set_thread_id(msg.thread_id)
    if msg.action == "approve":
        canvas_tools.approve_node(msg.node_id)
    elif msg.action == "reject":
        canvas_tools.reject_node(msg.node_id, msg.feedback or "")
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=canvas_data(msg.thread_id))


async def handle_execute_node(ctx: WSCtx, msg: ExecuteNodeMsg) -> None:
    provider = msg.image_gen_provider or IMAGE_GEN_PROVIDER
    print(
        f"[执行] execute_node node={msg.node_id} type={msg.node_type} provider={provider} prompt={msg.description[:50]}..."
    )
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

    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=canvas_data(msg.thread_id))


async def handle_update_node_status(ctx: WSCtx, msg: UpdateNodeStatusMsg) -> None:
    print(f"[状态] update_node_status node={msg.node_id} → {msg.node_status}")
    canvas_tools.set_thread_id(msg.thread_id)
    canvas_tools.update_canvas_node(msg.node_id, node_status=msg.node_status)
    updated = canvas_tools._load_node(msg.node_id)
    print(f"[状态] 确认 node={msg.node_id} node_status={updated.get('node_status') if updated else 'NOT FOUND'}")
    await send_json(ctx.ws, type="canvas_updated", thread_id=msg.thread_id, canvas=canvas_data(msg.thread_id))


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
    asyncio.create_task(
        agent_runner.run_agent(
            ctx.user_id,
            ctx.pool,
            msg.thread_id,
            msg.content,
            ctx.ws,
            selected_niche=msg.selected_niche,
        )
    )
    await send_json(ctx.ws, type="processing", thread_id=msg.thread_id)


# ---------- registry ----------

HandlerFn = Callable[[WSCtx, Any], Awaitable[None]]

# (model class, handler) — ws_server dispatch 查这个表,先验证再调用 handler
HANDLERS: dict[str, tuple[type, HandlerFn]] = {
    "list_sessions": (ListSessionsMsg, handle_list_sessions),
    "delete_session": (DeleteSessionMsg, handle_delete_session),
    "get_session_state": (GetSessionStateMsg, handle_get_session_state),
    "reorder_edge": (ReorderEdgeMsg, handle_reorder_edge),
    "create_edge": (CreateEdgeMsg, handle_create_edge),
    "delete_edge": (DeleteEdgeMsg, handle_delete_edge),
    "update_position": (UpdatePositionMsg, handle_update_position),
    "review_node": (ReviewNodeMsg, handle_review_node),
    "execute_node": (ExecuteNodeMsg, handle_execute_node),
    "update_node_status": (UpdateNodeStatusMsg, handle_update_node_status),
    "optimize_prompt": (OptimizePromptMsg, handle_optimize_prompt),
    "user_message": (UserMessageMsg, handle_user_message),
}


# sanity-check:确保 HANDLERS 与 INBOUND_MODELS 的 non-auth 部分对齐
_expected_keys = set(INBOUND_MODELS) - {"auth"}
_handler_keys = set(HANDLERS)
assert _expected_keys == _handler_keys, (
    f"HANDLERS / INBOUND_MODELS drift: missing handlers={_expected_keys - _handler_keys}, "
    f"extra handlers={_handler_keys - _expected_keys}"
)
