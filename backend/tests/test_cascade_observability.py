"""Tests for P4-3 cascade observability events.

Covers the four new event_types emitted from analysis_service._call_toprador:
    cascade_retry        — per-attempt retry triggered by transient failures
    cascade_circuit_open — emitted when a caller hits an open breaker
    cascade_cache_hit    — in-memory cache served the response (P3-7 cache layer)
    cascade_cache_miss   — cache lookup missed, real upstream call proceeded

Plus storm-prevention: cascade_circuit_open is rate-limited to ≤ 1 emit per
endpoint per 60s window.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path

import httpx
import pytest

from agent.cascade import analysis_service, circuit_breaker
from agent.cascade.analysis_service import (
    _CIRCUIT_OPEN_EMIT_WINDOW_S,
    _TOPRADOR_CACHE,
    _last_circuit_open_emit,
    request_shallow_analysis,
)
from agent.cascade.failures import FailureCode, HardFailure


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "src" / "agent" / "cascade" / "fixtures"
SYNTH = FIXTURES_ROOT / "synthetic_v1"


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


def _events_of_type(db_path: Path, name: str) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute(
        "SELECT payload_json FROM events WHERE event_name = ? ORDER BY id",
        (name,),
    ).fetchall()
    db.close()
    return [json.loads(r[0]) for r in rows]


def _response(status_code: int, payload: dict | None = None) -> httpx.Response:
    request = httpx.Request("POST", "https://toprador.test/analyze")
    return httpx.Response(status_code, json=payload or {}, request=request)


class _FakeAsyncClient:
    """Minimal AsyncClient stand-in supporting sequenced responses + exceptions."""

    response: httpx.Response | None = None
    responses: list[httpx.Response] = []
    exc: Exception | None = None
    exceptions: list[Exception] = []
    calls: int = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, endpoint: str, *, json: dict, headers: dict):
        type(self).calls += 1
        if self.exceptions:
            raise self.exceptions.pop(0)
        if self.exc:
            raise self.exc
        if self.responses:
            return self.responses.pop(0)
        assert self.response is not None
        return self.response


async def _no_sleep(attempt: int) -> None:
    return None


def _setup_toprador(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    circuit_breaker.reset()
    _TOPRADOR_CACHE.clear()
    _last_circuit_open_emit.clear()
    monkeypatch.setenv("CASCADE_UPSTREAM", "toprador")
    monkeypatch.setenv("TOPRADOR_ENDPOINT", "https://toprador.test/analyze")
    monkeypatch.setenv("TOPRADOR_API_KEY", "secret")
    _FakeAsyncClient.response = None
    _FakeAsyncClient.responses = []
    _FakeAsyncClient.exc = None
    _FakeAsyncClient.exceptions = []
    _FakeAsyncClient.calls = 0
    monkeypatch.setattr("agent.cascade.analysis_service.httpx.AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr("agent.cascade.analysis_service._retry_sleep", _no_sleep)
    return db_path


# ---------- 1. cascade_cache_miss fires on first call ----------


def test_cache_miss_emits_on_first_call(monkeypatch, tmp_path):
    db_path = _setup_toprador(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _FakeAsyncClient.response = _response(200, raw)

    asyncio.run(request_shallow_analysis("https://example.com/miss", user_id="u_x", run_id="r1"))

    misses = _events_of_type(db_path, "cascade_cache_miss")
    hits = _events_of_type(db_path, "cascade_cache_hit")
    assert len(misses) == 1
    assert len(hits) == 0
    assert misses[0]["source_url_hash"] and len(misses[0]["source_url_hash"]) == 12
    # Hash must NOT be the raw URL (privacy)
    assert "example.com" not in misses[0]["source_url_hash"]


# ---------- 2. cascade_cache_hit fires on warm cache for different user ----------


def test_cache_hit_emits_on_warm_cache(monkeypatch, tmp_path):
    db_path = _setup_toprador(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _FakeAsyncClient.responses = [_response(200, raw)]

    # First call populates the toprador cache for the URL
    asyncio.run(request_shallow_analysis("https://example.com/warm", user_id="u_a", run_id="r1"))
    # Second call by a different user with same URL → still hits the toprador cache
    # (load_analysis_for_source is per-user so the DB short-circuit is skipped)
    asyncio.run(request_shallow_analysis("https://example.com/warm", user_id="u_b", run_id="r2"))

    hits = _events_of_type(db_path, "cascade_cache_hit")
    assert len(hits) == 1
    assert hits[0]["source_url_hash"] and len(hits[0]["source_url_hash"]) == 12
    assert 0 < hits[0]["ttl_remaining_s"] <= 60.0


# ---------- 3. cascade_retry fires for transient 5xx then succeeds ----------


def test_cascade_retry_fires_on_transient_5xx(monkeypatch, tmp_path):
    db_path = _setup_toprador(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _FakeAsyncClient.responses = [_response(503), _response(200, raw)]

    asyncio.run(request_shallow_analysis("https://example.com/retry503", user_id="u_x", run_id="r1"))

    retries = _events_of_type(db_path, "cascade_retry")
    assert len(retries) == 1
    assert retries[0]["attempt"] == 1
    assert retries[0]["reason"] == "upstream_5xx_503"
    assert retries[0]["endpoint"] == "https://toprador.test/analyze"
    assert retries[0]["duration_ms"] >= 0


# ---------- 4. cascade_retry fires for timeout but stops after max attempts ----------


def test_cascade_retry_caps_at_attempt_limit(monkeypatch, tmp_path):
    db_path = _setup_toprador(monkeypatch, tmp_path)
    _FakeAsyncClient.exc = httpx.TimeoutException("too slow")

    with pytest.raises(HardFailure) as exc_info:
        asyncio.run(request_shallow_analysis(
            "https://example.com/timeout", user_id="u_x", run_id="r1",
        ))
    assert exc_info.value.code == FailureCode.S7_UPSTREAM_TIMEOUT

    retries = _events_of_type(db_path, "cascade_retry")
    # 3 attempts → retries emitted for attempts 1 and 2 only (final attempt raises, no retry-event)
    assert len(retries) == 2
    assert [r["attempt"] for r in retries] == [1, 2]
    assert all(r["reason"] == "timeout" for r in retries)


# ---------- 5. cascade_circuit_open emits when a caller hits an open breaker ----------


def test_cascade_circuit_open_emits_when_breaker_trips(monkeypatch, tmp_path):
    db_path = _setup_toprador(monkeypatch, tmp_path)
    # Pre-open the breaker by recording the threshold of failures
    for _ in range(circuit_breaker.FAILURE_THRESHOLD):
        circuit_breaker.record_failure(analysis_service._TOPRADOR_BREAKER)

    with pytest.raises(HardFailure) as exc_info:
        asyncio.run(request_shallow_analysis(
            "https://example.com/blocked", user_id="u_x", run_id="r1",
        ))
    assert exc_info.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert exc_info.value.debug_detail == "circuit_open"

    opens = _events_of_type(db_path, "cascade_circuit_open")
    assert len(opens) == 1
    assert opens[0]["endpoint"] == "https://toprador.test/analyze"
    assert opens[0]["consecutive_failures"] == circuit_breaker.FAILURE_THRESHOLD
    assert opens[0]["cooldown_s"] >= 0


# ---------- 6. cascade_circuit_open storm-prevention: 1 emit per 60s window ----------


def test_cascade_circuit_open_storm_prevention(monkeypatch, tmp_path):
    db_path = _setup_toprador(monkeypatch, tmp_path)
    for _ in range(circuit_breaker.FAILURE_THRESHOLD):
        circuit_breaker.record_failure(analysis_service._TOPRADOR_BREAKER)

    # Three callers hit the open breaker back-to-back within the 60s window
    for i in range(3):
        with pytest.raises(HardFailure):
            asyncio.run(request_shallow_analysis(
                f"https://example.com/blocked-{i}", user_id="u_x", run_id=f"r{i}",
            ))

    opens = _events_of_type(db_path, "cascade_circuit_open")
    # Storm-prevention: only the first caller emits, others suppressed
    assert len(opens) == 1
    assert _CIRCUIT_OPEN_EMIT_WINDOW_S == 60.0

    # Manually expire the window and the next caller re-emits
    _last_circuit_open_emit["https://toprador.test/analyze"] = time.monotonic() - _CIRCUIT_OPEN_EMIT_WINDOW_S - 1
    with pytest.raises(HardFailure):
        asyncio.run(request_shallow_analysis(
            "https://example.com/blocked-after-window", user_id="u_x", run_id="r9",
        ))

    opens = _events_of_type(db_path, "cascade_circuit_open")
    assert len(opens) == 2
