from __future__ import annotations

import asyncio
import json
from typing import Iterable

from agent import config, server, store
from agent.cascade import cost_guard
from agent.transport import http_router as http_router_mod
from agent.workers import generation_worker


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
    monkeypatch.setattr(store, "list_sessions", lambda user_id: [{"thread_id": f"{user_id}-t"}])
    monkeypatch.setattr(generation_worker, "start_workers", lambda: None)
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

    monkeypatch.setattr(store, "list_sessions", list_sessions)
    monkeypatch.setattr(store, "delete_session", lambda user_id, thread_id: deleted.append((user_id, thread_id)))
    monkeypatch.setattr(generation_worker, "start_workers", lambda: None)
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

    monkeypatch.setattr(cost_guard, "cost_status", fake_cost_status)
    reader = FakeReader(b"GET /api/cost/status?user_id=u1&run_id=r1 HTTP/1.1\r\nHost: test\r\n\r\n")
    writer = FakeWriter()

    asyncio.run(server._handle_http(reader, writer))

    status, body = _http_json_response(writer.data)
    assert status == 200
    assert body["user_id"] == "u1"
    assert body["run_id"] == "r1"


# ---------- P0: HTTP API auth gate ----------


def _drive(raw: bytes) -> tuple[int, dict]:
    reader = FakeReader(raw)
    writer = FakeWriter()
    asyncio.run(server._handle_http(reader, writer))
    return _http_json_response(writer.data)


def _req(method: str, path: str, *, headers: str = "", body: dict | None = None) -> bytes:
    payload = json.dumps(body or {}).encode("utf-8")
    head = f"{method} {path} HTTP/1.1\r\nHost: test\r\n{headers}"
    if body is not None:
        head += f"Content-Length: {len(payload)}\r\n"
    return head.encode("utf-8") + b"\r\n" + (payload if body is not None else b"")


def test_open_routes_need_no_auth(monkeypatch):
    # Even with both gates configured, OPEN routes stay reachable.
    monkeypatch.setattr(config, "INVITE_CODES", frozenset({"GOOD"}))
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret")
    status, body = _drive(_req("GET", "/api/health"))
    assert status == 200 and body.get("ok") is True
    status, body = _drive(_req("GET", "/api/stats/public"))
    assert status == 200 and "runs" in body and "creators" in body


def test_invite_verify_open_and_validates_code(monkeypatch):
    # W5D4 — pre-flight gate check. OPEN (no auth header), returns valid:bool.
    monkeypatch.setattr(config, "INVITE_CODES", frozenset({"cascade"}))
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret")
    # Correct code → valid:true, reachable WITHOUT any auth header.
    status, body = _drive(_req("GET", "/api/invite/verify?code=cascade"))
    assert status == 200 and body == {"valid": True, "gate": "cohort"}
    # Wrong code → valid:false (still 200; the gate reads the flag).
    status, body = _drive(_req("GET", "/api/invite/verify?code=ee"))
    assert status == 200 and body["valid"] is False
    # Missing code → invalid.
    status, body = _drive(_req("GET", "/api/invite/verify"))
    assert status == 200 and body["valid"] is False


def test_invite_verify_open_gate_when_codes_empty(monkeypatch):
    # Dev/test: empty INVITE_CODES → gate disabled → any code valid.
    monkeypatch.setattr(config, "INVITE_CODES", frozenset())
    status, body = _drive(_req("GET", "/api/invite/verify?code=whatever"))
    assert status == 200 and body == {"valid": True, "gate": "open"}


def test_admin_route_requires_token_when_configured(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret")
    monkeypatch.setattr(config, "INVITE_CODES", frozenset())
    # No token → 401
    status, body = _drive(_req("GET", "/api/creators"))
    assert status == 401 and body["error"] == "admin_token_required"
    # Correct token → passes the gate (200 from the handler)
    status, _ = _drive(_req("GET", "/api/creators", headers="X-Admin-Token: secret\r\n"))
    assert status == 200


def test_admin_token_constant_time_compare(monkeypatch):
    """B8 regression: admin token check uses hmac.compare_digest, not `==`.

    We can't time the comparison in a unit test, but we assert the security
    contract that compare_digest guarantees holds: only the exact token passes,
    while prefix-matching and length-matching near-misses are rejected. (A buggy
    refactor back to `==` would still pass these — so we also assert
    http_router actually references compare_digest.)
    """
    from agent.transport import http_router

    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret-token-123")
    monkeypatch.setattr(config, "INVITE_CODES", frozenset())

    # Exact token → passes the gate (handler returns 200).
    status, _ = _drive(_req("GET", "/api/creators", headers="X-Admin-Token: secret-token-123\r\n"))
    assert status == 200

    # Prefix match (right start, wrong rest) → rejected.
    status, body = _drive(_req("GET", "/api/creators", headers="X-Admin-Token: secret-token-XXX\r\n"))
    assert status == 401 and body["error"] == "admin_token_required"

    # Same length, one byte off → rejected.
    status, body = _drive(_req("GET", "/api/creators", headers="X-Admin-Token: secret-token-124\r\n"))
    assert status == 401 and body["error"] == "admin_token_required"

    # Empty header → rejected.
    status, body = _drive(_req("GET", "/api/creators"))
    assert status == 401 and body["error"] == "admin_token_required"

    # The source must actually use the constant-time primitive.
    import inspect

    src = inspect.getsource(http_router._check_auth)
    assert "compare_digest" in src
    assert "== config.ADMIN_TOKEN" not in src


# ---------- 鉴权 A (B8-3): per-user mapped code pins cost-cap identity ----------


def test_mapped_invite_overrides_spoofed_user_id_for_cost_cap(monkeypatch):
    """The刷钱 fix end-to-end: a request with a per-user MAPPED invite code but a
    spoofed body user_id must charge the cost_guard against the SERVER-derived
    (mapped) identity, not the client's claim."""
    monkeypatch.setattr(config, "INVITE_CODES", frozenset())
    monkeypatch.setattr(config, "INVITE_CODE_MAP", {"alice-code": "alice"})

    seen: dict[str, str] = {}

    async def _capture_guard(user_id: str, run_id: str, predicted: float) -> None:
        seen["user_id"] = user_id

    async def _fake_analysis(source_url: str, *, user_id: str, run_id: str):
        # minimal stand-in so the handler returns without real upstream
        class _C:
            model = "test"
            cost_cny = 0.0

            def model_dump(self, mode="json"):
                return {"analysis_id": "ana_x", "model": "test"}

        return _C()

    monkeypatch.setattr(cost_guard, "cost_guard", _capture_guard)
    monkeypatch.setattr(http_router_mod, "request_shallow_analysis", _fake_analysis)

    status, _ = _drive(
        _req(
            "POST",
            "/api/analysis/shallow",
            headers="X-Invite-Code: alice-code\r\n",
            body={"source_url": "https://example.com/v", "user_id": "attacker-claims-bob"},
        )
    )
    assert status == 200
    # cost_guard must have been keyed on the mapped identity, NOT the spoof
    assert seen["user_id"] == "alice"


def test_shared_invite_keeps_client_user_id(monkeypatch):
    """Shared (non-mapped) code → legacy behavior: client-claimed user_id is used
    (residual gap, documented; closed by issuing per-user codes)."""
    monkeypatch.setattr(config, "INVITE_CODES", frozenset({"SHARED"}))
    monkeypatch.setattr(config, "INVITE_CODE_MAP", {})

    seen: dict[str, str] = {}

    async def _capture_guard(user_id: str, run_id: str, predicted: float) -> None:
        seen["user_id"] = user_id

    async def _fake_analysis(source_url: str, *, user_id: str, run_id: str):
        class _C:
            model = "test"
            cost_cny = 0.0

            def model_dump(self, mode="json"):
                return {"analysis_id": "ana_x", "model": "test"}

        return _C()

    monkeypatch.setattr(cost_guard, "cost_guard", _capture_guard)
    monkeypatch.setattr(http_router_mod, "request_shallow_analysis", _fake_analysis)

    status, _ = _drive(
        _req(
            "POST",
            "/api/analysis/shallow",
            headers="X-Invite-Code: SHARED\r\n",
            body={"source_url": "https://example.com/v", "user_id": "claimed-self"},
        )
    )
    assert status == 200
    assert seen["user_id"] == "claimed-self"


def test_admin_route_fail_closed_in_prod_without_token(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    monkeypatch.setattr(config, "IS_PROD_LIKE", True)
    status, body = _drive(_req("GET", "/api/events"))
    assert status == 403 and body["error"] == "admin_not_configured"


def test_cohort_route_requires_invite_code_when_configured(monkeypatch):
    # Stub emit so the test exercises the auth gate, not event-schema validation.
    from agent.transport import http_router

    async def _noop_emit(*a, **k):
        return None

    monkeypatch.setattr(http_router, "emit", _noop_emit)
    monkeypatch.setattr(config, "INVITE_CODES", frozenset({"GOOD"}))
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    monkeypatch.setattr(config, "IS_PROD_LIKE", False)
    ev = {"event_name": "consent_accepted", "user_id": "u1", "payload": {}}
    # Missing / wrong code → 401, handler not reached
    status, body = _drive(_req("POST", "/api/events", body=ev))
    assert status == 401 and body["error"] == "invite_code_required"
    status, body = _drive(_req("POST", "/api/events", headers="X-Invite-Code: BAD\r\n", body=ev))
    assert status == 401
    # Valid code → handler runs
    status, body = _drive(_req("POST", "/api/events", headers="X-Invite-Code: GOOD\r\n", body=ev))
    assert status == 200 and body == {"ok": True}


def test_cohort_route_open_when_invite_codes_empty(monkeypatch):
    # Dev/test parity: empty INVITE_CODES disables the cohort gate.
    from agent.transport import http_router

    async def _noop_emit(*a, **k):
        return None

    monkeypatch.setattr(http_router, "emit", _noop_emit)
    monkeypatch.setattr(config, "INVITE_CODES", frozenset())
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    monkeypatch.setattr(config, "IS_PROD_LIKE", False)
    ev = {"event_name": "consent_accepted", "user_id": "u1", "payload": {}}
    status, body = _drive(_req("POST", "/api/events", body=ev))
    assert status == 200 and body == {"ok": True}
