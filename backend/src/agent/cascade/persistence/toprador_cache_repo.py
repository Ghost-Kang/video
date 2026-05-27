from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from agent.cascade.persistence.db import _connect


async def save_toprador_cache(
    source_url_hash: str,
    payload: dict[str, Any],
    ttl_s: float,
) -> None:
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_s)).isoformat()
    db = await _connect()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO toprador_cache (
              source_url_hash, payload_json, expires_at
            ) VALUES (?, ?, ?)""",
            (source_url_hash, json.dumps(payload, ensure_ascii=False, sort_keys=True), expires_at),
        )
        await db.commit()
    finally:
        await db.close()


async def _load_toprador_cache_entry(
    source_url_hash: str,
) -> tuple[dict[str, Any], float] | None:
    now = datetime.now(timezone.utc)
    await cleanup_expired_toprador_cache(now=now)
    db = await _connect()
    try:
        row = await db.execute_fetchall(
            """SELECT payload_json, expires_at FROM toprador_cache
               WHERE source_url_hash = ? AND expires_at > ?""",
            (source_url_hash, now.isoformat()),
        )
    finally:
        await db.close()
    if not row:
        return None
    payload_json, expires_at = row[0]
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return None
    expires = datetime.fromisoformat(expires_at)
    ttl_remaining_s = max(0.0, (expires - now).total_seconds())
    return payload, ttl_remaining_s


async def load_toprador_cache(source_url_hash: str) -> dict[str, Any] | None:
    entry = await _load_toprador_cache_entry(source_url_hash)
    if entry is None:
        return None
    return entry[0]


async def cleanup_expired_toprador_cache(now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(timezone.utc)).isoformat()
    db = await _connect()
    try:
        cursor = await db.execute(
            "DELETE FROM toprador_cache WHERE expires_at <= ?",
            (cutoff,),
        )
        await db.commit()
        return int(cursor.rowcount or 0)
    finally:
        await db.close()
