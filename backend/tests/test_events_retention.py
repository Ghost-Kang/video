from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.cascade.storage import retention_sweep, save_event


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


async def _seed_event(event_name: str, created_at: datetime) -> None:
    await save_event(
        event_name,
        user_id="user_1",
        run_id="run_1",
        payload={"test": True},
        created_at=created_at.isoformat(),
    )


def _event_counts(db_path: Path) -> dict[str, int]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute(
        "SELECT event_name, COUNT(*) FROM events GROUP BY event_name ORDER BY event_name"
    ).fetchall()
    db.close()
    return {str(name): int(count) for name, count in rows}


def test_business_events_are_kept_forever(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    now = datetime(2026, 5, 23, tzinfo=timezone.utc)
    old = now - timedelta(days=1000)

    async def go() -> dict[str, int]:
        for event_name in (
            "run_started",
            "analysis_returned",
            "script_rewritten",
            "publish_pack_copied",
            "shot_generated",
            "anchor_created",
            "anchor_reused",
            "interview_logged",
            "consent_accepted",
            "generation_cost",
        ):
            await _seed_event(event_name, old)
        return await retention_sweep(now=now)

    deleted = asyncio.run(go())

    assert all(count == 0 for count in deleted.values())
    assert sum(_event_counts(db_path).values()) == 10


def test_failure_events_older_than_180_days_are_deleted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    now = datetime(2026, 5, 23, tzinfo=timezone.utc)

    async def go() -> dict[str, int]:
        await _seed_event("failure_emitted", now - timedelta(days=181))
        await _seed_event("failure_emitted", now - timedelta(days=179))
        await _seed_event("failure_recovered", now - timedelta(days=181))
        await _seed_event("failure_recovered", now - timedelta(days=179))
        return await retention_sweep(now=now)

    deleted = asyncio.run(go())

    assert deleted["failure_emitted"] == 1
    assert deleted["failure_recovered"] == 1
    assert _event_counts(db_path) == {"failure_emitted": 1, "failure_recovered": 1}


def test_cascade_events_older_than_90_days_are_deleted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    now = datetime(2026, 5, 23, tzinfo=timezone.utc)

    async def go() -> dict[str, int]:
        for event_name in (
            "cascade_retry",
            "cascade_circuit_open",
            "cascade_cache_hit",
            "cascade_cache_miss",
        ):
            await _seed_event(event_name, now - timedelta(days=91))
            await _seed_event(event_name, now - timedelta(days=89))
        return await retention_sweep(now=now)

    deleted = asyncio.run(go())

    assert deleted["cascade_retry"] == 1
    assert deleted["cascade_circuit_open"] == 1
    assert deleted["cascade_cache_hit"] == 1
    assert deleted["cascade_cache_miss"] == 1
    assert _event_counts(db_path) == {
        "cascade_cache_hit": 1,
        "cascade_cache_miss": 1,
        "cascade_circuit_open": 1,
        "cascade_retry": 1,
    }


def test_retention_sweep_returns_deleted_counts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    now = datetime(2026, 5, 23, tzinfo=timezone.utc)

    async def go() -> dict[str, int]:
        await _seed_event("cascade_retry", now - timedelta(days=91))
        await _seed_event("cascade_retry", now - timedelta(days=92))
        await _seed_event("cascade_cache_hit", now - timedelta(days=10))
        await _seed_event("failure_emitted", now - timedelta(days=181))
        return await retention_sweep(now=now)

    deleted = asyncio.run(go())

    assert deleted == {
        "cascade_cache_hit": 0,
        "cascade_cache_miss": 0,
        "cascade_circuit_open": 0,
        "cascade_retry": 2,
        "failure_emitted": 1,
        "failure_recovered": 0,
    }
