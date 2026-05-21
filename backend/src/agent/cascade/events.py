"""Single write path for Cascade Phase 1 telemetry."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from agent.cascade.storage import save_event


ALLOWED_EVENTS: frozenset[str] = frozenset({
    "run_started",
    "analysis_returned",
    "script_rewritten",
    "shot_generated",
    "publish_pack_copied",
    "anchor_created",
    "anchor_reused",
    "failure_emitted",
    "failure_recovered",
    "generation_cost",
    "interview_logged",
})

_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "run_started": frozenset({"entry_kind", "niche_text_len", "niche_text_hash"}),
    "analysis_returned": frozenset({
        "analysis_id",
        "source_url",
        "platform",
        "cost_cny",
        "duration_s",
        "scenes_count",
        "warnings_count",
        "confidence",
        "had_fallback",
        "model",
    }),
    "script_rewritten": frozenset({"shot_count", "script_char_len", "parser_warnings"}),
    "shot_generated": frozenset({"shot_index", "provider", "model", "outcome", "attempt", "latency_ms", "anchor_refs"}),
    "publish_pack_copied": frozenset(),
    "anchor_created": frozenset({"anchor_id", "anchor_type", "source_run_id"}),
    "anchor_reused": frozenset({"anchor_id", "anchor_type", "source_run_id", "current_run_id", "days_since_created"}),
    "failure_emitted": frozenset({"failure_code", "stage", "recovery_path_id"}),
    "failure_recovered": frozenset({"failure_code", "recovery_action", "seconds_since_failure"}),
    "generation_cost": frozenset({"run_id", "call_kind", "provider", "model", "cost_fen", "latency_ms", "tokens_in", "tokens_out", "outcome"}),
    "interview_logged": frozenset({"value_statement_match", "would_pay_39", "notes_url", "niche"}),
}

_lock = asyncio.Lock()
_last_by_run: dict[str, datetime] = {}


def _now_after(run_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    if run_id:
        previous = _last_by_run.get(run_id)
        if previous is not None and now <= previous:
            now = previous + timedelta(microseconds=1)
        _last_by_run[run_id] = now
    return now.isoformat()


async def emit(
    event_name: str,
    *,
    user_id: str,
    run_id: str | None,
    payload: dict[str, Any],
) -> None:
    """Validate and persist one Phase 1 event."""
    if event_name not in ALLOWED_EVENTS:
        raise ValueError(f"unknown event_name: {event_name}")
    if event_name == "publish_pack_copied":
        has_old = {"shot_count_in_pack", "has_title", "has_tags", "script_char_len"} <= payload.keys()
        has_new = {"rewrite_id", "shots_count", "titles_offered", "tags_count", "payload_size_chars"} <= payload.keys()
        if not has_old and not has_new:
            raise ValueError("publish_pack_copied missing required fields")
        missing = []
    else:
        missing = sorted(_REQUIRED_FIELDS[event_name] - payload.keys())
    if missing:
        raise ValueError(f"{event_name} missing required fields: {', '.join(missing)}")
    if event_name == "failure_emitted" and not str(payload.get("recovery_path_id") or "").strip():
        raise ValueError("failure_emitted requires non-empty recovery_path_id")

    async with _lock:
        created_at = _now_after(run_id)
        await save_event(event_name, user_id, run_id, payload, created_at)
