"""write_todos→画布进度(P2 ③):_emit_todos 读 agent state["todos"] 推 todos_updated 帧;
todos 空时不推(不清前端已显示的进度);读 state 失败 best-effort 不抛。"""

import asyncio

from agent.transport import agent_runner


class _FakeState:
    def __init__(self, todos):
        self.values = {"todos": todos}


class _FakeAgent:
    def __init__(self, todos, raise_=False):
        self._todos = todos
        self._raise = raise_

    async def aget_state(self, config):
        if self._raise:
            raise RuntimeError("state read failed")
        return _FakeState(self._todos)


def _run_emit(monkeypatch, agent):
    sent = []

    async def _fake_send(uid, frame, fallback_ws=None):
        sent.append(frame)

    monkeypatch.setattr(agent_runner.notify, "send_to_user", _fake_send)
    asyncio.run(agent_runner._emit_todos(agent, {}, "u", "t1", None))
    return sent


def test_emits_todos_frame(monkeypatch):
    todos = [
        {"content": "策划书", "status": "completed"},
        {"content": "角色三视图", "status": "in_progress"},
    ]
    sent = _run_emit(monkeypatch, _FakeAgent(todos))
    assert len(sent) == 1
    assert sent[0]["type"] == "todos_updated"
    assert sent[0]["thread_id"] == "t1"
    assert sent[0]["todos"] == todos


def test_empty_todos_no_emit(monkeypatch):
    assert _run_emit(monkeypatch, _FakeAgent([])) == []


def test_state_read_failure_best_effort(monkeypatch):
    # 读 state 抛错不应冒泡(best-effort,不挡主流程)
    assert _run_emit(monkeypatch, _FakeAgent([], raise_=True)) == []
