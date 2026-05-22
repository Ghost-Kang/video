from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from agent.cascade.events import emit


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


def _seed_events(db_path: Path, count: int = 1000) -> None:
    db = sqlite3.connect(str(db_path))
    rows = [
        (
            "failure_emitted" if i % 2 else "run_started",
            f"user_{i % 10}",
            f"run_{i % 25}",
            "{}",
            f"2026-05-22T12:{i // 60:02d}:{i % 60:02d}+00:00",
        )
        for i in range(count)
    ]
    db.executemany(
        """INSERT INTO events (event_name, user_id, run_id, payload_json, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    db.commit()
    db.close()


def _plan_for(db_path: Path, sql: str, params: tuple[str, ...]) -> str:
    db = sqlite3.connect(str(db_path))
    rows = db.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    db.close()
    return " | ".join(str(part) for row in rows for part in row)


def _index_names(db_path: Path) -> set[str]:
    db = sqlite3.connect(str(db_path))
    names = {str(row[1]) for row in db.execute("PRAGMA index_list(events)").fetchall()}
    db.close()
    return names


def test_events_run_id_created_at_query_uses_compound_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(
        emit(
            "failure_emitted",
            user_id="user_1",
            run_id="run_1",
            payload={
                "failure_code": "S3_NO_FORMULA",
                "stage": "analysis",
                "recovery_path_id": "RETRY_WITH_NEW_URL",
            },
        )
    )
    _seed_events(db_path)

    assert "idx_events_thread_ts" in _index_names(db_path)
    plan = _plan_for(
        db_path,
        "SELECT * FROM events WHERE run_id = ? ORDER BY created_at DESC LIMIT 200",
        ("run_7",),
    )

    assert "USING INDEX idx_events_thread_ts" in plan or "SEARCH events USING INDEX" in plan


def test_events_type_created_at_query_uses_compound_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(
        emit(
            "failure_emitted",
            user_id="user_1",
            run_id="run_1",
            payload={
                "failure_code": "S3_NO_FORMULA",
                "stage": "analysis",
                "recovery_path_id": "RETRY_WITH_NEW_URL",
            },
        )
    )
    _seed_events(db_path)

    assert "idx_events_type_ts" in _index_names(db_path)
    plan = _plan_for(
        db_path,
        "SELECT * FROM events WHERE event_name = ? ORDER BY created_at DESC LIMIT 200",
        ("failure_emitted",),
    )

    assert "USING INDEX idx_events_type_ts" in plan or "SEARCH events USING INDEX" in plan
