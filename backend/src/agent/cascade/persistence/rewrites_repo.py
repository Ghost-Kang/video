from __future__ import annotations

from agent.cascade.contract import REWRITE_PIPELINE_REVISION
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
            """INSERT INTO rewrites
               (rewrite_id, analysis_id, niche, user_id, run_id, result_json, created_at, pipeline_revision)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rewrite_id,
                analysis_id,
                niche,
                user_id,
                run_id,
                result_json,
                created_at,
                REWRITE_PIPELINE_REVISION,
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def load_rewrite_by_id(rewrite_id: str) -> str | None:
    """Look up a stored rewrite by its `rewrite_id` (rw_xxx).

    Returns the raw `result_json` string for the caller to
    `RewriteResult.model_validate_json` — or None when not found.
    Used by `cascade_generate_first_frame` to resolve the shot's `visual` prompt
    given just the rewrite id from a previous chat turn.
    """
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            "SELECT result_json FROM rewrites WHERE rewrite_id = ? LIMIT 1",
            (rewrite_id,),
        )
    finally:
        await db.close()
    return row[0][0] if row else None


async def load_recent_rewrite(
    *,
    analysis_id: str,
    niche: str,
    user_id: str,
    since: str,
) -> str | None:
    db = await _connect()
    try:
        # pipeline_revision guard (B2): only serve cache from the CURRENT rewrite
        # pipeline. After 改写解封 bumps REWRITE_PIPELINE_REVISION, older rows
        # (incl. legacy fixture rows backfilled to 0) fail this predicate and the
        # caller regenerates — no stale fixture 套娃 within the 24h window.
        row = await db.execute_fetchall(
            """SELECT result_json FROM rewrites
               WHERE analysis_id = ? AND niche = ? AND user_id = ?
                 AND created_at >= ? AND pipeline_revision = ?
               ORDER BY created_at DESC LIMIT 1""",
            (analysis_id, niche, user_id, since, REWRITE_PIPELINE_REVISION),
        )
    finally:
        await db.close()
    return row[0][0] if row else None
