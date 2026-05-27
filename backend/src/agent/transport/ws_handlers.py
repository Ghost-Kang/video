"""WS inbound message handlers — 一个 type 一个 handler,HANDLERS dict 集中注册。

handler 签名:`async def handle_xxx(ctx: WSCtx, msg: dict) -> None`
- 不读 thread_id 的(list_sessions / delete_session)在 handler 内部处理
- 读 thread_id 的自带 `if not thread_id: return` 兜底
- 全部从 `ctx.ws` 发送响应,统一走 `send_json`

`auth` 由 ws_server 直接处理(它要拿 user_id 才能构造 ctx),不入 HANDLERS。

未知 msg_type 由 ws_server silently drop。
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from agent import store  # 通过 module 访问,方便 test monkeypatch
from agent.config import IMAGE_GEN_PROVIDER
from agent.tools import canvas as canvas_tools
from agent.transport import agent_runner  # module 访问同理
from agent.transport.context import WSCtx, canvas_data, send_json


# ---------- session ----------


async def handle_list_sessions(ctx: WSCtx, msg: dict) -> None:
    sessions = store.list_sessions(ctx.user_id)
    await send_json(ctx.ws, type="session_list", sessions=sessions)


async def handle_delete_session(ctx: WSCtx, msg: dict) -> None:
    target_thread = msg.get("thread_id", "")
    if not target_thread:
        return
    store.delete_session(ctx.user_id, target_thread)
    sessions = store.list_sessions(ctx.user_id)
    await send_json(ctx.ws, type="session_list", sessions=sessions)


async def handle_get_session_state(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    store.ensure_session_exists(ctx.user_id, thread_id)
    print(f"[请求] get_session_state thread={thread_id}")
    msgs = store.get_messages(ctx.user_id, thread_id)
    canvas = canvas_data(thread_id)
    print(f"[请求] 返回 msgs={len(msgs)} canvas={canvas is not None}")
    await send_json(
        ctx.ws,
        type="session_state",
        thread_id=thread_id,
        messages=msgs,
        canvas=canvas,
    )


# ---------- canvas edges ----------


async def handle_reorder_edge(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    eid = msg.get("edge_id", "")
    direction = msg.get("direction", "up")
    canvas_tools.set_thread_id(thread_id)
    canvas_tools.reorder_edge(eid, direction)
    await send_json(ctx.ws, type="canvas_updated", thread_id=thread_id, canvas=canvas_data(thread_id))


async def handle_create_edge(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    src = msg.get("source", "")
    tgt = msg.get("target", "")
    canvas_tools.set_thread_id(thread_id)
    result = canvas_tools.create_canvas_edge(src, tgt)
    if "error" not in result:
        await send_json(ctx.ws, type="canvas_updated", thread_id=thread_id, canvas=canvas_data(thread_id))
    else:
        print(f"[边] 创建失败: {result['error']}")


async def handle_delete_edge(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    eid = msg.get("edge_id", "")
    canvas_tools.set_thread_id(thread_id)
    result = canvas_tools.delete_canvas_edge(eid)
    if "deleted" in result:
        await send_json(ctx.ws, type="canvas_updated", thread_id=thread_id, canvas=canvas_data(thread_id))
    else:
        print(f"[边] 删除失败: {result.get('error')}")


# ---------- canvas nodes ----------


async def handle_update_position(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    canvas_tools.set_thread_id(thread_id)
    nid = msg["node_id"]
    node = canvas_tools._load_node(nid)
    if node:
        node["x"] = msg["x"]
        node["y"] = msg["y"]
        canvas_tools._upsert_node(node)


async def handle_review_node(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    action = msg.get("action", "")
    nid = msg.get("node_id", "")
    canvas_tools.set_thread_id(thread_id)
    if action == "approve":
        canvas_tools.approve_node(nid)
    elif action == "reject":
        canvas_tools.reject_node(nid, msg.get("feedback", ""))
    await send_json(ctx.ws, type="canvas_updated", thread_id=thread_id, canvas=canvas_data(thread_id))


async def handle_execute_node(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    nid = msg.get("node_id", "")
    node_type = msg.get("node_type", "")
    description = msg.get("description", "")
    provider = msg.get("image_gen_provider") or IMAGE_GEN_PROVIDER
    print(
        f"[执行] execute_node node={nid} type={node_type} provider={provider} prompt={description[:50]}..."
    )
    canvas_tools.set_thread_id(thread_id)

    result = canvas_tools.execute_node(nid, node_type, description, provider)
    if "_pending_submit" in result:
        # 媒体节点:入队让 worker 处理
        canvas_tools.enqueue_generation(nid)
        if node_type == "video":
            canvas_tools._update_node_result(nid, {
                "prompt": description,
                "duration": msg.get("duration", 5),
                "resolution": msg.get("resolution", "720p"),
                "generate_audio": msg.get("generate_audio", True),
            })

    await send_json(ctx.ws, type="canvas_updated", thread_id=thread_id, canvas=canvas_data(thread_id))


async def handle_update_node_status(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    nid = msg.get("node_id", "")
    node_status = msg.get("node_status", "reviewing")
    print(f"[状态] update_node_status node={nid} → {node_status}")
    canvas_tools.set_thread_id(thread_id)
    canvas_tools.update_canvas_node(nid, node_status=node_status)
    updated = canvas_tools._load_node(nid)
    print(f"[状态] 确认 node={nid} node_status={updated.get('node_status') if updated else 'NOT FOUND'}")
    await send_json(ctx.ws, type="canvas_updated", thread_id=thread_id, canvas=canvas_data(thread_id))


async def handle_optimize_prompt(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    nid = msg.get("node_id", "")
    prompt = msg.get("prompt", "")
    feedback = msg.get("feedback", "")
    print(f"[润色] optimize_prompt node={nid} feedback={feedback[:50]}...")
    canvas_tools.set_thread_id(thread_id)
    optimized = await agent_runner.optimize_prompt(nid, prompt, feedback)
    print(f"[润色] 完成 node={nid} optimized={optimized[:80]}...")
    await send_json(
        ctx.ws,
        type="prompt_optimized",
        thread_id=thread_id,
        node_id=nid,
        optimized_prompt=optimized,
    )


# ---------- agent ----------


async def handle_user_message(ctx: WSCtx, msg: dict) -> None:
    thread_id = msg.get("thread_id", "")
    if not thread_id:
        return
    content = msg.get("content", "").strip()
    if not content:
        return
    print(f"[用户] thread={thread_id} {content[:80]}...")
    asyncio.create_task(agent_runner.run_agent(ctx.user_id, ctx.pool, thread_id, content, ctx.ws))
    await send_json(ctx.ws, type="processing", thread_id=thread_id)


# ---------- registry ----------

HandlerFn = Callable[[WSCtx, dict], Awaitable[None]]

HANDLERS: dict[str, HandlerFn] = {
    "list_sessions": handle_list_sessions,
    "delete_session": handle_delete_session,
    "get_session_state": handle_get_session_state,
    "reorder_edge": handle_reorder_edge,
    "create_edge": handle_create_edge,
    "delete_edge": handle_delete_edge,
    "update_position": handle_update_position,
    "review_node": handle_review_node,
    "execute_node": handle_execute_node,
    "update_node_status": handle_update_node_status,
    "optimize_prompt": handle_optimize_prompt,
    "user_message": handle_user_message,
}
