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


_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "canvas.db"

_current_thread_id: ContextVar[str] = ContextVar("canvas_thread_id", default="default")
_current_user_id: ContextVar[str] = ContextVar("canvas_user_id", default="default")


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
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=5000")
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
            PRIMARY KEY (user_id, thread_id, node_id)
        )"""
    )
    # 兼容旧数据库:添加新列(若不存在)
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
    try:
        db.execute("ALTER TABLE canvas_edges ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE canvas_edges ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
    except sqlite3.OperationalError:
        pass
    return db
