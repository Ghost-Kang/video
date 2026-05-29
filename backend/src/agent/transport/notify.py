"""WS 用户连接注册表 + 推送 helper。

W5D4 P0-A — single send path for ALL out-of-band frames (run progress/results
AND worker canvas updates). The registry maps user_id → **set of live ws** and
`send_to_user` resolves the *current* live socket(s) at send time. This fixes
the dominant "卡 95%" cause: a run captured its ws at start (`RUN_CTX["ws"]`)
and kept pushing `analysis_progress`/`analysis_returned`/`rewrite_returned` to
that exact object for 20–50s; if the socket died and the browser reconnected on
a NEW ws, every later frame went to the dead socket and was silently swallowed.
Routing through the registry self-heals across reconnects — the same pattern the
worker path always used.

`send_to_user` accepts an optional `fallback_ws`: when the registry has no live
socket for the user, it tries that captured ws as a last resort (covers tests
that drive `run_agent` with a `FakeWebSocket` without registering it, and any
edge where registration lagged). Crucially, when a live registered socket
exists, the fallback is NOT used — so we never send to a dead captured ws while
a live one is available, which is the whole point of the fix.
"""

from __future__ import annotations

import asyncio
from typing import Any

from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from agent.transport.context import canvas_data, send_json


# user_id → set of live ws connections. auth handler adds; handle finally removes.
# A set (not a single value) so a reconnect that briefly overlaps the old socket,
# or a second tab, doesn't evict a live connection.
_ws_registry: dict[str, set[Any]] = {}


def register(user_id: str, ws: Any) -> None:
    _ws_registry.setdefault(user_id, set()).add(ws)


def unregister(user_id: str, ws: Any = None) -> None:
    """Remove a ws for a user. `ws=None` clears all (back-compat for callers that
    don't track the specific socket)."""
    if ws is None:
        _ws_registry.pop(user_id, None)
        return
    conns = _ws_registry.get(user_id)
    if conns is not None:
        conns.discard(ws)
        if not conns:
            _ws_registry.pop(user_id, None)


def _discard(user_id: str, ws: Any) -> None:
    conns = _ws_registry.get(user_id)
    if conns is not None:
        conns.discard(ws)
        if not conns:
            _ws_registry.pop(user_id, None)


async def send_to_user(user_id: str, payload: dict, *, fallback_ws: Any = None) -> int:
    """Push one frame to every live socket of `user_id`. Returns # delivered.

    `payload` is a dict including its `type` (e.g. {"type": "analysis_progress",
    ...}); it's forwarded to `send_json(ws, **payload)`. Dead sockets are dropped
    from the registry. If nothing was delivered and `fallback_ws` is given, it's
    tried once as a last resort (see module docstring)."""
    targets = list(_ws_registry.get(user_id) or ())
    delivered = 0
    for ws in targets:
        try:
            await send_json(ws, **payload)
            delivered += 1
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            _discard(user_id, ws)
        except Exception:
            # Non-connection error (e.g. malformed payload) — don't poison the
            # whole fan-out; skip this socket but keep it registered.
            pass
    if delivered == 0 and fallback_ws is not None:
        try:
            await send_json(fallback_ws, **payload)
            delivered = 1
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass
    return delivered


def notify_user(user_id: str, thread_id: str) -> None:
    """向指定用户推送 canvas_updated(worker 路径)。无连接则 log skip。"""
    if not _ws_registry.get(user_id):
        print(f"[通知] user={user_id} 未连接,跳过推送 thread={thread_id}")
        return
    payload = {"type": "canvas_updated", "thread_id": thread_id, "canvas": canvas_data(thread_id)}
    asyncio.create_task(send_to_user(user_id, payload))
