"""Per-shot generated assets (草稿图 + 图生视频) + 合成整片 持久化。

视频闭环:草稿图段写 image_url(供视频段 image-grounding 取用);视频段写 video_url
(供合成段读取);合成段写 film_url。资产都落 /media 持久(ARK 视频 URL 会过期),
会话重载时据此重放,工具也据此幂等(已生成则不重复烧钱)。
"""

from __future__ import annotations

from agent.cascade.persistence.db import _connect, utc_now_rfc3339


async def record_shot_image(rewrite_id: str, shot_index: int, image_url: str) -> None:
    """Upsert 草稿图 URL,保留可能已存在的 video_url。"""
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO shot_assets (rewrite_id, shot_index, image_url, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(rewrite_id, shot_index)
               DO UPDATE SET image_url = excluded.image_url, updated_at = excluded.updated_at""",
            (rewrite_id, shot_index, image_url, utc_now_rfc3339()),
        )
        await db.commit()
    finally:
        await db.close()


async def record_shot_video(rewrite_id: str, shot_index: int, video_url: str) -> None:
    """Upsert 图生视频 URL,保留 image_url。"""
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO shot_assets (rewrite_id, shot_index, video_url, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(rewrite_id, shot_index)
               DO UPDATE SET video_url = excluded.video_url, updated_at = excluded.updated_at""",
            (rewrite_id, shot_index, video_url, utc_now_rfc3339()),
        )
        await db.commit()
    finally:
        await db.close()


async def load_shot_assets(rewrite_id: str) -> list[dict]:
    """该 rewrite 全部镜头资产,按 shot_index 升序。
    返回 [{"shot_index": int, "image_url": str|None, "video_url": str|None}]。"""
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            """SELECT shot_index, image_url, video_url FROM shot_assets
               WHERE rewrite_id = ? ORDER BY shot_index ASC""",
            (rewrite_id,),
        )
    finally:
        await db.close()
    return [
        {"shot_index": r[0], "image_url": r[1], "video_url": r[2]} for r in rows
    ]


async def load_shot_image(rewrite_id: str, shot_index: int) -> str | None:
    """单镜草稿图 URL(视频段 image-grounding 取用)。"""
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            "SELECT image_url FROM shot_assets WHERE rewrite_id = ? AND shot_index = ? LIMIT 1",
            (rewrite_id, shot_index),
        )
    finally:
        await db.close()
    return row[0][0] if row and row[0][0] else None


async def record_film(rewrite_id: str, film_url: str) -> None:
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO rewrite_films (rewrite_id, film_url, created_at)
               VALUES (?, ?, ?)
               ON CONFLICT(rewrite_id)
               DO UPDATE SET film_url = excluded.film_url, created_at = excluded.created_at""",
            (rewrite_id, film_url, utc_now_rfc3339()),
        )
        await db.commit()
    finally:
        await db.close()


async def load_film(rewrite_id: str) -> str | None:
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            "SELECT film_url FROM rewrite_films WHERE rewrite_id = ? LIMIT 1",
            (rewrite_id,),
        )
    finally:
        await db.close()
    return row[0][0] if row else None
