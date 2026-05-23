from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from agent.cascade import circuit_breaker
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.mediakit import storyline_client
from agent.cascade.mediakit.storyline_client import (
    analyze_storyline,
    poll_task,
    submit_storyline_task,
)


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


def _events(db_path: Path, event_name: str) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute(
        "SELECT payload_json FROM events WHERE event_name = ? ORDER BY id",
        (event_name,),
    ).fetchall()
    db.close()
    return [json.loads(row[0]) for row in rows]


def _response(status_code: int, payload: dict | None = None, method: str = "POST") -> httpx.Response:
    request = httpx.Request(method, "https://mediakit.test")
    return httpx.Response(status_code, json=payload or {}, request=request)


class _FakeAsyncClient:
    post_responses: list[httpx.Response] = []
    get_responses: list[httpx.Response] = []
    post_calls: int = 0
    get_calls: int = 0
    last_post_headers: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url: str, *, json: dict, headers: dict):
        type(self).post_calls += 1
        type(self).last_post_headers = headers
        assert self.post_responses
        return self.post_responses.pop(0)

    async def get(self, url: str, *, headers: dict):
        type(self).get_calls += 1
        assert self.get_responses
        return self.get_responses.pop(0)


async def _no_sleep(_seconds: float) -> None:
    return None


def _setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    circuit_breaker.reset()
    monkeypatch.setattr("agent.config.VOLC_MEDIAKIT_AK", "ak-test")
    monkeypatch.setattr("agent.cascade.mediakit.storyline_client.httpx.AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr("agent.cascade.mediakit.storyline_client.asyncio.sleep", _no_sleep)
    _FakeAsyncClient.post_responses = []
    _FakeAsyncClient.get_responses = []
    _FakeAsyncClient.post_calls = 0
    _FakeAsyncClient.get_calls = 0
    _FakeAsyncClient.last_post_headers = None
    return db_path


def test_submit_storyline_task_parses_task_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    _FakeAsyncClient.post_responses = [
        _response(200, {"success": True, "task_id": "task_1", "request_id": "req_1"}),
    ]

    task_id = asyncio.run(submit_storyline_task(["https://cdn.test/v.mp4"]))

    assert task_id == "task_1"
    assert _FakeAsyncClient.last_post_headers == {
        "Authorization": "Bearer ak-test",
        "Content-Type": "application/json",
    }


def test_poll_task_returns_completed_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    _FakeAsyncClient.get_responses = [
        _response(200, {"status": "pending"}, method="GET"),
        _response(200, {"status": "completed", "result": {"duration": 12.3}}, method="GET"),
    ]

    result = asyncio.run(poll_task("task_1", timeout_s=5, poll_interval_s=0))

    assert result == {"duration": 12.3}
    assert _FakeAsyncClient.get_calls == 2


def test_poll_task_failed_maps_s8(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    _FakeAsyncClient.get_responses = [
        _response(200, {"status": "failed", "error": {"message": "bad video"}}, method="GET"),
    ]

    with pytest.raises(HardFailure) as exc:
        asyncio.run(poll_task("task_1", timeout_s=5, poll_interval_s=0))

    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert "bad video" in str(exc.value)


def test_submit_retries_5xx_then_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _setup(monkeypatch, tmp_path)
    _FakeAsyncClient.post_responses = [
        _response(503, {"success": False}),
        _response(200, {"success": True, "task_id": "task_2"}),
    ]

    task_id = asyncio.run(submit_storyline_task(["https://cdn.test/v.mp4"]))

    assert task_id == "task_2"
    assert _FakeAsyncClient.post_calls == 2
    retries = _events(db_path, "cascade_retry")
    assert retries[0]["reason"] == "upstream_5xx_503"


def test_analyze_storyline_caches_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _setup(monkeypatch, tmp_path)
    _FakeAsyncClient.post_responses = [
        _response(200, {"success": True, "task_id": "task_3"}),
    ]
    _FakeAsyncClient.get_responses = [
        _response(200, {"status": "completed", "result": {"duration": 8.0}}, method="GET"),
    ]

    first = asyncio.run(
        analyze_storyline("https://cdn.test/cache.mp4", user_id="u1", run_id="r1", poll_interval_s=0)
    )
    second = asyncio.run(
        analyze_storyline("https://cdn.test/cache.mp4", user_id="u2", run_id="r2", poll_interval_s=0)
    )

    assert first == second == {"duration": 8.0}
    assert _FakeAsyncClient.post_calls == 1
    assert len(_events(db_path, "cascade_cache_miss")) == 1
    hits = _events(db_path, "cascade_cache_hit")
    assert len(hits) == 1
    assert hits[0]["cache_layer"] == "sqlite"


def test_distinct_urls_do_not_share_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    _FakeAsyncClient.post_responses = [
        _response(200, {"success": True, "task_id": "task_a"}),
        _response(200, {"success": True, "task_id": "task_b"}),
    ]
    _FakeAsyncClient.get_responses = [
        _response(200, {"status": "completed", "result": {"duration": 1}}, method="GET"),
        _response(200, {"status": "completed", "result": {"duration": 2}}, method="GET"),
    ]

    first = asyncio.run(analyze_storyline("https://cdn.test/a.mp4", user_id="u", run_id="r1", poll_interval_s=0))
    second = asyncio.run(analyze_storyline("https://cdn.test/b.mp4", user_id="u", run_id="r2", poll_interval_s=0))

    assert first == {"duration": 1}
    assert second == {"duration": 2}
    assert _FakeAsyncClient.post_calls == 2
