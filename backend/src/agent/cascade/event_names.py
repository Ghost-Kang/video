"""Canonical Cascade telemetry event names."""

from __future__ import annotations

from enum import StrEnum


class EventName(StrEnum):
    RUN_STARTED = "run_started"
    ANALYSIS_RETURNED = "analysis_returned"
    # W4D5: free-form Q&A response against a prior analysis. Carries the
    # cascade_ask tool's answer string + the originating analysis_id so
    # /admin/events can audit which analyses creators are interrogating.
    ANALYSIS_ANSWER_RETURNED = "analysis_answer_returned"
    SCRIPT_REWRITTEN = "script_rewritten"
    SHOT_GENERATED = "shot_generated"
    SHOT_FIRST_FRAME_RETURNED = "shot_first_frame_returned"
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
    # Fired when a user sends a chat message tagged with their onboarding-picked niche.
    # Lets /admin/events confirm the WS field actually wires through end-to-end.
    NICHE_SELECTED = "niche_selected"
    # W5D2 observability — backend Python uncaught exception escape into a
    # request/agent handler. Captured by run_agent / ws_server / http_router
    # global try/except. Carries truncated traceback so /admin/events can
    # surface server-side bugs without ssh'ing into the container.
    UNCAUGHT_EXCEPTION = "uncaught_exception"
    # W5D2 observability — browser-side JS error caught by window.onerror /
    # unhandledrejection / React ErrorBoundary, POSTed back to backend via
    # /api/client_error. Lets founder see cohort 创作者 JS issues without
    # asking the user to paste console output.
    CLIENT_ERROR = "client_error"
