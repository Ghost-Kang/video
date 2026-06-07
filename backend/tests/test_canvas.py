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


def test_execute_node_inflight_is_idempotent_no_reset():
    """H2:媒体节点已在途时,重复 execute_node 不能把它重置 generating/_pending_submit
    (否则二次 submit 付费调用 + 并发回写)。返回 _already_in_flight,不返回 _pending_submit。"""
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "在途图", "prompt")
    # 模拟已在途(worker 提交后状态)
    enqueue_generation(node["id"])
    claim_pending_tasks("image")  # → generation_status = submitted
    before = get_canvas_state(node["id"])["node"]
    assert before["generation_status"] == "submitted"

    result = execute_node(node["id"], "image", "新 prompt")

    assert result.get("_already_in_flight") is True
    assert "_pending_submit" not in result
    after = get_canvas_state(node["id"])["node"]
    # 状态/任务未被重置(仍是 submitted,attempt 不增)
    assert after["generation_status"] == "submitted"
    assert after["generation_attempt_count"] == before["generation_attempt_count"]


def test_execute_node_proceeds_after_terminal_status():
    """H2 守卫只拦在途(pending/submitted/polling);done/failed/cancelled 等终态正常重新执行。"""
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "已完成图", "prompt")
    canvas_tools._update_node_result(node["id"], {"url": "https://done.png"})
    n = canvas_tools._load_node(node["id"])
    n["generation_status"] = "done"
    canvas_tools._upsert_node(n)

    result = execute_node(node["id"], "image", "再来一张")

    assert result.get("_pending_submit") is True
    assert "_already_in_flight" not in result


def test_regenerate_node_inflight_returns_none():
    """H2:在途节点 regenerate 应返回 None(幂等,不重复 submit),镜像 restore_node_version。"""
    from agent.tools.canvas import regenerate_node

    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    node = create_canvas_node("image", "在途重生图", "prompt")
    canvas_tools._update_node_result(node["id"], {"url": "https://v1.png"})
    enqueue_generation(node["id"])
    claim_pending_tasks("image")  # → submitted(在途)

    assert regenerate_node(node["id"]) is None
    # 节点未被清产物/重置
    state = get_canvas_state(node["id"])["node"]
    assert state["generation_status"] == "submitted"
    assert (state.get("result") or {}).get("url") == "https://v1.png"


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


# ── M1(审计 2026-06-06):create_canvas_node 三条拒绝分支(护栏唯一机制,之前零负向测试) ──


def test_create_node_rejects_missing_parent():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    res = create_canvas_node("image", "孤儿", "x", parent_ids=["nope"], subtype="character")
    assert "error" in res and "不存在" in res["error"]


def test_create_node_rejects_unconfirmed_parent():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    parent = create_canvas_node("script", "父", "x")  # 默认 reviewing,未确认
    res = create_canvas_node("image", "子", "y", parent_ids=[parent["id"]], subtype="character")
    assert "error" in res and "确认" in res["error"]
    # 护栏触发时不应建出节点的下游边
    assert canvas_tools._load_all_edges() == []


def test_create_node_rejects_illegal_hierarchy():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    parent = create_canvas_node("script", "父", "x")
    update_canvas_node(parent["id"], node_status="confirmed")
    # grid 的父必须是 image(character|scene),挂在 script 下非法
    res = create_canvas_node("image", "宫格", "y", parent_ids=[parent["id"]], subtype="grid")
    assert "error" in res and "层级" in res["error"]


# ── M2(审计 2026-06-06):手动连线 create_canvas_edge 的领域校验 ──────────────


def _mk_edge_node(nid, *, type="image", subtype=None, node_status="reviewing"):
    canvas_tools._upsert_node({
        "id": nid, "type": type, "title": nid, "description": f"desc-{nid}",
        "status": "pending", "node_status": node_status, "asset_status": "idle",
        "result": None, "needs_regen": False, "subtype": subtype,
    })


def test_create_edge_valid_script_to_character():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    _mk_edge_node("s1", type="script", node_status="confirmed")
    _mk_edge_node("c1", type="image", subtype="character")
    edge = canvas_tools.create_canvas_edge("s1", "c1")
    assert "error" not in edge
    assert edge["source"] == "s1" and edge["target"] == "c1"


def test_create_edge_rejects_unconfirmed_parent():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    _mk_edge_node("s1", type="script", node_status="reviewing")  # 未确认
    _mk_edge_node("c1", type="image", subtype="character")
    res = canvas_tools.create_canvas_edge("s1", "c1")
    assert "error" in res and "确认" in res["error"]
    assert canvas_tools._load_all_edges() == []  # 没建出边


def test_create_edge_rejects_illegal_hierarchy():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    _mk_edge_node("s1", type="script", node_status="confirmed")
    _mk_edge_node("g1", type="image", subtype="grid")  # grid 父必须 character/scene
    res = canvas_tools.create_canvas_edge("s1", "g1")
    assert "error" in res and "层级" in res["error"]


def test_create_edge_rejects_cycle():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    _mk_edge_node("a", type="script", node_status="confirmed")
    _mk_edge_node("b", type="script", node_status="confirmed")
    canvas_tools._upsert_edge({"id": "a-b", "source": "a", "target": "b"})  # 已有 a→b
    res = canvas_tools.create_canvas_edge("b", "a")  # 连 b→a 成环
    assert "error" in res and "环" in res["error"]


def test_create_edge_rejects_self_loop():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    _mk_edge_node("s1", type="script", node_status="confirmed")
    res = canvas_tools.create_canvas_edge("s1", "s1")
    assert "error" in res


# ── M4(审计 2026-06-06):pending 预占额度求和 ──────────────────────────────


def test_pending_reserved_sums_only_pending_media():
    """只数 pending 的 image/video(图 ¥1.5、视频 ¥0.3/秒);done/submitted 不算。"""
    import pytest

    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)
    img = create_canvas_node("image", "图", "p")
    enqueue_generation(img["id"])  # pending → 1.5
    vid = create_canvas_node("video", "视频", "p")
    canvas_tools._update_node_result(vid["id"], {"duration": 10})
    enqueue_generation(vid["id"])  # pending → 10 * 0.3 = 3.0
    # done 节点不占额度
    done = create_canvas_node("image", "完成图", "p")
    dn = canvas_tools._load_node(done["id"])
    dn["generation_status"] = "done"
    canvas_tools._upsert_node(dn)

    reserved = canvas_tools.pending_generation_reserved_cny(thread_id=tid)
    assert reserved == pytest.approx(1.5 + 3.0)

    # claim image → submitted(已在 submit 时 emit,走 recorded)→ 不再计入预占
    claim_pending_tasks("image")
    reserved2 = canvas_tools.pending_generation_reserved_cny(thread_id=tid)
    assert reserved2 == pytest.approx(3.0)  # 只剩 pending 的视频
