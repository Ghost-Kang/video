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


def test_unknown_event_name_raises() -> None:
    with pytest.raises(ValueError, match="unknown event_name"):
        asyncio.run(emit("not_real", user_id="user_1", run_id=None, payload={}))


def test_known_event_missing_required_field_raises() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        asyncio.run(
            emit(
                "analysis_returned",
                user_id="user_1",
                run_id="run_1",
                payload={"analysis_id": "ana_1"},
            )
        )


def test_successful_emit_persists_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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

    db = sqlite3.connect(str(db_path))
    row = db.execute("SELECT event_name, user_id, run_id, payload_json FROM events").fetchone()
    db.close()
    assert row[0] == "failure_emitted"
    assert row[1] == "user_1"
    assert row[2] == "run_1"
    assert "S3_NO_FORMULA" in row[3]


def test_created_at_is_strictly_monotonic_within_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    payload = {
        "failure_code": "S3_NO_FORMULA",
        "stage": "analysis",
        "recovery_path_id": "RETRY_WITH_NEW_URL",
    }

    asyncio.run(emit("failure_emitted", user_id="user_1", run_id="run_1", payload=payload))
    asyncio.run(emit("failure_emitted", user_id="user_1", run_id="run_1", payload=payload))
    asyncio.run(emit("failure_emitted", user_id="user_1", run_id="run_1", payload=payload))

    db = sqlite3.connect(str(db_path))
    rows = [r[0] for r in db.execute("SELECT created_at FROM events WHERE run_id = 'run_1' ORDER BY id").fetchall()]
    db.close()
    assert rows == sorted(rows)
    assert len(set(rows)) == 3
