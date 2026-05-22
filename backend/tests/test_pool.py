"""AgentPool 单元测试

AgentPool.get() became async (see `pool.py:18`) — these tests wrap each test
body in an inner async function + asyncio.run() to match the existing pattern
used in test_cost_guard.py / test_events.py.
"""
import asyncio

from agent.pool import AgentPool


def test_pool_basics():
    async def _run():
        pool = AgentPool(max_size=3)
        a = await pool.get("a")
        b = await pool.get("b")
        assert a is not b
        assert a["config"]["configurable"]["thread_id"] == "a"
    asyncio.run(_run())


def test_pool_reuse():
    async def _run():
        pool = AgentPool(max_size=3)
        a1 = await pool.get("a")
        a2 = await pool.get("a")
        assert a1 is a2  # 同一实例复用
    asyncio.run(_run())


def test_pool_eviction():
    async def _run():
        pool = AgentPool(max_size=2)
        await pool.get("a")
        await pool.get("b")
        # a 是最久未用的
        await pool.get("c")  # 应淘汰 a
        assert "a" not in pool._pool
        assert "b" in pool._pool
        assert "c" in pool._pool
    asyncio.run(_run())


def test_pool_lru_order():
    async def _run():
        pool = AgentPool(max_size=2)
        await pool.get("a")
        await pool.get("b")
        await pool.get("a")  # 访问 a，a 变最新
        await pool.get("c")  # 淘汰最旧的 b
        assert "a" in pool._pool
        assert "b" not in pool._pool
        assert "c" in pool._pool
    asyncio.run(_run())


# test_pool_manual_evict removed 2026-05-22: AgentPool.evict() does not exist
# (orphan test predating a method removal — no src/ caller references evict).
# If/when AgentPool needs explicit manual eviction (e.g. for /admin/evict
# endpoint), re-add evict() to pool.py and reinstate this test.
