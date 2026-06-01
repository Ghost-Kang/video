"""DAO for landing-page showcase cases (auto-showcase feature).

Replaces the static SAMPLE_CASES array baked into the frontend bundle. A
completed analysis that passes the quality gate (showcase_service) lands a row
here; the landing page fetches published rows via GET /api/showcase. founder can
hide/restore via the admin status endpoint.
"""

from __future__ import annotations

import json
from typing import Any

from agent.cascade.persistence.db import _connect, utc_now_rfc3339


async def list_published(limit: int = 10) -> list[dict[str, Any]]:
    """Published cases for the landing carousel, shaped like the frontend
    SampleCase. Ranked by **confidence DESC, then created_at DESC** (founder:
    show the highest-confidence cases first; on a tie the newer case wins over
    the older). Capped at `limit` (landing shows ≤10 real cases)."""
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            """SELECT case_id, source_url, category, emoji, hook, emotion,
                      gradient, slides_json
               FROM showcase_cases
               WHERE status = 'published'
               ORDER BY confidence DESC, created_at DESC
               LIMIT ?""",
            (limit,),
        )
    finally:
        await db.close()
    out: list[dict[str, Any]] = []
    for case_id, source_url, category, emoji, hook, emotion, gradient, slides_json in rows:
        try:
            slides = json.loads(slides_json) if slides_json else []
        except (ValueError, TypeError):
            slides = []
        out.append({
            "id": case_id,
            "source_url": source_url,
            "category": category,
            "emoji": emoji or None,
            "hook": hook,
            "emotion": emotion or None,
            "gradient": gradient or None,
            "slides": slides,
        })
    return out


async def get_by_source_url(source_url: str) -> dict[str, Any] | None:
    """Row for a source_url regardless of status (gate uses this to skip
    already-decided URLs — published OR hidden). Returns minimal fields."""
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            "SELECT case_id, status FROM showcase_cases WHERE source_url = ? LIMIT 1",
            (source_url,),
        )
    finally:
        await db.close()
    if not rows:
        return None
    return {"case_id": rows[0][0], "status": rows[0][1]}


async def count_published() -> int:
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            "SELECT COUNT(*) FROM showcase_cases WHERE status = 'published'"
        )
    finally:
        await db.close()
    return int(rows[0][0]) if rows else 0


async def lowest_confidence_auto() -> dict[str, Any] | None:
    """The weakest auto-published case (lowest confidence; oldest on a tie) —
    the displacement candidate when a higher-confidence case arrives at the cap.
    Only `origin='auto'` rows are eligible (never auto-evict a manual/curated one)."""
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            """SELECT case_id, confidence FROM showcase_cases
               WHERE status = 'published' AND origin = 'auto'
               ORDER BY confidence ASC, created_at ASC
               LIMIT 1""",
        )
    finally:
        await db.close()
    if not rows:
        return None
    return {"case_id": rows[0][0], "confidence": float(rows[0][1])}


async def delete_case(case_id: str) -> None:
    db = await _connect()
    try:
        await db.execute("DELETE FROM showcase_cases WHERE case_id = ?", (case_id,))
        await db.commit()
    finally:
        await db.close()


async def insert_case(
    *,
    case_id: str,
    source_url: str,
    category: str,
    emoji: str | None,
    hook: str,
    emotion: str | None,
    gradient: str | None,
    slides: list[dict[str, Any]],
    confidence: float,
    origin: str = "auto",
    status: str = "published",
) -> None:
    """Insert (or replace) a showcase case. INSERT OR REPLACE keyed on case_id;
    source_url is UNIQUE so a re-run of the same video updates in place."""
    db = await _connect()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO showcase_cases (
              case_id, source_url, category, emoji, hook, emotion, gradient,
              slides_json, confidence, status, origin, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                source_url,
                category,
                emoji,
                hook,
                emotion,
                gradient,
                json.dumps(slides, ensure_ascii=False),
                confidence,
                status,
                origin,
                utc_now_rfc3339(),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def set_status(case_id: str, status: str) -> bool:
    """Hide / restore a case (founder admin action). Returns True if a row matched."""
    db = await _connect()
    try:
        cur = await db.execute(
            "UPDATE showcase_cases SET status = ? WHERE case_id = ?",
            (status, case_id),
        )
        await db.commit()
        return (cur.rowcount or 0) > 0
    finally:
        await db.close()
