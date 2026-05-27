"""MediaKit transcribe-client unit tests (W4D5).

Hermetic — patches httpx.AsyncClient + cost_guard. The transcribe path is
"best-effort" by contract: it must return "" on every failure mode and
must NEVER raise, because analysis_service relies on this to keep the
pipeline alive when transcribe degrades.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from agent.cascade.mediakit import transcribe_client as tc


# ---------- fakes ----------


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | str | None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if isinstance(self._body, str):
            return json.loads(self._body)
        if isinstance(self._body, dict):
            return self._body
        raise ValueError("no body")


class _FakeAsyncClient:
    response: _FakeResponse | None = None
    exc: Exception | None = None
    last_url: str | None = None
    last_body: dict | None = None
    last_headers: dict | None = None

    def __init__(self, *args, **kwargs):
        type(self).last_headers = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, *, json=None, headers=None):
        type(self).last_url = url
        type(self).last_body = json
        type(self).last_headers = headers
        if self.exc:
            raise self.exc
        assert self.response is not None, "test forgot to set _FakeAsyncClient.response"
        return self.response


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    _FakeAsyncClient.response = None
    _FakeAsyncClient.exc = None
    _FakeAsyncClient.last_url = None
    _FakeAsyncClient.last_body = None
    _FakeAsyncClient.last_headers = None
    monkeypatch.setattr(tc.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(tc.config, "VOLC_MEDIAKIT_AK", "fake-token")

    async def _no_cost(*_args, **_kwargs):
        return None

    async def _no_emit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(tc, "cost_guard", _no_cost)
    monkeypatch.setattr(tc, "emit", _no_emit)
    yield


# ---------- happy paths ----------


def test_happy_path_result_text():
    _FakeAsyncClient.response = _FakeResponse(
        200,
        {"result": {"text": "第一段\n第二段\n第三段"}},
    )

    transcript = asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1"))

    assert transcript == "第一段\n第二段\n第三段"
    assert _FakeAsyncClient.last_url.endswith("/tools/extract-audio-text")
    assert _FakeAsyncClient.last_body == {"video_urls": ["https://cdn.test/x.mp4"]}
    assert _FakeAsyncClient.last_headers["Authorization"] == "Bearer fake-token"


def test_happy_path_utterances_array():
    _FakeAsyncClient.response = _FakeResponse(
        200,
        {
            "result": {
                "utterances": [
                    {"text": "宝宝拒食"},
                    {"text": "妈妈换苹果"},
                    {"text": "宝宝抢勺子"},
                ]
            }
        },
    )

    transcript = asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1"))
    assert transcript == "宝宝拒食\n妈妈换苹果\n宝宝抢勺子"


def test_long_transcript_is_capped_at_20k():
    """Contract.full_transcript max_length=20_000 — client must enforce."""
    huge = "测" * 25_000
    _FakeAsyncClient.response = _FakeResponse(200, {"result": {"text": huge}})

    transcript = asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1"))
    assert len(transcript) <= 20_000
    assert transcript.endswith("…[truncated]")


# ---------- failure paths (all must return "" — never raise) ----------


def test_missing_token_returns_empty(monkeypatch):
    monkeypatch.setattr(tc.config, "VOLC_MEDIAKIT_AK", "")
    transcript = asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1"))
    assert transcript == ""
    # And we never tried to hit the network.
    assert _FakeAsyncClient.last_url is None


def test_non_200_returns_empty():
    _FakeAsyncClient.response = _FakeResponse(500, {"error": "boom"})
    assert asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1")) == ""


def test_network_error_returns_empty():
    _FakeAsyncClient.exc = httpx.ConnectError("dns failure")
    assert asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1")) == ""


def test_invalid_json_returns_empty():
    _FakeAsyncClient.response = _FakeResponse(200, None)
    assert asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1")) == ""


def test_unexpected_shape_returns_empty():
    # No `result.text`, no `result.utterances`, no `text` anywhere.
    _FakeAsyncClient.response = _FakeResponse(200, {"result": {"foo": "bar"}})
    assert asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1")) == ""


def test_cost_guard_block_returns_empty(monkeypatch):
    from agent.cascade.failures import FailureCode, HardFailure

    async def boom(*_args, **_kwargs):
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "over cap")

    monkeypatch.setattr(tc, "cost_guard", boom)
    transcript = asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1"))
    # cost_guard refused → no network call, transcript empty
    assert transcript == ""
    assert _FakeAsyncClient.last_url is None


def test_fallback_to_flat_text_field():
    # Some endpoint variants put `text` at the top level.
    _FakeAsyncClient.response = _FakeResponse(200, {"text": "flat top-level"})
    assert asyncio.run(tc.fetch_transcript("https://cdn.test/x.mp4", user_id="u1")) == "flat top-level"
