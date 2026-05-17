"""WebSocket 服务

单 WS 连接承载多个会话，agent 实例走 LRU 池管理。
"""

import asyncio
import json

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedOK

from agent.pool import AgentPool
from agent.store import get_messages, save_message
from agent.tools import canvas as canvas_tools

POOL_SIZE = 5


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return str(content)


def _canvas_data(thread_id: str) -> dict | None:
    canvas_tools.set_thread_id(thread_id)
    nodes = canvas_tools._load_all_nodes()
    edges = canvas_tools._load_all_edges()
    return {"nodes": nodes, "edges": edges} if nodes else None


def _update_position(thread_id: str, msg: dict):
    canvas_tools.set_thread_id(thread_id)
    nid = msg["node_id"]
    node = canvas_tools._load_node(nid)
    if node:
        node["x"] = msg["x"]
        node["y"] = msg["y"]
        canvas_tools._upsert_node(node)


async def _send(ws, **kwargs):
    await ws.send(json.dumps(kwargs, ensure_ascii=False))


async def _run_agent(pool: AgentPool, thread_id: str, user_content: str, ws):
    """后台执行 agent。"""
    try:
        save_message(thread_id, "user", user_content)
        entry = pool.get(thread_id)

        from langchain_core.messages import AIMessageChunk, ToolMessage

        full_reply = ""
        async for chunk in entry["agent"].astream(
            {"messages": [{"role": "user", "content": user_content}]},
            config=entry["config"],
            stream_mode="messages",
            version="v2",
        ):
            # V2 返回 StreamPart 字典: {"type": "messages", "data": (msg, metadata)}
            msg, meta = chunk["data"]

            # 工具调用事件
            if isinstance(msg, AIMessageChunk) and msg.tool_calls:
                for tc in msg.tool_calls:
                    await _send(ws, type="agent_stream", thread_id=thread_id,
                                event="tool_call", name=tc.get("name", ""), args=str(tc.get("args", {})))

            # token 文本（跳过 tool 消息和空内容）
            elif isinstance(msg, AIMessageChunk) and msg.content and not isinstance(msg, ToolMessage):
                token = _extract_text(msg.content)
                # 去重：只取新 token（避免某些 provider 的累积 chunk）
                if token and not full_reply.endswith(token):
                    full_reply += token
                    await _send(ws, type="agent_stream", thread_id=thread_id, event="text", content=token)

        reply = full_reply or "（未生成回复）"
        save_message(thread_id, "agent", reply)
    except Exception as e:
        reply = f"处理出错: {e}"
        save_message(thread_id, "agent", reply)
        print(f"[错误] thread={thread_id} {e}")

    # 自动执行已审核通过的图片节点
    await _auto_execute_pending(thread_id)
    # 轮询正在执行的图片任务
    await _poll_image_tasks(thread_id, ws)

    try:
        await _send(
            ws,
            type="agent_response",
            thread_id=thread_id,
            content=reply,
            canvas=_canvas_data(thread_id),
        )
    except (ConnectionClosedOK, Exception):
        pass


async def _auto_execute_pending(thread_id: str):
    """扫描 approved 但未执行的 image 节点，自动提交生图任务。"""
    from agent.tools.generation import submit_image

    canvas = _canvas_data(thread_id)
    if not canvas:
        return

    tasks = [
        (nid, node) for nid, node in canvas["nodes"].items()
        if node["type"] == "image"
        and node["status"] == "approved"
        and not (node.get("result") or {}).get("task_id")
    ]
    if not tasks:
        return

    canvas_tools.set_thread_id(thread_id)
    for nid, node in tasks:
        desc = node.get("description", "")
        print(f"[自动执行] node={nid} prompt={desc[:50]}...")
        submitted = submit_image(prompt=desc)
        if submitted.get("task_id"):
            canvas_tools.update_canvas_node(nid, status="executing")
            canvas_tools._update_node_result(nid, {"task_id": submitted["task_id"], "prompt": desc})
            print(f"[自动执行] node={nid} task={submitted['task_id']}")
        else:
            print(f"[自动执行失败] node={nid} {submitted.get('error')}")


async def _poll_image_tasks(thread_id: str, ws):
    """扫描画布中 executing 状态的 image 节点，后台轮询直到完成。"""
    from agent.tools.generation import poll_image

    canvas = _canvas_data(thread_id)
    if not canvas:
        return

    tasks = [
        (nid, node) for nid, node in canvas["nodes"].items()
        if node["type"] == "image" and node["status"] == "executing" and node.get("result", {}).get("task_id")
    ]
    if not tasks:
        return

    for nid, node in tasks:
        task_id = node["result"]["task_id"]
        print(f"[生图轮询] node={nid} task={task_id}")
        result = await poll_image(task_id)
        canvas_tools.set_thread_id(thread_id)
        if result.get("url"):
            # 统一走 canvas 工具更新，避免直接写文件导致竞态
            canvas_tools._update_node_result(nid, {"url": result["url"], "actual_time": result.get("actual_time", 0)})
            canvas_tools.update_canvas_node(nid, status="awaiting_review")
            print(f"[生图完成] node={nid} url={result['url'][:60]}...")
        else:
            canvas_tools.update_canvas_node(nid, status="failed")
            print(f"[生图失败] node={nid} {result.get('error')}")

    # 推送更新后的画布
    try:
        await _send(ws, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
    except (ConnectionClosedOK, Exception):
        pass


async def handle(websocket):
    pool = AgentPool(max_size=POOL_SIZE)
    print(f"[连接] 单 WS 连接已建立，pool 上限 {POOL_SIZE}")

    try:
        async for raw in websocket:
            msg = json.loads(raw)
            msg_type = msg.get("type")
            thread_id = msg.get("thread_id", "")

            if not thread_id:
                continue

            if msg_type == "update_position":
                _update_position(thread_id, msg)
                continue

            if msg_type == "review_node":
                action = msg.get("action", "")
                nid = msg.get("node_id", "")
                canvas_tools.set_thread_id(thread_id)
                if action == "approve":
                    canvas_tools.approve_node(nid)
                elif action == "reject":
                    canvas_tools.reject_node(nid, msg.get("feedback", ""))
                # 审核通过后自动执行 + 轮询
                await _auto_execute_pending(thread_id)
                await _poll_image_tasks(thread_id, websocket)
                await _send(
                    ws=websocket,
                    type="canvas_updated",
                    thread_id=thread_id,
                    canvas=_canvas_data(thread_id),
                )
                continue

            if msg_type == "get_session_state":
                print(f"[请求] get_session_state thread={thread_id}")
                msgs = get_messages(thread_id)
                print(f"[请求] 返回 msgs={len(msgs)} canvas={_canvas_data(thread_id) is not None}")
                await _send(
                    ws=websocket,
                    type="session_state",
                    thread_id=thread_id,
                    messages=msgs,
                    canvas=_canvas_data(thread_id),
                )
                continue

            if msg_type == "user_message":
                content = msg.get("content", "").strip()
                if not content:
                    continue
                print(f"[用户] thread={thread_id} {content[:80]}...")
                asyncio.create_task(_run_agent(pool, thread_id, content, websocket))
                await _send(ws=websocket, type="processing", thread_id=thread_id)
                continue

    except ConnectionClosedOK:
        pass

    print("[断开] WS 连接已关闭")


async def main(host="0.0.0.0", port=8765):
    print(f"OpenRHTV WebSocket 服务: ws://{host}:{port}")
    async with serve(handle, host, port):
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
