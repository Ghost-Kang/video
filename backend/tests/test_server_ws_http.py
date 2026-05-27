from __future__ import annotations

import asyncio
import json
from typing import Iterable

from agent import server


class FakeWebSocket:
    def __init__(self, messages: Iterable[dict]):
        self._messages = [json.dumps(message) for message in messages]
        self.sent: list[dict] = []
        self.closed: tuple[int, str] | None = None

    def __aiter__(self):
        self._iter = iter(self._messages)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def close(self, code: int, reason: str) -> None:
        self.closed = (code, reason)


class FakeReader:
    def __init__(self, request: bytes):
        self._request = request

    async def readuntil(self, _separator: bytes) -> bytes:
        head, _sep, rest = self._request.partition(b"\r\n\r\n")
        self._body = rest
        return head + b"\r\n\r\n"

    async def readexactly(self, n: int) -> bytes:
        return self._body[:n]


class FakeWriter:
    def __init__(self):
        self.data = b""
        self.closed = False

    def write(self, data: bytes) -> None:
        self.data += data

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


def _http_json_response(raw: bytes) -> tuple[int, dict]:
    head, _sep, body = raw.partition(b"\r\n\r\n")
    status = int(head.split(b" ", 2)[1])
    return status, json.loads(body.decode("utf-8"))


def test_ws_list_sessions_without_thread_id(monkeypatch):
    monkeypatch.setattr(server, "list_sessions", lambda user_id: [{"thread_id": f"{user_id}-t"}])
    monkeypatch.setattr(server, "_start_worker", lambda: None)
    ws = FakeWebSocket([
        {"type": "auth", "user_id": "u1"},
        {"type": "list_sessions"},
    ])

    asyncio.run(server.handle(ws))

    assert ws.closed is None
    assert [message["type"] for message in ws.sent] == ["session_list", "session_list"]
    assert ws.sent[-1]["sessions"] == [{"thread_id": "u1-t"}]


def test_ws_delete_session_sends_refreshed_session_list(monkeypatch):
    deleted: list[tuple[str, str]] = []
    calls = {"list": 0}

    def list_sessions(user_id: str):
        calls["list"] += 1
        if calls["list"] == 1:
            return [{"thread_id": "t1"}]
        return []

    monkeypatch.setattr(server, "list_sessions", list_sessions)
    monkeypatch.setattr(server, "store_delete_session", lambda user_id, thread_id: deleted.append((user_id, thread_id)))
    monkeypatch.setattr(server, "_start_worker", lambda: None)
    ws = FakeWebSocket([
        {"type": "auth", "user_id": "u1"},
        {"type": "delete_session", "thread_id": "t1"},
    ])

    asyncio.run(server.handle(ws))

    assert deleted == [("u1", "t1")]
    assert ws.sent[-1] == {"type": "session_list", "sessions": []}


def test_cost_status_requires_user_id():
    reader = FakeReader(b"GET /api/cost/status HTTP/1.1\r\nHost: test\r\n\r\n")
    writer = FakeWriter()

    asyncio.run(server._handle_http(reader, writer))

    status, body = _http_json_response(writer.data)
    assert status == 400
    assert body == {"error": "user_id required"}


def test_cost_status_accepts_user_id(monkeypatch):
    async def fake_cost_status(user_id: str, run_id: str):
        return {"user_id": user_id, "run_id": run_id, "run_cost_cny": 0.0, "user_pct": 0.0}

    monkeypatch.setattr(server, "cost_status", fake_cost_status)
    reader = FakeReader(b"GET /api/cost/status?user_id=u1&run_id=r1 HTTP/1.1\r\nHost: test\r\n\r\n")
    writer = FakeWriter()

    asyncio.run(server._handle_http(reader, writer))

    status, body = _http_json_response(writer.data)
    assert status == 200
    assert body["user_id"] == "u1"
    assert body["run_id"] == "r1"
