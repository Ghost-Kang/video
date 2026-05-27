"""Canonical Cascade telemetry event names."""

from __future__ import annotations

from enum import StrEnum


class EventName(StrEnum):
    RUN_STARTED = "run_started"
    ANALYSIS_RETURNED = "analysis_returned"
    SCRIPT_REWRITTEN = "script_rewritten"
    SHOT_GENERATED = "shot_generated"
    PUBLISH_PACK_COPIED = "publish_pack_copied"
    ANCHOR_CREATED = "anchor_created"
    ANCHOR_REUSED = "anchor_reused"
    FAILURE_EMITTED = "failure_emitted"
    FAILURE_RECOVERED = "failure_recovered"
    GENERATION_COST = "generation_cost"
    INTERVIEW_LOGGED = "interview_logged"
    CONSENT_ACCEPTED = "consent_accepted"
    CASCADE_RETRY = "cascade_retry"
    CASCADE_CIRCUIT_OPEN = "cascade_circuit_open"
    CASCADE_CACHE_HIT = "cascade_cache_hit"
    CASCADE_CACHE_MISS = "cascade_cache_miss"
