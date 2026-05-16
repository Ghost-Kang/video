"""AgentPool 单元测试"""
from agent.pool import AgentPool


def test_pool_basics():
    pool = AgentPool(max_size=3)
    a = pool.get("a")
    b = pool.get("b")
    assert a is not b
    assert a["config"]["configurable"]["thread_id"] == "a"


def test_pool_reuse():
    pool = AgentPool(max_size=3)
    a1 = pool.get("a")
    a2 = pool.get("a")
    assert a1 is a2  # 同一实例复用


def test_pool_eviction():
    pool = AgentPool(max_size=2)
    pool.get("a")
    pool.get("b")
    # a 是最久未用的
    pool.get("c")  # 应淘汰 a
    assert "a" not in pool._pool
    assert "b" in pool._pool
    assert "c" in pool._pool


def test_pool_lru_order():
    pool = AgentPool(max_size=2)
    pool.get("a")
    pool.get("b")
    pool.get("a")  # 访问 a，a 变最新
    pool.get("c")  # 淘汰最旧的 b
    assert "a" in pool._pool
    assert "b" not in pool._pool
    assert "c" in pool._pool


def test_pool_manual_evict():
    pool = AgentPool(max_size=3)
    pool.get("a")
    pool.evict("a")
    assert "a" not in pool._pool
