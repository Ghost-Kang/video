"""P2 审核闸门(LangGraph interrupt)— run_agent / resume_agent 闸门行为测试。

覆盖 canvas 统筹 P2 slice-1 的核心契约:
- Director **自主**调生成工具 → graph 暂停 → 推 review_required + 标 awaiting_review,
  **不**发 agent_response(回合没结束,等用户决策)。
- 用户**显式**点生成([generate_*] 标记)→ 自动批准,不弹审核卡。
- resume_agent(approve/reject)把决策透传给 graph 续跑。
- 无 pending interrupt 时 resume 是 no-op(防双击/陈旧 resume 把上一回合重跑)。

FakeAgent 模拟 HumanInTheLoopMiddleware:首回合产出受拦工具调用 + aget_state 报
interrupt;收到 Command(resume) 后续跑、aget_state 清空。完全屏蔽 langchain/模型。
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import AIMessageChunk
from langgraph.types import Command

from agent.transport import agent_runner
from agent.transport.agent_runner import (
    _build_review_frame,
    _is_explicit_generation,
    resume_agent,
    run_agent,
)


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


class InterruptingAgent:
    """First turn proposes a gated tool call and PAUSES (aget_state.interrupts
    non-empty, mirroring HumanInTheLoopMiddleware.after_model → interrupt). A
    Command(resume) input continues (emits text, clears the interrupt). Records
    resume payloads for assertions."""

    def __init__(self, tool_name: str = "cascade_generate_first_frame", args: dict | None = None) -> None:
        self.tool_name = tool_name
        self.args = args if args is not None else {"rewrite_id": "rw_1", "shot_index": 2}
        self.resumes: list[Any] = []
        self._paused = False

    async def astream(self, agent_input, *, config, stream_mode, version):
        assert stream_mode == "messages"
        assert version == "v2"
        if isinstance(agent_input, Command):
            self.resumes.append(agent_input.resume)
            self._paused = False
            yield {"data": (AIMessageChunk(content="好的，已处理"), {})}
        else:
            # initial turn → propose the gated tool, then pause.
            self._paused = True
            yield {
                "data": (
                    AIMessageChunk(
                        content="",
                        tool_calls=[{"name": self.tool_name, "args": self.args, "id": "c1"}],
                    ),
                    {},
                )
            }

    async def aget_state(self, config):
        if self._paused:
            hitl = {
                "action_requests": [
                    {"name": self.tool_name, "args": self.args, "description": "Tool execution requires approval"}
                ],
                "review_configs": [
                    {"action_name": self.tool_name, "allowed_decisions": ["approve", "edit", "reject"]}
                ],
            }
            return SimpleNamespace(interrupts=(SimpleNamespace(value=hitl, id="int_1"),))
        return SimpleNamespace(interrupts=())


class FakePool:
    def __init__(self, agent) -> None:
        self._agent = agent

    async def get(self, user_id: str, thread_id: str) -> dict[str, Any]:
        return {"agent": self._agent, "config": {"thread_id": thread_id}}


@pytest.fixture
def saved_messages(monkeypatch):
    calls: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        agent_runner, "save_message",
        lambda user_id, thread_id, role, content: calls.append((user_id, thread_id, role, content)),
    )
    return calls


@pytest.fixture
def stub_canvas_data(monkeypatch):
    monkeypatch.setattr(agent_runner, "canvas_data", lambda thread_id: None)


@pytest.fixture
def lifecycle(monkeypatch):
    """Capture run_state.mark_* (running/done/failed/awaiting_review) without DB."""
    calls: list[tuple[str, Any]] = []

    async def _running(user_id, thread_id):
        calls.append(("running", thread_id))
        return 1

    async def _done(thread_id):
        calls.append(("done", thread_id))

    async def _failed(thread_id, failure):
        calls.append(("failed", failure))

    async def _awaiting(thread_id):
        calls.append(("awaiting_review", thread_id))

    monkeypatch.setattr(agent_runner.run_state, "mark_running", _running)
    monkeypatch.setattr(agent_runner.run_state, "mark_done", _done)
    monkeypatch.setattr(agent_runner.run_state, "mark_failed", _failed)
    monkeypatch.setattr(agent_runner.run_state, "mark_awaiting_review", _awaiting)
    return calls


# ---------- helpers (pure) ----------


class TestHelpers:
    def test_is_explicit_generation_markers(self):
        assert _is_explicit_generation("[generate_first_frame: shot_index=2]")
        assert _is_explicit_generation("[generate_shot_video: shot_index=3]")
        assert _is_explicit_generation("[compose_film]")
        assert _is_explicit_generation("  [compose_film] 现在合成")  # leading ws tolerated
        # free-form chat is NOT an explicit click
        assert not _is_explicit_generation("把整个脚本都生成出来")
        assert not _is_explicit_generation("")
        assert not _is_explicit_generation("帮我生成首帧")

    def test_build_review_frame_shapes_card(self):
        hitl = {
            "action_requests": [
                {"name": "cascade_generate_shot_video", "args": {"rewrite_id": "rw_1", "shot_index": 3}, "description": "x"}
            ],
            "review_configs": [
                {"action_name": "cascade_generate_shot_video", "allowed_decisions": ["approve", "reject"]}
            ],
        }
        frame = _build_review_frame("t1", hitl)
        assert frame["type"] == "review_required"
        assert frame["thread_id"] == "t1"
        assert len(frame["reviews"]) == 1
        r = frame["reviews"][0]
        assert r["tool"] == "cascade_generate_shot_video"
        assert "镜头 3" in r["label"]
        assert r["args"] == {"rewrite_id": "rw_1", "shot_index": 3}
        assert r["allowed_decisions"] == ["approve", "reject"]
        assert "待你确认" in frame["summary"]


# ---------- autonomous gate → pause ----------


class TestAutonomousGate:
    def test_autonomous_call_pauses_and_pushes_review(self, saved_messages, stub_canvas_data, lifecycle):
        agent = InterruptingAgent()
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(agent), "t1", "把整个脚本都生成出来", ws))

        reviews = [m for m in ws.sent if m["type"] == "review_required"]
        assert len(reviews) == 1
        assert reviews[0]["reviews"][0]["tool"] == "cascade_generate_first_frame"
        assert "镜头 2" in reviews[0]["reviews"][0]["label"]

        # paused turn must NOT look finished: no agent_response, lifecycle awaiting_review.
        assert [m for m in ws.sent if m["type"] == "agent_response"] == []
        statuses = [c[0] for c in lifecycle]
        assert statuses == ["running", "awaiting_review"]
        assert "done" not in statuses
        # graph not resumed yet
        assert agent.resumes == []

    def test_paused_then_resume_approve_runs_tool(self, saved_messages, stub_canvas_data, lifecycle):
        agent = InterruptingAgent()
        pool = FakePool(agent)
        # 1) autonomous turn pauses
        asyncio.run(run_agent("u1", pool, "t1", "一条龙全做了", FakeWS()))
        # 2) user approves → resume
        ws2 = FakeWS()
        asyncio.run(resume_agent("u1", pool, "t1", [{"type": "approve"}], ws2))

        assert agent.resumes == [{"decisions": [{"type": "approve"}]}]
        # resumed turn completes with a normal agent_response
        finals = [m for m in ws2.sent if m["type"] == "agent_response"]
        assert len(finals) == 1
        assert finals[0]["content"] == "好的，已处理"
        # lifecycle: ...awaiting_review (run1) then running+done (run2)
        assert lifecycle[-1] == ("done", "t1")

    def test_resume_reject_passes_decision_through(self, saved_messages, stub_canvas_data, lifecycle):
        agent = InterruptingAgent()
        pool = FakePool(agent)
        asyncio.run(run_agent("u1", pool, "t1", "都生成", FakeWS()))
        asyncio.run(resume_agent("u1", pool, "t1", [{"type": "reject", "message": "先不生成"}], FakeWS()))
        assert agent.resumes == [{"decisions": [{"type": "reject", "message": "先不生成"}]}]


# ---------- explicit click → auto-approve ----------


class TestExplicitMarkerAutoApprove:
    def test_explicit_marker_auto_approves_no_review_card(self, saved_messages, stub_canvas_data, lifecycle):
        agent = InterruptingAgent()
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(agent), "t1", "[generate_first_frame: shot_index=2]", ws))

        # gate auto-approved → no review card surfaced to the user
        assert [m for m in ws.sent if m["type"] == "review_required"] == []
        # the gate WAS approved under the hood (one resume w/ one approve decision)
        assert agent.resumes == [{"decisions": [{"type": "approve"}]}]
        # turn finishes normally
        assert [m for m in ws.sent if m["type"] == "agent_response"]
        assert [c[0] for c in lifecycle][-1] == "done"


# ---------- resume guard ----------


class TestResumeGuard:
    def test_resume_without_pending_interrupt_is_noop(self, saved_messages, stub_canvas_data, lifecycle):
        agent = InterruptingAgent()  # never paused (no prior run)
        ws = FakeWS()
        asyncio.run(resume_agent("u1", FakePool(agent), "t1", [{"type": "approve"}], ws))

        # never resumed the graph (would otherwise re-run the last user turn)
        assert agent.resumes == []
        # gracefully marked done + synced canvas (no agent_response)
        assert [c[0] for c in lifecycle][-1] == "done"
        assert [m for m in ws.sent if m["type"] == "canvas_updated"]
        assert [m for m in ws.sent if m["type"] == "agent_response"] == []

    def test_review_required_frame_carries_interrupt_id(self, saved_messages, stub_canvas_data, lifecycle):
        agent = InterruptingAgent()
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(agent), "t1", "都生成", ws))
        card = [m for m in ws.sent if m["type"] == "review_required"][0]
        assert card["interrupt_id"] == "int_1"  # bound to the LangGraph interrupt

    def test_matching_interrupt_id_resumes(self, saved_messages, stub_canvas_data, lifecycle):
        agent = InterruptingAgent()
        pool = FakePool(agent)
        asyncio.run(run_agent("u1", pool, "t1", "都生成", FakeWS()))
        asyncio.run(resume_agent("u1", pool, "t1", [{"type": "approve"}], FakeWS(), interrupt_id="int_1"))
        assert agent.resumes == [{"decisions": [{"type": "approve"}]}]

    def test_stale_interrupt_id_does_not_resume_and_repushes_card(self, saved_messages, stub_canvas_data, lifecycle):
        """review #3 — a decision made for an already-resolved gate must NOT be
        applied to the (different) currently-pending gate. Drop it + re-push."""
        agent = InterruptingAgent()  # pending gate id == "int_1"
        pool = FakePool(agent)
        asyncio.run(run_agent("u1", pool, "t1", "都生成", FakeWS()))
        ws = FakeWS()
        asyncio.run(resume_agent("u1", pool, "t1", [{"type": "approve"}], ws, interrupt_id="STALE_OTHER"))

        assert agent.resumes == [], "stale decision must not resume the graph"
        cards = [m for m in ws.sent if m["type"] == "review_required"]
        assert len(cards) == 1 and cards[0]["interrupt_id"] == "int_1"
        assert [c[0] for c in lifecycle][-1] == "awaiting_review"


# ---------- review #1: tool failure wins over a pending review ----------


class ToolFailThenPauseAgent:
    """A non-gated tool failed (set tool_failure on the ctx) AND the LLM then
    autonomously proposed a gated tool → interrupt. The failure must win."""

    def __init__(self) -> None:
        self.failure = {
            "code": "S8_UPSTREAM_REFUSED",
            "hint": "上游忙,换条链接重试",
            "actions": ["RETRY_WITH_NEW_URL"],
            "request_id": "",
        }
        self._paused = False
        self.resumes: list = []

    async def astream(self, agent_input, *, config, stream_mode, version):
        from agent.transport.runtime_ctx import get_run_ctx

        if isinstance(agent_input, Command):
            self.resumes.append(agent_input.resume)
            self._paused = False
            yield {"data": (AIMessageChunk(content="x"), {})}
        else:
            get_run_ctx()["tool_failure"] = self.failure  # non-gated tool failed
            self._paused = True
            yield {
                "data": (
                    AIMessageChunk(
                        content="",
                        tool_calls=[{"name": "cascade_generate_first_frame", "args": {"shot_index": 1}, "id": "c1"}],
                    ),
                    {},
                )
            }

    async def aget_state(self, config):
        if self._paused:
            hitl = {
                "action_requests": [{"name": "cascade_generate_first_frame", "args": {"shot_index": 1}, "description": "x"}],
                "review_configs": [{"action_name": "cascade_generate_first_frame", "allowed_decisions": ["approve", "reject"]}],
            }
            return SimpleNamespace(interrupts=(SimpleNamespace(value=hitl, id="i1"),))
        return SimpleNamespace(interrupts=())


class TestToolFailureWinsOverReview:
    def test_tool_failure_marks_failed_not_awaiting_review(self, saved_messages, stub_canvas_data, lifecycle):
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(ToolFailThenPauseAgent()), "t1", "分析并生成", ws))

        statuses = [c[0] for c in lifecycle]
        assert statuses[-1] == "failed", "a recorded tool failure must win over a pending review"
        assert "awaiting_review" not in statuses
        # no review card surfaced (the failure is terminal, recovery payload preserved)
        assert [m for m in ws.sent if m["type"] == "review_required"] == []
        failed_payload = [c[1] for c in lifecycle if c[0] == "failed"][0]
        assert failed_payload["code"] == "S8_UPSTREAM_REFUSED"
