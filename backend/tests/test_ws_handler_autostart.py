"""handle_seed_canvas 的「进画布自动开工」(H5,flag CANVAS_AUTOSTART_DIRECTOR)测试。

会花钱的功能 → 默认 OFF,且只在「首次 seed + 有分析上下文」触发。这里锁死 flag 门控与触发条件:
- OFF → 绝不自动开工(退回前端手动 CTA)。
- ON + 有 summary + 首次 seed → 触发一条 [canvas_autostart] 给 Director。
- ON + 无 summary → 不触发(没分析依据可自动开工)。
- ON + 画布已有节点(重连重发 seed_canvas)→ 不触发(幂等,每张画布最多一次)。
"""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from agent import config
from agent.tools import canvas as canvas_tools
from agent.tools.canvas_persistence import db as canvas_db
from agent.transport import ws_handlers
from agent.transport.context import WSCtx
from agent.transport.ws_handlers import handle_seed_canvas
from agent.transport.ws_messages import SeedCanvasMsg


@pytest.fixture(autouse=True)
def _isolated_canvas_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    canvas_db._MIGRATED_PATHS.discard(str(tmp_path / "canvas.db"))
    yield


class _FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


@pytest.fixture
def captured_autostart(monkeypatch):
    """捕获 _run_agent_serialized 的调用(同步记录,不真跑 Director)。记 msg + agent_prefix。"""
    calls: list = []

    def _capture(ctx, msg, agent_prefix=""):
        calls.append({"msg": msg, "agent_prefix": agent_prefix})

        async def _noop():
            return None

        return _noop()

    monkeypatch.setattr(ws_handlers, "_run_agent_serialized", _capture)
    return calls


def _seed_msg(tid: str, summary: str = "") -> SeedCanvasMsg:
    return SeedCanvasMsg(type="seed_canvas", thread_id=tid, analysis_id="a1", analysis_summary=summary)


def _ctx() -> WSCtx:
    return WSCtx(user_id="default", ws=_FakeWS(), pool=None)


def test_autostart_off_does_not_trigger(captured_autostart, monkeypatch):
    monkeypatch.setattr(config, "CANVAS_AUTOSTART_DIRECTOR", False)
    tid = f"as-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    asyncio.run(handle_seed_canvas(_ctx(), _seed_msg(tid, "为什么火:开场钩子强")))
    assert captured_autostart == []  # OFF → 不自动开工
    assert len(canvas_tools.get_canvas_state()["nodes"]) == 2  # 但仍 seed 了脚手架(📊 + ✍️)


def test_autostart_on_with_summary_triggers_once(captured_autostart, monkeypatch):
    monkeypatch.setattr(config, "CANVAS_AUTOSTART_DIRECTOR", True)
    tid = f"as-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    asyncio.run(handle_seed_canvas(_ctx(), _seed_msg(tid, "为什么火:开场钩子强")))
    assert len(captured_autostart) == 1
    call = captured_autostart[0]
    assert call["msg"].thread_id == tid
    # MEDIUM #3:标记走 agent_prefix(只进 LLM turn),不混进存历史的 content。
    assert call["agent_prefix"] == "[canvas_autostart]"
    assert "[canvas_autostart]" not in call["msg"].content  # 存历史的文案干净


def test_autostart_summary_truncated(captured_autostart, monkeypatch):
    """MEDIUM #2:超大 summary 被截断(防放大 autostart 输入 token)。"""
    monkeypatch.setattr(config, "CANVAS_AUTOSTART_DIRECTOR", True)
    tid = f"as-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    asyncio.run(handle_seed_canvas(_ctx(), _seed_msg(tid, "猫" * 20000)))  # 远超上限
    ref = next(n for n in canvas_tools.get_canvas_state()["nodes"] if "为什么火" in n["title"])
    assert len(ref["description"]) <= 6000


def test_autostart_on_without_summary_no_trigger(captured_autostart, monkeypatch):
    """无分析摘要(没有 📊 节点)→ 没什么可自动开工的,不触发。"""
    monkeypatch.setattr(config, "CANVAS_AUTOSTART_DIRECTOR", True)
    tid = f"as-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    asyncio.run(handle_seed_canvas(_ctx(), _seed_msg(tid, "")))
    assert captured_autostart == []


def test_autostart_idempotent_when_canvas_nonempty(captured_autostart, monkeypatch):
    """画布已有节点(重连重发 seed_canvas)→ 不重复 seed → 不重复触发(每张画布最多一次)。"""
    monkeypatch.setattr(config, "CANVAS_AUTOSTART_DIRECTOR", True)
    tid = f"as-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    canvas_tools.create_canvas_node("script", "已存在", "x")  # 画布非空
    asyncio.run(handle_seed_canvas(_ctx(), _seed_msg(tid, "为什么火")))
    assert captured_autostart == []
