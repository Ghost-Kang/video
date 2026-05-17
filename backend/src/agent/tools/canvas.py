"""画布工具 — SQLite 持久化"""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Literal

NodeType = Literal["script", "storyboard", "image", "video", "audio"]
ImageSubtype = Literal["character", "scene", "grid"] | None
AudioSubtype = Literal["character_voice"] | None
NodeStatus = Literal["pending", "approved", "executing", "awaiting_review", "done", "failed"]

_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "canvas.db"
_current_thread_id = "default"


def set_thread_id(thread_id: str):
    global _current_thread_id
    _current_thread_id = thread_id


def _node_id(type: str) -> str:
    return f"{type}-{uuid.uuid4().hex[:6]}"


# ---------- 数据库 ----------


def _db() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """CREATE TABLE IF NOT EXISTS canvas_nodes (
            thread_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            subtype TEXT,
            feedback TEXT,
            x REAL, y REAL,
            PRIMARY KEY (thread_id, node_id)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS canvas_edges (
            thread_id TEXT NOT NULL,
            edge_id TEXT NOT NULL,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (thread_id, edge_id)
        )"""
    )
    return db


def _row_to_node(row: tuple) -> dict:
    """SQLite row → node dict"""
    cols = ["thread_id", "node_id", "type", "title", "description", "status", "result", "subtype", "feedback", "x", "y"]
    d = dict(zip(cols, row))
    # 去掉内部字段
    d["id"] = d.pop("node_id")
    d.pop("thread_id", None)
    d.pop("feedback", None)
    # 解析 result JSON
    if d["result"]:
        try:
            d["result"] = json.loads(d["result"])
        except json.JSONDecodeError:
            d["result"] = None
    else:
        d["result"] = None
    return d


def _load_node(node_id: str) -> dict | None:
    db = _db()
    row = db.execute(
        "SELECT * FROM canvas_nodes WHERE thread_id=? AND node_id=?",
        (_current_thread_id, node_id),
    ).fetchone()
    db.close()
    return _row_to_node(row) if row else None


def _load_all_nodes() -> dict[str, dict]:
    db = _db()
    rows = db.execute(
        "SELECT * FROM canvas_nodes WHERE thread_id=?", (_current_thread_id,)
    ).fetchall()
    db.close()
    return {r[1]: _row_to_node(r) for r in rows}


def _load_all_edges() -> list[dict]:
    db = _db()
    rows = db.execute(
        "SELECT edge_id, source, target FROM canvas_edges WHERE thread_id=?",
        (_current_thread_id,),
    ).fetchall()
    db.close()
    return [{"id": r[0], "source": r[1], "target": r[2]} for r in rows]


def _upsert_node(node: dict):
    db = _db()
    r = node.get("result")
    result_json = json.dumps(r, ensure_ascii=False) if r is not None else None
    db.execute(
        """INSERT INTO canvas_nodes (thread_id, node_id, type, title, description, status, result, subtype, x, y)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(thread_id, node_id) DO UPDATE SET
           type=excluded.type, title=excluded.title, description=excluded.description,
           status=excluded.status, result=excluded.result, subtype=excluded.subtype,
           x=excluded.x, y=excluded.y""",
        (
            _current_thread_id, node["id"], node["type"], node["title"],
            node.get("description", ""), node["status"], result_json,
            node.get("subtype"), node.get("x"), node.get("y"),
        ),
    )
    db.commit()
    db.close()


def _upsert_edge(edge: dict):
    db = _db()
    db.execute(
        "INSERT INTO canvas_edges (thread_id, edge_id, source, target) VALUES (?, ?, ?, ?)",
        (_current_thread_id, edge["id"], edge["source"], edge["target"]),
    )
    db.commit()
    db.close()


# ---------- 节点 CRUD ----------


def create_canvas_node(
    type: NodeType,
    title: str,
    description: str = "",
    parent_id: str = "",
    subtype: str | None = None,
) -> dict:
    """在画布上创建一个节点。type: script/storyboard/image/video/audio。"""
    nid = _node_id(type)
    node = {
        "id": nid, "type": type, "title": title, "description": description,
        "status": "pending", "result": None, "subtype": subtype,
    }

    # 上游校验
    if parent_id:
        parent = _load_node(parent_id)
        if not parent:
            return {"error": f"上游节点 {parent_id} 不存在"}
        if parent["status"] == "awaiting_review":
            return {
                "error": (
                    f"上游节点「{parent['title']}」({parent_id}) 尚未审核通过，"
                    f"当前状态为 {parent['status']}，无法创建下游节点。\n"
                    f"请告知用户：需先在画布上点击该节点，然后点击「通过」按钮完成审核，"
                    f"之后才能继续创建 {type} 节点。"
                )
            }

    _upsert_node(node)

    if parent_id:
        edge = {"id": f"e-{parent_id}-{nid}", "source": parent_id, "target": nid}
        _upsert_edge(edge)

    return node


def _update_node_result(node_id: str, updates: dict):
    node = _load_node(node_id)
    if node:
        existing = node.get("result") or {}
        if isinstance(existing, dict):
            existing.update(updates)
        else:
            existing = updates
        node["result"] = existing
        _upsert_node(node)


def update_canvas_node(
    node_id: str,
    title: str | None = None,
    description: str | None = None,
    status: NodeStatus | None = None,
    confirmed: bool = False,
) -> dict:
    """更新画布节点属性。修改 done/approved 节点需 confirmed=True。"""
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在"}

    changing_content = title is not None or description is not None
    if changing_content and node["status"] in ("done", "approved") and not confirmed:
        return {
            "error": (
                f"节点「{node['title']}」({node_id}) 状态为 {node['status']}，"
                f"修改其内容前必须先向用户确认。\n"
                f"请先向用户说明你要修改什么内容，征得同意后，"
                f"再调 update_canvas_node 并传入 confirmed=True。"
            )
        }

    if title is not None:
        node["title"] = title
    if description is not None:
        node["description"] = description
    if status is not None:
        node["status"] = status
    _upsert_node(node)
    return node


def delete_canvas_node(node_id: str) -> dict:
    """删除画布上的一个节点。"""
    db = _db()
    db.execute("DELETE FROM canvas_nodes WHERE thread_id=? AND node_id=?", (_current_thread_id, node_id))
    db.execute("DELETE FROM canvas_edges WHERE thread_id=? AND source=? OR target=?", (_current_thread_id, node_id, node_id))
    db.commit()
    db.close()
    return {"id": node_id, "deleted": True}


# ---------- 分镜解析 ----------


def _parse_storyboard(text: str) -> list[dict]:
    from agent.config import STORYBOARD_COLUMNS
    keys = [c["key"] for c in STORYBOARD_COLUMNS]
    required = [i for i, c in enumerate(STORYBOARD_COLUMNS) if c.get("required")]
    shots = []
    for line in text.strip().split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < max(required) + 1:
            continue
        # 跳过表头行
        if parts[0] in ("镜号", "no", "#", "shot"):
            continue
        shot = {}
        for i, key in enumerate(keys):
            shot[key] = parts[i] if i < len(parts) else ""
        shots.append(shot)
    return shots


# ---------- 节点执行 ----------


def execute_node(node_id: str, node_type: NodeType, description: str) -> dict:
    """执行节点资产生成。文字节点直接结构化，媒体节点需 approved 状态。"""
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在，请先 create"}

    if node_type == "script":
        node["status"] = "awaiting_review"
        node["result"] = {"content": description, "word_count": len(description)}
        _upsert_node(node)
        return {"id": node_id, "status": "awaiting_review", "result": node["result"]}

    if node_type == "storyboard":
        shots = _parse_storyboard(description)
        node["status"] = "awaiting_review"
        node["result"] = {"content": description, "shots": shots}
        _upsert_node(node)
        return {"id": node_id, "status": "awaiting_review", "result": node["result"]}

    if node["status"] != "approved":
        return {
            "error": (
                f"节点 {node_id} 当前状态为 {node['status']}，"
                f"必须先审核通过 prompt（状态应为 approved）后才能执行生成。"
                f"请先让用户审核该节点的 prompt 和参考图。"
            )
        }

    subtype = node.get("subtype")

    if node_type == "image":
        try:
            from agent.tools.generation import submit_image
            submitted = submit_image(prompt=description)
            result = {
                "prompt": description, "resolution": "1920x1080",
                "subtype": subtype,
                "task_id": submitted.get("task_id", ""),
                "error": submitted.get("error"),
            }
        except Exception as e:
            result = {"prompt": description, "resolution": "1920x1080", "subtype": subtype, "error": str(e)}
        final_status = "executing" if result.get("task_id") else "failed"
    elif node_type == "video":
        result = {"url": f"https://mock.videos/{node_id}.mp4", "prompt": description, "duration_seconds": 5, "resolution": "1920x1080"}
        final_status = "executing"
    elif node_type == "audio":
        result = {"url": f"https://mock.audio/{node_id}.mp3", "text": description, "voice": subtype or "default", "duration_seconds": 8, "subtype": subtype}
        if subtype == "character_voice":
            result["catchphrase"] = description[:50]
        final_status = "executing"
    else:
        node["status"] = "failed"
        _upsert_node(node)
        return {"id": node_id, "status": "failed", "error": f"未知节点类型: {node_type}"}

    node["status"] = final_status
    node["result"] = result
    _upsert_node(node)
    return {"id": node_id, "status": final_status, "result": result}


def get_canvas_state() -> dict:
    """读取当前画布全部节点摘要。返回 {nodes: [{id, type, title, status, subtype}], edges}。"""
    nodes = _load_all_nodes()
    edges = _load_all_edges()
    summary = []
    for n in nodes.values():
        summary.append({"id": n["id"], "type": n["type"], "title": n["title"], "status": n["status"], "subtype": n.get("subtype")})
    return {"nodes": summary, "edges": edges}


# ---------- 审核操作 ----------


def approve_node(node_id: str) -> dict:
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在"}
    node["status"] = "approved" if node["status"] == "pending" else "done"
    _upsert_node(node)
    return node


def reject_node(node_id: str, feedback: str = "") -> dict:
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在"}
    node["status"] = "failed"
    if feedback:
        node["feedback"] = feedback
    _upsert_node(node)
    return node
