"""transport/notify.py unit tests.

_ws_registry + register/unregister + notify_user/_safe_notify。
worker pipelines 调 notify_user 把 canvas_updated 推回前端 — 是 worker→UI 的唯一通路。
"""

from __future__ import annotations

import asyncio
import json

import pytest
from websockets.exceptions import ConnectionClosedOK

from agent.transport import notify
from agent.transport.notify import _safe_notify, notify_user, register, unregister


class FakeWS:
    """支持 async send + 可选 raise — 模拟正常/断开两种状态。"""

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
    def test_register_adds_user(self):
        ws = FakeWS()
        register("u1", ws)
        assert notify._ws_registry == {"u1": ws}

    def test_register_overwrites_existing(self):
        ws1 = FakeWS()
        ws2 = FakeWS()
        register("u1", ws1)
        register("u1", ws2)
        assert notify._ws_registry["u1"] is ws2

    def test_unregister_removes_user(self):
        ws = FakeWS()
        register("u1", ws)
        unregister("u1")
        assert "u1" not in notify._ws_registry

    def test_unregister_missing_user_silent(self):
        # unregister 不存在的 user 不应 raise(connection close 时常见)
        unregister("u_never_existed")
        assert notify._ws_registry == {}


# ---------- notify_user ----------


class TestNotifyUser:
    def test_registered_user_creates_task(self):
        """notify_user 应 schedule 一个 _safe_notify task 走 ws.send。"""
        ws = FakeWS()
        register("u1", ws)

        async def driver():
            notify_user("u1", "t1")
            # 给 asyncio.create_task 一个 tick 跑
            await asyncio.sleep(0)

        asyncio.run(driver())
        # _safe_notify 内部 canvas_data 对空 thread 返 None,但 send_json 仍发一帧
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "canvas_updated"
        assert ws.sent[0]["thread_id"] == "t1"

    def test_unregistered_user_no_send(self, capsys):
        # 没注册 → 直接 print skip 而不是 raise
        notify_user("u_missing", "t1")
        captured = capsys.readouterr()
        assert "未连接" in captured.out
        assert "u_missing" in captured.out


# ---------- _safe_notify ----------


class TestSafeNotify:
    def test_happy_path_sends_canvas_updated(self):
        ws = FakeWS()
        asyncio.run(_safe_notify(ws, "t1"))
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "canvas_updated"

    def test_swallows_connection_closed(self):
        """ConnectionClosedOK 不应冒泡 — 客户端正常关闭时 worker 不该崩。"""
        ws = FakeWS(raise_on_send=ConnectionClosedOK(None, None))
        # 不应 raise
        asyncio.run(_safe_notify(ws, "t1"))

    def test_swallows_generic_exception(self):
        """任何 send 异常都不应冒泡(notify 是 fire-and-forget)。"""
        ws = FakeWS(raise_on_send=RuntimeError("ws closed"))
        asyncio.run(_safe_notify(ws, "t1"))
