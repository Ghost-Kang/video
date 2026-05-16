"""画布工具

操作画布 JSON 文件，持久化到本地文件系统。
"""

import json
import uuid
from pathlib import Path
from typing import Literal

NodeType = Literal["script", "storyboard", "image", "video", "audio"]
NodeStatus = Literal["pending", "executing", "done", "failed"]

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "canvas"
_current_thread_id = "default"


def set_thread_id(thread_id: str):
    """设置当前对话的 thread_id，工具内部据此定位画布文件。"""
    global _current_thread_id
    _current_thread_id = thread_id


# ---------- 内部 ----------


def _node_id(type: str) -> str:
    return f"{type}-{uuid.uuid4().hex[:6]}"


def _canvas_file() -> Path:
    return _DATA_DIR / f"{_current_thread_id}.json"


def _load() -> dict:
    f = _canvas_file()
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"nodes": {}, "edges": []}


def _save(data: dict):
    f = _canvas_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- 节点 CRUD ----------


def create_canvas_node(
    type: NodeType,
    title: str,
    description: str = "",
) -> dict:
    """在画布上创建一个节点，持久化到 JSON 文件。

    Args:
        type: script / storyboard / image / video / audio
        title: 节点标题
        description: 节点内容或描述
    """
    canvas = _load()
    nid = _node_id(type)
    node = {
        "id": nid,
        "type": type,
        "title": title,
        "description": description,
        "status": "pending",
        "result": None,
    }
    canvas["nodes"][nid] = node
    _save(canvas)
    return node


def update_canvas_node(
    node_id: str,
    title: str | None = None,
    description: str | None = None,
    status: NodeStatus | None = None,
) -> dict:
    """更新画布节点属性，只传需要修改的字段。

    Args:
        node_id: 节点 ID
        title: 新标题（可选）
        description: 新描述（可选）
        status: pending / executing / done / failed（可选）
    """
    canvas = _load()
    if node_id not in canvas["nodes"]:
        return {"error": f"节点 {node_id} 不存在"}
    node = canvas["nodes"][node_id]
    if title is not None:
        node["title"] = title
    if description is not None:
        node["description"] = description
    if status is not None:
        node["status"] = status
    _save(canvas)
    return node


def delete_canvas_node(node_id: str) -> dict:
    """删除画布上的一个节点。

    Args:
        node_id: 要删除的节点 ID
    """
    canvas = _load()
    if node_id in canvas["nodes"]:
        del canvas["nodes"][node_id]
    _save(canvas)
    return {"id": node_id, "deleted": True}


# ---------- 节点执行（mock 资产生成）----------


def execute_node(node_id: str, node_type: NodeType, description: str) -> dict:
    """执行节点内的资产生成任务。

    先从画布 JSON 中找到对应节点，mock 生成资产，
    然后将结果写回节点并更新状态为 done。

    Args:
        node_id: 节点 ID
        node_type: 节点类型
        description: 节点的当前描述/提示词，用于 mock 生成
    """
    canvas = _load()
    if node_id not in canvas["nodes"]:
        return {"error": f"节点 {node_id} 不存在，请先 create"}

    if node_type == "script":
        result = {
            "content": f"[剧本] 根据「{description[:80]}」生成的完整脚本...",
            "word_count": 120,
        }
    elif node_type == "storyboard":
        result = {
            "shots": [
                {"no": 1, "duration": 5, "camera": "中景固定", "description": "开场镜头"},
                {"no": 2, "duration": 8, "camera": "特写推近", "description": "细节强调"},
                {"no": 3, "duration": 7, "camera": "全景横移", "description": "环境展现"},
            ],
            "total_duration": 20,
        }
    elif node_type == "image":
        result = {
            "url": f"https://mock.images/{node_id}.png",
            "prompt": description,
            "resolution": "1920x1080",
        }
    elif node_type == "video":
        result = {
            "url": f"https://mock.videos/{node_id}.mp4",
            "prompt": description,
            "duration_seconds": 5,
            "resolution": "1920x1080",
        }
    elif node_type == "audio":
        result = {
            "url": f"https://mock.audio/{node_id}.mp3",
            "text": description,
            "voice": "default",
            "duration_seconds": 8,
        }
    else:
        canvas["nodes"][node_id]["status"] = "failed"
        _save(canvas)
        return {"id": node_id, "status": "failed", "error": f"未知节点类型: {node_type}"}

    canvas["nodes"][node_id]["status"] = "done"
    canvas["nodes"][node_id]["result"] = result
    _save(canvas)

    return {
        "id": node_id,
        "status": "done",
        "result": result,
    }
