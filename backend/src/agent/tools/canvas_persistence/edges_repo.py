"""边 CRUD — load_all / upsert / position 重整。"""

from __future__ import annotations

from agent.tools.canvas_persistence.db import _db, _resolve_ids


def _load_all_edges(*, user_id: str | None = None, thread_id: str | None = None) -> list[dict]:
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    rows = db.execute(
        "SELECT edge_id, source, target, position FROM canvas_edges WHERE user_id=? AND thread_id=? ORDER BY position",
        (uid, tid),
    ).fetchall()
    db.close()
    return [
        {"id": r["edge_id"], "source": r["source"], "target": r["target"], "position": r["position"]}
        for r in rows
    ]


def _upsert_edge(edge: dict, *, user_id: str | None = None, thread_id: str | None = None) -> None:
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    # 自动分配 position:该 target 已有边数 + 1
    if edge.get("position") is None:
        existing = db.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM canvas_edges WHERE user_id=? AND thread_id=? AND target=?",
            (uid, tid, edge["target"]),
        ).fetchone()
        edge["position"] = existing[0] if existing else 1
    db.execute(
        "INSERT INTO canvas_edges (user_id, thread_id, edge_id, source, target, position) VALUES (?, ?, ?, ?, ?, ?)",
        (uid, tid, edge["id"], edge["source"], edge["target"], edge["position"]),
    )
    db.commit()
    db.close()


def _renormalize_positions(target_id: str, *, user_id: str | None = None, thread_id: str | None = None) -> None:
    """重整 position,确保同一 target 下的边位置连续 (1,2,3...)。"""
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    rows = db.execute(
        "SELECT edge_id FROM canvas_edges WHERE user_id=? AND thread_id=? AND target=? ORDER BY position",
        (uid, tid, target_id),
    ).fetchall()
    for i, row in enumerate(rows):
        db.execute(
            "UPDATE canvas_edges SET position=? WHERE user_id=? AND thread_id=? AND edge_id=?",
            (i + 1, uid, tid, row["edge_id"]),
        )
    db.commit()
    db.close()
