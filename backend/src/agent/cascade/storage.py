"""SQLite persistence for Cascade analyses and telemetry events."""

from __future__ import annotations

import json
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from agent.cascade.contract import CascadeAnalysisContract


_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "messages.db"

_analysis_user_id: ContextVar[str] = ContextVar("cascade_analysis_user_id", default="default")
_analysis_run_id: ContextVar[str | None] = ContextVar("cascade_analysis_run_id", default=None)


def db_path() -> Path:
    override = os.getenv("CASCADE_DB_PATH")
    return Path(override) if override else _DB_PATH


def set_analysis_context(user_id: str, run_id: str | None) -> None:
    _analysis_user_id.set(user_id)
    _analysis_run_id.set(run_id)


async def _connect() -> aiosqlite.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(path))
    await db.execute(
        """CREATE TABLE IF NOT EXISTS analyses (
          analysis_id TEXT PRIMARY KEY,
          user_id     TEXT NOT NULL,
          run_id      TEXT,
          source_url  TEXT NOT NULL,
          platform    TEXT NOT NULL,
          cost_cny    REAL NOT NULL,
          confidence  REAL NOT NULL,
          contract_json TEXT NOT NULL,
          created_at  TEXT NOT NULL
        )"""
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC)"
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS events (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          event_name   TEXT NOT NULL,
          user_id      TEXT NOT NULL,
          run_id       TEXT,
          payload_json TEXT NOT NULL,
          created_at   TEXT NOT NULL
        )"""
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_user_name_time ON events(user_id, event_name, created_at DESC)"
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, created_at)")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_thread_ts ON events(run_id, created_at DESC)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(event_name, created_at DESC)"
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS rewrites (
          rewrite_id TEXT PRIMARY KEY,
          analysis_id TEXT NOT NULL,
          niche TEXT NOT NULL,
          user_id TEXT NOT NULL,
          run_id TEXT,
          result_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        )"""
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_rewrites_lookup ON rewrites(analysis_id, niche, user_id, created_at DESC)"
    )
    await db.commit()
    return db


def utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat()


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


async def save_event(event_name: str, user_id: str, run_id: str | None, payload: dict[str, Any], created_at: str) -> None:
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO events (event_name, user_id, run_id, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event_name, user_id, run_id, json.dumps(payload, ensure_ascii=False, sort_keys=True), created_at),
        )
        await db.commit()
    finally:
        await db.close()


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


async def sum_generation_cost(
    *,
    user_id: str | None = None,
    run_id: str | None = None,
    since: str | None = None,
) -> float:
    clauses = ["event_name = 'generation_cost'"]
    params: list[Any] = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if run_id is not None:
        clauses.append("run_id = ?")
        params.append(run_id)
    if since is not None:
        clauses.append("created_at >= ?")
        params.append(since)
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            f"SELECT payload_json FROM events WHERE {' AND '.join(clauses)}",
            tuple(params),
        )
    finally:
        await db.close()
    total_fen = 0
    for (payload_json,) in rows:
        try:
            payload = json.loads(payload_json)
            total_fen += int(payload.get("cost_fen") or 0)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return total_fen / 100.0


async def list_creators() -> list[dict[str, Any]]:
    """Aggregate per-user activity for the admin creator view (P3-3).

    Each creator dict shape:
        {
          user_id, first_seen, last_seen,
          runs_started, rewrites_completed, publish_packs_copied,
          anchors_count, anchors_total_reuse_count, interview_logged
        }
    Sorted by last_seen DESC. Returns [] when DB or tables are absent.
    """
    db = await _connect()
    try:
        # Activity window per user
        rows = await db.execute_fetchall(
            "SELECT user_id, MIN(created_at), MAX(created_at) "
            "FROM events GROUP BY user_id"
        )
        creators: dict[str, dict[str, Any]] = {}
        for user_id, first_seen, last_seen in rows:
            creators[user_id] = {
                "user_id": user_id,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "runs_started": 0,
                "rewrites_completed": 0,
                "publish_packs_copied": 0,
                "anchors_count": 0,
                "anchors_total_reuse_count": 0,
                "interview_logged": False,
            }

        # Per-event counters
        for event_name, key in (
            ("run_started", "runs_started"),
            ("script_rewritten", "rewrites_completed"),
            ("publish_pack_copied", "publish_packs_copied"),
        ):
            counter_rows = await db.execute_fetchall(
                "SELECT user_id, COUNT(*) FROM events WHERE event_name = ? GROUP BY user_id",
                (event_name,),
            )
            for user_id, count in counter_rows:
                creator = creators.setdefault(user_id, _empty_creator(user_id))
                creator[key] = int(count or 0)

        # Anchor aggregates (table may not exist if anchors module never ran)
        try:
            anchor_rows = await db.execute_fetchall(
                "SELECT user_id, COUNT(*), SUM(reuse_count) FROM anchors GROUP BY user_id"
            )
            for user_id, count, total_reuse in anchor_rows:
                creator = creators.setdefault(user_id, _empty_creator(user_id))
                creator["anchors_count"] = int(count or 0)
                creator["anchors_total_reuse_count"] = int(total_reuse or 0)
        except Exception:
            # anchors table absent — leave defaults
            pass

        interview_rows = await db.execute_fetchall(
            "SELECT DISTINCT user_id FROM events WHERE event_name = 'interview_logged'"
        )
        for (user_id,) in interview_rows:
            creator = creators.setdefault(user_id, _empty_creator(user_id))
            creator["interview_logged"] = True
    finally:
        await db.close()

    def _sort_key(c: dict[str, Any]) -> str:
        return c.get("last_seen") or ""

    return sorted(creators.values(), key=_sort_key, reverse=True)


def _empty_creator(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "first_seen": None,
        "last_seen": None,
        "runs_started": 0,
        "rewrites_completed": 0,
        "publish_packs_copied": 0,
        "anchors_count": 0,
        "anchors_total_reuse_count": 0,
        "interview_logged": False,
    }


_LIST_EVENTS_MAX_LIMIT = 1000


async def list_events(
    *,
    limit: int = 200,
    offset: int = 0,
    event_name: str | None = None,
    user_id: str | None = None,
    since_ts: str | None = None,
) -> dict[str, Any]:
    """List telemetry events for the admin firehose (P4-2).

    Returns:
        {
          "events": [{id, ts, event_name, user_id, run_id, payload}, ...],
          "has_more": bool,
          "next_offset": int | None,
        }
    Events are ordered by created_at DESC (most recent first).
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if limit > _LIST_EVENTS_MAX_LIMIT:
        limit = _LIST_EVENTS_MAX_LIMIT
    if offset < 0:
        raise ValueError("offset must be non-negative")

    clauses: list[str] = []
    params: list[Any] = []
    if event_name is not None:
        clauses.append("event_name = ?")
        params.append(event_name)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if since_ts is not None:
        clauses.append("created_at > ?")
        params.append(since_ts)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            f"SELECT id, event_name, user_id, run_id, payload_json, created_at "
            f"FROM events{where} ORDER BY created_at DESC, id DESC "
            f"LIMIT ? OFFSET ?",
            tuple([*params, limit + 1, offset]),
        )
    finally:
        await db.close()

    rows_list = list(rows)
    has_more = len(rows_list) > limit
    if has_more:
        rows_list = rows_list[:limit]

    events: list[dict[str, Any]] = []
    for row_id, name, uid, rid, payload_json, created_at in rows_list:
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except json.JSONDecodeError:
            payload = {"_raw": payload_json}
        events.append({
            "id": int(row_id),
            "ts": created_at,
            "event_name": name,
            "user_id": uid,
            "run_id": rid,
            "payload": payload,
        })

    return {
        "events": events,
        "has_more": has_more,
        "next_offset": (offset + limit) if has_more else None,
    }
