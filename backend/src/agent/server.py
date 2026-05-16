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
    f = canvas_tools._canvas_file()
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def _update_position(thread_id: str, msg: dict):
    canvas_tools.set_thread_id(thread_id)
    f = canvas_tools._canvas_file()
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
        nid = msg["node_id"]
        if nid in data.get("nodes", {}):
            data["nodes"][nid]["x"] = msg["x"]
            data["nodes"][nid]["y"] = msg["y"]
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def _send(ws, **kwargs):
    await ws.send(json.dumps(kwargs, ensure_ascii=False))


async def _run_agent(pool: AgentPool, thread_id: str, user_content: str, ws):
    """后台执行 agent。"""
    try:
        save_message(thread_id, "user", user_content)
        entry = pool.get(thread_id)
        result = await entry["agent"].ainvoke(
            {"messages": [{"role": "user", "content": user_content}]},
            config=entry["config"],
        )
        last_msg = result["messages"][-1]
        reply = _extract_text(last_msg.content)
        save_message(thread_id, "agent", reply)
    except Exception as e:
        reply = f"处理出错: {e}"
        save_message(thread_id, "agent", reply)
        print(f"[错误] thread={thread_id} {e}")

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
