"""WS 连接级上下文 + 共用发送 / 快照 helper。

WSCtx 携带 connection-scoped 状态(user_id / ws / pool),per-message 数据走 msg dict。

W5D3 P0-3 — WS send serialization. The `websockets` library requires that
`send()` calls on the same connection be serialized; concurrent sends from
multiple async tasks (agent_stream + cascade tool pushes + worker notify +
analysis_progress) would either interleave frames or raise ConcurrencyError.
We hold a per-connection asyncio.Lock keyed by the ws object id in a
WeakValueDictionary so it's GC'd with the connection.
"""

from __future__ import annotations

import asyncio
import json
import weakref
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


# Per-WS-connection send lock. WeakValueDictionary so locks evaporate when
# the ws object is GC'd. Keyed by id(ws) since ws objects may not be hashable
# in all libraries.
_send_locks: "weakref.WeakValueDictionary[int, asyncio.Lock]" = weakref.WeakValueDictionary()
# Hold a strong reference to the Lock as long as the ws object lives, so the
# weak dict doesn't drop it between sends. We pin via a regular dict keyed by
# id(ws), and clean it up lazily in `_get_send_lock` if the ws is gone.
_lock_pins: dict[int, asyncio.Lock] = {}


def _get_send_lock(ws: Any) -> asyncio.Lock:
    """Return the per-ws send Lock, creating it on first use."""
    key = id(ws)
    lock = _send_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _send_locks[key] = lock
        _lock_pins[key] = lock
    return lock


def _release_send_lock(ws: Any) -> None:
    """Drop the pinned lock reference for a closed ws (best-effort housekeeping)."""
    _lock_pins.pop(id(ws), None)


async def send_json(ws, **kwargs) -> None:
    """向 ws 写一帧 JSON。所有 outbound 都走这里。

    Serialized per connection via _get_send_lock — prevents interleaved frames
    when agent_stream / analysis_progress / cascade tool pushes / worker
    notifications all try to send concurrently on the same ws.
    """
    payload = json.dumps(kwargs, ensure_ascii=False)
    async with _get_send_lock(ws):
        await ws.send(payload)


def canvas_data(thread_id: str, user_id: str | None = None) -> dict | None:
    """快照当前 thread 的 canvas (nodes + edges)。无节点返回 None。

    Claude-A2(2026-06-10 真用户事故修复):画布按 (user_id, thread_id) 双键存,
    user 此前只从 ContextVar 取 —— **worker 任务上下文里是默认值 "default"**,导致
    notify_user 推给真实用户的快照永远是空(canvas:null,前端静默丢)→ 用户付了钱
    UI 永挂「生成中」。跨上下文调用方(worker)必须显式传 user_id;不传时回退
    ContextVar(WS 连接路径在 auth 时已 set,行为不变)。
    """
    canvas_tools.set_thread_id(thread_id)
    nodes = canvas_tools._load_all_nodes(user_id=user_id, thread_id=thread_id)
    edges = canvas_tools._load_all_edges(user_id=user_id, thread_id=thread_id)
    return {"nodes": nodes, "edges": edges} if nodes else None
