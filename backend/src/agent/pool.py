"""Agent 实例池 — LRU 淘汰，最多 N 个热实例。checkpoint 持久化到 SQLite。

W5D3 P0-2 fix: lifted from per-WS-connection scope to module-level singleton,
keyed by (user_id, thread_id) instead of thread_id alone. Reasons:

1. Per-connection pools leaked aiosqlite connections every reconnect (the old
   `ws_server.handle()` never called `pool.close()` in finally). Module-level
   pool with LRU eviction keeps file descriptor usage bounded regardless of
   reconnect churn.

2. Keying by thread_id alone meant the abstraction was unsafe if two users
   ever picked the same client-generated thread_id. Composite key makes the
   cross-user isolation explicit.

3. Reconnects from the same user-thread now hit the LRU hot path → instant
   agent reuse instead of cold checkpoint load.

The pool capacity grew from 5 (per-connection) to 50 (shared). Each entry
holds one aiosqlite connection to checkpoints.db. LRU eviction closes the
connection as part of `_pool.popitem()`.
"""

import aiosqlite
import asyncio
from collections import OrderedDict
from pathlib import Path
from typing import Tuple

from agent.main import create_director_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

_CHECKPOINT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "checkpoints.db"

# Composite key: (user_id, thread_id). Module-level state — single shared pool
# across all WS connections in this process.
PoolKey = Tuple[str, str]


class AgentPool:
    def __init__(self, max_size: int = 50):
        self._max = max_size
        self._pool: OrderedDict[PoolKey, dict] = OrderedDict()
        # Guard concurrent `get()` calls on the same key — without this, two
        # near-simultaneous user_message frames from the same (user, thread)
        # would both miss the cache and create two checkpoint connections,
        # leaking one. The lock is per-pool, not per-key, but `get()` is fast
        # so contention is negligible.
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        """Close all checkpoint connections held by the pool.

        Called by the test suite. In prod, the module-level pool lives for the
        process lifetime — graceful shutdown via the server's SIGTERM handler
        is responsible for draining + closing before exit.
        """
        async with self._lock:
            while self._pool:
                _, entry = self._pool.popitem(last=False)
                conn = entry.get("_conn")
                if conn:
                    await conn.close()

    async def get(self, user_id: str, thread_id: str) -> dict:
        """异步获取或创建 agent 实例，返回 {agent, checkpointer, config}。

        Composite-key cache: same (user_id, thread_id) reuses the entry, LRU
        moves to end. Different users with the same thread_id are isolated.
        """
        key: PoolKey = (user_id, thread_id)
        async with self._lock:
            if key in self._pool:
                self._pool.move_to_end(key)
                return self._pool[key]

            while len(self._pool) >= self._max:
                evicted_key, evicted_entry = self._pool.popitem(last=False)
                evicted_conn = evicted_entry.get("_conn")
                if evicted_conn:
                    await evicted_conn.close()
                print(f"[Pool] 淘汰 {evicted_key} (已满 {self._max})")

            conn = await aiosqlite.connect(str(_CHECKPOINT_DB))
            checkpointer = AsyncSqliteSaver(conn)
            await checkpointer.setup()
            agent = create_director_agent(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": thread_id}}

            entry = {"agent": agent, "checkpointer": checkpointer, "config": config, "_conn": conn}
            self._pool[key] = entry
            print(f"[Pool] 创建 {key} (当前 {len(self._pool)}/{self._max})")
            return entry


# Module-level singleton. Process lifetime; closed by SIGTERM handler.
SHARED_POOL = AgentPool(max_size=50)
