from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from agent.cascade import circuit_breaker
from agent.cascade.analysis_service import _TOPRADOR_CACHE, request_shallow_analysis
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.failures import FailureCode, HardFailure
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


def _event_payloads(db_path: Path, event_name: str) -> list[dict]:
    return [json.loads(payload) for name, payload in _events(db_path) if name == event_name]


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
    required_keys = {
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
        "upstream_latency_ms",
        "upstream_attempts",
    }
    assert required_keys <= set(payload)
    assert set(payload) <= required_keys | {"minor_audit"}
    assert payload["analysis_id"] == contract.analysis_id
    assert payload["source_url"] == "https://example.com/event"
    assert payload["scenes_count"] == len(contract.scenes)
    assert payload["warnings_count"] == len(contract.warnings)


def test_analysis_returned_includes_minor_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "jiating_chufang" / "001.json").read_text(encoding="utf-8"))
    raw["scenes"][0]["visual_content"] = "宝宝坐在厨房地垫上看镜头"

    async def loader(source_url: str) -> dict:
        return dict(raw)

    monkeypatch.setattr("agent.cascade.analysis_service._load_upstream_payload", loader)
    asyncio.run(request_shallow_analysis("https://example.com/minor", user_id="user_1", run_id="run_1"))

    payload = _event_payloads(db_path, "analysis_returned")[0]
    assert payload["minor_audit"] == {"hit_count": 1, "scene_indices": ["1"]}


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


def test_concurrent_same_url_emits_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))

    async def run_two() -> None:
        ready = asyncio.Event()
        calls = 0

        async def loader(source_url: str) -> dict:
            nonlocal calls
            calls += 1
            if calls == 2:
                ready.set()
            await ready.wait()
            return dict(raw)

        monkeypatch.setattr("agent.cascade.analysis_service._load_upstream_payload", loader)
        await asyncio.gather(
            request_shallow_analysis("https://example.com/race", user_id="user_1", run_id="run_a"),
            request_shallow_analysis("https://example.com/race", user_id="user_1", run_id="run_b"),
        )

    asyncio.run(run_two())
    assert len(_event_payloads(db_path, "analysis_returned")) == 1


def test_different_urls_same_user_emit_twice(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(request_shallow_analysis("https://example.com/a", user_id="user_1"))
    asyncio.run(request_shallow_analysis("https://example.com/b", user_id="user_1"))
    assert len(_event_payloads(db_path, "analysis_returned")) == 2


def test_different_users_same_url_emit_twice(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(request_shallow_analysis("https://example.com/shared", user_id="user_1"))
    asyncio.run(request_shallow_analysis("https://example.com/shared", user_id="user_2"))
    assert len(_event_payloads(db_path, "analysis_returned")) == 2


class _FakeAsyncClient:
    response: httpx.Response | None = None
    responses: list[httpx.Response] = []
    exc: Exception | None = None
    exceptions: list[Exception] = []
    last_headers: dict | None = None
    calls: int = 0

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, endpoint: str, *, json: dict, headers: dict):
        type(self).last_headers = headers
        type(self).calls += 1
        if self.exceptions:
            raise self.exceptions.pop(0)
        if self.exc:
            raise self.exc
        if self.responses:
            return self.responses.pop(0)
        assert self.response is not None
        return self.response


def _use_toprador(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, response: httpx.Response | None = None, exc: Exception | None = None) -> Path:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    circuit_breaker.reset()
    _TOPRADOR_CACHE.clear()
    monkeypatch.setenv("CASCADE_UPSTREAM", "toprador")
    monkeypatch.setenv("TOPRADOR_ENDPOINT", "https://toprador.test/analyze")
    monkeypatch.setenv("TOPRADOR_API_KEY", "secret")
    _FakeAsyncClient.response = response
    _FakeAsyncClient.responses = []
    _FakeAsyncClient.exc = exc
    _FakeAsyncClient.exceptions = []
    monkeypatch.setattr("agent.cascade.analysis_service.httpx.AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr("agent.cascade.analysis_service._retry_sleep", _no_sleep)
    _FakeAsyncClient.calls = 0
    return db_path


async def _no_sleep(attempt: int) -> None:
    return None


def _response(status_code: int, payload: dict | None = None) -> httpx.Response:
    request = httpx.Request("POST", "https://toprador.test/analyze")
    return httpx.Response(status_code, json=payload or {}, request=request)


def test_toprador_happy_path_validates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _use_toprador(monkeypatch, tmp_path, _response(200, raw))
    contract = asyncio.run(request_shallow_analysis("https://example.com/toprador", user_id="user_1"))
    assert isinstance(contract, CascadeAnalysisContract)
    assert _FakeAsyncClient.last_headers == {"Authorization": "Bearer secret"}


def test_toprador_timeout_maps_s7_and_emits_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_toprador(monkeypatch, tmp_path, exc=httpx.TimeoutException("too slow"))
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_shallow_analysis("https://example.com/timeout", user_id="user_1", run_id="run_1"))
    assert exc.value.code == FailureCode.S7_UPSTREAM_TIMEOUT
    assert _event_payloads(db_path, "failure_emitted")[0]["failure_code"] == "S7_UPSTREAM_TIMEOUT"


@pytest.mark.parametrize(
    ("status", "detail"),
    [(429, "rate_limit"), (401, "auth_refused"), (500, "upstream_5xx_500")],
)
def test_toprador_refusals_map_s8(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int, detail: str) -> None:
    _use_toprador(monkeypatch, tmp_path, _response(status, {"error": detail}))
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_shallow_analysis(f"https://example.com/{status}", user_id="user_1"))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert detail in str(exc.value)


def test_toprador_malformed_response_maps_contract_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    raw["schema_version"] = "2.0"
    _use_toprador(monkeypatch, tmp_path, _response(200, raw))
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_shallow_analysis("https://example.com/bad-schema", user_id="user_1"))
    assert exc.value.code in {FailureCode.S2_VERSION_MISMATCH, FailureCode.S5_INVALID_PAYLOAD}


def test_toprador_retries_transient_5xx_then_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_toprador(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _FakeAsyncClient.responses = [_response(503), _response(200, raw)]

    contract = asyncio.run(request_shallow_analysis("https://example.com/retry", user_id="user_1"))

    assert isinstance(contract, CascadeAnalysisContract)
    assert _FakeAsyncClient.calls == 2
    payload = _event_payloads(db_path, "analysis_returned")[0]
    assert payload["upstream_attempts"] == 2
    assert payload["upstream_latency_ms"] >= 0


def test_toprador_retries_transport_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_toprador(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _FakeAsyncClient.exceptions = [httpx.ConnectError("offline")]
    _FakeAsyncClient.responses = [_response(200, raw)]

    contract = asyncio.run(request_shallow_analysis("https://example.com/network", user_id="user_1"))

    assert isinstance(contract, CascadeAnalysisContract)
    assert _FakeAsyncClient.calls == 2


def test_toprador_cache_reuses_same_source_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_toprador(monkeypatch, tmp_path)
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _FakeAsyncClient.response = _response(200, raw)

    asyncio.run(request_shallow_analysis("https://example.com/cache", user_id="user_1"))
    asyncio.run(request_shallow_analysis("https://example.com/cache", user_id="user_2"))

    assert _FakeAsyncClient.calls == 1


def test_toprador_circuit_opens_after_consecutive_s8(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_toprador(monkeypatch, tmp_path, _response(429))
    for idx in range(5):
        with pytest.raises(HardFailure) as exc:
            asyncio.run(request_shallow_analysis(f"https://example.com/limited-{idx}", user_id="user_1"))
        assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED

    calls_before = _FakeAsyncClient.calls
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_shallow_analysis("https://example.com/open", user_id="user_1"))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert "circuit_open" in str(exc.value)
    assert _FakeAsyncClient.calls == calls_before


def test_toprador_circuit_half_open_closes_after_cooldown(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_toprador(monkeypatch, tmp_path, _response(429))
    clock = {"now": 100.0}
    monkeypatch.setattr("agent.cascade.circuit_breaker.time.monotonic", lambda: clock["now"])
    for idx in range(5):
        with pytest.raises(HardFailure):
            asyncio.run(request_shallow_analysis(f"https://example.com/cooldown-{idx}", user_id="user_1"))

    clock["now"] += 31.0
    raw = json.loads((SYNTH / "baomam_fushi" / "001.json").read_text(encoding="utf-8"))
    _FakeAsyncClient.response = _response(200, raw)

    contract = asyncio.run(request_shallow_analysis("https://example.com/half-open", user_id="user_1"))

    assert isinstance(contract, CascadeAnalysisContract)
