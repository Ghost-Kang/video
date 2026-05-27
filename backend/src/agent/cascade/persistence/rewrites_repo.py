from __future__ import annotations

from agent.cascade.persistence.db import _connect


async def save_rewrite(
    rewrite_id: str,
    *,
    analysis_id: str,
    niche: str,
    user_id: str,
    run_id: str | None,
    result_json: str,
    created_at: str,
) -> None:
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO rewrites (rewrite_id, analysis_id, niche, user_id, run_id, result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (rewrite_id, analysis_id, niche, user_id, run_id, result_json, created_at),
        )
        await db.commit()
    finally:
        await db.close()


async def load_recent_rewrite(
    *,
    analysis_id: str,
    niche: str,
    user_id: str,
    since: str,
) -> str | None:
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            """SELECT result_json FROM rewrites
               WHERE analysis_id = ? AND niche = ? AND user_id = ? AND created_at >= ?
               ORDER BY created_at DESC LIMIT 1""",
            (analysis_id, niche, user_id, since),
        )
    finally:
        await db.close()
    return row[0][0] if row else None
