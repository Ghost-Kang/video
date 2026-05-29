"""AgentPool 单元测试

W5D3: AgentPool now keyed by (user_id, thread_id) composite key (P0-2 fix).
Tests updated to pass both args.
"""
import asyncio

from agent.pool import AgentPool


def test_pool_basics():
    async def _run():
        pool = AgentPool(max_size=3)
        try:
            a = await pool.get("u1", "a")
            b = await pool.get("u1", "b")
            assert a is not b
            assert a["config"]["configurable"]["thread_id"] == "a"
        finally:
            await pool.close()
    asyncio.run(_run())


def test_pool_reuse():
    async def _run():
        pool = AgentPool(max_size=3)
        try:
            a1 = await pool.get("u1", "a")
            a2 = await pool.get("u1", "a")
            assert a1 is a2  # 同一实例复用
        finally:
            await pool.close()
    asyncio.run(_run())


def test_pool_eviction():
    async def _run():
        pool = AgentPool(max_size=2)
        try:
            await pool.get("u1", "a")
            await pool.get("u1", "b")
            # a 是最久未用的
            await pool.get("u1", "c")  # 应淘汰 a
            assert ("u1", "a") not in pool._pool
            assert ("u1", "b") in pool._pool
            assert ("u1", "c") in pool._pool
        finally:
            await pool.close()
    asyncio.run(_run())


def test_pool_lru_order():
    async def _run():
        pool = AgentPool(max_size=2)
        try:
            await pool.get("u1", "a")
            await pool.get("u1", "b")
            await pool.get("u1", "a")  # 访问 a，a 变最新
            await pool.get("u1", "c")  # 淘汰最旧的 b
            assert ("u1", "a") in pool._pool
            assert ("u1", "b") not in pool._pool
            assert ("u1", "c") in pool._pool
        finally:
            await pool.close()
    asyncio.run(_run())


def test_pool_cross_user_isolation():
    """W5D3 P0-2 — same thread_id from two users must be isolated."""
    async def _run():
        pool = AgentPool(max_size=10)
        try:
            a_u1 = await pool.get("alice", "session-x")
            a_u2 = await pool.get("bob",   "session-x")  # same thread_id
            assert a_u1 is not a_u2
            assert ("alice", "session-x") in pool._pool
            assert ("bob",   "session-x") in pool._pool
        finally:
            await pool.close()
    asyncio.run(_run())


def test_pool_close_releases_all_connections():
    """W5D3 P0-1 — verify pool.close() drains every entry, no residual."""
    async def _run():
        pool = AgentPool(max_size=10)
        for tid in ("a", "b", "c"):
            await pool.get("u1", tid)
        assert len(pool._pool) == 3
        await pool.close()
        assert len(pool._pool) == 0
    asyncio.run(_run())
