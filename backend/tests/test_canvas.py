"""画布工具验证"""

import json
import uuid

import pytest
from agent.tools import canvas as canvas_tools
from agent.tools.canvas import (
    create_canvas_node,
    delete_canvas_node,
    execute_node,
    update_canvas_node,
)


def _unique_thread():
    return f"test-{uuid.uuid4().hex[:8]}"


# ---------- 直接调用 ----------


def test_create_node_persists():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)

    node = create_canvas_node("script", "开场独白", "主角在雨夜的街道上独行")
    assert node["type"] == "script"
    assert node["title"] == "开场独白"
    assert node["status"] == "pending"
    assert "id" in node

    # 验证 JSON 文件已创建
    f = canvas_tools._canvas_file()
    assert f.exists()
    data = json.loads(f.read_text())
    assert node["id"] in data["nodes"]


def test_update_node_persists():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)

    node = create_canvas_node("video", "测试视频", "一段测试")
    result = update_canvas_node(node["id"], status="executing")
    assert result["status"] == "executing"

    # 验证文件已更新
    f = canvas_tools._canvas_file()
    data = json.loads(f.read_text())
    assert data["nodes"][node["id"]]["status"] == "executing"


def test_delete_node():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)

    node = create_canvas_node("audio", "临时配音", "删除测试")
    result = delete_canvas_node(node["id"])
    assert result["deleted"] is True

    f = canvas_tools._canvas_file()
    data = json.loads(f.read_text())
    assert node["id"] not in data["nodes"]


def test_execute_node_persists():
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)

    node = create_canvas_node("storyboard", "科幻分镜", "赛博朋克城市夜景")
    result = execute_node(node["id"], "storyboard", node["description"])

    assert result["status"] == "done"
    assert len(result["result"]["shots"]) == 3

    # 验证文件同步更新
    f = canvas_tools._canvas_file()
    data = json.loads(f.read_text())
    assert data["nodes"][node["id"]]["status"] == "done"
    assert data["nodes"][node["id"]]["result"] is not None


# ---------- 导演 agent 端到端 ----------


def test_director_create_and_execute_workflow():
    """验证导演按 create → execute 流程操作画布"""
    tid = _unique_thread()
    canvas_tools.set_thread_id(tid)

    from agent.main import create_director_agent

    agent = create_director_agent()
    result = agent.invoke({
        "messages": [{"role": "user", "content": "帮我写一个10秒短片剧本：一只猫在窗台上晒太阳"}]
    })

    tool_names = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_names.append(tc["name"])

    print(f"调用的工具: {tool_names}")
    assert "create_canvas_node" in tool_names
    assert "execute_node" in tool_names

    # 验证画布文件已存在且有内容
    f = canvas_tools._canvas_file()
    assert f.exists()
    data = json.loads(f.read_text())
    assert len(data["nodes"]) > 0
    print(f"画布节点数: {len(data['nodes'])}")
