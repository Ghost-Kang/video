"""Anchor service — character/scene assets users carry across runs.

Reuse of an anchor is the load-bearing learning-loop signal for the H8
moat thesis (Reviewer Synthesis §5). Every reuse emits anchor_reused so
the founder can measure how often "你之前用过的" actually gets pulled
into a new run.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import aiosqlite
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from agent.cascade.events import emit
from agent.cascade.storage import db_path


class AnchorKind(str, Enum):
    CHARACTER = "character"
    SCENE = "scene"


class Anchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^anc_[A-Za-z0-9_]+$")
    user_id: str = Field(..., min_length=1)
    kind: AnchorKind
    label: str = Field(..., min_length=1, max_length=40)
    image_url: HttpUrl
    source_run_id: str | None = None
    source_shot_index: int | None = Field(None, ge=1)
    reuse_count: int = Field(..., ge=0)
    created_at: datetime


async def _connect() -> aiosqlite.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(path))
    await db.execute(
        """CREATE TABLE IF NOT EXISTS anchors (
          id            TEXT PRIMARY KEY,
          user_id       TEXT NOT NULL,
          kind          TEXT NOT NULL CHECK (kind IN ('character', 'scene')),
          label         TEXT NOT NULL,
          image_url     TEXT NOT NULL,
          source_run_id TEXT,
          source_shot_index INTEGER,
          reuse_count   INTEGER NOT NULL DEFAULT 0,
          created_at    TEXT NOT NULL
        )"""
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_anchors_user_kind ON anchors(user_id, kind, created_at DESC)"
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS anchor_reuses (
          id            INTEGER PRIMARY KEY AUTOINCREMENT,
          anchor_id     TEXT NOT NULL REFERENCES anchors(id),
          reused_in_run_id TEXT NOT NULL,
          reused_in_shot_index INTEGER,
          reused_at     TEXT NOT NULL
        )"""
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_anchor_reuses_anchor ON anchor_reuses(anchor_id, reused_at DESC)"
    )
    # Idempotent: events table may not exist yet if reuse_anchor runs before
    # any emit() has bootstrapped it.
    await db.execute(
        """CREATE TABLE IF NOT EXISTS events (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          event_name   TEXT NOT NULL,
          user_id      TEXT NOT NULL,
          run_id       TEXT,
          payload_json TEXT NOT NULL,
          created_at   TEXT NOT NULL
        )"""
    )
    await db.commit()
    return db


def _new_id() -> str:
    return "anc_" + uuid.uuid4().hex[:16]


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _days_since(value: str) -> int:
    return max(0, (datetime.now(timezone.utc) - _parse_utc(value)).days)


async def create_anchor(
    *,
    user_id: str,
    kind: str,
    label: str,
    image_url: str,
    source_run_id: str | None = None,
    source_shot_index: int | None = None,
) -> Anchor:
    """Insert an anchor row and emit anchor_created.

    Raises pydantic.ValidationError for malformed input (e.g. label > 40,
    unknown kind). Server.py maps that to HTTP 400.
    """
    anchor = Anchor(
        id=_new_id(),
        user_id=user_id,
        kind=AnchorKind(kind),
        label=label,
        image_url=image_url,
        source_run_id=source_run_id,
        source_shot_index=source_shot_index,
        reuse_count=0,
        created_at=datetime.now(timezone.utc),
    )
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO anchors (
                id, user_id, kind, label, image_url, source_run_id,
                source_shot_index, reuse_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                anchor.id,
                anchor.user_id,
                anchor.kind.value,
                anchor.label,
                str(anchor.image_url),
                anchor.source_run_id,
                anchor.source_shot_index,
                anchor.reuse_count,
                anchor.created_at.isoformat(),
            ),
        )
        await db.commit()
    finally:
        await db.close()

    await emit(
        "anchor_created",
        user_id=user_id,
        run_id=source_run_id,
        payload={
            "anchor_id": anchor.id,
            "anchor_type": anchor.kind.value,
            "source_run_id": source_run_id or "",
            "anchor_label": anchor.label,
        },
    )
    return anchor


def _row_to_anchor(row: tuple) -> Anchor:
    return Anchor(
        id=row[0],
        user_id=row[1],
        kind=AnchorKind(row[2]),
        label=row[3],
        image_url=row[4],
        source_run_id=row[5],
        source_shot_index=row[6],
        reuse_count=row[7],
        created_at=row[8],
    )


async def list_anchors(*, user_id: str, kind: str | None = None) -> list[Anchor]:
    """Return anchors sorted by (reuse_count DESC, created_at DESC) — most-used first.

    Raises ValueError if kind is provided but not a known AnchorKind.
    """
    clauses = ["user_id = ?"]
    params: list[Any] = [user_id]
    if kind is not None:
        AnchorKind(kind)
        clauses.append("kind = ?")
        params.append(kind)
    sql = (
        "SELECT id, user_id, kind, label, image_url, source_run_id, "
        "source_shot_index, reuse_count, created_at "
        f"FROM anchors WHERE {' AND '.join(clauses)} "
        "ORDER BY reuse_count DESC, created_at DESC"
    )
    db = await _connect()
    try:
        rows = await db.execute_fetchall(sql, tuple(params))
    finally:
        await db.close()
    return [_row_to_anchor(row) for row in rows]


async def get_anchor(anchor_id: str) -> Anchor | None:
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            """SELECT id, user_id, kind, label, image_url, source_run_id,
                     source_shot_index, reuse_count, created_at
               FROM anchors WHERE id = ?""",
            (anchor_id,),
        )
    finally:
        await db.close()
    if not rows:
        return None
    return _row_to_anchor(rows[0])


async def list_reuses(*, anchor_id: str, user_id: str) -> dict[str, Any]:
    """Return reuse history for one anchor, newest first.

    Raises LookupError if the anchor doesn't exist → 404.
    Raises PermissionError if the anchor belongs to a different user → 403.
    """
    db = await _connect()
    try:
        anchors = await db.execute_fetchall(
            """SELECT id, user_id, kind, label, reuse_count, created_at
               FROM anchors WHERE id = ?""",
            (anchor_id,),
        )
        if not anchors:
            raise LookupError(f"anchor not found: {anchor_id}")
        anchor = anchors[0]
        if anchor[1] != user_id:
            raise PermissionError(f"anchor {anchor_id} belongs to a different user")

        reuses = await db.execute_fetchall(
            """SELECT reused_in_run_id, reused_in_shot_index, reused_at
               FROM anchor_reuses
               WHERE anchor_id = ?
               ORDER BY reused_at DESC, id DESC""",
            (anchor_id,),
        )
    finally:
        await db.close()

    days_since_created = _days_since(anchor[5])
    last_reuse_at = reuses[0][2] if reuses else None
    return {
        "anchor_id": anchor[0],
        "anchor_label": anchor[3],
        "anchor_kind": anchor[2],
        "reuse_count": anchor[4],
        "reuses": [
            {
                "reused_in_run_id": row[0],
                "reused_in_shot_index": row[1],
                "reused_at": row[2],
            }
            for row in reuses
        ],
        "days_since_last_reuse": _days_since(last_reuse_at) if last_reuse_at else days_since_created,
        "days_since_created": days_since_created,
    }


async def reuse_anchor(
    *,
    anchor_id: str,
    user_id: str,
    reused_in_run_id: str,
    reused_in_shot_index: int | None = None,
) -> Anchor:
    """Record one reuse: bump reuse_count, append anchor_reuses row, emit anchor_reused.

    Raises LookupError if the anchor doesn't exist → 404.
    Raises PermissionError if the anchor belongs to a different user → 403.
    """
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            """SELECT id, user_id, kind, label, image_url, source_run_id,
                     source_shot_index, reuse_count, created_at
               FROM anchors WHERE id = ?""",
            (anchor_id,),
        )
        if not rows:
            raise LookupError(f"anchor not found: {anchor_id}")
        row = rows[0]
        if row[1] != user_id:
            raise PermissionError(f"anchor {anchor_id} belongs to a different user")

        new_count = row[7] + 1
        reused_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE anchors SET reuse_count = ? WHERE id = ?",
            (new_count, anchor_id),
        )
        await db.execute(
            """INSERT INTO anchor_reuses (anchor_id, reused_in_run_id, reused_in_shot_index, reused_at)
               VALUES (?, ?, ?, ?)""",
            (anchor_id, reused_in_run_id, reused_in_shot_index, reused_at),
        )

        # is_first_reuse_for_user — count prior anchor_reused events for this user.
        prior = await db.execute_fetchall(
            "SELECT COUNT(*) FROM events WHERE user_id = ? AND event_name = 'anchor_reused'",
            (user_id,),
        )
        prior_count = prior[0][0] if prior else 0
        is_first_reuse_for_user = prior_count == 0
        await db.commit()
    finally:
        await db.close()

    created_at = datetime.fromisoformat(row[8])
    days_since_created = max(0, (datetime.now(timezone.utc) - created_at).days)

    await emit(
        "anchor_reused",
        user_id=user_id,
        run_id=reused_in_run_id,
        payload={
            "anchor_id": anchor_id,
            "anchor_type": row[2],
            "source_run_id": row[5] or "",
            "current_run_id": reused_in_run_id,
            "days_since_created": days_since_created,
            "anchor_label": row[3],
            "reused_in_shot_index": reused_in_shot_index,
            "is_first_reuse_for_user": is_first_reuse_for_user,
        },
    )

    return Anchor(
        id=row[0],
        user_id=row[1],
        kind=AnchorKind(row[2]),
        label=row[3],
        image_url=row[4],
        source_run_id=row[5],
        source_shot_index=row[6],
        reuse_count=new_count,
        created_at=created_at,
    )
