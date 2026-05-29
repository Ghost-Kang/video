from __future__ import annotations

from contextvars import ContextVar

from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.persistence.db import _connect, utc_now_rfc3339


_analysis_user_id: ContextVar[str] = ContextVar("cascade_analysis_user_id", default="default")
_analysis_run_id: ContextVar[str | None] = ContextVar("cascade_analysis_run_id", default=None)


def set_analysis_context(user_id: str, run_id: str | None) -> None:
    _analysis_user_id.set(user_id)
    _analysis_run_id.set(run_id)


async def save_analysis(contract: CascadeAnalysisContract) -> bool:
    """Persist an analysis. Returns True only when a new row was inserted."""
    user_id = _analysis_user_id.get()
    run_id = _analysis_run_id.get()
    db = await _connect()
    try:
        cursor = await db.execute(
            """INSERT OR IGNORE INTO analyses (
              analysis_id, user_id, run_id, source_url, platform, cost_cny,
              confidence, contract_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                contract.analysis_id,
                user_id,
                run_id,
                str(contract.source_url),
                contract.platform.value,
                contract.cost_cny,
                contract.confidence,
                contract.model_dump_json(),
                utc_now_rfc3339(),
            ),
        )
        await db.commit()
        return cursor.rowcount == 1
    finally:
        await db.close()


async def load_analysis(analysis_id: str) -> CascadeAnalysisContract | None:
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            "SELECT contract_json FROM analyses WHERE analysis_id = ?",
            (analysis_id,),
        )
    finally:
        await db.close()
    if not row:
        return None
    return CascadeAnalysisContract.model_validate_json(row[0][0])


async def load_analysis_for_source(user_id: str, source_url: str) -> CascadeAnalysisContract | None:
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            """SELECT contract_json FROM analyses
               WHERE user_id = ? AND source_url = ?
               ORDER BY created_at DESC LIMIT 1""",
            (user_id, source_url),
        )
    finally:
        await db.close()
    if not row:
        return None
    return CascadeAnalysisContract.model_validate_json(row[0][0])


async def load_latest_analysis_for_source(source_url: str) -> CascadeAnalysisContract | None:
    """Load the newest analysis for a public source URL, regardless of user.

    Used as a cost/perf cache: the source video analysis is independent from
    the creator's later niche rewrite, so we can reuse the normalized contract
    and persist a user-scoped clone with a fresh analysis_id.
    """
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            """SELECT contract_json FROM analyses
               WHERE source_url = ?
               ORDER BY created_at DESC LIMIT 1""",
            (source_url,),
        )
    finally:
        await db.close()
    if not row:
        return None
    return CascadeAnalysisContract.model_validate_json(row[0][0])
