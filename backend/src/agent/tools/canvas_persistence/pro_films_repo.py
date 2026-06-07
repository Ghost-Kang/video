"""「我的成片」库 —— 用户把 Pro 画布跑出的成片存进个人库(per user)。

成片发布出口(founder 选定:存产品内库,非外部平台)。video_url 多为 /media/<run>_compose/out.mp4
(本地持久);存的是引用,不复制文件。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from agent.tools.canvas_persistence.db import _db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_film(*, user_id: str, video_url: str, title: str = "", thread_id: str = "") -> dict:
    """存一条成片,返回 {film_id, video_url, title, thread_id, created_at}。"""
    film_id = f"film_{uuid.uuid4().hex[:12]}"
    created = _now()
    db = _db()
    try:
        db.execute(
            """INSERT OR REPLACE INTO pro_films (user_id, film_id, video_url, title, thread_id, created_at)
               VALUES (?,?,?,?,?,?)""",
            (user_id, film_id, video_url, title or "", thread_id or "", created),
        )
        db.commit()
    finally:
        db.close()
    return {"film_id": film_id, "video_url": video_url, "title": title or "", "thread_id": thread_id or "", "created_at": created}


def list_films(*, user_id: str) -> list[dict]:
    """该用户的成片(新→旧)。"""
    db = _db()
    try:
        rows = db.execute(
            """SELECT film_id, video_url, title, thread_id, created_at FROM pro_films
               WHERE user_id=? ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
    finally:
        db.close()
    return [
        {"film_id": r[0], "video_url": r[1], "title": r[2], "thread_id": r[3], "created_at": r[4]}
        for r in rows
    ]


def delete_film(*, user_id: str, film_id: str) -> None:
    db = _db()
    try:
        db.execute("DELETE FROM pro_films WHERE user_id=? AND film_id=?", (user_id, film_id))
        db.commit()
    finally:
        db.close()
