from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.failures import HardFailure
from agent.cascade.storage import load_analysis


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "src" / "agent" / "cascade" / "fixtures"
SYNTH = FIXTURES_ROOT / "synthetic_v1"


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    monkeypatch.setenv("CASCADE_UPSTREAM", "fixture")
    return db_path


def _events(db_path: Path) -> list[tuple[str, str]]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute("SELECT event_name, payload_json FROM events ORDER BY id").fetchall()
    db.close()
    return rows


def test_fixture_mode_returns_valid_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)

    contract = asyncio.run(
        request_shallow_analysis(
            "https://example.com/x",
            user_id="user_1",
            run_id="run_1",
        )
    )

    assert isinstance(contract, CascadeAnalysisContract)
    assert str(contract.source_url) == "https://example.com/x"
    assert contract.analysis_id.startswith("ana_")


def test_persistence_round_trips(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)

    contract = asyncio.run(
        request_shallow_analysis("https://example.com/round-trip", user_id="user_1", run_id="run_1")
    )
    loaded = asyncio.run(load_analysis(contract.analysis_id))

    assert loaded == contract


def test_analysis_returned_event_payload_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)

    contract = asyncio.run(
        request_shallow_analysis("https://example.com/event", user_id="user_1", run_id="run_1")
    )
    rows = _events(db_path)

    assert [name for name, _ in rows] == ["analysis_returned"]
    payload = json.loads(rows[0][1])
    assert set(payload) == {
        "analysis_id",
        "source_url",
        "platform",
        "cost_cny",
        "duration_s",
        "scenes_count",
        "warnings_count",
        "confidence",
        "had_fallback",
        "model",
    }
    assert payload["analysis_id"] == contract.analysis_id
    assert payload["source_url"] == "https://example.com/event"
    assert payload["scenes_count"] == len(contract.scenes)
    assert payload["warnings_count"] == len(contract.warnings)


def test_hard_failure_records_failure_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)

    async def corrupted_fixture(source_url: str) -> dict:
        return json.loads((SYNTH / "edge_no_formula.json").read_text(encoding="utf-8"))

    monkeypatch.setattr("agent.cascade.analysis_service._load_upstream_payload", corrupted_fixture)

    with pytest.raises(HardFailure):
        asyncio.run(
            request_shallow_analysis("https://example.com/bad", user_id="user_1", run_id="run_bad")
        )

    rows = _events(db_path)
    assert [name for name, _ in rows] == ["failure_emitted"]
    payload = json.loads(rows[0][1])
    assert payload == {
        "failure_code": "S3_NO_FORMULA",
        "stage": "analysis",
        "recovery_path_id": "RETRY_WITH_NEW_URL",
    }


def test_idempotency_same_user_and_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    url = "https://example.com/same"

    first = asyncio.run(request_shallow_analysis(url, user_id="user_1", run_id="run_1"))
    second = asyncio.run(request_shallow_analysis(url, user_id="user_1", run_id="run_2"))

    assert second == first
    db = sqlite3.connect(str(db_path))
    count = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    event_count = db.execute("SELECT COUNT(*) FROM events WHERE event_name = 'analysis_returned'").fetchone()[0]
    db.close()
    assert count == 1
    assert event_count == 1
