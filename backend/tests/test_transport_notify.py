"""transport/notify.py unit tests.

W5D4 P0-A — registry is now user_id → set[ws], and `send_to_user` is the single
out-of-band send path (run frames + worker canvas_updated). These tests pin:
register/unregister on a set, send_to_user fan-out + dead-socket drop + fallback,
and notify_user delegating to send_to_user.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from websockets.exceptions import ConnectionClosedOK

from agent.transport import notify
from agent.transport.notify import notify_user, register, send_to_user, unregister


class FakeWS:
    """支持 async send + 可选 raise — 模拟正常/断开两种状态。

    send_json calls `ws.send(json_str)`, so we accept the serialized frame.
    """

    def __init__(self, *, raise_on_send: Exception | None = None) -> None:
        self.sent: list[dict] = []
        self.raise_on_send = raise_on_send

    async def send(self, data: str) -> None:
        if self.raise_on_send:
            raise self.raise_on_send
        self.sent.append(json.loads(data))


@pytest.fixture(autouse=True)
def _clean_registry(monkeypatch):
    """每个 test 隔离 _ws_registry,避免互相污染。"""
    monkeypatch.setattr(notify, "_ws_registry", {})
    yield


# ---------- register / unregister ----------


class TestRegistry:
    def test_register_adds_user_as_set(self):
        ws = FakeWS()
        register("u1", ws)
        assert notify._ws_registry == {"u1": {ws}}

    def test_register_keeps_multiple_sockets(self):
        ws1, ws2 = FakeWS(), FakeWS()
        register("u1", ws1)
        register("u1", ws2)
        assert notify._ws_registry["u1"] == {ws1, ws2}

    def test_unregister_removes_only_that_socket(self):
        ws1, ws2 = FakeWS(), FakeWS()
        register("u1", ws1)
        register("u1", ws2)
        unregister("u1", ws1)
        assert notify._ws_registry["u1"] == {ws2}  # ws2 (a live reconnect) survives

    def test_unregister_last_socket_drops_key(self):
        ws = FakeWS()
        register("u1", ws)
        unregister("u1", ws)
        assert "u1" not in notify._ws_registry

    def test_unregister_none_clears_all(self):
        register("u1", FakeWS())
        register("u1", FakeWS())
        unregister("u1")  # back-compat: ws=None clears all
        assert "u1" not in notify._ws_registry

    def test_unregister_missing_user_silent(self):
        unregister("u_never_existed", FakeWS())
        assert notify._ws_registry == {}


# ---------- send_to_user ----------


class TestSendToUser:
    def test_delivers_to_all_live_sockets(self):
        ws1, ws2 = FakeWS(), FakeWS()
        register("u1", ws1)
        register("u1", ws2)
        n = asyncio.run(send_to_user("u1", {"type": "ping", "thread_id": "t1"}))
        assert n == 2
        assert ws1.sent[0]["type"] == "ping" and ws2.sent[0]["type"] == "ping"

    def test_drops_dead_socket_from_registry(self):
        live = FakeWS()
        dead = FakeWS(raise_on_send=ConnectionClosedOK(None, None))
        register("u1", live)
        register("u1", dead)
        n = asyncio.run(send_to_user("u1", {"type": "ping", "thread_id": "t1"}))
        assert n == 1  # only live delivered
        assert notify._ws_registry["u1"] == {live}  # dead pruned

    def test_no_registered_socket_uses_fallback(self):
        fb = FakeWS()
        n = asyncio.run(send_to_user("u1", {"type": "ping", "thread_id": "t1"}, fallback_ws=fb))
        assert n == 1 and fb.sent[0]["type"] == "ping"

    def test_live_socket_means_fallback_not_used(self):
        # The core P0-A invariant: never send to a (possibly dead) captured
        # fallback ws while a live registered socket exists.
        live = FakeWS()
        fb = FakeWS()
        register("u1", live)
        n = asyncio.run(send_to_user("u1", {"type": "ping", "thread_id": "t1"}, fallback_ws=fb))
        assert n == 1
        assert live.sent and not fb.sent

    def test_no_socket_no_fallback_returns_zero(self):
        n = asyncio.run(send_to_user("u_missing", {"type": "ping", "thread_id": "t1"}))
        assert n == 0


# ---------- notify_user (worker path delegates to send_to_user) ----------


class TestNotifyUser:
    def test_registered_user_delivers_canvas_updated(self):
        ws = FakeWS()
        register("u1", ws)

        async def driver():
            notify_user("u1", "t1")
            await asyncio.sleep(0)  # let the created task run

        asyncio.run(driver())
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "canvas_updated"
        assert ws.sent[0]["thread_id"] == "t1"

    def test_unregistered_user_no_send(self, capsys):
        notify_user("u_missing", "t1")
        captured = capsys.readouterr()
        assert "未连接" in captured.out and "u_missing" in captured.out
