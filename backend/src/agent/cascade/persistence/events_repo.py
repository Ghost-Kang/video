from __future__ import annotations

import json
from typing import Any

from agent.cascade.persistence.db import _connect


async def save_event(event_name: str, user_id: str, run_id: str | None, payload: dict[str, Any], created_at: str) -> None:
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO events (event_name, user_id, run_id, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event_name, user_id, run_id, json.dumps(payload, ensure_ascii=False, sort_keys=True), created_at),
        )
        await db.commit()
    finally:
        await db.close()


async def sum_generation_cost(
    *,
    user_id: str | None = None,
    run_id: str | None = None,
    since: str | None = None,
) -> float:
    clauses = ["event_name = 'generation_cost'"]
    params: list[Any] = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if run_id is not None:
        clauses.append("run_id = ?")
        params.append(run_id)
    if since is not None:
        clauses.append("created_at >= ?")
        params.append(since)
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            f"SELECT payload_json FROM events WHERE {' AND '.join(clauses)}",
            tuple(params),
        )
    finally:
        await db.close()
    total_fen = 0
    for (payload_json,) in rows:
        try:
            payload = json.loads(payload_json)
            total_fen += int(payload.get("cost_fen") or 0)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return total_fen / 100.0


_LIST_EVENTS_MAX_LIMIT = 1000


async def list_events(
    *,
    limit: int = 200,
    offset: int = 0,
    event_name: str | None = None,
    user_id: str | None = None,
    since_ts: str | None = None,
) -> dict[str, Any]:
    """List telemetry events for the admin firehose (P4-2)."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    if limit > _LIST_EVENTS_MAX_LIMIT:
        limit = _LIST_EVENTS_MAX_LIMIT
    if offset < 0:
        raise ValueError("offset must be non-negative")

    clauses: list[str] = []
    params: list[Any] = []
    if event_name is not None:
        clauses.append("event_name = ?")
        params.append(event_name)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if since_ts is not None:
        clauses.append("created_at > ?")
        params.append(since_ts)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            f"SELECT id, event_name, user_id, run_id, payload_json, created_at "
            f"FROM events{where} ORDER BY created_at DESC, id DESC "
            f"LIMIT ? OFFSET ?",
            tuple([*params, limit + 1, offset]),
        )
    finally:
        await db.close()

    rows_list = list(rows)
    has_more = len(rows_list) > limit
    if has_more:
        rows_list = rows_list[:limit]

    events: list[dict[str, Any]] = []
    for row_id, name, uid, rid, payload_json, created_at in rows_list:
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except json.JSONDecodeError:
            payload = {"_raw": payload_json}
        events.append({
            "id": int(row_id),
            "ts": created_at,
            "event_name": name,
            "user_id": uid,
            "run_id": rid,
            "payload": payload,
        })

    return {
        "events": events,
        "has_more": has_more,
        "next_offset": (offset + limit) if has_more else None,
    }
