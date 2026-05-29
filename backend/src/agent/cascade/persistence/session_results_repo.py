"""Per-(user, thread) pointer to the latest analysis + rewrite (W5D4).

`analysis_returned` / `rewrite_returned` are transient WS pushes — the rich
result lives in the `analyses` / `rewrites` tables, but nothing recorded *which
thread* produced it. On reconnect, `get_session_state(thread_id)` had no way to
find the thread's result, so a finished session reloaded empty. This tiny map
closes that gap: the cascade tool upserts a pointer when it pushes a result,
and the WS handler reads it back to replay the full frames.

A separate `rewrite_id` column lets a rewrite be recorded without clobbering the
thread's `analysis_id` (a thread analyzes once, then may rewrite several times).
"""

from __future__ import annotations

from agent.cascade.persistence.db import _connect, utc_now_rfc3339


async def record_analysis(user_id: str, thread_id: str, analysis_id: str) -> None:
    """Point a thread at the analysis it just produced (clears stale rewrite)."""
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO session_results (user_id, thread_id, analysis_id, rewrite_id, updated_at)
               VALUES (?, ?, ?, NULL, ?)
               ON CONFLICT(user_id, thread_id) DO UPDATE SET
                 analysis_id = excluded.analysis_id,
                 rewrite_id  = NULL,
                 updated_at  = excluded.updated_at""",
            (user_id, thread_id, analysis_id, utc_now_rfc3339()),
        )
        await db.commit()
    finally:
        await db.close()


async def record_rewrite(user_id: str, thread_id: str, rewrite_id: str) -> None:
    """Attach the latest rewrite to a thread, leaving analysis_id intact."""
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO session_results (user_id, thread_id, analysis_id, rewrite_id, updated_at)
               VALUES (?, ?, NULL, ?, ?)
               ON CONFLICT(user_id, thread_id) DO UPDATE SET
                 rewrite_id = excluded.rewrite_id,
                 updated_at = excluded.updated_at""",
            (user_id, thread_id, rewrite_id, utc_now_rfc3339()),
        )
        await db.commit()
    finally:
        await db.close()


async def load_pointers(user_id: str, thread_id: str) -> tuple[str | None, str | None]:
    """Return (analysis_id, rewrite_id) for a thread, or (None, None)."""
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            "SELECT analysis_id, rewrite_id FROM session_results WHERE user_id = ? AND thread_id = ?",
            (user_id, thread_id),
        )
    finally:
        await db.close()
    if not row:
        return None, None
    return row[0][0], row[0][1]
