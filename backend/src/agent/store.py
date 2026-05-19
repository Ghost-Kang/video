"""消息持久化存储（SQLite）"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "messages.db"
_current_user_id = "default"


def set_user_id(user_id: str):
    global _current_user_id
    _current_user_id = user_id


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
    c.commit()
    return c


def save_message(thread_id: str, role: str, content: str):
    db = _conn()
    db.execute(
        "INSERT INTO messages (user_id, thread_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (_current_user_id, thread_id, role, content, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    db.close()


def get_messages(thread_id: str, limit: int = 100) -> list[dict]:
    db = _conn()
    rows = db.execute(
        "SELECT role, content, created_at FROM messages WHERE user_id=? AND thread_id = ? ORDER BY id LIMIT ?",
        (_current_user_id, thread_id, limit),
    ).fetchall()
    db.close()
    return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]
