from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.cascade.event_names import EventName
from agent.cascade.persistence.db import _connect


_FAILURE_RETENTION_EVENTS = frozenset({
    EventName.FAILURE_EMITTED.value,
    EventName.FAILURE_RECOVERED.value,
})
_INFRA_RETENTION_EVENTS = frozenset({
    EventName.CASCADE_RETRY.value,
    EventName.CASCADE_CIRCUIT_OPEN.value,
    EventName.CASCADE_CACHE_HIT.value,
    EventName.CASCADE_CACHE_MISS.value,
})


async def retention_sweep(now: datetime | None = None) -> dict[str, int]:
    """Delete expired telemetry events according to the Phase 1 retention policy."""
    current = now or datetime.now(timezone.utc)
    policies: tuple[tuple[frozenset[str], datetime], ...] = (
        (_FAILURE_RETENTION_EVENTS, current - timedelta(days=180)),
        (_INFRA_RETENTION_EVENTS, current - timedelta(days=90)),
    )
    deleted: dict[str, int] = {
        event_name: 0
        for event_names, _cutoff in policies
        for event_name in sorted(event_names)
    }
    db = await _connect()
    try:
        await db.execute("BEGIN")
        for event_names, cutoff in policies:
            for event_name in sorted(event_names):
                cursor = await db.execute(
                    "DELETE FROM events WHERE event_name = ? AND created_at < ?",
                    (event_name, cutoff.isoformat()),
                )
                deleted[event_name] = int(cursor.rowcount or 0)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
    return deleted
