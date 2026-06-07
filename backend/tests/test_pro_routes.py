"""Pro 画布 HTTP 路由 + WS handler 接缝测试。

锁:flag 门控、编译校验前移、跨境闸、成本闸在 enqueue 之前、入队正确、run_id 铸造 + server-derived 身份。
"""

from __future__ import annotations

import asyncio
import json

import pytest

from agent import config
from agent.cascade.failures import FailureCode, HardFailure
from agent.tools.canvas_persistence import pro_runs_repo
from agent.transport import http_router, ws_handlers
from agent.transport.context import WSCtx
from agent.transport.ws_messages import ProRunCancelMsg, ProRunSubmitMsg


VALID_GRAPH = {
    "version": 1,
    "nodes": [
        {"id": "m", "type": "Model"},
        {"id": "p", "type": "Prompt", "params": {"text": "猫"}},
        {"id": "g", "type": "Generate"},
        {"id": "v", "type": "Preview"},
    ],
    "edges": [
        {"id": "1", "source": "m", "sourceHandle": "model", "target": "g", "targetHandle": "model"},
        {"id": "2", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
        {"id": "3", "source": "g", "sourceHandle": "image", "target": "v", "targetHandle": "image"},
    ],
}


class _FakeWS:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


def _tmp_canvas_db(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "agent.tools.canvas_persistence.db.canvas_db_path", lambda: tmp_path / "canvas.db"
    )


# ── HTTP /api/pro/estimate ──────────────────────────────────────────────────────


def test_estimate_disabled_returns_403(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", False)
    status, body, _ = asyncio.run(http_router.handle_pro_estimate({}, {"graph": VALID_GRAPH}))
    assert status == 403 and body["error"] == "pro_canvas_disabled"


def test_estimate_ok(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    status, body, _ = asyncio.run(http_router.handle_pro_estimate({}, {"graph": VALID_GRAPH}))
    assert status == 200
    assert body["billable_node_count"] == 1
    assert body["cost_cny"] == pytest.approx(1.5)


def test_estimate_bad_graph_400(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    status, body, _ = asyncio.run(http_router.handle_pro_estimate({}, {"graph": {"nodes": [], "edges": []}}))
    assert status == 400 and body["error"] == "empty_graph"


def test_estimate_missing_graph_400(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    status, body, _ = asyncio.run(http_router.handle_pro_estimate({}, {}))
    assert status == 400 and body["error"] == "graph_required"


# ── HTTP /api/pro/seed ──────────────────────────────────────────────────────────


def test_seed_disabled_403(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", False)
    status, body, _ = asyncio.run(http_router.handle_pro_seed({}, {"analysis_id": "ana_x"}))
    assert status == 403


def test_seed_no_analysis_returns_null(monkeypatch):
    # 无 analysis_id 且无 thread → 200 {graph: null}(前端转主题输入框,不报错)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    status, body, _ = asyncio.run(http_router.handle_pro_seed({}, {}))
    assert status == 200 and body["graph"] is None


def test_seed_ok(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)

    async def fake_build(analysis_id, user_id, *, thread_id=None):
        return {"version": 1, "nodes": [], "edges": [], "meta": {"analysis_id": analysis_id}}

    monkeypatch.setattr("agent.transport.http_router.build_seed_graph", fake_build)
    status, body, _ = asyncio.run(
        http_router.handle_pro_seed({}, {"analysis_id": "ana_x", "thread_id": "t1", "user_id": "u1"})
    )
    assert status == 200
    assert body["graph"]["meta"]["analysis_id"] == "ana_x"


def test_seed_not_found_returns_null(monkeypatch):
    # analysis_not_found → 当作无分析,返回 {graph: null}(容错,前端走主题输入)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    from agent.comfyui.seed_builder import SeedBuildError

    async def fake_build(analysis_id, user_id, *, thread_id=None):
        raise SeedBuildError("analysis_not_found", "nope")

    monkeypatch.setattr("agent.transport.http_router.build_seed_graph", fake_build)
    status, body, _ = asyncio.run(http_router.handle_pro_seed({}, {"analysis_id": "missing"}))
    assert status == 200 and body["graph"] is None


def test_seed_from_theme_ok(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)

    async def fake_theme(theme, user_id):
        return {"version": 1, "nodes": [], "edges": [], "meta": {"source": "theme", "theme": theme}}

    async def ok_guard(*a, **k):
        return None

    async def ok_record(**k):
        return None

    monkeypatch.setattr("agent.transport.http_router.build_seed_graph_from_theme", fake_theme)
    monkeypatch.setattr(http_router.cost_guard, "cost_guard", ok_guard)
    monkeypatch.setattr(http_router.cost_guard, "record_generation_cost", ok_record)
    status, body, _ = asyncio.run(http_router.handle_pro_seed_from_theme({}, {"theme": "宝宝辅食", "thread_id": "t1"}))
    assert status == 200 and body["graph"]["meta"]["source"] == "theme"


def test_seed_from_theme_missing_theme_400(monkeypatch):
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    status, body, _ = asyncio.run(http_router.handle_pro_seed_from_theme({}, {}))
    assert status == 400 and body["error"] == "theme_required"


# ── WS pro_run_submit ───────────────────────────────────────────────────────────


def _submit(graph=VALID_GRAPH, provider=None, tid="t1"):
    return ProRunSubmitMsg(type="pro_run_submit", thread_id=tid, graph=graph, provider=provider)


def test_submit_disabled_no_enqueue(monkeypatch, tmp_path):
    _tmp_canvas_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", False)
    ctx = WSCtx(user_id="u1", ws=_FakeWS(), pool=None)
    asyncio.run(ws_handlers.handle_pro_run_submit(ctx, _submit()))
    assert ctx.ws.sent[0]["code"] == "pro_canvas_disabled"
    assert pro_runs_repo.list_pro_runs(user_id="u1", thread_id="t1") == []


def test_submit_bad_graph_no_enqueue(monkeypatch, tmp_path):
    _tmp_canvas_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    ctx = WSCtx(user_id="u1", ws=_FakeWS(), pool=None)
    asyncio.run(ws_handlers.handle_pro_run_submit(ctx, _submit(graph={"nodes": [], "edges": []})))
    assert ctx.ws.sent[0]["type"] == "error"
    assert ctx.ws.sent[0]["code"] == "empty_graph"
    assert pro_runs_repo.list_pro_runs(user_id="u1", thread_id="t1") == []


def test_submit_cross_border_blocked(monkeypatch, tmp_path):
    _tmp_canvas_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    monkeypatch.setattr(config, "STRICT_CROSS_BORDER_REJECT", True)
    ctx = WSCtx(user_id="u1", ws=_FakeWS(), pool=None)
    asyncio.run(ws_handlers.handle_pro_run_submit(ctx, _submit(provider="runninghub")))
    assert ctx.ws.sent[0]["code"] == "cross_border_blocked"
    assert pro_runs_repo.list_pro_runs(user_id="u1", thread_id="t1") == []


def test_submit_over_cap_no_enqueue(monkeypatch, tmp_path):
    _tmp_canvas_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)

    async def _raise(user_id, run_id, predicted, **_kw):
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "over cap")

    monkeypatch.setattr(ws_handlers.cost_guard, "cost_guard", _raise)
    ctx = WSCtx(user_id="u1", ws=_FakeWS(), pool=None)
    asyncio.run(ws_handlers.handle_pro_run_submit(ctx, _submit()))
    assert ctx.ws.sent[0]["type"] == "pro_run_failed"
    assert pro_runs_repo.list_pro_runs(user_id="u1", thread_id="t1") == []


def test_submit_happy_enqueues_and_returns_run_id(monkeypatch, tmp_path):
    _tmp_canvas_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    seen = {}

    async def _spy(user_id, run_id, predicted, **_kw):
        seen.update(user_id=user_id, run_id=run_id, predicted=predicted)

    monkeypatch.setattr(ws_handlers.cost_guard, "cost_guard", _spy)
    ctx = WSCtx(user_id="u1", ws=_FakeWS(), pool=None)
    asyncio.run(ws_handlers.handle_pro_run_submit(ctx, _submit()))

    frame = ctx.ws.sent[0]
    assert frame["type"] == "pro_run_progress" and frame["status"] == "queued"
    run_id = frame["run_id"]
    assert run_id.startswith("pro_")
    # cost guard: server-derived identity + minted run_id (same bucket worker records to)
    assert seen["user_id"] == "u1"
    assert seen["run_id"] == run_id
    assert seen["predicted"] == pytest.approx(1.5)
    # enqueued
    runs = pro_runs_repo.list_pro_runs(user_id="u1", thread_id="t1")
    assert len(runs) == 1 and runs[0]["run_id"] == run_id
    assert runs[0]["status"] == "pending"
    assert runs[0]["cost_est"] == pytest.approx(1.5)


def test_cancel_marks_cancelled(monkeypatch, tmp_path):
    _tmp_canvas_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    pro_runs_repo.create_pro_run(
        "pro_x", user_id="u1", thread_id="t1", graph_json="{}", provider="fixture", cost_est=1.5
    )
    pro_runs_repo.claim_pending_pro_runs()
    ctx = WSCtx(user_id="u1", ws=_FakeWS(), pool=None)
    asyncio.run(ws_handlers.handle_pro_run_cancel(ctx, ProRunCancelMsg(type="pro_run_cancel", thread_id="t1", run_id="pro_x")))
    assert ctx.ws.sent[0]["status"] == "cancelled"
    assert pro_runs_repo.get_pro_run("pro_x", user_id="u1", thread_id="t1")["status"] == "cancelled"


def test_cancel_disabled_no_op(monkeypatch, tmp_path):
    _tmp_canvas_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", False)
    pro_runs_repo.create_pro_run(
        "pro_x", user_id="u1", thread_id="t1", graph_json="{}", provider="fixture", cost_est=1.5
    )
    pro_runs_repo.claim_pending_pro_runs()
    ctx = WSCtx(user_id="u1", ws=_FakeWS(), pool=None)
    asyncio.run(ws_handlers.handle_pro_run_cancel(ctx, ProRunCancelMsg(type="pro_run_cancel", thread_id="t1", run_id="pro_x")))
    assert ctx.ws.sent[0]["code"] == "pro_canvas_disabled"
    # flag OFF → run untouched (still submitted, not cancelled)
    assert pro_runs_repo.get_pro_run("pro_x", user_id="u1", thread_id="t1")["status"] == "submitted"
