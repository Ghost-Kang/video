"""handle_execute_node 的 enqueue-time 成本闸接缝测试(审计 2026-06-06 H6 / P0-5)。

成本守卫反复在 prod 栽跟头(#1-7 日闸失效、C1 画布不记账)。`test_cost_guard` 只测
cost_guard 函数本身,但「成本闸在 execute_node 这个调用点被正确调用、超额时拦在 enqueue
之前」从没被守住 —— 若顺序写反 / 超限分支不 return / predict 参数取错,worker 仍会真花钱
而单测全绿。这里在 handler 接缝上锁死:超额 → 不入队 + 回 generation 失败帧;通过 → 入队。
"""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from agent.cascade.failures import FailureCode, HardFailure
from agent.tools import canvas as canvas_tools
from agent.tools.canvas import create_canvas_node, enqueue_generation, get_canvas_state
from agent.tools.canvas_persistence import db as canvas_db
from agent.transport import ws_handlers
from agent.transport.context import WSCtx
from agent.transport.ws_handlers import handle_execute_node
from agent.transport.ws_messages import ExecuteNodeMsg


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


def _exec_msg(tid: str, node_id: str) -> ExecuteNodeMsg:
    return ExecuteNodeMsg(
        type="execute_node", thread_id=tid, node_id=node_id, node_type="image", description="prompt"
    )


def test_execute_node_over_cap_refuses_before_enqueue(monkeypatch):
    """cost_guard 抛 HardFailure → 节点绝不入队(worker 不会被 claim → 不花钱)+ 回 generation 失败帧。"""
    tid = f"cg-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "超额图", "prompt")

    async def _raise(user_id, run_id, predicted, **_kw):
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "run cost > cap")

    monkeypatch.setattr(ws_handlers.cost_guard, "cost_guard", _raise)

    ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
    asyncio.run(handle_execute_node(ctx, _exec_msg(tid, node["id"])))

    fail = [m for m in ctx.ws.sent if m["type"] == "analysis_failed"]
    assert len(fail) == 1
    assert fail[0]["stage"] == "generation"
    assert fail[0]["code"] == FailureCode.S8_UPSTREAM_REFUSED.value
    # 核心断言:超额时节点没进队列(否则 worker 照样花钱,成本闸形同虚设)。
    state = get_canvas_state(node["id"])["node"]
    assert state["generation_status"] != "pending"


def test_execute_node_under_cap_enqueues(monkeypatch):
    """对照组:cost_guard 通过 → 节点入队 pending,且不发失败帧。"""
    tid = f"cg-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "正常图", "prompt")

    async def _ok(user_id, run_id, predicted, **_kw):
        return None

    monkeypatch.setattr(ws_handlers.cost_guard, "cost_guard", _ok)

    ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
    asyncio.run(handle_execute_node(ctx, _exec_msg(tid, node["id"])))

    state = get_canvas_state(node["id"])["node"]
    assert state["generation_status"] == "pending"
    assert [m for m in ctx.ws.sent if m["type"] == "analysis_failed"] == []


def test_execute_node_burst_blocked_by_pending_reservation(monkeypatch):
    """M4:一轮内已有 pending 生成时,新 enqueue 把它们的预占额度计入 → 超 run cap 即拒,
    即使尚无任何完成记账(recorded=0)。防 burst 入队绕过 ¥/run cap。用真 cost_guard。"""
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "2.0")  # 低 cap 便于触发:1.5(pending)+1.5(new)>2
    tid = f"burst-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    queued = create_canvas_node("image", "已排队图", "prompt")
    enqueue_generation(queued["id"])  # generation_status = pending → 预占 ¥1.5
    fresh = create_canvas_node("image", "新图", "prompt")

    ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
    asyncio.run(handle_execute_node(ctx, _img_msg(tid, fresh["id"], "seedream")))

    fails = [m for m in ctx.ws.sent if m["type"] == "analysis_failed"]
    assert len(fails) == 1 and fails[0]["stage"] == "generation"
    # 新节点没入队(预占 + 预测越 cap)
    assert get_canvas_state(fresh["id"])["node"]["generation_status"] != "pending"


def _img_msg(tid: str, node_id: str, provider: str) -> ExecuteNodeMsg:
    return ExecuteNodeMsg(
        type="execute_node", thread_id=tid, node_id=node_id, node_type="image",
        description="prompt", image_gen_provider=provider,
    )


def test_execute_node_cross_border_provider_blocked(monkeypatch):
    """M3:STRICT 开时,image 节点选 google(跨境)→ enqueue 前拒绝 + 回 cross_border_blocked。"""
    from agent import config

    monkeypatch.setattr(config, "STRICT_CROSS_BORDER_REJECT", True)
    tid = f"cb-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "跨境图", "prompt")

    ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
    asyncio.run(handle_execute_node(ctx, _img_msg(tid, node["id"], "google")))

    errs = [m for m in ctx.ws.sent if m["type"] == "error"]
    assert len(errs) == 1 and errs[0]["code"] == "cross_border_blocked"
    assert get_canvas_state(node["id"])["node"]["generation_status"] != "pending"


def test_execute_node_seedream_allowed_under_strict(monkeypatch):
    """境内 seedream 不受跨境闸影响 → 正常入队。"""
    from agent import config

    monkeypatch.setattr(config, "STRICT_CROSS_BORDER_REJECT", True)

    async def _ok(user_id, run_id, predicted, **_kw):
        return None

    monkeypatch.setattr(ws_handlers.cost_guard, "cost_guard", _ok)
    tid = f"cb-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "境内图", "prompt")

    ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
    asyncio.run(handle_execute_node(ctx, _img_msg(tid, node["id"], "seedream")))

    assert [m for m in ctx.ws.sent if m["type"] == "error"] == []
    assert get_canvas_state(node["id"])["node"]["generation_status"] == "pending"


def test_execute_node_cross_border_allowed_when_flag_off(monkeypatch):
    """运营显式关掉 STRICT(=0)时,google 放行(运营自担合规)。"""
    from agent import config

    monkeypatch.setattr(config, "STRICT_CROSS_BORDER_REJECT", False)

    async def _ok(user_id, run_id, predicted, **_kw):
        return None

    monkeypatch.setattr(ws_handlers.cost_guard, "cost_guard", _ok)
    tid = f"cb-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "跨境图", "prompt")

    ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
    asyncio.run(handle_execute_node(ctx, _img_msg(tid, node["id"], "google")))

    assert [m for m in ctx.ws.sent if m["type"] == "error"] == []
    assert get_canvas_state(node["id"])["node"]["generation_status"] == "pending"


def test_execute_node_cost_guard_called_with_thread_id_as_run_id(monkeypatch):
    """run_id 桶 = thread_id —— worker 的 record_generation_cost 也用 thread_id,两边同桶
    cap 才读得到画布花费(refuted 的「键对不上」不成立,真问题是同桶但之前根本不记账)。"""
    tid = f"cg-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "记账图", "prompt")

    seen: dict = {}

    async def _spy(user_id, run_id, predicted, **_kw):
        seen["user_id"] = user_id
        seen["run_id"] = run_id
        seen["predicted"] = predicted

    monkeypatch.setattr(ws_handlers.cost_guard, "cost_guard", _spy)

    ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
    asyncio.run(handle_execute_node(ctx, _exec_msg(tid, node["id"])))

    assert seen["run_id"] == tid  # 与 worker record_generation_cost(run_id=thread_id) 同桶
    assert seen["user_id"] == "default"  # server-derived,不可由 client payload 伪造
    assert seen["predicted"] == 1.5  # image 1 张
