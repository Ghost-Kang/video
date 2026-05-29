"""Shared SQLite connection and schema bootstrap for Cascade persistence."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import aiosqlite


_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "messages.db"


def db_path() -> Path:
    override = os.getenv("CASCADE_DB_PATH")
    return Path(override) if override else _DB_PATH


def utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat()


async def bootstrap_schema(db: aiosqlite.Connection | None = None) -> None:
    own_connection = db is None
    if db is None:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(str(path))
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA busy_timeout=5000")
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
        await db.execute(
            """CREATE TABLE IF NOT EXISTS toprador_cache (
              source_url_hash TEXT PRIMARY KEY,
              payload_json     TEXT NOT NULL,
              expires_at       TEXT NOT NULL
            )"""
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_toprador_cache_expires ON toprador_cache(expires_at)"
        )
        await db.commit()
    finally:
        if own_connection:
            await db.close()


async def _connect() -> aiosqlite.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(path))
    await db.execute("PRAGMA busy_timeout=5000")
    await bootstrap_schema(db)
    return db


@asynccontextmanager
async def session() -> AsyncIterator[aiosqlite.Connection]:
    db = await _connect()
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
