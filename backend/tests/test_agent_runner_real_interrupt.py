"""P2 审核闸门 — 真实栈集成测试。

其他闸门测试用 *fake* agent(手写 aget_state)。这里用**真的** deepagents
create_deep_agent + 真的 interrupt_on(HumanInTheLoopMiddleware)+ 真的 checkpointer
(MemorySaver),只把 LLM 换成脚本化假模型。验证:
- 真的 LangGraph interrupt 在工具执行前触发,
- run_agent 经由 _drive_turn 的 aget_state 真的检测到暂停 → 推 review_required,
- resume_agent 用真的 Command(resume) 续跑、工具真的执行。

闭合「fake aget_state 单测」与「真实运行时」之间的最后一道缝。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, List

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from deepagents import create_deep_agent
from agent.transport import agent_runner
from agent.transport.agent_runner import resume_agent, run_agent


class ScriptedToolModel(BaseChatModel):
    """First model turn → call the gated tool; after a tool result exists → final text.
    Supports bind_tools (create_agent calls it)."""

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kw):
        return self

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kw) -> ChatResult:
        has_tool_result = any(getattr(m, "type", "") == "tool" for m in messages)
        if has_tool_result:
            msg = AIMessage(content="已经处理好了")
        else:
            msg = AIMessage(
                content="",
                tool_calls=[{"name": "spend_money", "args": {"amount": 10}, "id": "call_1", "type": "tool_call"}],
            )
        return ChatResult(generations=[ChatGeneration(message=msg)])


_executed: list[int] = []


@tool
def spend_money(amount: int) -> str:
    """Spend money (a gated, costly action)."""
    _executed.append(amount)
    return f"spent {amount}"


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


class RealAgentPool:
    """Returns ONE real compiled deep agent (with interrupt_on + MemorySaver),
    shared across run_agent + resume_agent so the checkpoint persists between them."""

    def __init__(self) -> None:
        self._agent = create_deep_agent(
            model=ScriptedToolModel(),
            system_prompt="spend money when asked",
            tools=[spend_money],
            interrupt_on={"spend_money": {"allowed_decisions": ["approve", "edit", "reject"]}},
            checkpointer=MemorySaver(),
        )

    async def get(self, user_id: str, thread_id: str) -> dict[str, Any]:
        return {"agent": self._agent, "config": {"configurable": {"thread_id": thread_id}}}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    _executed.clear()
    monkeypatch.setattr(agent_runner, "save_message", lambda *a, **k: None)
    monkeypatch.setattr(agent_runner, "canvas_data", lambda thread_id: None)

    async def _noop(*a, **k):
        return 1

    monkeypatch.setattr(agent_runner.run_state, "mark_running", _noop)
    monkeypatch.setattr(agent_runner.run_state, "mark_done", _noop)
    monkeypatch.setattr(agent_runner.run_state, "mark_failed", _noop)
    monkeypatch.setattr(agent_runner.run_state, "mark_awaiting_review", _noop)


def test_real_interrupt_pauses_then_resume_executes_tool():
    """Autonomous gated call → real interrupt → review_required (tool NOT yet run) →
    resume approve → tool actually executes."""
    pool = RealAgentPool()

    async def _flow():
        ws1 = FakeWS()
        await run_agent("u1", pool, "t1", "去把钱花了", ws1)  # autonomous, no marker
        return ws1

    ws1 = asyncio.run(_flow())
    reviews = [m for m in ws1.sent if m["type"] == "review_required"]
    assert len(reviews) == 1, "real interrupt must surface a review_required frame"
    assert reviews[0]["reviews"][0]["tool"] == "spend_money"
    assert [m for m in ws1.sent if m["type"] == "agent_response"] == []
    assert _executed == [], "gated tool must NOT execute before approval"

    # resume approve → tool runs
    ws2 = FakeWS()
    asyncio.run(resume_agent("u1", pool, "t1", [{"type": "approve"}], ws2))
    assert _executed == [10], "approved tool must actually execute on resume"
    assert [m for m in ws2.sent if m["type"] == "agent_response"]


def test_real_interrupt_explicit_marker_auto_approves():
    """Explicit [generate_*] marker → auto-approve → tool runs, NO review card."""
    pool = RealAgentPool()
    ws = FakeWS()
    asyncio.run(run_agent("u1", pool, "t1", "[generate_first_frame: shot_index=1] 花钱", ws))
    assert [m for m in ws.sent if m["type"] == "review_required"] == []
    assert _executed == [10], "explicit click must auto-approve and execute"
    assert [m for m in ws.sent if m["type"] == "agent_response"]


def test_real_interrupt_resume_reject_skips_tool():
    """Resume reject → tool does NOT execute; turn still completes."""
    pool = RealAgentPool()
    asyncio.run(run_agent("u1", pool, "t1", "花钱", FakeWS()))
    assert _executed == []
    ws = FakeWS()
    asyncio.run(resume_agent("u1", pool, "t1", [{"type": "reject", "message": "先别花"}], ws))
    assert _executed == [], "rejected tool must NOT execute"
