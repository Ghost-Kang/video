"""Authoritative, persisted run-lifecycle record per thread (W5D4 P0-B).

Was an in-memory dict (lost on restart → `get_session_state` had to *infer*
status from the chat-history tail, which `50f37d8`/`de32e22` show is fragile).
Now every transition writes through to the `run_lifecycle` SQLite table, with
the in-memory map kept as a hot-read cache. On boot, `reconcile_stale_runs()`
flips any row left `running` (a run that died with the previous process) to
`failed`, so the post-restart answer is deterministic instead of guessed.

API is unchanged in spirit (mark_running/done/failed/get) but the marks are now
async (they hit the DB) and take `user_id` (the table needs it). Callers in
`agent_runner` are already in async context, so `await` is clean.

`get()` is sync and cache-only for the hot path; `load(thread_id)` is the async
DB-backed read used by `get_session_state` so it survives a process that never
ran this thread in-memory (e.g. right after restart, or another worker).
"""

from __future__ import annotations

import json
import time
from typing import Any, Literal, Optional, TypedDict

from agent.cascade.persistence.db import _connect, utc_now_rfc3339

# "awaiting_review" (P2) — the Director paused at an autonomous interrupt gate
# (HumanInTheLoopMiddleware). NOT terminal: the turn resumes on the user's
# decision (resume_agent). The pending review payload lives in the LangGraph
# checkpoint (the single source of truth), so reconnect replay reads it back via
# aget_state — no separate column needed here.
RunStatus = Literal["running", "done", "failed", "awaiting_review"]


class RunState(TypedDict):
    status: RunStatus
    updated_at: float
    failure: Optional[dict[str, Any]]  # FailurePayload-shaped when status == "failed"


# Hot-read cache: thread_id → RunState. Write-through; never the source of truth.
_runs: dict[str, RunState] = {}
_MAX_RUNS = 1024


def _evict_if_needed() -> None:
    """Bound cache growth. Drop oldest *terminal* entries first; never a running one."""
    if len(_runs) < _MAX_RUNS:
        return
    terminal = sorted(
        ((k, v["updated_at"]) for k, v in _runs.items() if v["status"] != "running"),
        key=lambda kv: kv[1],
    )
    for k, _ in terminal[: max(1, len(_runs) - _MAX_RUNS + 1)]:
        _runs.pop(k, None)


async def mark_running(user_id: str, thread_id: str) -> int:
    """Transition a thread to `running`. Returns the new run_seq (bumped each run)."""
    _evict_if_needed()
    _runs[thread_id] = {"status": "running", "updated_at": time.time(), "failure": None}
    now = utc_now_rfc3339()
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO run_lifecycle (thread_id, user_id, run_seq, status, failure, started_at, updated_at)
               VALUES (?, ?, 1, 'running', NULL, ?, ?)
               ON CONFLICT(thread_id) DO UPDATE SET
                 user_id    = excluded.user_id,
                 run_seq    = run_lifecycle.run_seq + 1,
                 status     = 'running',
                 failure    = NULL,
                 started_at = excluded.started_at,
                 updated_at = excluded.updated_at""",
            (thread_id, user_id, now, now),
        )
        await db.commit()
        row = await db.execute_fetchall(
            "SELECT run_seq FROM run_lifecycle WHERE thread_id = ?", (thread_id,)
        )
        return int(row[0][0]) if row else 1
    finally:
        await db.close()


async def mark_done(thread_id: str) -> None:
    _runs[thread_id] = {"status": "done", "updated_at": time.time(), "failure": None}
    await _set_terminal(thread_id, "done", None)


async def mark_failed(thread_id: str, failure: dict[str, Any] | None) -> None:
    _runs[thread_id] = {"status": "failed", "updated_at": time.time(), "failure": failure}
    await _set_terminal(thread_id, "failed", failure)


async def mark_awaiting_review(thread_id: str) -> None:
    """Pause a thread at an autonomous interrupt gate. NON-terminal: the row was
    already `running` (mark_running at turn start); we flip it to awaiting_review
    and clear any failure. The pending review payload is NOT stored here — it
    lives in the LangGraph checkpoint (reconnect replay reads it via aget_state)."""
    _runs[thread_id] = {"status": "awaiting_review", "updated_at": time.time(), "failure": None}
    now = utc_now_rfc3339()
    db = await _connect()
    try:
        await db.execute(
            "UPDATE run_lifecycle SET status = 'awaiting_review', failure = NULL, updated_at = ? WHERE thread_id = ?",
            (now, thread_id),
        )
        await db.commit()
    finally:
        await db.close()


async def _set_terminal(thread_id: str, status: str, failure: dict | None) -> None:
    now = utc_now_rfc3339()
    failure_json = json.dumps(failure, ensure_ascii=False) if failure else None
    db = await _connect()
    try:
        # UPDATE-only: a terminal mark for a thread that was never mark_running'd
        # (shouldn't happen) simply no-ops rather than inventing a row.
        await db.execute(
            "UPDATE run_lifecycle SET status = ?, failure = ?, updated_at = ? WHERE thread_id = ?",
            (status, failure_json, now, thread_id),
        )
        await db.commit()
    finally:
        await db.close()


def get(thread_id: str) -> RunState | None:
    """Cache-only hot read (same-process, same run). Use `load` for the DB truth."""
    return _runs.get(thread_id)


async def load(thread_id: str) -> RunState | None:
    """DB-backed read — authoritative across restarts / processes."""
    cached = _runs.get(thread_id)
    if cached is not None:
        return cached
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            "SELECT status, failure, updated_at FROM run_lifecycle WHERE thread_id = ?",
            (thread_id,),
        )
    finally:
        await db.close()
    if not row:
        return None
    status, failure_json, _updated = row[0]
    failure = json.loads(failure_json) if failure_json else None
    return {"status": status, "updated_at": time.time(), "failure": failure}


async def reconcile_stale_runs() -> int:
    """Boot-time: any row left `running` belongs to a process that died mid-run.
    Flip it to `failed` so reconnecting clients get a deterministic terminal
    state (and a recoverable hint) instead of an infinite spinner. Returns the
    number of rows reconciled."""
    failure = json.dumps(
        {
            "code": "S11_INTERNAL_ERROR",
            "hint": "上次处理被中断了,重试一下或换一条链接。",
            "actions": ["RETRY_SAME_URL", "RETRY_WITH_NEW_URL"],
            "request_id": "",
        },
        ensure_ascii=False,
    )
    now = utc_now_rfc3339()
    db = await _connect()
    try:
        cur = await db.execute(
            "UPDATE run_lifecycle SET status = 'failed', failure = ?, updated_at = ? WHERE status = 'running'",
            (failure, now),
        )
        await db.commit()
        return cur.rowcount if cur.rowcount is not None else 0
    finally:
        await db.close()


def clear(thread_id: str) -> None:
    _runs.pop(thread_id, None)
