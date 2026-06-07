"""Pro 计算图执行队列状态机 —— claim / recover / 单点状态更新(镜像 generation_repo)。

一个 pro_run = 一张提交的 ComfyUI 计算图。队列语义与 canvas 节点生成完全一致:
    enqueue(create_pro_run, status=pending)
      → claim_pending_pro_runs(原子认领 → submitted, 置 lease)
      → submit 后 update_pro_run_state('polling', comfy_prompt_id=...)
      → 完成 update_pro_run_state('done', result=[urls], expected_prompt_id=...)(fencing)
      → 失败 schedule_pro_run_retry(指数退避,满 3 次 → failed)

跨用户查询(claim/recover)直接扫全表(worker 用),不走 ContextVar。per-run 更新走显式
user_id/thread_id(worker 显式传)。asyncio 单线程下 claim 原子(SELECT+UPDATE 间无 yield)。

防错(与 generation_repo 同款):
  - 取消守卫:status=='cancelled' 的 run,worker 在途回写一律跳过(取消优先)。
  - fencing token:终态回写带 expected_prompt_id;若 row 的 comfy_prompt_id 已变(被取消/重提交清掉/换掉),
    说明这条 worker 已作废,迟到的状态翻转必须跳过。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from agent.tools.canvas_persistence.db import _db


PRO_RUN_LEASE_SECONDS = 600  # 比 canvas 节点(300s)长 —— ComfyUI 整图可能跑更久,避免健康任务被误恢复
PRO_RUN_RETRY_BASE_SECONDS = 15
PRO_RUN_RETRY_MAX_SECONDS = 300
PRO_RUN_MAX_ATTEMPTS = 3

_TERMINAL = ("cancelled", "done", "failed")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _retry_delay_seconds(attempt_count: int) -> int:
    attempt = max(1, attempt_count)
    return min(PRO_RUN_RETRY_BASE_SECONDS * (2 ** (attempt - 1)), PRO_RUN_RETRY_MAX_SECONDS)


def _row_to_run(row) -> dict:
    d = dict(row)
    raw = d.get("result")
    if raw:
        try:
            d["result"] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            d["result"] = None
    else:
        d["result"] = None
    return d


def _load_run(run_id: str, *, user_id: str, thread_id: str) -> dict | None:
    db = _db()
    try:
        row = db.execute(
            "SELECT * FROM pro_runs WHERE user_id=? AND thread_id=? AND run_id=?",
            (user_id, thread_id, run_id),
        ).fetchone()
    finally:
        db.close()
    return _row_to_run(row) if row else None


def create_pro_run(
    run_id: str,
    *,
    user_id: str,
    thread_id: str,
    graph_json: str,
    provider: str,
    cost_est: float,
) -> None:
    """入队一条 Pro run(status=pending)。worker 随后 claim。"""
    db = _db()
    try:
        db.execute(
            """INSERT OR REPLACE INTO pro_runs
               (user_id, thread_id, run_id, graph_json, provider, status, comfy_prompt_id,
                cost_est, error, result, attempt_count, lease_until, next_retry_at, created_at)
               VALUES (?,?,?,?,?, 'pending', NULL, ?, NULL, NULL, 0, NULL, NULL, ?)""",
            (user_id, thread_id, run_id, graph_json, provider, cost_est, _iso(_utc_now())),
        )
        db.commit()
    finally:
        db.close()


def claim_pending_pro_runs() -> list[dict]:
    """原子认领所有到期 pending 的 run(→ submitted,置 lease,attempt+1)。"""
    db = _db()
    now = _iso(_utc_now())
    lease_until = _iso(_utc_now() + timedelta(seconds=PRO_RUN_LEASE_SECONDS))
    try:
        rows = db.execute(
            """SELECT * FROM pro_runs
               WHERE status='pending'
                 AND (next_retry_at IS NULL OR next_retry_at <= ?)
               ORDER BY rowid""",
            (now,),
        ).fetchall()
        runs = [_row_to_run(r) for r in rows]
        for r in runs:
            db.execute(
                """UPDATE pro_runs
                   SET status='submitted', attempt_count=attempt_count + 1,
                       lease_until=?, next_retry_at=NULL, error=NULL
                   WHERE user_id=? AND thread_id=? AND run_id=?""",
                (lease_until, r["user_id"], r["thread_id"], r["run_id"]),
            )
        db.commit()
    finally:
        db.close()
    if runs:
        print(f"[ProQueue] claim {len(runs)} 个待执行计算图")
    return runs


def recover_pro_runs() -> list[dict]:
    """获取 lease 过期的 submitted/polling run(服务重启恢复)。"""
    db = _db()
    now = _iso(_utc_now())
    lease_until = _iso(_utc_now() + timedelta(seconds=PRO_RUN_LEASE_SECONDS))
    try:
        rows = db.execute(
            """SELECT * FROM pro_runs
               WHERE status IN ('submitted', 'polling')
                 AND (lease_until IS NULL OR lease_until <= ?)
               ORDER BY rowid""",
            (now,),
        ).fetchall()
        runs = [_row_to_run(r) for r in rows]
        for r in runs:
            db.execute(
                """UPDATE pro_runs
                   SET attempt_count=attempt_count + 1, lease_until=?
                   WHERE user_id=? AND thread_id=? AND run_id=?""",
                (lease_until, r["user_id"], r["thread_id"], r["run_id"]),
            )
        db.commit()
    finally:
        db.close()
    if runs:
        print(f"[ProQueue] 恢复 {len(runs)} 个未完成计算图")
    return runs


def update_pro_run_state(
    run_id: str,
    status: str,
    *,
    user_id: str,
    thread_id: str,
    comfy_prompt_id: str | None = None,
    error: str | None = None,
    result: list | None = None,
    expected_prompt_id: str | None = None,
) -> None:
    """更新一条 run 的队列状态。带取消守卫 + fencing(见模块 docstring)。

    expected_prompt_id=None = 不 fencing(submit 写 prompt_id 那次 / 直接调用,向后兼容)。
    """
    run = _load_run(run_id, user_id=user_id, thread_id=thread_id)
    if not run:
        return
    # 取消守卫:已取消的 run,worker 对在途任务的回写一律跳过(取消优先)。
    if run.get("status") == "cancelled":
        return
    # fencing:run 已被取消/重提交(comfy_prompt_id 变更)→ 这条陈旧 worker 的终态回写作废。
    if expected_prompt_id is not None and run.get("comfy_prompt_id") != expected_prompt_id:
        return

    new_prompt_id = comfy_prompt_id if comfy_prompt_id is not None else run.get("comfy_prompt_id")
    new_error = error if error is not None else run.get("error")
    result_json = json.dumps(result, ensure_ascii=False) if result is not None else (
        json.dumps(run["result"], ensure_ascii=False) if run.get("result") is not None else None
    )
    lease = run.get("lease_until")
    next_retry = run.get("next_retry_at")
    if status in ("done", "failed"):
        lease = None
        next_retry = None
    elif status == "pending":
        lease = None
    elif status == "polling":
        # 续租:让 lease 覆盖整个 poll 窗口,而不是硬扛 claim 时的 600s 减去 submit 耗时
        # (否则 submit 慢 + 满 300s poll 会逼近边界,recover 可能误抢在跑的 run)。
        lease = _iso(_utc_now() + timedelta(seconds=PRO_RUN_LEASE_SECONDS))

    # 原子化 cancel/fencing(review 修复 TOCTOU):把两个守卫塞进 WHERE。即使 _load_run 与本次
    # UPDATE 之间(跨连接、worker 在事件循环线程 vs cancel 在 to_thread 线程)行被取消或换了
    # prompt_id,这次写也只在守卫仍成立时落地(WAL 末写者胜)。Python 早返回只是快路径。
    where = "user_id=? AND thread_id=? AND run_id=? AND status != 'cancelled'"
    args: list = [status, new_prompt_id, new_error, result_json, lease, next_retry, user_id, thread_id, run_id]
    if expected_prompt_id is not None:
        where += " AND comfy_prompt_id = ?"
        args.append(expected_prompt_id)

    db = _db()
    try:
        db.execute(
            f"UPDATE pro_runs SET status=?, comfy_prompt_id=?, error=?, result=?, lease_until=?, next_retry_at=? WHERE {where}",
            tuple(args),
        )
        db.commit()
    finally:
        db.close()


def schedule_pro_run_retry(run_id: str, error: str, *, user_id: str, thread_id: str) -> bool:
    """退回 pending + 指数退避。已是终态(cancelled/done/failed)或耗尽次数 → 返回 False(置 failed)。"""
    run = _load_run(run_id, user_id=user_id, thread_id=thread_id)
    if not run:
        return False
    if run.get("status") in _TERMINAL:
        return False
    attempts = int(run.get("attempt_count") or 0)
    db = _db()
    try:
        if attempts >= PRO_RUN_MAX_ATTEMPTS:
            db.execute(
                """UPDATE pro_runs SET status='failed', error=?, lease_until=NULL, next_retry_at=NULL
                   WHERE user_id=? AND thread_id=? AND run_id=?""",
                (error, user_id, thread_id, run_id),
            )
            db.commit()
            return False
        delay = _retry_delay_seconds(attempts)
        db.execute(
            """UPDATE pro_runs SET status='pending', error=?, lease_until=NULL, next_retry_at=?
               WHERE user_id=? AND thread_id=? AND run_id=?""",
            (error, _iso(_utc_now() + timedelta(seconds=delay)), user_id, thread_id, run_id),
        )
        db.commit()
    finally:
        db.close()
    return True


def cancel_pro_run(run_id: str, *, user_id: str, thread_id: str) -> bool:
    """逐 run 取消。原子条件 UPDATE(无 load-then-write 竞态):只在 run 仍非终态时置 cancelled。

    返回是否真的发生了转换(rowcount>0)。与 update_pro_run_state 的 `status != 'cancelled'` 守卫
    互补:cancel 先到则 worker 终态写被挡(取消优先);worker done 先到则 cancel 落空返回 False。"""
    db = _db()
    try:
        cur = db.execute(
            """UPDATE pro_runs SET status='cancelled', lease_until=NULL, next_retry_at=NULL
               WHERE user_id=? AND thread_id=? AND run_id=? AND status NOT IN ('done','failed','cancelled')""",
            (user_id, thread_id, run_id),
        )
        db.commit()
        return cur.rowcount > 0
    finally:
        db.close()


def touch_lease(run_id: str, *, user_id: str, thread_id: str) -> None:
    """续租(per-node 执行器在每个慢节点后调,防长 run 被 recover 误抢)。仅对非终态/非取消生效。"""
    db = _db()
    lease_until = _iso(_utc_now() + timedelta(seconds=PRO_RUN_LEASE_SECONDS))
    try:
        db.execute(
            """UPDATE pro_runs SET lease_until=?
               WHERE user_id=? AND thread_id=? AND run_id=? AND status NOT IN ('done','failed','cancelled')""",
            (lease_until, user_id, thread_id, run_id),
        )
        db.commit()
    finally:
        db.close()


def get_pro_run(run_id: str, *, user_id: str, thread_id: str) -> dict | None:
    """读单条 run(状态查询 / 测试)。"""
    return _load_run(run_id, user_id=user_id, thread_id=thread_id)


def list_pro_runs(*, user_id: str, thread_id: str, limit: int = 50) -> list[dict]:
    """某 thread 的 run 列表(最新在前)。"""
    db = _db()
    try:
        rows = db.execute(
            "SELECT * FROM pro_runs WHERE user_id=? AND thread_id=? ORDER BY rowid DESC LIMIT ?",
            (user_id, thread_id, int(limit)),
        ).fetchall()
    finally:
        db.close()
    return [_row_to_run(r) for r in rows]
