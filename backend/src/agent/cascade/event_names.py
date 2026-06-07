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
    SHOT_VIDEO_RETURNED = "shot_video_returned"
    FILM_RETURNED = "film_returned"
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
    # 等待态遥测(AnalyzingHero,project_analyzing_wait_redesign)— 分析等待漏斗:
    # 用户发起分析(started)→ 成功收尾(completed)/ 超时(timeout)/ 中途跳出
    # (abandoned)。前端已 emit 但后端 allowlist 漏列 → 全被 /api/events 400 拒,漏斗
    # 有洞(直接影响「Day1 完成首条」与放弃率口径)。2026-06-04 浏览器真机验证抓出补齐。
    ANALYSIS_WAIT_STARTED = "analysis_wait_started"
    ANALYSIS_WAIT_COMPLETED = "analysis_wait_completed"
    ANALYSIS_WAIT_TIMEOUT = "analysis_wait_timeout"
    ANALYSIS_WAIT_ABANDONED = "analysis_wait_abandoned"
    # AnalysisProgress pin-escape 观测(进度条「钉住/逃逸」误报排查)。前端 emit,同样漏列。
    PIN_ESCAPE_SHOWN = "pin_escape_shown"
    PIN_ESCAPE_ACTION = "pin_escape_action"
    # Pro 画布漏斗(灰度上量观测):种子/主题建图 → 运行 → 出片成功。均 server-side 可观测。
    PRO_SEEDED = "pro_seeded"
    PRO_RUN_SUBMITTED = "pro_run_submitted"
    PRO_RUN_DONE = "pro_run_done"
