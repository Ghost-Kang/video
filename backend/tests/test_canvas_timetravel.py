"""time-travel 回溯(canvas 统筹 P2 slice-2)— 后端核心:下游遍历 / 版本快照 / 重生标脏。

「回上游改重生下游」= 画布级 DAG 操作(画布在 canvas.db 侧库,不是 LangGraph
time-travel)。验证:沿边找下游、重生前快照旧版、重生清产物入队 + 标脏下游、
只标「已有产物」的下游。
"""

import asyncio
import json
import uuid

import pytest

from agent.tools import canvas as canvas_tools
from agent.tools.canvas import (
    regenerate_node,
    restore_node_version,
    _descendants,
    _mark_descendants_stale,
)
from agent.tools.canvas_persistence import db as canvas_db
from agent.tools.canvas_persistence.versions_repo import list_versions
from agent.transport.context import WSCtx
from agent.transport.ws_handlers import handle_list_node_versions, handle_restore_node_version
from agent.transport.ws_messages import ListNodeVersionsMsg, RestoreNodeVersionMsg


@pytest.fixture(autouse=True)
def _isolated_canvas_db(tmp_path, monkeypatch):
    p = tmp_path / "canvas.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    canvas_db._MIGRATED_PATHS.discard(str(p))
    yield


def _thread():
    tid = f"tt-{uuid.uuid4().hex[:8]}"
    canvas_tools.set_thread_id(tid)
    return tid


def _mk(nid, *, type="image", asset_status="idle", result=None, needs_regen=False):
    canvas_tools._upsert_node({
        "id": nid, "type": type, "title": nid, "description": f"desc-{nid}",
        "status": "pending", "node_status": "reviewing",
        "asset_status": asset_status, "result": result, "needs_regen": needs_regen,
    })


def _edge(s, t):
    canvas_tools._upsert_edge({"id": f"{s}-{t}", "source": s, "target": t})


# ---------- descendants traversal ----------


class TestDescendants:
    def test_bfs_transitive(self):
        _thread()
        for nid in ("A", "B", "C", "D"):
            _mk(nid)
        _edge("A", "B"); _edge("B", "C"); _edge("A", "D")  # A→B→C, A→D
        assert set(_descendants("A")) == {"B", "C", "D"}
        assert set(_descendants("B")) == {"C"}
        assert _descendants("C") == []

    def test_cycle_safe_excludes_self(self):
        _thread()
        _mk("A"); _mk("B")
        _edge("A", "B"); _edge("B", "A")  # cycle
        d = _descendants("A")
        assert set(d) == {"B"}  # terminates, excludes self


# ---------- version snapshot ----------


class TestVersionSnapshot:
    def test_regenerate_snapshots_old_product(self):
        _thread()
        _mk("X", asset_status="done", result={"url": "old.png"})
        regenerate_node("X")
        versions = list_versions("X")
        assert len(versions) == 1
        assert versions[0]["version_seq"] == 1
        assert versions[0]["result"] == {"url": "old.png"}  # OLD product preserved
        assert versions[0]["description"] == "desc-X"
        assert versions[0]["reason"] == "regenerate"

    def test_version_seq_increments(self):
        _thread()
        _mk("X", asset_status="done", result={"url": "v0.png"})
        regenerate_node("X")
        # simulate a new product, then regenerate again
        n = canvas_tools._load_node("X")
        n["result"] = {"url": "v1.png"}
        n["asset_status"] = "done"
        canvas_tools._upsert_node(n)
        regenerate_node("X")
        versions = list_versions("X")
        assert [v["version_seq"] for v in versions] == [1, 2]
        assert versions[1]["result"] == {"url": "v1.png"}

    def test_snapshot_skips_null_result(self):
        # mid-generation(result=None)时 snapshot 不写 junk 行 —— 否则 NodeVersionHistory
        # 默认选中它、回滚到它会把节点弄成 product-less 卡死。也回头护住 regenerate。
        _thread()
        _mk("N", asset_status="generating", result=None)  # no product yet
        regenerate_node("N")  # snapshot_version called with result=None → skipped
        assert list_versions("N") == []


# ---------- regenerate: clear + enqueue + mark downstream stale ----------


class TestRegenerate:
    def test_clears_product_and_enqueues(self):
        _thread()
        _mk("X", asset_status="done", result={"url": "old.png"}, needs_regen=True)
        regenerate_node("X")
        n = canvas_tools._load_node("X")
        assert n["result"] is None
        assert n["asset_status"] == "generating"
        assert n["generation_status"] == "pending"
        assert n["needs_regen"] is False  # cleared on the node being regenerated

    def test_marks_downstream_with_assets_stale(self):
        _thread()
        _mk("up", asset_status="done", result={"url": "up.png"})
        _mk("mid", asset_status="done", result={"url": "mid.png"})   # has asset → stale
        _mk("leaf", asset_status="idle", result=None)                # no asset → NOT stale
        _edge("up", "mid"); _edge("mid", "leaf")
        regenerate_node("up")
        assert canvas_tools._load_node("mid")["needs_regen"] is True
        assert canvas_tools._load_node("leaf")["needs_regen"] is False

    def test_missing_node_returns_none(self):
        _thread()
        assert regenerate_node("nope") is None


# ---------- mark stale: only nodes with assets ----------


class TestMarkStale:
    def test_only_marks_nodes_with_assets(self):
        _thread()
        _mk("root")
        _mk("done_child", asset_status="done", result={"url": "x"})
        _mk("failed_child", asset_status="failed")
        _mk("idle_child", asset_status="idle")
        _edge("root", "done_child"); _edge("root", "failed_child"); _edge("root", "idle_child")
        stale = _mark_descendants_stale("root")
        assert set(stale) == {"done_child", "failed_child"}  # idle has nothing to regen
        assert canvas_tools._load_node("idle_child")["needs_regen"] is False

    def test_needs_regen_surfaces_to_frontend_and_agent(self):
        from agent.transport.context import canvas_data

        tid = _thread()
        _mk("up", asset_status="done", result={"url": "up.png"})
        _mk("down", asset_status="done", result={"url": "down.png"})
        _edge("up", "down")
        regenerate_node("up")
        # frontend path (canvas_updated.canvas = canvas_data) — keyed by node_id
        snap = canvas_data(tid)
        assert snap["nodes"]["down"]["needs_regen"] is True
        # agent-facing get_canvas_state summary (list)
        state = canvas_tools.get_canvas_state()
        down = next(n for n in state["nodes"] if n["id"] == "down")
        assert down["needs_regen"] is True


# ---------- WS endpoint: list_node_versions → node_versions_returned (2b) ----------


class _FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


def _sent_versions(ctx) -> list[dict]:
    frames = [m for m in ctx.ws.sent if m["type"] == "node_versions_returned"]
    assert len(frames) == 1
    return frames[0]


class TestListNodeVersionsHandler:
    def test_returns_snapshots_ascending(self):
        tid = _thread()
        _mk("X", asset_status="done", result={"url": "v1.png"})
        regenerate_node("X")  # snapshots v1 (the old product) before clearing
        n = canvas_tools._load_node("X")
        n["result"] = {"url": "v2.png"}
        n["asset_status"] = "done"
        canvas_tools._upsert_node(n)
        regenerate_node("X")  # snapshots v2

        ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
        asyncio.run(
            handle_list_node_versions(
                ctx, ListNodeVersionsMsg(type="list_node_versions", thread_id=tid, node_id="X")
            )
        )
        frame = _sent_versions(ctx)
        assert frame["node_id"] == "X" and frame["thread_id"] == tid
        assert [v["version_seq"] for v in frame["versions"]] == [1, 2]
        assert frame["versions"][0]["result"] == {"url": "v1.png"}
        assert frame["versions"][1]["result"] == {"url": "v2.png"}
        assert frame["versions"][0]["reason"] == "regenerate"

    def test_empty_for_node_without_history(self):
        tid = _thread()
        _mk("Y", asset_status="done", result={"url": "y.png"})  # never regenerated → no versions
        ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
        asyncio.run(
            handle_list_node_versions(
                ctx, ListNodeVersionsMsg(type="list_node_versions", thread_id=tid, node_id="Y")
            )
        )
        assert _sent_versions(ctx)["versions"] == []


# ---------- restore: swap to old version + archive current + mark stale (2c) ----------


class TestRestore:
    def test_swaps_to_old_and_archives_current(self):
        _thread()
        _mk("X", asset_status="done", result={"url": "p1.png"})
        regenerate_node("X")  # archives v1 = p1, clears
        n = canvas_tools._load_node("X")
        n["result"] = {"url": "p2.png"}
        n["asset_status"] = "done"
        n["generation_status"] = "done"  # worker finished → restore allowed (not in-flight)
        canvas_tools._upsert_node(n)  # current = p2; versions = [v1(p1)]

        restored = restore_node_version("X", 1)  # restore to v1(p1), archive current p2 as v2
        assert restored["result"] == {"url": "p1.png"}
        assert restored["asset_status"] == "done"
        assert restored["generation_status"] == "done"
        assert restored["needs_regen"] is False
        versions = list_versions("X")
        assert [v["version_seq"] for v in versions] == [1, 2]
        assert versions[0]["result"] == {"url": "p1.png"}  # v1 unchanged
        assert versions[1]["result"] == {"url": "p2.png"}  # the current got archived
        assert versions[1]["reason"] == "restore"

    def test_marks_downstream_stale(self):
        _thread()
        _mk("up", asset_status="done", result={"url": "up1.png"})
        _mk("down", asset_status="done", result={"url": "down.png"})
        _edge("up", "down")
        regenerate_node("up")  # archives up v1; also stales down — clear it to isolate restore
        d = canvas_tools._load_node("down")
        d["needs_regen"] = False
        canvas_tools._upsert_node(d)
        u = canvas_tools._load_node("up")
        u["result"] = {"url": "up2.png"}
        u["asset_status"] = "done"
        u["generation_status"] = "done"
        canvas_tools._upsert_node(u)

        restore_node_version("up", 1)
        assert canvas_tools._load_node("down")["needs_regen"] is True

    def test_missing_node_or_version_returns_none(self):
        _thread()
        _mk("X", asset_status="done", result={"url": "p1.png"})
        assert restore_node_version("nope", 1) is None
        assert restore_node_version("X", 99) is None  # node exists, version doesn't

    def test_refuses_while_generating(self):
        # 生成在途回滚会被 worker 盖掉 → 后端硬拒(返回 None,节点不动)。
        _thread()
        _mk("G", asset_status="done", result={"url": "g1.png"})
        regenerate_node("G")  # archives v1; node now generation_status='pending' (in-flight)
        assert canvas_tools._load_node("G")["generation_status"] == "pending"
        assert restore_node_version("G", 1) is None
        assert canvas_tools._load_node("G")["generation_status"] == "pending"  # unchanged

    def test_coerces_asset_status_to_done_for_valid_old_product(self):
        # 旧版归档时可能是 failed/timeout 但产物有效 → 回滚后 asset_status 一律置 done,
        # 不照抄归档值(否则有图却显示失败);并清 generation_task_id。
        _thread()
        _mk("F", asset_status="failed", result={"url": "f1.png"})  # valid product, failed-marked
        regenerate_node("F")  # archives v1 (result=f1, asset=failed)
        n = canvas_tools._load_node("F")
        n["result"] = {"url": "f2.png"}
        n["asset_status"] = "done"
        n["generation_status"] = "done"
        n["generation_task_id"] = "stale-task-123"
        canvas_tools._upsert_node(n)

        restored = restore_node_version("F", 1)
        assert restored["result"] == {"url": "f1.png"}
        assert restored["asset_status"] == "done"  # coerced, NOT 'failed'
        assert restored["generation_task_id"] is None  # stale task id cleared

    def test_refuses_restore_to_null_result_version(self):
        # 守旧库可能残留 result=None 的 junk 版本 —— 不能回滚到它(否则节点变 product-less)。
        from agent.tools.canvas_persistence.db import _db, _resolve_ids

        _thread()
        _mk("J", asset_status="done", result={"url": "j1.png"})
        uid, tid = _resolve_ids(None, None)
        db = _db()
        try:  # 直插一条 result=None 的历史 junk 行(绕过 snapshot_version 的新守卫)
            db.execute(
                "INSERT INTO canvas_node_versions "
                "(user_id, thread_id, node_id, version_seq, description, result, asset_status, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, tid, "J", 1, "", None, "generating", "legacy", "2026-01-01T00:00:00Z"),
            )
            db.commit()
        finally:
            db.close()
        assert restore_node_version("J", 1) is None  # refused: target has no product


class TestRestoreNodeVersionHandler:
    def test_sends_canvas_and_fresh_versions(self):
        tid = _thread()
        _mk("X", asset_status="done", result={"url": "p1.png"})
        regenerate_node("X")  # v1 = p1
        n = canvas_tools._load_node("X")
        n["result"] = {"url": "p2.png"}
        n["asset_status"] = "done"
        n["generation_status"] = "done"
        canvas_tools._upsert_node(n)  # current = p2

        ctx = WSCtx(user_id="default", ws=_FakeWS(), pool=None)
        asyncio.run(
            handle_restore_node_version(
                ctx,
                RestoreNodeVersionMsg(
                    type="restore_node_version", thread_id=tid, node_id="X", version_seq=1
                ),
            )
        )
        types = [m["type"] for m in ctx.ws.sent]
        assert "canvas_updated" in types and "node_versions_returned" in types
        canvas_frame = next(m for m in ctx.ws.sent if m["type"] == "canvas_updated")
        assert canvas_frame["canvas"]["nodes"]["X"]["result"] == {"url": "p1.png"}  # restored
        ver_frame = next(m for m in ctx.ws.sent if m["type"] == "node_versions_returned")
        # fresh list includes the just-archived current (p2) as v2
        assert [v["version_seq"] for v in ver_frame["versions"]] == [1, 2]
        assert ver_frame["versions"][1]["result"] == {"url": "p2.png"}
