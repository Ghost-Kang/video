"""Agent 实例池 — LRU 淘汰，最多 N 个热实例。checkpoint 持久化到 SQLite。"""

import aiosqlite
from collections import OrderedDict
from pathlib import Path

from agent.main import create_director_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

_CHECKPOINT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "checkpoints.db"


class AgentPool:
    def __init__(self, max_size: int = 5):
        self._max = max_size
        self._pool: OrderedDict[str, dict] = OrderedDict()

    async def get(self, thread_id: str) -> dict:
        """异步获取或创建 agent 实例，返回 {agent, checkpointer, config}。"""
        if thread_id in self._pool:
            self._pool.move_to_end(thread_id)
            return self._pool[thread_id]

        while len(self._pool) >= self._max:
            evicted = self._pool.popitem(last=False)
            # 关闭被淘汰的连接
            evicted_conn = evicted[1].get("_conn")
            if evicted_conn:
                await evicted_conn.close()
            print(f"[Pool] 淘汰 {evicted[0]} (已满 {self._max})")

        conn = await aiosqlite.connect(str(_CHECKPOINT_DB))
        checkpointer = AsyncSqliteSaver(conn)
        await checkpointer.setup()
        agent = create_director_agent(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        entry = {"agent": agent, "checkpointer": checkpointer, "config": config, "_conn": conn}
        self._pool[thread_id] = entry
        print(f"[Pool] 创建 {thread_id} (当前 {len(self._pool)}/{self._max})")
        return entry
