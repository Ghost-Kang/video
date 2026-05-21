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
