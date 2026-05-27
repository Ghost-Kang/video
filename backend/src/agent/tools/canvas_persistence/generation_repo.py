"""生成队列状态机 — claim / recover / 单点状态更新。

跨用户查询(claim_pending_tasks / recover_generation_tasks)不走 _resolve_ids,
直接扫全表。per-task 状态更新走 nodes_repo 的 _load_node / _upsert_node 显式参数。

asyncio 单线程下 claim 是原子的(sqlite3 同步调用,SELECT + UPDATE 之间无 yield 点)。
"""

from __future__ import annotations

from agent.tools.canvas_persistence.db import _db
from agent.tools.canvas_persistence.nodes_repo import _load_node, _row_to_node, _upsert_node


def claim_pending_tasks(task_type: str | None = None) -> list[dict]:
    """获取所有 pending 节点并原子认领(状态→submitted)。

    Args:
        task_type: 可选 node type 过滤。None = 所有 type;非 None 时 SQL 层过滤,
                   配合 per-type worker 使用,避免互相认领。
    """
    db = _db()
    if task_type is None:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status='pending' ORDER BY rowid"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status='pending' AND type=? ORDER BY rowid",
            (task_type,),
        ).fetchall()
    tasks = [_row_to_node(r) for r in rows]
    for t in tasks:
        db.execute(
            "UPDATE canvas_nodes SET generation_status='submitted' WHERE user_id=? AND thread_id=? AND node_id=?",
            (t["user_id"], t["thread_id"], t["id"]),
        )
    db.commit()
    db.close()
    if tasks:
        label = task_type or "all"
        print(f"[队列] claim {len(tasks)} 个待生成任务 (type={label})")
    return tasks


def recover_generation_tasks(task_type: str | None = None) -> list[dict]:
    """获取所有 submitted/polling 状态的节点(服务重启后恢复)。"""
    db = _db()
    if task_type is None:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status IN ('submitted', 'polling') ORDER BY rowid"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status IN ('submitted', 'polling') AND type=? ORDER BY rowid",
            (task_type,),
        ).fetchall()
    tasks = [_row_to_node(r) for r in rows]
    db.close()
    if tasks:
        label = task_type or "all"
        print(f"[队列] 恢复 {len(tasks)} 个未完成任务 (type={label})")
    return tasks


def update_generation_state(
    node_id: str,
    status: str,
    task_id: str | None = None,
    error: str | None = None,
    *,
    user_id: str | None = None,
    thread_id: str | None = None,
) -> None:
    """更新节点的生成队列状态 + 同步 asset_status。

    worker pipeline 必须显式传 user_id/thread_id;handler 调用可省略走 ContextVar。
    """
    node = _load_node(node_id, user_id=user_id, thread_id=thread_id)
    if not node:
        return
    node["generation_status"] = status
    if task_id is not None:
        node["generation_task_id"] = task_id
    if error is not None:
        node["generation_error"] = error
    if status == "done":
        node["asset_status"] = "done"
    elif status == "failed":
        node["asset_status"] = "failed"
        node["generation_error"] = error
    _upsert_node(node, user_id=user_id, thread_id=thread_id)
