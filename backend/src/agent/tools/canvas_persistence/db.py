"""SQLite 连接 + schema bootstrap + ContextVar 解析。

- `_db()` 每次 open 一个连接(WAL),return 给 caller close
- 顶层 schema/migration 在 _db() 内部反复 CREATE TABLE IF NOT EXISTS + ALTER TABLE
  ADD COLUMN(避免外部要求一次性 bootstrap)
- `set_user_id` / `set_thread_id` 给 handlers 用(单消息内的 ContextVar)
- `_resolve_ids(uid, tid)` 显式参数优先,缺省回退 ContextVar — workers 走显式
"""

from __future__ import annotations

import sqlite3
from contextvars import ContextVar
from pathlib import Path

from agent.cascade.persistence.db import resolve_data_dir


# Local-dev default data dir. The *effective* path is resolved lazily by
# `canvas_db_path()` via the shared `resolve_data_dir` policy (override /
# container / local) — see W5D4 review B4: previously this DB (which holds the
# whole generation queue) computed a parent×5 relative path with NO container
# detection and NO CASCADE_DB_PATH support, so it only landed on the mounted
# volume by coincidence of directory depth. Any Dockerfile/layout change would
# silently drop it onto an ephemeral layer → restart loses the queue (and
# Google in-memory tasks re-enqueue = double billing).
_LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data"


def canvas_db_path() -> Path:
    """Resolve canvas.db through the shared data-dir policy so it always sits on
    the same volume as cascade.db + clip media (no split-brain, honors
    CASCADE_DB_PATH override). Returns an identical path to the old constant in
    every current real layout — this only adds correctness, no migration."""
    return resolve_data_dir(_LOCAL_DATA_DIR) / "canvas.db"


# Backward-compat exports (canvas.py re-exports these; older import paths rely
# on them). Equal to `canvas_db_path()` in the non-override case. New code and
# every connection path go through `canvas_db_path()` so the override is honored.
_DB_DIR = _LOCAL_DATA_DIR
_DB_PATH = _DB_DIR / "canvas.db"

_current_thread_id: ContextVar[str] = ContextVar("canvas_thread_id", default="default")
_current_user_id: ContextVar[str] = ContextVar("canvas_user_id", default="default")

# Paths whose ALTER-TABLE migrations have already run this process. Every `_db()`
# previously attempted 13 `ALTER TABLE ADD COLUMN` statements that almost always
# raise OperationalError ("column exists") and get caught — wasted work on every
# connection. CREATE TABLE IF NOT EXISTS still runs every time (cheap, keeps us
# resilient if the file is recreated); only the migrations are gated.
_MIGRATED_PATHS: set[str] = set()


def set_thread_id(thread_id: str) -> None:
    _current_thread_id.set(thread_id)


def set_user_id(user_id: str) -> None:
    _current_user_id.set(user_id)


def _resolve_ids(user_id: str | None, thread_id: str | None) -> tuple[str, str]:
    """显式参数优先,缺省回退到 ContextVar。"""
    return (
        user_id if user_id is not None else _current_user_id.get(),
        thread_id if thread_id is not None else _current_thread_id.get(),
    )


def _db() -> sqlite3.Connection:
    path = canvas_db_path()
    path_key = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=5000")
    # CREATE TABLE is the complete source of truth for the current schema. The
    # ALTER block below only migrates genuinely-old databases that predate a
    # column. Keeping CREATE complete means a fresh file gets every column even
    # when the ALTER migrations are gated (see _MIGRATED_PATHS) — otherwise a
    # recreated file would be missing the generation_* columns.
    db.execute(
        """CREATE TABLE IF NOT EXISTS canvas_nodes (
            user_id TEXT NOT NULL DEFAULT 'default',
            thread_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            node_status TEXT NOT NULL DEFAULT 'reviewing',
            asset_status TEXT NOT NULL DEFAULT 'idle',
            result TEXT,
            subtype TEXT,
            feedback TEXT,
            x REAL, y REAL,
            shot_no TEXT,
            image_gen_provider TEXT,
            generation_status TEXT NOT NULL DEFAULT 'idle',
            generation_task_id TEXT,
            generation_error TEXT,
            generation_attempt_count INTEGER NOT NULL DEFAULT 0,
            generation_lease_until TEXT,
            generation_next_retry_at TEXT,
            PRIMARY KEY (user_id, thread_id, node_id)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS canvas_edges (
            user_id TEXT NOT NULL DEFAULT 'default',
            thread_id TEXT NOT NULL,
            edge_id TEXT NOT NULL,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, thread_id, edge_id)
        )"""
    )

    # ALTER migrations — run once per path per process (see _MIGRATED_PATHS).
    if path_key not in _MIGRATED_PATHS:
        for col, defn in [
            ("user_id", "TEXT NOT NULL DEFAULT 'default'"),
            ("node_status", "TEXT NOT NULL DEFAULT 'reviewing'"),
            ("asset_status", "TEXT NOT NULL DEFAULT 'idle'"),
            ("shot_no", "TEXT"),
            ("image_gen_provider", "TEXT"),
            ("generation_status", "TEXT NOT NULL DEFAULT 'idle'"),
            ("generation_task_id", "TEXT"),
            ("generation_error", "TEXT"),
            ("generation_attempt_count", "INTEGER NOT NULL DEFAULT 0"),
            ("generation_lease_until", "TEXT"),
            ("generation_next_retry_at", "TEXT"),
        ]:
            try:
                db.execute(f"ALTER TABLE canvas_nodes ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass  # 列已存在
        try:
            db.execute("ALTER TABLE canvas_edges ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            db.execute("ALTER TABLE canvas_edges ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
        except sqlite3.OperationalError:
            pass
        _MIGRATED_PATHS.add(path_key)
    return db
