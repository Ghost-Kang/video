"""节点 CRUD — load / upsert + Pydantic validation。

`_row_to_node` 走 `CanvasNode.model_validate` (Codex-F),drift 直接 raise。
"""

from __future__ import annotations

import json
import sqlite3

from agent.cascade.canvas_contract import CanvasNode
from agent.tools.canvas_persistence.db import _db, _resolve_ids


def _row_to_node(row: sqlite3.Row) -> dict:
    """SQLite row → node dict(按列名访问,兼容新旧表结构)。"""
    d = {
        "id": row["node_id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "node_status": row["node_status"] or "reviewing",
        "asset_status": row["asset_status"] or "idle",
        "result": None,
        "subtype": row["subtype"],
        "shot_no": row["shot_no"],
        "image_gen_provider": row["image_gen_provider"],
        "generation_status": row["generation_status"] or "idle",
        "generation_task_id": row["generation_task_id"],
        "generation_error": row["generation_error"],
        "generation_attempt_count": row["generation_attempt_count"] or 0,
        "generation_lease_until": row["generation_lease_until"],
        "generation_next_retry_at": row["generation_next_retry_at"],
        "user_id": row["user_id"],
        "thread_id": row["thread_id"],
        "x": row["x"],
        "y": row["y"],
    }
    if d["result"] is None and row["result"]:
        try:
            d["result"] = json.loads(row["result"])
        except json.JSONDecodeError:
            d["result"] = None
    return CanvasNode.model_validate(d).model_dump(mode="json")


def _load_node(node_id: str, *, user_id: str | None = None, thread_id: str | None = None) -> dict | None:
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    row = db.execute(
        "SELECT * FROM canvas_nodes WHERE user_id=? AND thread_id=? AND node_id=?",
        (uid, tid, node_id),
    ).fetchone()
    db.close()
    return _row_to_node(row) if row else None


def _load_all_nodes(*, user_id: str | None = None, thread_id: str | None = None) -> dict[str, dict]:
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    rows = db.execute(
        "SELECT * FROM canvas_nodes WHERE user_id=? AND thread_id=?", (uid, tid)
    ).fetchall()
    db.close()
    return {r["node_id"]: _row_to_node(r) for r in rows}


def _upsert_node(node: dict, *, user_id: str | None = None, thread_id: str | None = None) -> None:
    db = _db()
    r = node.get("result")
    result_json = json.dumps(r, ensure_ascii=False) if r is not None else None
    uid, tid = _resolve_ids(user_id, thread_id)
    values = (
        node["type"], node["title"], node.get("description", ""), node.get("status", "pending"),
        node.get("node_status", "reviewing"), node.get("asset_status", "idle"),
        result_json, node.get("subtype"),
        node.get("shot_no"), node.get("image_gen_provider"),
        node.get("generation_status", "idle"),
        node.get("generation_task_id"),
        node.get("generation_error"),
        node.get("generation_attempt_count", 0),
        node.get("generation_lease_until"),
        node.get("generation_next_retry_at"),
        node.get("x"), node.get("y"),
        uid, tid, node["id"],
    )
    cursor = db.execute(
        """UPDATE canvas_nodes SET
           type=?, title=?, description=?, status=?, node_status=?, asset_status=?,
           result=?, subtype=?, shot_no=?, image_gen_provider=?,
           generation_status=?, generation_task_id=?, generation_error=?,
           generation_attempt_count=?, generation_lease_until=?, generation_next_retry_at=?,
           x=?, y=?
           WHERE user_id=? AND thread_id=? AND node_id=?""",
        values,
    )
    if cursor.rowcount == 0:
        db.execute(
            """INSERT INTO canvas_nodes (user_id, thread_id, node_id, type, title, description, status, node_status, asset_status, result, subtype, shot_no, image_gen_provider, generation_status, generation_task_id, generation_error, generation_attempt_count, generation_lease_until, generation_next_retry_at, x, y)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                uid, tid, node["id"], node["type"], node["title"],
                node.get("description", ""), node.get("status", "pending"),
                node.get("node_status", "reviewing"), node.get("asset_status", "idle"),
                result_json, node.get("subtype"),
                node.get("shot_no"), node.get("image_gen_provider"),
                node.get("generation_status", "idle"),
                node.get("generation_task_id"),
                node.get("generation_error"),
                node.get("generation_attempt_count", 0),
                node.get("generation_lease_until"),
                node.get("generation_next_retry_at"),
                node.get("x"), node.get("y"),
            ),
        )
    db.commit()
    db.close()


def _update_node_result(
    node_id: str,
    updates: dict,
    *,
    user_id: str | None = None,
    thread_id: str | None = None,
) -> None:
    """Patch node.result dict. 节点不存在 silently no-op。"""
    node = _load_node(node_id, user_id=user_id, thread_id=thread_id)
    if node:
        existing = node.get("result") or {}
        if isinstance(existing, dict):
            existing.update(updates)
        else:
            existing = updates
        node["result"] = existing
        _upsert_node(node, user_id=user_id, thread_id=thread_id)


def _delete_node(node_id: str, *, user_id: str | None = None, thread_id: str | None = None) -> None:
    """删除节点 + 级联删除所有连接的 edge(同一连接内原子完成)。"""
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    db.execute(
        "DELETE FROM canvas_nodes WHERE user_id=? AND thread_id=? AND node_id=?",
        (uid, tid, node_id),
    )
    db.execute(
        "DELETE FROM canvas_edges WHERE user_id=? AND thread_id=? AND (source=? OR target=?)",
        (uid, tid, node_id, node_id),
    )
    db.commit()
    db.close()
