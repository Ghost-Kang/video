"""生成队列状态机 — claim / recover / 单点状态更新。

跨用户查询(claim_pending_tasks / recover_generation_tasks)不走 _resolve_ids,
直接扫全表。per-task 状态更新走 nodes_repo 的 _load_node / _upsert_node 显式参数。

asyncio 单线程下 claim 是原子的(sqlite3 同步调用,SELECT + UPDATE 之间无 yield 点)。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.tools.canvas_persistence.db import _db
from agent.tools.canvas_persistence.nodes_repo import _load_node, _row_to_node, _upsert_node


GENERATION_LEASE_SECONDS = 300
GENERATION_RETRY_BASE_SECONDS = 15
GENERATION_RETRY_MAX_SECONDS = 300
GENERATION_MAX_ATTEMPTS = 3


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _retry_delay_seconds(attempt_count: int) -> int:
    attempt = max(1, attempt_count)
    return min(GENERATION_RETRY_BASE_SECONDS * (2 ** (attempt - 1)), GENERATION_RETRY_MAX_SECONDS)


def claim_pending_tasks(task_type: str | None = None) -> list[dict]:
    """获取所有 pending 节点并原子认领(状态→submitted)。

    Args:
        task_type: 可选 node type 过滤。None = 所有 type;非 None 时 SQL 层过滤,
                   配合 per-type worker 使用,避免互相认领。
    """
    db = _db()
    now = _iso(_utc_now())
    lease_until = _iso(_utc_now() + timedelta(seconds=GENERATION_LEASE_SECONDS))
    if task_type is None:
        rows = db.execute(
            """SELECT * FROM canvas_nodes
               WHERE generation_status='pending'
                 AND (generation_next_retry_at IS NULL OR generation_next_retry_at <= ?)
               ORDER BY rowid""",
            (now,),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT * FROM canvas_nodes
               WHERE generation_status='pending'
                 AND type=?
                 AND (generation_next_retry_at IS NULL OR generation_next_retry_at <= ?)
               ORDER BY rowid""",
            (task_type, now),
        ).fetchall()
    tasks = [_row_to_node(r) for r in rows]
    for t in tasks:
        db.execute(
            """UPDATE canvas_nodes
               SET generation_status='submitted',
                   generation_attempt_count=generation_attempt_count + 1,
                   generation_lease_until=?,
                   generation_next_retry_at=NULL,
                   generation_error=NULL
               WHERE user_id=? AND thread_id=? AND node_id=?""",
            (lease_until, t["user_id"], t["thread_id"], t["id"]),
        )
    db.commit()
    db.close()
    if tasks:
        label = task_type or "all"
        print(f"[队列] claim {len(tasks)} 个待生成任务 (type={label})")
    return tasks


def recover_generation_tasks(task_type: str | None = None) -> list[dict]:
    """获取 lease 过期的 submitted/polling 节点(服务重启后恢复)。"""
    db = _db()
    now = _iso(_utc_now())
    lease_until = _iso(_utc_now() + timedelta(seconds=GENERATION_LEASE_SECONDS))
    if task_type is None:
        rows = db.execute(
            """SELECT * FROM canvas_nodes
               WHERE generation_status IN ('submitted', 'polling')
                 AND (generation_lease_until IS NULL OR generation_lease_until <= ?)
               ORDER BY rowid""",
            (now,),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT * FROM canvas_nodes
               WHERE generation_status IN ('submitted', 'polling')
                 AND type=?
                 AND (generation_lease_until IS NULL OR generation_lease_until <= ?)
               ORDER BY rowid""",
            (task_type, now),
        ).fetchall()
    tasks = [_row_to_node(r) for r in rows]
    for t in tasks:
        db.execute(
            """UPDATE canvas_nodes
               SET generation_attempt_count=generation_attempt_count + 1,
                   generation_lease_until=?
               WHERE user_id=? AND thread_id=? AND node_id=?""",
            (lease_until, t["user_id"], t["thread_id"], t["id"]),
        )
    db.commit()
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
    # 取消守卫(逐镜取消,P2 ③):节点已被用户取消 → worker 对在途任务的回写一律跳过(取消
    # 优先,防 in-flight 竞态:已 claim 的任务跑完会盖掉取消)。重新生成走 enqueue 直接置
    # pending(不经此函数),故能正常重启;只有这条旧任务的回写被拦下。
    if node.get("generation_status") == "cancelled":
        return
    node["generation_status"] = status
    if task_id is not None:
        node["generation_task_id"] = task_id
    if error is not None:
        node["generation_error"] = error
    if status == "done":
        node["asset_status"] = "done"
        node["generation_lease_until"] = None
        node["generation_next_retry_at"] = None
    elif status == "failed":
        node["asset_status"] = "failed"
        node["generation_error"] = error
        node["generation_lease_until"] = None
        node["generation_next_retry_at"] = None
    elif status == "pending":
        node["generation_lease_until"] = None
    _upsert_node(node, user_id=user_id, thread_id=thread_id)


def schedule_generation_retry(
    node_id: str,
    error: str,
    *,
    user_id: str | None = None,
    thread_id: str | None = None,
) -> bool:
    """Return a generation task to pending with exponential backoff.

    Returns False when the task has exhausted attempts and is marked failed.
    """
    node = _load_node(node_id, user_id=user_id, thread_id=thread_id)
    if not node:
        return False
    # 终态守卫(bug 审计 2026-06-04 #9):已是终态的节点不重试 —— 不仅 cancelled,
    # done/failed 也算。否则一条迟到的失败回调能把已成功(done)的节点拉回 pending,
    # 用户看到「明明好了又转圈」;已 failed 的节点被陈旧回调重新入队也无意义。
    # 正常流程里此刻状态是 submitted/polling(在途),不受影响。
    if node.get("generation_status") in ("cancelled", "done", "failed"):
        return False
    attempts = int(node.get("generation_attempt_count") or 0)
    if attempts >= GENERATION_MAX_ATTEMPTS:
        node["generation_status"] = "failed"
        node["asset_status"] = "failed"
        node["generation_error"] = error
        node["generation_lease_until"] = None
        node["generation_next_retry_at"] = None
        _upsert_node(node, user_id=user_id, thread_id=thread_id)
        return False

    delay = _retry_delay_seconds(attempts)
    node["generation_status"] = "pending"
    node["asset_status"] = "generating"
    node["generation_error"] = error
    node["generation_lease_until"] = None
    node["generation_next_retry_at"] = _iso(_utc_now() + timedelta(seconds=delay))
    _upsert_node(node, user_id=user_id, thread_id=thread_id)
    return True
