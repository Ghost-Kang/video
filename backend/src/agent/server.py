"""WebSocket 服务

接收前端消息 → 运行 agent → 返回响应 + 画布 JSON。
"""

import asyncio
import json

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedOK

from agent.main import create_director_agent
from agent.tools import canvas as canvas_tools
from langgraph.checkpoint.memory import InMemorySaver


def _extract_text(content) -> str:
    """从 Gemini 返回的 content（可能是 list[dict] 或 str）中提取纯文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return str(content)


async def handle(websocket):
    thread_id = websocket.request.path.strip("/") or "demo-1"
    canvas_tools.set_thread_id(thread_id)
    print(f"[连接] thread={thread_id}")

    checkpointer = InMemorySaver()
    agent = create_director_agent(checkpointer=checkpointer)
    config_ = {"configurable": {"thread_id": thread_id}}

    try:
        async for raw in websocket:
            msg = json.loads(raw)
            if msg.get("type") != "user_message":
                continue

            content = msg.get("content", "").strip()
            if not content:
                continue

            print(f"[用户] {content[:80]}...")

            try:
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": content}]},
                    config=config_,
                )
                last_msg = result["messages"][-1]
                reply = _extract_text(last_msg.content)
            except Exception as e:
                reply = f"处理出错: {e}"
                print(f"[错误] {e}")

            # 读取画布 JSON
            canvas_file = canvas_tools._canvas_file()
            canvas_data = None
            if canvas_file.exists():
                canvas_data = json.loads(canvas_file.read_text(encoding="utf-8"))

            response = {
                "type": "agent_response",
                "content": reply,
                "canvas": canvas_data,
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))

    except ConnectionClosedOK:
        pass

    print(f"[断开] thread={thread_id}")


async def main(host="0.0.0.0", port=8765):
    print(f"OpenRHTV WebSocket 服务: ws://{host}:{port}")
    async with serve(handle, host, port):
        await asyncio.get_running_loop().create_future()  # 永久运行


if __name__ == "__main__":
    asyncio.run(main())
