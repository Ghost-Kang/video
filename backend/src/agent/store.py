"""消息持久化存储（SQLite）"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _resolve_db_path() -> Path:
    """Chat-history DB location.

    W5D4 — fixes the persistence split-brain. In the container the old
    ``__file__.parent×3 / data`` walked to ``/app/src/data`` (the ephemeral image
    layer, wiped on every redeploy) instead of the mounted ``/app/data`` volume,
    so chat history silently vanished on each deploy. Mirror the Cascade
    persistence resolver (agent/cascade/persistence/db.py): detect the image via
    the ``/app/src`` marker and use the volume; keep the repo-relative path for
    local dev. ``MESSAGES_DB_PATH`` overrides (tests / non-standard layouts)."""
    override = os.getenv("MESSAGES_DB_PATH")
    if override:
        return Path(override)
    if Path("/app/src").exists():  # Dockerfile: WORKDIR /app, COPY src ./src
        return Path("/app/data/messages.db")
    return Path(__file__).resolve().parent.parent.parent / "data" / "messages.db"


_DB_PATH = _resolve_db_path()
_DB_DIR = _DB_PATH.parent

# Paths whose ALTER migration has already run this process (see canvas db.py).
_MIGRATED_PATHS: set[str] = set()


def _conn() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH))
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA busy_timeout=5000")
    c.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_thread ON messages(user_id, thread_id, id)"
    )
    if str(_DB_PATH) not in _MIGRATED_PATHS:
        try:
            c.execute("ALTER TABLE messages ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
        except sqlite3.OperationalError:
            pass
        _MIGRATED_PATHS.add(str(_DB_PATH))

    # 会话元信息（is_deleted 软删除标志）
    c.execute(
        """CREATE TABLE IF NOT EXISTS session_meta (
            user_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, thread_id)
        )"""
    )
    c.commit()
    return c


def save_message(user_id: str, thread_id: str, role: str, content: str):
    db = _conn()
    db.execute(
        "INSERT INTO messages (user_id, thread_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, thread_id, role, content, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    db.close()


def get_messages(user_id: str, thread_id: str, limit: int = 100) -> list[dict]:
    db = _conn()
    rows = db.execute(
        "SELECT role, content, created_at FROM messages WHERE user_id=? AND thread_id = ? ORDER BY id LIMIT ?",
        (user_id, thread_id, limit),
    ).fetchall()
    db.close()
    return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]


def list_sessions(user_id: str) -> list[dict]:
    """返回用户所有未删除的会话（is_deleted=0 或无记录）。"""
    db = _conn()
    rows = db.execute(
        """SELECT m.thread_id,
                  MAX(m.created_at) AS last_active
           FROM messages m
           LEFT JOIN session_meta sm ON sm.user_id=m.user_id AND sm.thread_id=m.thread_id
           WHERE m.user_id=? AND COALESCE(sm.is_deleted, 0) = 0
           GROUP BY m.thread_id
           ORDER BY last_active DESC""",
        (user_id,),
    ).fetchall()

    sessions = []
    seen: set[str] = set()
    for r in rows:
        tid = r[0]
        seen.add(tid)
        sessions.append({
            "thread_id": tid,
            "last_active": r[1] or "",
        })

    # 合并仅有画布数据但无消息的会话
    try:
        from agent.tools.canvas_persistence.db import canvas_db_path
        cdb = sqlite3.connect(str(canvas_db_path()))
        cdb.row_factory = sqlite3.Row
        crows = cdb.execute(
            """SELECT DISTINCT cn.thread_id
               FROM canvas_nodes cn
               LEFT JOIN session_meta sm ON sm.user_id=cn.user_id AND sm.thread_id=cn.thread_id
               WHERE cn.user_id=? AND COALESCE(sm.is_deleted, 0) = 0""",
            (user_id,),
        ).fetchall()
        cdb.close()
        for cr in crows:
            tid = cr[0]
            if tid not in seen:
                seen.add(tid)
                sessions.append({
                    "thread_id": tid,
                    "last_active": "",
                })
    except Exception:
        pass

    # 合并仅有 session_meta 记录的空会话（新建但未发消息也未创建画布节点）
    meta_rows = db.execute(
        """SELECT thread_id FROM session_meta
           WHERE user_id=? AND is_deleted=0
           ORDER BY rowid DESC""",
        (user_id,),
    ).fetchall()
    for mr in meta_rows:
        tid = mr[0]
        if tid not in seen:
            sessions.append({
                "thread_id": tid,
                "last_active": "",
            })

    db.close()
    return sessions


def ensure_session_exists(user_id: str, thread_id: str):
    """确保会话在 session_meta 中有记录（首次访问时落盘）。"""
    db = _conn()
    db.execute(
        """INSERT OR IGNORE INTO session_meta (user_id, thread_id, is_deleted)
           VALUES (?, ?, 0)""",
        (user_id, thread_id),
    )
    db.commit()
    db.close()


def delete_session(user_id: str, thread_id: str):
    """软删除：设置 is_deleted=1，数据完整保留。"""
    db = _conn()
    db.execute(
        """INSERT INTO session_meta (user_id, thread_id, is_deleted)
           VALUES (?, ?, 1)
           ON CONFLICT(user_id, thread_id) DO UPDATE SET is_deleted=1""",
        (user_id, thread_id),
    )
    db.commit()
    db.close()
    print(f"[存储] 软删除 user={user_id} thread={thread_id}")


def delete_sessions(user_id: str, thread_ids: list[str]):
    """批量软删除（历史「清理空会话」）。一个事务设全部 is_deleted=1。"""
    if not thread_ids:
        return
    db = _conn()
    db.executemany(
        """INSERT INTO session_meta (user_id, thread_id, is_deleted)
           VALUES (?, ?, 1)
           ON CONFLICT(user_id, thread_id) DO UPDATE SET is_deleted=1""",
        [(user_id, t) for t in thread_ids],
    )
    db.commit()
    db.close()
    print(f"[存储] 批量软删除 user={user_id} count={len(thread_ids)}")
