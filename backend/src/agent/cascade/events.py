"""Single write path for Cascade Phase 1 telemetry."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from agent.cascade.event_names import EventName
from agent.cascade.storage import save_event


ALLOWED_EVENTS: frozenset[str] = frozenset(event.value for event in EventName)

_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    EventName.RUN_STARTED.value: frozenset({"entry_kind", "niche_text_len", "niche_text_hash"}),
    EventName.ANALYSIS_RETURNED.value: frozenset({
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
        "upstream_latency_ms",
        "upstream_attempts",
    }),
    EventName.SCRIPT_REWRITTEN.value: frozenset({"shot_count", "script_char_len", "parser_warnings"}),
    EventName.SHOT_GENERATED.value: frozenset({"shot_index", "provider", "model", "outcome", "attempt", "latency_ms", "anchor_refs"}),
    EventName.SHOT_FIRST_FRAME_RETURNED.value: frozenset({"rewrite_id", "shot_index", "cost_cny"}),
    EventName.PUBLISH_PACK_COPIED.value: frozenset(),
    EventName.ANCHOR_CREATED.value: frozenset({"anchor_id", "anchor_type", "source_run_id"}),
    EventName.ANCHOR_REUSED.value: frozenset({"anchor_id", "anchor_type", "source_run_id", "current_run_id", "days_since_created"}),
    EventName.FAILURE_EMITTED.value: frozenset({"failure_code", "stage", "recovery_path_id"}),
    EventName.FAILURE_RECOVERED.value: frozenset({"failure_code", "recovery_action", "seconds_since_failure"}),
    EventName.GENERATION_COST.value: frozenset({"run_id", "call_kind", "provider", "model", "cost_fen", "latency_ms", "tokens_in", "tokens_out", "outcome"}),
    EventName.INTERVIEW_LOGGED.value: frozenset({"value_statement_match", "would_pay_39", "notes_url", "niche"}),
    EventName.CONSENT_ACCEPTED.value: frozenset({"version", "accepted_at", "documents"}),
    EventName.CASCADE_RETRY.value: frozenset({"endpoint", "attempt", "reason", "duration_ms"}),
    EventName.CASCADE_CIRCUIT_OPEN.value: frozenset({"endpoint", "consecutive_failures", "cooldown_s"}),
    EventName.CASCADE_CACHE_HIT.value: frozenset({"source_url_hash", "ttl_remaining_s", "cache_layer"}),
    EventName.CASCADE_CACHE_MISS.value: frozenset({"source_url_hash"}),
    EventName.NICHE_SELECTED.value: frozenset({"niche", "thread_id"}),
    EventName.UNCAUGHT_EXCEPTION.value: frozenset({"site", "exc_type", "message"}),
    EventName.CLIENT_ERROR.value: frozenset({"kind", "message"}),
    # 前端遥测:不强制 required 字段(payload 因端而异,宽松摄入,避免缺字段又被 400 拒)。
    EventName.ANALYSIS_WAIT_STARTED.value: frozenset(),
    EventName.ANALYSIS_WAIT_COMPLETED.value: frozenset(),
    EventName.ANALYSIS_WAIT_TIMEOUT.value: frozenset(),
    EventName.ANALYSIS_WAIT_ABANDONED.value: frozenset(),
    EventName.PIN_ESCAPE_SHOWN.value: frozenset(),
    EventName.PIN_ESCAPE_ACTION.value: frozenset(),
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
    event_name: str | EventName,
    *,
    user_id: str,
    run_id: str | None,
    payload: dict[str, Any],
) -> None:
    """Validate and persist one Phase 1 event."""
    event_name = event_name.value if isinstance(event_name, EventName) else event_name
    if event_name not in ALLOWED_EVENTS:
        raise ValueError(f"unknown event_name: {event_name}")
    if event_name == EventName.PUBLISH_PACK_COPIED.value:
        has_old = {"shot_count_in_pack", "has_title", "has_tags", "script_char_len"} <= payload.keys()
        has_new = {"rewrite_id", "shots_count", "titles_offered", "tags_count", "payload_size_chars"} <= payload.keys()
        if not has_old and not has_new:
            raise ValueError("publish_pack_copied missing required fields")
        missing = []
    else:
        # .get 兜底:enum 里有但 _REQUIRED_FIELDS 没显式列的事件(如 analysis_answer_returned /
        # shot_video_returned / film_returned)默认无必填字段,而不是 KeyError→500/漏点。
        missing = sorted(_REQUIRED_FIELDS.get(event_name, frozenset()) - payload.keys())
    if missing:
        raise ValueError(f"{event_name} missing required fields: {', '.join(missing)}")
    if event_name == EventName.FAILURE_EMITTED.value and not str(payload.get("recovery_path_id") or "").strip():
        raise ValueError("failure_emitted requires non-empty recovery_path_id")

    async with _lock:
        created_at = _now_after(run_id)
        await save_event(event_name, user_id, run_id, payload, created_at)
