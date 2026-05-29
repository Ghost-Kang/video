"""run_state P0-B — persisted run_lifecycle table.

Pins: marks write through to SQLite; load() survives a cache clear (simulating a
fresh process); boot reconcile flips stale 'running' → 'failed'.
"""

from __future__ import annotations

import asyncio

import pytest

from agent.cascade.persistence import db as cascade_db
from agent.transport import run_state


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    """Point the cascade DB at a fresh temp file + clear the in-memory cache."""
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    cascade_db._BOOTSTRAPPED_PATHS.clear()
    run_state._runs.clear()
    yield
    run_state._runs.clear()


def test_mark_running_then_done_persists(_isolated_db=None):
    async def t():
        seq = await run_state.mark_running("u1", "t1")
        assert seq == 1
        await run_state.mark_done("t1")
        # clear cache → forces DB read
        run_state._runs.clear()
        st = await run_state.load("t1")
        assert st is not None and st["status"] == "done"
    asyncio.run(t())


def test_mark_failed_persists_failure_payload():
    async def t():
        await run_state.mark_running("u1", "t1")
        await run_state.mark_failed("t1", {"code": "S7_UPSTREAM_TIMEOUT", "hint": "慢", "actions": [], "request_id": ""})
        run_state._runs.clear()
        st = await run_state.load("t1")
        assert st["status"] == "failed"
        assert st["failure"]["code"] == "S7_UPSTREAM_TIMEOUT"
    asyncio.run(t())


def test_run_seq_bumps_each_run():
    async def t():
        assert await run_state.mark_running("u1", "t1") == 1
        await run_state.mark_done("t1")
        assert await run_state.mark_running("u1", "t1") == 2
    asyncio.run(t())


def test_reconcile_flips_stale_running_to_failed():
    async def t():
        await run_state.mark_running("u1", "t1")
        await run_state.mark_running("u1", "t2")
        await run_state.mark_done("t2")  # t2 terminal, t1 still running
        run_state._runs.clear()  # simulate process restart (cache gone)
        n = await run_state.reconcile_stale_runs()
        assert n == 1  # only t1
        st1 = await run_state.load("t1")
        st2 = await run_state.load("t2")
        assert st1["status"] == "failed" and st1["failure"]["code"] == "S11_INTERNAL_ERROR"
        assert st2["status"] == "done"
    asyncio.run(t())


def test_load_unknown_thread_returns_none():
    async def t():
        assert await run_state.load("never") is None
    asyncio.run(t())
