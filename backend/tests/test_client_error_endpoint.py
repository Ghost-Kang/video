"""W5D2 — /api/client_error endpoint contract tests.

Frontend Sentry-lite POSTs browser JS errors here. We assert:
- happy path: payload emits `client_error` event with truncated fields
- missing message: 400
- giant payload: fields actually clipped (no overflow)
- anonymous default user_id fallback

Repo uses asyncio.run() rather than pytest-asyncio (see test_doubao_*).
"""

from __future__ import annotations

import asyncio

from agent.cascade.event_names import EventName
from agent.transport.http_router import handle_client_error


def test_happy_path_emits_client_error(monkeypatch):
    captured: list[dict] = []

    async def fake_emit(event_name, *, user_id, run_id, payload):
        captured.append({"event_name": event_name, "user_id": user_id, "payload": payload})

    monkeypatch.setattr("agent.transport.http_router.emit", fake_emit)

    status, resp, reason = asyncio.run(
        handle_client_error(
            qs={},
            body={
                "kind": "window_error",
                "message": "ReferenceError: x is not defined",
                "stack": "at foo.js:42",
                "filename": "https://cascade.herwin.top/assets/main-abc.js",
                "lineno": 42,
                "colno": 17,
                "url": "https://cascade.herwin.top/chat/session-xyz",
                "ua": "Mozilla/5.0 (Macintosh)",
                "user_id": "anon-test",
                "thread_id": "session-xyz",
            },
        )
    )
    assert status == 200
    assert resp == {"ok": True}
    assert reason == "OK"

    assert len(captured) == 1
    e = captured[0]
    assert e["event_name"] == EventName.CLIENT_ERROR
    assert e["user_id"] == "anon-test"
    assert e["payload"]["kind"] == "window_error"
    assert e["payload"]["message"] == "ReferenceError: x is not defined"
    assert e["payload"]["lineno"] == 42
    assert e["payload"]["thread_id"] == "session-xyz"


def test_missing_message_rejects():
    status, resp, _ = asyncio.run(handle_client_error(qs={}, body={"kind": "window_error"}))
    assert status == 400
    assert "message" in resp["error"]


def test_truncation_kicks_in(monkeypatch):
    captured: list[dict] = []

    async def fake_emit(event_name, *, user_id, run_id, payload):
        captured.append(payload)

    monkeypatch.setattr("agent.transport.http_router.emit", fake_emit)

    big = "X" * 10_000
    status, _, _ = asyncio.run(
        handle_client_error(
            qs={},
            body={
                "kind": "k" * 200,
                "message": big,
                "stack": big,
                "ua": big,
                "filename": big,
                "url": big,
                "user_id": "u" * 200,
                "thread_id": "t" * 200,
            },
        )
    )
    assert status == 200
    p = captured[0]
    # message ≤500, stack ≤4000, ua ≤200, filename ≤200, url ≤500,
    # thread_id ≤80, kind ≤40
    assert len(p["message"]) == 500
    assert len(p["stack"]) == 4000
    assert len(p["ua"]) == 200
    assert len(p["filename"]) == 200
    assert len(p["url"]) == 500
    assert len(p["thread_id"]) == 80
    assert len(p["kind"]) == 40


def test_anonymous_user_id_default(monkeypatch):
    captured: list[dict] = []

    async def fake_emit(event_name, *, user_id, run_id, payload):
        captured.append({"user_id": user_id})

    monkeypatch.setattr("agent.transport.http_router.emit", fake_emit)

    status, _, _ = asyncio.run(
        handle_client_error(qs={}, body={"kind": "window_error", "message": "boom"})
    )
    assert status == 200
    assert captured[0]["user_id"] == "anonymous"
