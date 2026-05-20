"""消息持久化存储（SQLite）"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "messages.db"


def _conn() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH))
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
    try:
        c.execute("ALTER TABLE messages ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
    except sqlite3.OperationalError:
        pass

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
                  (SELECT content FROM messages m2 WHERE m2.user_id=m.user_id AND m2.thread_id=m.thread_id AND m2.role='user' ORDER BY m2.id LIMIT 1) AS first_msg,
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
        first = (r[1] or "")[:80]
        sessions.append({
            "thread_id": tid,
            "name": first if first else "新会话",
            "last_active": r[2] or "",
        })

    # 合并仅有画布数据但无消息的会话（如刚创建未发消息的 session）
    try:
        from agent.tools.canvas import _DB_PATH as _CANVAS_DB
        cdb = sqlite3.connect(str(_CANVAS_DB))
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
                sessions.append({
                    "thread_id": tid,
                    "name": "新会话",
                    "last_active": "",
                })
    except Exception:
        pass

    db.close()
    return sessions


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
