"""WS 连接级上下文 + 共用发送 / 快照 helper。

WSCtx 携带 connection-scoped 状态(user_id / ws / pool),per-message 数据走 msg dict。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent.pool import AgentPool
from agent.tools import canvas as canvas_tools


@dataclass
class WSCtx:
    """单个 WS 连接的上下文。auth 通过后由 ws_server 创建,传给所有 handler。"""

    user_id: str
    ws: Any  # websockets ServerConnection;duck-typed 便于测试 FakeWebSocket
    pool: AgentPool


async def send_json(ws, **kwargs) -> None:
    """向 ws 写一帧 JSON。所有 outbound 都走这里。"""
    await ws.send(json.dumps(kwargs, ensure_ascii=False))


def canvas_data(thread_id: str) -> dict | None:
    """快照当前 thread 的 canvas (nodes + edges)。无节点返回 None。

    Note: 仍然走 canvas_tools.set_thread_id (ContextVar) — 见 Claude-A2 待办。
    """
    canvas_tools.set_thread_id(thread_id)
    nodes = canvas_tools._load_all_nodes()
    edges = canvas_tools._load_all_edges()
    return {"nodes": nodes, "edges": edges} if nodes else None
