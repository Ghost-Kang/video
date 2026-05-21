from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.rewrite_service import RewriteResult, error_payload, request_rewrite


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    monkeypatch.setenv("CASCADE_UPSTREAM", "fixture")
    return db_path


async def _analysis() -> str:
    contract = await request_shallow_analysis(
        "https://example.com/rewrite-source",
        user_id="u1",
        run_id="r1",
    )
    return contract.analysis_id


def _events(db_path: Path, name: str) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute("SELECT payload_json FROM events WHERE event_name = ? ORDER BY id", (name,)).fetchall()
    db.close()
    return [json.loads(row[0]) for row in rows]


def test_happy_path_returns_rewrite_and_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    result = asyncio.run(
        request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1", run_id="r1")
    )
    assert isinstance(result, RewriteResult)
    assert result.rewrite_id.startswith("rw_")
    assert len(_events(db_path, "script_rewritten")) == 1


def test_unknown_analysis_raises_lookup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    with pytest.raises(LookupError):
        asyncio.run(request_rewrite(analysis_id="missing", niche="baomam_fushi", user_id="u1"))


def test_unsupported_niche_raises_hard_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_rewrite(analysis_id=analysis_id, niche="bad", user_id="u1"))  # type: ignore[arg-type]
    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD


def test_cost_cap_exceeded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    monkeypatch.setattr("agent.cascade.rewrite_service.predict_rewrite_cost", lambda *_: 3.01)
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert _events(db_path, "script_rewritten") == []


def test_idempotency_within_24h(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    first = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    second = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    assert second.rewrite_id == first.rewrite_id
    assert len(_events(db_path, "script_rewritten")) == 1


def test_multi_user_isolation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    first = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    second = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u2"))
    assert second.rewrite_id != first.rewrite_id


def test_event_payload_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    payload = _events(db_path, "script_rewritten")[0]
    assert {
        "analysis_id",
        "rewrite_id",
        "niche",
        "parser_warnings",
        "shots_count",
        "confidence",
        "cost_cny",
        "model",
        "had_anchor_reference",
    } <= set(payload)


def test_error_payload_has_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CASCADE_DEBUG_ERRORS", raising=False)
    payload = error_payload(HardFailure(FailureCode.S5_INVALID_PAYLOAD, "detail"))
    assert payload["request_id"]
    assert "debug_detail" not in payload


def test_debug_detail_only_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CASCADE_DEBUG_ERRORS", "1")
    payload = error_payload(HardFailure(FailureCode.S5_INVALID_PAYLOAD, "debug"))
    assert payload["debug_detail"] == "debug"
