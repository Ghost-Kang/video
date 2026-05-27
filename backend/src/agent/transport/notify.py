"""WS 用户连接注册表 + 推送 helper。

worker 通过 `notify_user` 推送 canvas_updated。注册由 ws_server auth handler 写入。
"""

from __future__ import annotations

import asyncio
from typing import Any

from websockets.exceptions import ConnectionClosedOK

from agent.transport.context import canvas_data, send_json


# user_id → ws connection。auth handler 写入,handle finally 清理。
_ws_registry: dict[str, Any] = {}


def register(user_id: str, ws: Any) -> None:
    _ws_registry[user_id] = ws


def unregister(user_id: str) -> None:
    _ws_registry.pop(user_id, None)


def notify_user(user_id: str, thread_id: str) -> None:
    """向指定用户推送 canvas_updated。无连接则 log skip。"""
    ws = _ws_registry.get(user_id)
    if ws:
        asyncio.create_task(_safe_notify(ws, thread_id))
    else:
        print(f"[通知] user={user_id} 未连接,跳过推送 thread={thread_id}")


async def _safe_notify(ws: Any, thread_id: str) -> None:
    try:
        await send_json(ws, type="canvas_updated", thread_id=thread_id, canvas=canvas_data(thread_id))
    except (ConnectionClosedOK, Exception):
        pass
