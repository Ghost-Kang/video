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
from agent.tools.canvas import regenerate_node, _descendants, _mark_descendants_stale
from agent.tools.canvas_persistence import db as canvas_db
from agent.tools.canvas_persistence.versions_repo import list_versions
from agent.transport.context import WSCtx
from agent.transport.ws_handlers import handle_list_node_versions
from agent.transport.ws_messages import ListNodeVersionsMsg


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
