"""`handle_user_message` 单元测试 — 验证 niche 字段端到端打通。

`selected_niche` 走 WS → handler → agent_runner.run_agent 的链路是新加的;
我们 mock run_agent 和 emit,只盯 handler 是否正确把字段透传 + 发了 telemetry。
"""

from __future__ import annotations

import asyncio
import json

import pytest

from agent.cascade import events as cascade_events
from agent.cascade.event_names import EventName
from agent.transport import agent_runner, ws_handlers
from agent.transport.context import WSCtx
from agent.transport.ws_messages import UserMessageMsg


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


class FakePool:
    """run_agent 被 mock 掉了,这里只是给 WSCtx 凑一个 attr。"""


@pytest.fixture
def captured_runner(monkeypatch):
    """Capture run_agent 调用参数 — handler 透传必须可观测。

    handler 用 `asyncio.create_task` 启 run_agent,我们替换为同步 coro 直接 await
    便于断言;另保留实际 args/kwargs。
    """
    calls: list[dict] = []

    async def _capture(user_id, pool, thread_id, content, ws, *, selected_niche=None, agent_prefix=""):
        calls.append({
            "user_id": user_id,
            "thread_id": thread_id,
            "content": content,
            "selected_niche": selected_niche,
        })

    monkeypatch.setattr(agent_runner, "run_agent", _capture)
    return calls


@pytest.fixture
def captured_emit(monkeypatch):
    """Capture telemetry emit — handler 应在 niche 非 None 时打一条 niche_selected。"""
    calls: list[dict] = []

    async def _capture(event_name, *, user_id, run_id, payload):
        calls.append({
            "event_name": event_name,
            "user_id": user_id,
            "run_id": run_id,
            "payload": payload,
        })

    monkeypatch.setattr(cascade_events, "emit", _capture)
    return calls


def _run(coro):
    return asyncio.run(coro)


class TestHandleUserMessageNiche:
    def test_passes_selected_niche_to_runner(self, captured_runner, captured_emit):
        """handler 必须把 msg.selected_niche 透传给 run_agent。"""
        ws = FakeWS()
        ctx = WSCtx(user_id="u1", ws=ws, pool=FakePool())
        msg = UserMessageMsg.model_validate({
            "type": "user_message",
            "thread_id": "t1",
            "content": "改写这条",
            "selected_niche": "jiating_chufang",
        })

        _run(ws_handlers.handle_user_message(ctx, msg))
        # handler 用 create_task,等 loop drain
        _run(asyncio.sleep(0))

        # 至少有一次 run_agent 调用,且带着 niche
        assert len(captured_runner) == 1
        call = captured_runner[0]
        assert call["selected_niche"] == "jiating_chufang"
        assert call["user_id"] == "u1"
        assert call["thread_id"] == "t1"
        assert call["content"] == "改写这条"

    def test_no_niche_passes_none(self, captured_runner, captured_emit):
        """老客户端不带字段时,run_agent 收到 None,不该报错。"""
        ws = FakeWS()
        ctx = WSCtx(user_id="u1", ws=ws, pool=FakePool())
        msg = UserMessageMsg.model_validate({
            "type": "user_message",
            "thread_id": "t1",
            "content": "hi",
        })

        _run(ws_handlers.handle_user_message(ctx, msg))
        _run(asyncio.sleep(0))

        assert len(captured_runner) == 1
        assert captured_runner[0]["selected_niche"] is None
        # 没有 niche 就不该发 telemetry — 避免 /admin/events 噪音
        assert captured_emit == []

    def test_emits_niche_selected_event_when_present(self, captured_runner, captured_emit):
        """有 niche 时打一条 niche_selected 事件,带 {niche, thread_id}。"""
        ws = FakeWS()
        ctx = WSCtx(user_id="u1", ws=ws, pool=FakePool())
        msg = UserMessageMsg.model_validate({
            "type": "user_message",
            "thread_id": "t-xyz",
            "content": "go",
            "selected_niche": "baomam_fushi",
        })

        _run(ws_handlers.handle_user_message(ctx, msg))
        _run(asyncio.sleep(0))

        assert len(captured_emit) == 1
        ev = captured_emit[0]
        assert ev["event_name"] == EventName.NICHE_SELECTED
        assert ev["user_id"] == "u1"
        assert ev["payload"] == {"niche": "baomam_fushi", "thread_id": "t-xyz"}

    def test_processing_frame_sent(self, captured_runner, captured_emit):
        """handler 仍要发 processing 帧,不然前端看不到 loading 状态。"""
        ws = FakeWS()
        ctx = WSCtx(user_id="u1", ws=ws, pool=FakePool())
        msg = UserMessageMsg.model_validate({
            "type": "user_message",
            "thread_id": "t1",
            "content": "hi",
            "selected_niche": "yuer_richang",
        })

        _run(ws_handlers.handle_user_message(ctx, msg))
        _run(asyncio.sleep(0))

        # 至少有一条 processing 帧
        processing = [m for m in ws.sent if m.get("type") == "processing"]
        assert len(processing) == 1
        assert processing[0]["thread_id"] == "t1"

    def test_emit_failure_does_not_block_runner(self, captured_runner, monkeypatch):
        """telemetry 是 best-effort — emit 抛错时 run_agent 必须照常调用。"""

        async def _explode(*args, **kwargs):
            raise RuntimeError("storage down")

        monkeypatch.setattr(cascade_events, "emit", _explode)

        ws = FakeWS()
        ctx = WSCtx(user_id="u1", ws=ws, pool=FakePool())
        msg = UserMessageMsg.model_validate({
            "type": "user_message",
            "thread_id": "t1",
            "content": "hi",
            "selected_niche": "jiating_chufang",
        })

        _run(ws_handlers.handle_user_message(ctx, msg))
        _run(asyncio.sleep(0))

        # emit 炸了不应阻止 run_agent
        assert len(captured_runner) == 1
        assert captured_runner[0]["selected_niche"] == "jiating_chufang"
