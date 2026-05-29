"""Shared SQLite connection and schema bootstrap for Cascade persistence."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import aiosqlite


# W5D3 P0-4 — Path resolution is context-sensitive:
#   - Container layout (/app/src/agent/cascade/persistence/db.py):
#     `/app/data/cascade.db` is the volume-mounted location. Before this fix,
#     `parent.parent.parent.parent` walked to `/app/src` and resulted in
#     `/app/src/data/...` (ephemeral container layer, wiped on redeploy).
#   - Local dev (.../backend/src/agent/cascade/persistence/db.py):
#     `.parent ×4 / data` correctly resolves to `<repo>/backend/data`.
# We detect the container by checking for /app/src and use the right default.
# Filename also renamed from `messages.db` (collided with agent/store.py's
# chat-history DB at the same name) to `cascade.db`.
_DEFAULT_LOCAL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "cascade.db"
)
_DEFAULT_CONTAINER_PATH = Path("/app/data/cascade.db")

# Paths whose schema DDL has already run in this process. Previously every
# `_connect()` re-ran ~12 CREATE TABLE/INDEX IF NOT EXISTS statements — cheap
# individually but paid on every connection (the health endpoint opens one per
# request). We run the DDL once per distinct path and only set per-connection
# PRAGMAs thereafter. Keyed by path string so tests that point CASCADE_DB_PATH
# at a fresh temp file still bootstrap.
_BOOTSTRAPPED_PATHS: set[str] = set()


def db_path() -> Path:
    override = os.getenv("CASCADE_DB_PATH")
    if override:
        return Path(override)
    # /app/src is the canonical marker that we're running inside the Docker image
    # (the Dockerfile WORKDIR /app and COPY src ./src). Filesystem check at
    # import time is cheap enough (single stat).
    if Path("/app/src").exists():
        return _DEFAULT_CONTAINER_PATH
    return _DEFAULT_LOCAL_PATH


def utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat()


async def bootstrap_schema(db: aiosqlite.Connection | None = None) -> None:
    own_connection = db is None
    path = db_path()
    if db is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(str(path))
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA busy_timeout=5000")
        if str(path) in _BOOTSTRAPPED_PATHS:
            return
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
        # W5D4 — per-(user, thread) pointer to the latest analysis + rewrite a
        # thread produced. analysis_returned / rewrite_returned are transient WS
        # pushes; without this map, get_session_state can't tell which stored
        # analysis/rewrite belongs to a thread, so a reloaded finished session
        # came back empty (and the dock mis-rendered "running" — see
        # chatPanelState fix). Upsert on each push; replay on reconnect.
        await db.execute(
            """CREATE TABLE IF NOT EXISTS session_results (
              user_id     TEXT NOT NULL,
              thread_id   TEXT NOT NULL,
              analysis_id TEXT,
              rewrite_id  TEXT,
              updated_at  TEXT NOT NULL,
              PRIMARY KEY (user_id, thread_id)
            )"""
        )
        # W5D4 P0-B — single authoritative, persisted run-lifecycle record per
        # thread. Replaces the in-memory run_state dict (lost on restart, which
        # forced get_session_state to *infer* status from chat-history tail).
        # Written through on every mark_*; reconciled on boot (stale 'running'
        # rows → 'failed') so a restart mid-run yields a deterministic answer.
        await db.execute(
            """CREATE TABLE IF NOT EXISTS run_lifecycle (
              thread_id   TEXT PRIMARY KEY,
              user_id     TEXT NOT NULL,
              run_seq     INTEGER NOT NULL DEFAULT 0,
              status      TEXT NOT NULL,
              failure     TEXT,
              started_at  TEXT NOT NULL,
              updated_at  TEXT NOT NULL
            )"""
        )
        await db.commit()
        _BOOTSTRAPPED_PATHS.add(str(path))
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
