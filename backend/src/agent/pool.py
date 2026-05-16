"""Agent 实例池 — LRU 淘汰，最多 N 个热实例"""

from collections import OrderedDict

from agent.main import create_director_agent
from langgraph.checkpoint.memory import InMemorySaver


class AgentPool:
    def __init__(self, max_size: int = 5):
        self._max = max_size
        self._pool: OrderedDict[str, dict] = OrderedDict()

    def get(self, thread_id: str) -> dict:
        """获取或创建 agent 实例，返回 {agent, checkpointer, config}。"""
        if thread_id in self._pool:
            self._pool.move_to_end(thread_id)
            return self._pool[thread_id]

        # 超限则淘汰最久未用
        while len(self._pool) >= self._max:
            evicted = self._pool.popitem(last=False)
            print(f"[Pool] 淘汰 {evicted[0]} (已满 {self._max})")

        checkpointer = InMemorySaver()
        agent = create_director_agent(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        entry = {"agent": agent, "checkpointer": checkpointer, "config": config}
        self._pool[thread_id] = entry
        print(f"[Pool] 创建 {thread_id} (当前 {len(self._pool)}/{self._max})")
        return entry

    def evict(self, thread_id: str):
        """手动淘汰某个实例。"""
        if thread_id in self._pool:
            del self._pool[thread_id]
            print(f"[Pool] 手动淘汰 {thread_id}")
