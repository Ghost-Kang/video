"""P2 审核闸门 — WS 层:reconnect 重放审核卡 + review_decision 路由 + 闸门开关契约。

- `_maybe_replay_review`:断线重连后从 checkpoint(aget_state)把待审核卡重新推给前端
  (reconnect-safety,呼应「卡 95%」复盘:暂停态不能在断线后丢)。
- `handle_review_decision`:回 processing ack + 后台串行 resume(镜像 user_message)。
- `build_interrupt_on`:CANVAS_INTERRUPT_GATE 开关决定挂不挂闸门(默认 OFF=行为不变)。
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from agent.transport import ws_handlers
from agent.transport.context import WSCtx
from agent.transport.ws_handlers import _maybe_replay_review, handle_review_decision, handle_user_message
from agent.transport.ws_messages import ReviewDecisionMsg, UserMessageMsg


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


class PausedAgent:
    """aget_state reports a pending interrupt (paused at a gate)."""

    def __init__(self, pending: bool = True) -> None:
        self._pending = pending

    async def aget_state(self, config):
        if self._pending:
            hitl = {
                "action_requests": [
                    {"name": "cascade_generate_first_frame", "args": {"rewrite_id": "rw_1", "shot_index": 4}, "description": "x"}
                ],
                "review_configs": [
                    {"action_name": "cascade_generate_first_frame", "allowed_decisions": ["approve", "edit", "reject"]}
                ],
            }
            return SimpleNamespace(interrupts=(SimpleNamespace(value=hitl, id="i1"),))
        return SimpleNamespace(interrupts=())


class FakePool:
    def __init__(self, agent) -> None:
        self._agent = agent
        self.got: list[tuple[str, str]] = []

    async def get(self, user_id: str, thread_id: str) -> dict[str, Any]:
        self.got.append((user_id, thread_id))
        return {"agent": self._agent, "config": {"thread_id": thread_id}}


class TestReplayReview:
    def test_replays_card_when_paused(self):
        ctx = WSCtx(user_id="u1", ws=FakeWS(), pool=FakePool(PausedAgent(pending=True)))
        asyncio.run(_maybe_replay_review(ctx, "t1"))
        cards = [m for m in ctx.ws.sent if m["type"] == "review_required"]
        assert len(cards) == 1
        assert cards[0]["thread_id"] == "t1"
        assert cards[0]["reviews"][0]["tool"] == "cascade_generate_first_frame"
        assert "镜头 4" in cards[0]["reviews"][0]["label"]

    def test_silent_when_no_pending_interrupt(self):
        ctx = WSCtx(user_id="u1", ws=FakeWS(), pool=FakePool(PausedAgent(pending=False)))
        asyncio.run(_maybe_replay_review(ctx, "t1"))
        assert [m for m in ctx.ws.sent if m["type"] == "review_required"] == []

    def test_replay_never_raises_on_pool_error(self):
        class BoomPool:
            async def get(self, user_id, thread_id):
                raise RuntimeError("pool down")

        ctx = WSCtx(user_id="u1", ws=FakeWS(), pool=BoomPool())
        # best-effort: must swallow, never propagate (replay can't block session_state)
        asyncio.run(_maybe_replay_review(ctx, "t1"))
        assert ctx.ws.sent == []


class TestReviewDecisionRouting:
    def test_acks_processing_and_spawns_resume(self, monkeypatch):
        resumed: list[tuple] = []

        async def _fake_resume(user_id, pool, thread_id, decisions, ws, interrupt_id=""):
            resumed.append((user_id, thread_id, decisions, interrupt_id))

        monkeypatch.setattr(ws_handlers.agent_runner, "resume_agent", _fake_resume)

        async def _run() -> FakeWS:
            ctx = WSCtx(user_id="u1", ws=FakeWS(), pool=FakePool(PausedAgent()))
            msg = ReviewDecisionMsg(
                type="review_decision", thread_id="t1",
                decisions=[{"type": "approve"}], interrupt_id="int_1",
            )
            await handle_review_decision(ctx, msg)
            # let the spawned background resume task run to completion
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return ctx.ws

        ws = asyncio.run(_run())
        assert [m for m in ws.sent if m["type"] == "processing"]
        # interrupt_id must be threaded through to resume_agent (review #3 binding)
        assert resumed == [("u1", "t1", [{"type": "approve"}], "int_1")]


class TestUserMessageGuardWhileAwaitingReview:
    """review #2 — a new user_message while a gate is pending must be refused
    (else it discards the interrupt and a later approve no-ops)."""

    def test_refuses_user_message_while_awaiting_review(self, monkeypatch):
        ran: list = []

        async def _spy_run(*a, **k):
            ran.append(a)

        monkeypatch.setattr(ws_handlers.agent_runner, "run_agent", _spy_run)
        monkeypatch.setattr(ws_handlers.run_state, "get", lambda tid: {"status": "awaiting_review"})

        async def _run() -> FakeWS:
            ctx = WSCtx(user_id="u1", ws=FakeWS(), pool=FakePool(PausedAgent()))
            msg = UserMessageMsg(type="user_message", thread_id="t1", content="另起一句")
            await handle_user_message(ctx, msg)
            await asyncio.sleep(0)
            return ctx.ws

        ws = asyncio.run(_run())
        # refused with a review_pending error; the agent was NOT run.
        errs = [m for m in ws.sent if m["type"] == "error"]
        assert errs and errs[0]["code"] == "review_pending"
        assert ran == []

    def test_allows_user_message_when_not_awaiting(self, monkeypatch):
        ran: list = []

        async def _spy_run(*a, **k):
            ran.append(a)

        monkeypatch.setattr(ws_handlers.agent_runner, "run_agent", _spy_run)
        monkeypatch.setattr(ws_handlers.run_state, "get", lambda tid: {"status": "done"})

        async def _run() -> FakeWS:
            ctx = WSCtx(user_id="u1", ws=FakeWS(), pool=FakePool(PausedAgent()))
            msg = UserMessageMsg(type="user_message", thread_id="t1", content="正常一句")
            await handle_user_message(ctx, msg)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return ctx.ws

        ws = asyncio.run(_run())
        assert [m for m in ws.sent if m["type"] == "processing"]
        assert len(ran) == 1  # agent ran normally


class TestInterruptGateFlag:
    def test_flag_off_returns_none(self, monkeypatch):
        import agent.config as config
        from agent.main import build_interrupt_on

        monkeypatch.setattr(config, "CANVAS_INTERRUPT_GATE", False)
        assert build_interrupt_on() is None

    def test_flag_on_gates_generation_tools(self, monkeypatch):
        import agent.config as config
        from agent.main import build_interrupt_on

        monkeypatch.setattr(config, "CANVAS_INTERRUPT_GATE", True)
        monkeypatch.setattr(
            config, "INTERRUPT_GATE_TOOLS",
            frozenset({"cascade_generate_first_frame", "cascade_generate_shot_video", "cascade_compose_film"}),
        )
        cfg = build_interrupt_on()
        assert set(cfg) == {"cascade_generate_first_frame", "cascade_generate_shot_video", "cascade_compose_film"}
        assert cfg["cascade_generate_first_frame"]["allowed_decisions"] == ["approve", "edit", "reject"]
