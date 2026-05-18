"""画布工具验证 — SQLite 持久化"""

import uuid

import pytest
from agent.tools import canvas as canvas_tools
from agent.tools.canvas import (
    approve_node,
    create_canvas_node,
    delete_canvas_node,
    execute_node,
    get_canvas_state,
    reject_node,
    update_canvas_node,
)


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
