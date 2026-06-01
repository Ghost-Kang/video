"""画布工具验证 — SQLite 持久化"""

import uuid

import pytest
from agent.tools import canvas as canvas_tools
from agent.tools.canvas import (
    approve_node,
    claim_pending_tasks,
    create_canvas_node,
    delete_canvas_node,
    enqueue_generation,
    execute_node,
    get_canvas_state,
    recover_generation_tasks,
    reject_node,
    schedule_generation_retry,
    update_canvas_node,
)
from agent.tools.canvas_persistence import db as canvas_db


@pytest.fixture(autouse=True)
def _isolated_canvas_db(tmp_path, monkeypatch):
    """Give every canvas test its own fresh canvas.db.

    These tests share module-level state and `claim_pending_tasks` /
    `recover_generation_tasks` are GLOBAL (not thread-scoped). Without isolation,
    pending image nodes left by one test (or a prior pytest run against the dev
    canvas.db) leak into another and break exact-count assertions.

    canvas.db now resolves through the shared `resolve_data_dir` policy
    (CASCADE_DB_PATH override → that file's dir), same as cascade.db. We set the
    env var to a temp file so `canvas_db_path()` lands the per-test canvas.db
    beside it — this is the standard isolation pattern the rest of the DB suite
    uses, and it exercises the real override path (not a monkeypatched constant).
    """
    p = tmp_path / "canvas.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    canvas_db._MIGRATED_PATHS.discard(str(p))
    yield


def _unique_thread():
    return f"test-{uuid.uuid4().hex[:8]}"


def test_create_node():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("script", "开场独白", "主角在雨夜")
    assert node["type"] == "script"
    assert node["node_status"] == "reviewing"
    assert node["asset_status"] == "idle"
    assert "id" in node
    state = get_canvas_state()
    assert len(state["nodes"]) == 1


def test_update_node():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("video", "测试视频", "一段测试")
    result = update_canvas_node(node["id"], asset_status="generating")
    assert result["asset_status"] == "generating"
    state = get_canvas_state()
    assert state["nodes"][0]["asset_status"] == "generating"


def test_delete_node():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("audio", "临时配音", "删除测试")
    result = delete_canvas_node(node["id"])
    assert result["deleted"] is True
    state = get_canvas_state()
    assert len(state["nodes"]) == 0


def test_execute_node():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("script", "策划书", "1 | 1 | 3s | 中景 | 赛博朋克城市夜景 | 切 | 电子乐")
    result = execute_node(node["id"], "script", node["description"])
    assert result["node_status"] == "reviewing"
    assert result["result"]["content"] == node["description"]
    assert len(result["result"]["shots"]) == 1


def test_approve_node():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("script", "测试脚本", "描述")
    execute_node(node["id"], "script", "描述")
    r = approve_node(node["id"])
    assert r["node_status"] == "confirmed"


def test_reject_node():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("script", "测试脚本", "描述")
    execute_node(node["id"], "script", "描述")
    r = reject_node(node["id"], "色调太暗")
    assert r["node_status"] == "reviewing"
    assert r["asset_status"] == "failed"
    assert r.get("feedback") == "色调太暗"


def test_update_done_blocked():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("script", "测试脚本", "描述")
    update_canvas_node(node["id"], node_status="confirmed")
    r = update_canvas_node(node["id"], description="新内容")
    assert "error" in r


def test_update_done_confirmed():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("script", "测试脚本", "描述")
    update_canvas_node(node["id"], node_status="confirmed")
    r = update_canvas_node(node["id"], description="新内容", confirmed=True)
    assert r["description"] == "新内容"


def test_update_pending_no_confirm():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("script", "测试脚本", "描述")
    r = update_canvas_node(node["id"], description="修改中")
    assert r["description"] == "修改中"


def test_edge_created():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    parent = create_canvas_node("script", "剧本", "测试")
    update_canvas_node(parent["id"], node_status="confirmed")
    child = create_canvas_node("image", "角色形象图", "测试", parent_ids=[parent["id"]], subtype="character")
    state = get_canvas_state()
    assert len(state["edges"]) == 1
    assert state["edges"][0]["source"] == parent["id"]
    assert state["edges"][0]["target"] == child["id"]


def test_generation_claim_sets_attempt_and_lease():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "测试图", "prompt")
    enqueue_generation(node["id"])

    tasks = claim_pending_tasks("image")

    assert [t["id"] for t in tasks] == [node["id"]]
    state = get_canvas_state(node["id"])["node"]
    assert state["generation_status"] == "submitted"
    assert state["generation_attempt_count"] == 1
    assert state["generation_lease_until"]
    assert state["generation_next_retry_at"] is None


def test_generation_retry_backoff_blocks_immediate_claim():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "重试图", "prompt")
    enqueue_generation(node["id"])
    claim_pending_tasks("image")

    assert schedule_generation_retry(node["id"], "provider 503") is True
    state = get_canvas_state(node["id"])["node"]
    assert state["generation_status"] == "pending"
    assert state["generation_error"] == "provider 503"
    assert state["generation_next_retry_at"]
    assert claim_pending_tasks("image") == []


def test_generation_recover_only_expired_lease():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "租约图", "prompt")
    enqueue_generation(node["id"])
    claim_pending_tasks("image")

    assert recover_generation_tasks("image") == []
