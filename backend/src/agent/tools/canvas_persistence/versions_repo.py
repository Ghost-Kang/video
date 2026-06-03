"""节点产物版本快照 — time-travel 回溯(canvas 统筹 P2 slice-2)。

「回上游改重生下游」前,把下游节点当前产物(description + result + asset_status)
快照一行,旧版本不丢(2b 做新旧对比 UI)。append-only,version_seq 每节点自增。
同步 sqlite3,镜像 nodes_repo / edges_repo 的连接模式。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from agent.tools.canvas_persistence.db import _db, _resolve_ids


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot_version(
    node: dict, reason: str, *, user_id: str | None = None, thread_id: str | None = None
) -> int:
    """把 node 的**当前**产物快照成一行,返回新 version_seq。

    在 regenerate 覆盖节点产物**之前**调用 —— 旧版本(description+result+asset_status)
    存档,2b 可回看/对比。版本号每节点自增(MAX+1)。

    **无产物不存**:result=None 没什么可归档。regenerate/restore 在 mid-generation
    (节点已被清成 result=None/asset=generating)时可能传进没产物的 node,跳过避免写
    result=None 的 junk 归档行(否则 NodeVersionHistory 默认选中它、回滚到它会把节点弄成
    product-less 卡死)。返回 0 表示未写。"""
    if node.get("result") is None:
        return 0
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    try:
        row = db.execute(
            "SELECT COALESCE(MAX(version_seq), 0) + 1 FROM canvas_node_versions "
            "WHERE user_id=? AND thread_id=? AND node_id=?",
            (uid, tid, node["id"]),
        ).fetchone()
        seq = int(row[0])
        r = node.get("result")
        result_json = json.dumps(r, ensure_ascii=False) if r is not None else None
        db.execute(
            "INSERT INTO canvas_node_versions "
            "(user_id, thread_id, node_id, version_seq, description, result, asset_status, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uid, tid, node["id"], seq,
                node.get("description", ""), result_json,
                node.get("asset_status", "idle"), reason, _now(),
            ),
        )
        db.commit()
        return seq
    finally:
        db.close()


def list_versions(
    node_id: str, *, user_id: str | None = None, thread_id: str | None = None
) -> list[dict]:
    """该节点的版本快照,按 version_seq 升序。供 2b 对比 UI / reconnect 重放。"""
    uid, tid = _resolve_ids(user_id, thread_id)
    db = _db()
    try:
        rows = db.execute(
            "SELECT version_seq, description, result, asset_status, reason, created_at "
            "FROM canvas_node_versions WHERE user_id=? AND thread_id=? AND node_id=? "
            "ORDER BY version_seq",
            (uid, tid, node_id),
        ).fetchall()
    finally:
        db.close()
    out: list[dict] = []
    for r in rows:
        result = None
        if r["result"]:
            try:
                result = json.loads(r["result"])
            except json.JSONDecodeError:
                result = None
        out.append({
            "version_seq": r["version_seq"],
            "description": r["description"],
            "result": result,
            "asset_status": r["asset_status"],
            "reason": r["reason"],
            "created_at": r["created_at"],
        })
    return out
