from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.cascade.cost_guard import cost_guard, cost_status
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.storage import save_event, utc_now_rfc3339


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    monkeypatch.delenv("CASCADE_RUN_CAP_CNY", raising=False)
    monkeypatch.delenv("CASCADE_USER_DAY_CAP_CNY", raising=False)
    return db_path


async def _cost(user_id: str, run_id: str, fen: int, created_at: str | None = None) -> None:
    await save_event(
        "generation_cost",
        user_id,
        run_id,
        {
            "run_id": run_id,
            "call_kind": "rewrite",
            "provider": "test",
            "model": "test",
            "cost_fen": fen,
            "latency_ms": 1,
            "tokens_in": 0,
            "tokens_out": 0,
            "outcome": "done",
        },
        created_at or utc_now_rfc3339(),
    )


def test_below_80_percent_has_no_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 100))
    asyncio.run(cost_guard("u1", "r1", 0.5))
    assert asyncio.run(cost_status("u1", "r1"))["warn"] is False


def test_at_80_percent_warns_without_block(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 240))
    asyncio.run(cost_guard("u1", "r1", 0.0))
    assert asyncio.run(cost_status("u1", "r1"))["warn"] is True


def test_run_cap_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 260))
    with pytest.raises(HardFailure) as exc:
        asyncio.run(cost_guard("u1", "r1", 0.5))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED


def test_user_day_cap_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 2_980))
    with pytest.raises(HardFailure):
        asyncio.run(cost_guard("u1", "r2", 0.5))


def test_costs_are_isolated_by_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 2_980))
    asyncio.run(cost_guard("u2", "r2", 0.5))


def test_utc_day_boundary_excludes_yesterday(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    asyncio.run(_cost("u1", "old", 2_980, yesterday))
    asyncio.run(cost_guard("u1", "new", 0.5))
    assert asyncio.run(cost_status("u1", "new"))["user_today_cost_cny"] == 0


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "1.0")
    asyncio.run(_cost("u1", "r1", 80))
    with pytest.raises(HardFailure):
        asyncio.run(cost_guard("u1", "r1", 0.3))


def test_generation_cost_sums_match_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 42))
    asyncio.run(_cost("u1", "r1", 58))
    assert asyncio.run(cost_status("u1", "r1"))["run_cost_cny"] == 1.0
    db = sqlite3.connect(str(db_path))
    total = sum(json.loads(row[0])["cost_fen"] for row in db.execute("SELECT payload_json FROM events"))
    db.close()
    assert total == 100
