"""agent_runner.run_agent 集成测试 — mock LangChain stream + pool。

`run_agent` 是 user_message handler → LangChain agent 的桥,负责:
- ContextVar 设置(user_id / thread_id)
- save_message 持久化(user + agent 各一次)
- astream chunks → agent_stream 帧(text / tool_call 两种 event)
- 末尾 agent_response 帧(含 canvas snapshot)
- 异常路径:仍 save + 发 agent_response,不让前端 hang

测试用 FakeAgent + FakePool 完全屏蔽 langchain/deepagents 依赖。
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import AIMessageChunk


def _clean_state() -> SimpleNamespace:
    """A StateSnapshot stub with no pending interrupt — models the flag-off /
    no-gate production path. _drive_turn calls aget_state after each stream pass
    to detect interrupts; the fakes must answer it (real CompiledStateGraph does)."""
    return SimpleNamespace(interrupts=())

from agent.tools import canvas as canvas_tools
from agent.transport import agent_runner
from agent.transport.agent_runner import run_agent


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


class FakeAgent:
    """astream 产出预设的 chunk 序列,模拟 LangGraph stream_mode='messages'。

    每个 chunk shape:`{"data": (msg, meta)}`,与真实 langgraph 输出一致。
    """

    def __init__(self, chunks: list[tuple[Any, dict]]) -> None:
        self._chunks = chunks

    async def astream(self, _input, *, config, stream_mode, version):
        # 测试 caller 传的参数符合 run_agent 内部预期
        assert stream_mode == "messages"
        assert version == "v2"
        for msg, meta in self._chunks:
            yield {"data": (msg, meta)}

    async def aget_state(self, config):
        return _clean_state()


class FakePool:
    def __init__(self, agent: FakeAgent) -> None:
        self._agent = agent

    async def get(self, user_id: str, thread_id: str) -> dict[str, Any]:
        # W5D3: pool keyed by (user_id, thread_id) — composite key.
        return {"agent": self._agent, "config": {"thread_id": thread_id}}


@pytest.fixture
def saved_messages(monkeypatch):
    """Capture save_message 调用 — run_agent 应该写 user + agent 两条。"""
    calls: list[tuple[str, str, str, str]] = []

    def _capture(user_id: str, thread_id: str, role: str, content: str) -> None:
        calls.append((user_id, thread_id, role, content))

    monkeypatch.setattr(agent_runner, "save_message", _capture)
    return calls


@pytest.fixture
def stub_canvas_data(monkeypatch):
    """run_agent 末尾会调 canvas_data — stub 成 None 避免触 DB 状态。"""
    monkeypatch.setattr(agent_runner, "canvas_data", lambda thread_id: None)


# ---------- happy path ----------


class TestHappyPath:
    def test_text_stream_emits_agent_stream_text_frames(self, saved_messages, stub_canvas_data):
        chunks = [
            (AIMessageChunk(content="你好"), {}),
            (AIMessageChunk(content=",我是 Cascade"), {}),
        ]
        ws = FakeWS()
        pool = FakePool(FakeAgent(chunks))

        asyncio.run(run_agent("u1", pool, "t1", "请帮我写脚本", ws))

        text_frames = [m for m in ws.sent if m.get("type") == "agent_stream"]
        assert len(text_frames) == 2
        assert text_frames[0] == {
            "type": "agent_stream", "thread_id": "t1", "event": "text", "content": "你好",
        }
        assert text_frames[1]["content"] == ",我是 Cascade"

    def test_final_agent_response_frame_with_joined_text(self, saved_messages, stub_canvas_data):
        chunks = [
            (AIMessageChunk(content="a"), {}),
            (AIMessageChunk(content="b"), {}),
        ]
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(FakeAgent(chunks)), "t1", "hi", ws))

        final = [m for m in ws.sent if m.get("type") == "agent_response"]
        assert len(final) == 1
        assert final[0]["content"] == "ab"
        assert final[0]["thread_id"] == "t1"
        assert final[0]["canvas"] is None  # stub

    def test_save_message_called_for_user_and_agent(self, saved_messages, stub_canvas_data):
        chunks = [(AIMessageChunk(content="ok"), {})]
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(FakeAgent(chunks)), "t1", "请写", ws))

        assert len(saved_messages) == 2
        assert saved_messages[0] == ("u1", "t1", "user", "请写")
        assert saved_messages[1] == ("u1", "t1", "agent", "ok")

    def test_context_vars_set_before_stream(self, saved_messages, stub_canvas_data):
        """ContextVar 必须在 stream 开始前设好,agent tools 才能读到正确 user/thread。

        Note: asyncio.run 创建新 loop,ContextVar 不跨 loop 传回外部 — 所以在
        stream 内部 capture,而不是 asyncio.run 之后断言。
        """
        captured: dict[str, str] = {}

        class CapturingAgent:
            async def astream(self, _input, *, config, stream_mode, version):
                captured["user_id"] = canvas_tools._current_user_id.get()
                captured["thread_id"] = canvas_tools._current_thread_id.get()
                yield {"data": (AIMessageChunk(content="x"), {})}

            async def aget_state(self, config):
                return _clean_state()

        ws = FakeWS()
        pool = FakePool(CapturingAgent())  # type: ignore[arg-type]

        asyncio.run(run_agent("u_target", pool, "t_target", "msg", ws))

        assert captured == {"user_id": "u_target", "thread_id": "t_target"}


# ---------- tool_call 流 ----------


class TestToolCallStream:
    def test_tool_call_chunk_emits_tool_call_frame(self, saved_messages, stub_canvas_data):
        tool_chunk = AIMessageChunk(
            content="",
            tool_calls=[{"name": "create_canvas_node", "args": {"type": "script"}, "id": "call_1"}],
        )
        chunks = [(tool_chunk, {})]
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(FakeAgent(chunks)), "t1", "hi", ws))

        tc_frames = [m for m in ws.sent if m.get("type") == "agent_stream" and m.get("event") == "tool_call"]
        assert len(tc_frames) == 1
        assert tc_frames[0]["name"] == "create_canvas_node"
        # args 走 str() 序列化
        assert "type" in tc_frames[0]["args"]
        assert "script" in tc_frames[0]["args"]

    def test_multiple_tool_calls_in_one_chunk(self, saved_messages, stub_canvas_data):
        tool_chunk = AIMessageChunk(
            content="",
            tool_calls=[
                {"name": "a", "args": {}, "id": "c1"},
                {"name": "b", "args": {}, "id": "c2"},
            ],
        )
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(FakeAgent([(tool_chunk, {})])), "t1", "hi", ws))

        tc_frames = [m for m in ws.sent if m.get("event") == "tool_call"]
        assert [f["name"] for f in tc_frames] == ["a", "b"]


# ---------- 边界 / 异常 ----------


class TestEmptyAndErrorPaths:
    def test_no_text_chunks_yields_placeholder_reply(self, saved_messages, stub_canvas_data):
        """当 stream 全程没有 text content,前端应收到「未生成回复」占位。"""
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(FakeAgent([])), "t1", "hi", ws))

        # 应仍发 agent_response,content 是 fallback
        finals = [m for m in ws.sent if m.get("type") == "agent_response"]
        assert len(finals) == 1
        assert "未生成回复" in finals[0]["content"]
        # 仍 save 一条 agent 消息
        agent_save = [c for c in saved_messages if c[2] == "agent"]
        assert "未生成回复" in agent_save[0][3]

    def test_dedupe_repeated_token_suffix(self, saved_messages, stub_canvas_data):
        """full_reply.endswith(token) 防止重复 token 累加 — 流复读不应放大。"""
        # 两个连续相同 chunk
        chunks = [
            (AIMessageChunk(content="hello"), {}),
            (AIMessageChunk(content="hello"), {}),  # 应被 dedupe 跳过
            (AIMessageChunk(content=" world"), {}),
        ]
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(FakeAgent(chunks)), "t1", "hi", ws))

        final = [m for m in ws.sent if m.get("type") == "agent_response"][0]
        assert final["content"] == "hello world"

    def test_stream_exception_pushes_structured_failure(self, saved_messages, stub_canvas_data):
        """W5D3 Bug #4 — astream 抛异常时,改推 analysis_failed + canvas_updated,
        不再把 raw exception 灌进 agent_response chat 历史(怕泄漏文件路径/内部 URL)。"""

        class ExplodingAgent:
            async def astream(self, _input, *, config, stream_mode, version):
                yield {"data": (AIMessageChunk(content="partial"), {})}
                raise RuntimeError("upstream gone")

        ws = FakeWS()
        pool = FakePool(ExplodingAgent())  # type: ignore[arg-type]
        # run_agent 内部 try/except 接住,不应冒泡
        asyncio.run(run_agent("u1", pool, "t1", "hi", ws))

        # 新契约:不再发 agent_response,而是发 analysis_failed + canvas_updated。
        finals = [m for m in ws.sent if m.get("type") == "agent_response"]
        assert finals == []

        failed = [m for m in ws.sent if m.get("type") == "analysis_failed"]
        assert len(failed) == 1
        # raw exc message 不该出现在用户可见的 hint 里
        assert "upstream gone" not in failed[0]["hint"]

        canvases = [m for m in ws.sent if m.get("type") == "canvas_updated"]
        assert len(canvases) == 1

        # W5D3 CR-P0 — save_message persists a SANITIZED hint (recovery taxonomy
        # message), NOT the raw exception. Reload-session would replay this back
        # to the user, so it must be safe to display. A bare RuntimeError with an
        # unrecognized message now classifies as S11_INTERNAL_ERROR (we no longer
        # pretend an unknown error was "upstream"); its hint mentions "系统出了点小问题".
        agent_save = [c for c in saved_messages if c[2] == "agent"]
        saved_text = agent_save[0][3]
        assert "upstream gone" not in saved_text, "raw exception leaked into chat history"
        # Sanitized message must come from RECOVERY_HINTS (友好中文) or fallback
        assert "小问题" in saved_text or "繁忙" in saved_text or "处理出错" in saved_text, (
            f"expected sanitized hint, got: {saved_text}"
        )

    def test_send_failure_on_final_frame_swallowed(self, saved_messages, stub_canvas_data):
        """末尾发 agent_response 时连接已关 — 不该再抛异常。"""

        class ClosingWS(FakeWS):
            async def send(self, data: str) -> None:
                # 第一次 send 成功(agent_stream),第二次抛(agent_response)
                if self.sent:
                    raise RuntimeError("ws closed")
                await super().send(data)

        ws = ClosingWS()
        chunks = [(AIMessageChunk(content="hello"), {})]
        # 不应 raise
        asyncio.run(run_agent("u1", FakePool(FakeAgent(chunks)), "t1", "hi", ws))
        # 只 capture 到 agent_stream(第一帧),agent_response 被抛但被吞
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "agent_stream"


# ---------- W5D4 B5: 工具级 HardFailure → run lifecycle 标 failed ----------


@pytest.fixture
def captured_lifecycle(monkeypatch):
    """Capture run_state.mark_* calls without touching the DB.

    Lets us assert the terminal transition: a tool that caught a HardFailure
    (and recorded it on RUN_CTX) must yield mark_failed, NOT mark_done — even
    though the agent stream itself completes normally.
    """
    calls: list[tuple[str, Any]] = []

    async def _mark_running(user_id: str, thread_id: str) -> int:
        calls.append(("running", thread_id))
        return 1

    async def _mark_done(thread_id: str) -> None:
        calls.append(("done", thread_id))

    async def _mark_failed(thread_id: str, failure: dict | None) -> None:
        calls.append(("failed", failure))

    monkeypatch.setattr(agent_runner.run_state, "mark_running", _mark_running)
    monkeypatch.setattr(agent_runner.run_state, "mark_done", _mark_done)
    monkeypatch.setattr(agent_runner.run_state, "mark_failed", _mark_failed)
    return calls


class TestToolFailureLifecycle:
    def test_tool_failure_marks_failed_not_done(self, saved_messages, stub_canvas_data, captured_lifecycle):
        """A tool catches a HardFailure → sets RUN_CTX['tool_failure'] mid-stream.
        Stream then ends normally, but run_agent must record `failed` (with the
        recovery payload) so a reconnect replay shows the next step."""
        from agent.transport.runtime_ctx import get_run_ctx

        failure = {
            "code": "S8_UPSTREAM_REFUSED",
            "hint": "上游忙,换条链接重试",
            "actions": ["RETRY_WITH_NEW_URL"],
            "request_id": "",
        }

        class ToolFailingAgent:
            async def astream(self, _input, *, config, stream_mode, version):
                # Simulate cascade._push_failure_frame writing to the live ctx.
                get_run_ctx()["tool_failure"] = failure
                yield {"data": (AIMessageChunk(content="分析失败了"), {})}

            async def aget_state(self, config):
                return _clean_state()

        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(ToolFailingAgent()), "t1", "hi", ws))  # type: ignore[arg-type]

        statuses = [c[0] for c in captured_lifecycle]
        assert "done" not in statuses, "tool-level failure must NOT be recorded done"
        assert statuses[0] == "running"
        assert statuses[-1] == "failed"
        # the recovery payload is carried through verbatim
        failed_payload = [c[1] for c in captured_lifecycle if c[0] == "failed"][0]
        assert failed_payload == failure

    def test_clean_stream_marks_done(self, saved_messages, stub_canvas_data, captured_lifecycle):
        """No tool_failure on the ctx → normal terminal `done` (regression guard)."""
        chunks = [(AIMessageChunk(content="ok"), {})]
        ws = FakeWS()
        asyncio.run(run_agent("u1", FakePool(FakeAgent(chunks)), "t1", "hi", ws))

        statuses = [c[0] for c in captured_lifecycle]
        assert statuses == ["running", "done"]
