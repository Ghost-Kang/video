from __future__ import annotations

from typing import Any

from agent.cascade.event_names import EventName
from agent.cascade.persistence.db import _connect


async def list_creators() -> list[dict[str, Any]]:
    """Aggregate per-user activity for the admin creator view (P3-3)."""
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            "SELECT user_id, MIN(created_at), MAX(created_at) "
            "FROM events GROUP BY user_id"
        )
        creators: dict[str, dict[str, Any]] = {}
        for user_id, first_seen, last_seen in rows:
            creators[user_id] = {
                "user_id": user_id,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "runs_started": 0,
                "rewrites_completed": 0,
                "publish_packs_copied": 0,
                "anchors_count": 0,
                "anchors_total_reuse_count": 0,
                "interview_logged": False,
            }

        for event_name, key in (
            (EventName.RUN_STARTED.value, "runs_started"),
            (EventName.SCRIPT_REWRITTEN.value, "rewrites_completed"),
            (EventName.PUBLISH_PACK_COPIED.value, "publish_packs_copied"),
        ):
            counter_rows = await db.execute_fetchall(
                "SELECT user_id, COUNT(*) FROM events WHERE event_name = ? GROUP BY user_id",
                (event_name,),
            )
            for user_id, count in counter_rows:
                creator = creators.setdefault(user_id, _empty_creator(user_id))
                creator[key] = int(count or 0)

        try:
            anchor_rows = await db.execute_fetchall(
                "SELECT user_id, COUNT(*), SUM(reuse_count) FROM anchors GROUP BY user_id"
            )
            for user_id, count, total_reuse in anchor_rows:
                creator = creators.setdefault(user_id, _empty_creator(user_id))
                creator["anchors_count"] = int(count or 0)
                creator["anchors_total_reuse_count"] = int(total_reuse or 0)
        except Exception:
            pass

        interview_rows = await db.execute_fetchall(
            "SELECT DISTINCT user_id FROM events WHERE event_name = ?",
            (EventName.INTERVIEW_LOGGED.value,),
        )
        for (user_id,) in interview_rows:
            creator = creators.setdefault(user_id, _empty_creator(user_id))
            creator["interview_logged"] = True
    finally:
        await db.close()

    def _sort_key(c: dict[str, Any]) -> str:
        return c.get("last_seen") or ""

    return sorted(creators.values(), key=_sort_key, reverse=True)


def _empty_creator(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "first_seen": None,
        "last_seen": None,
        "runs_started": 0,
        "rewrites_completed": 0,
        "publish_packs_copied": 0,
        "anchors_count": 0,
        "anchors_total_reuse_count": 0,
        "interview_logged": False,
    }
