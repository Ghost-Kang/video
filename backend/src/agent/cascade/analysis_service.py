"""Service layer for Phase 1 shallow analysis."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import httpx

from agent import config
from agent.cascade import circuit_breaker
from agent.cascade.adapter import normalize_analysis_result
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.event_names import EventName
from agent.cascade.events import emit
from agent.cascade.failures import FailureCode, HardFailure, WarningCode
from agent.cascade.mediakit import analyze_storyline, overlay_viral_dims, storyline_to_payload
from agent.cascade.mediakit.doubao_direct_client import (
    PREDICT_DOUBAO_DIRECT_CNY,
    analyze_video_direct,
)
from agent.cascade.mediakit.transcribe_client import fetch_transcript
from agent.cascade.mediakit.url_resolver import resolve_to_direct_media
from agent.cascade.persistence.toprador_cache_repo import (
    _load_toprador_cache_entry,
    save_toprador_cache,
)
from agent.cascade.storage import (
    load_analysis,
    load_analysis_for_source,
    load_latest_analysis_for_source,
    save_analysis,
    set_analysis_context,
)


_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "synthetic_v1"
_HAPPY_FIXTURES = (
    _FIXTURES_ROOT / "baomam_fushi" / "001.json",
    _FIXTURES_ROOT / "yuer_richang" / "001.json",
    _FIXTURES_ROOT / "jiating_chufang" / "001.json",
)
_TOPRADOR_CACHE_TTL_S = 60.0
_TOPRADOR_BREAKER = "toprador"

# Upstream mode constants. Kept here so service-level branching matches
# operator-facing env values verbatim.
FIXTURE_MODE = "fixture"
TOPRADOR_MODE = "toprador"
MEDIAKIT_MODE = "mediakit"
DOUBAO_DIRECT_MODE = "doubao_direct"

# P4-3 storm-prevention: per-endpoint last cascade_circuit_open emit timestamp.
# Same endpoint emits at most once per 60s even if many callers hit the open breaker.
_CIRCUIT_OPEN_EMIT_WINDOW_S = 60.0
_last_circuit_open_emit: dict[str, float] = {}
_source_analysis_locks: dict[str, asyncio.Lock] = {}
_MAX_SOURCE_LOCKS = 1024


def _hash_source_url(source_url: str) -> str:
    return hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:12]


def _get_source_lock(source_url_hash: str) -> asyncio.Lock:
    """Per-source-URL lock with a bound on dict growth.

    Previously `setdefault` grew this dict one entry per distinct URL forever.
    When over cap we drop currently-unlocked entries (an unlocked asyncio.Lock
    has no holder and no waiters, so removing it is safe)."""
    lock = _source_analysis_locks.get(source_url_hash)
    if lock is None:
        if len(_source_analysis_locks) >= _MAX_SOURCE_LOCKS:
            for k in [k for k, l in _source_analysis_locks.items() if not l.locked()]:
                del _source_analysis_locks[k]
        lock = asyncio.Lock()
        _source_analysis_locks[source_url_hash] = lock
    return lock


async def request_shallow_analysis(
    source_url: str,
    *,
    user_id: str,
    run_id: str | None = None,
) -> CascadeAnalysisContract:
    """Entry point. Calls upstream or fixture, normalizes, persists, emits event."""
    source_url_hash = _hash_source_url(source_url)
    lock = _get_source_lock(source_url_hash)
    async with lock:
        existing = await load_analysis_for_source(user_id, source_url)
        if existing is not None:
            return existing

        global_existing = await load_latest_analysis_for_source(source_url)
        if global_existing is not None:
            await emit(
                EventName.CASCADE_CACHE_HIT,
                user_id=user_id,
                run_id=run_id,
                payload={
                    "source_url_hash": source_url_hash,
                    # Stored analyses are reused permanently (no TTL); the
                    # earlier hardcoded 60.0 was misleading telemetry. null =
                    # "no expiry". (The separate toprador_cache table has a real
                    # TTL; this cross-user analysis reuse does not.)
                    "ttl_remaining_s": None,
                    "cache_layer": "sqlite",
                },
            )
            contract = global_existing.model_copy(
                update={"analysis_id": _analysis_id(user_id, source_url)}
            )
            set_analysis_context(user_id, run_id)
            inserted = await save_analysis(contract)
            if inserted:
                await emit(
                    EventName.ANALYSIS_RETURNED,
                    user_id=user_id,
                    run_id=run_id,
                    payload=_analysis_returned_payload(
                        contract,
                        upstream_latency_ms=0,
                        upstream_attempts=0,
                    ),
                )
            stored = await load_analysis(contract.analysis_id)
            return stored or contract

        try:
            raw = await _load_upstream_payload(source_url, user_id=user_id, run_id=run_id)
            raw = copy.deepcopy(raw)
            upstream_latency_ms = int(raw.pop("_upstream_latency_ms", 0) or 0)
            upstream_attempts = int(raw.pop("_upstream_attempts", 0) or 0)
            raw["source_url"] = source_url
            raw["analysis_id"] = _analysis_id(user_id, source_url)
            contract = normalize_analysis_result(raw)
        except HardFailure as exc:
            await emit(
                EventName.FAILURE_EMITTED,
                user_id=user_id,
                run_id=run_id,
                payload={
                    "failure_code": exc.code.value,
                    "stage": "analysis",
                    "recovery_path_id": _recovery_path_id(exc),
                },
            )
            raise

        set_analysis_context(user_id, run_id)
        inserted = await save_analysis(contract)
        if inserted:
            await emit(EventName.ANALYSIS_RETURNED,
                user_id=user_id,
                run_id=run_id,
                payload=_analysis_returned_payload(
                    contract,
                    upstream_latency_ms=upstream_latency_ms,
                    upstream_attempts=upstream_attempts,
                ),
            )
        else:
            stored = await load_analysis(contract.analysis_id)
            if stored is not None:
                return stored
        return contract


async def _load_upstream_payload(
    source_url: str,
    *,
    user_id: str,
    run_id: str | None,
) -> dict[str, Any]:
    upstream = os.getenv("CASCADE_UPSTREAM", config.CASCADE_UPSTREAM).strip().lower() or config.CASCADE_UPSTREAM
    if upstream == FIXTURE_MODE:
        return _load_fixture(source_url)
    if upstream == TOPRADOR_MODE:
        return await _call_toprador(source_url, user_id=user_id, run_id=run_id)
    if upstream == MEDIAKIT_MODE:
        return await _call_mediakit(source_url, user_id=user_id, run_id=run_id)
    if upstream == DOUBAO_DIRECT_MODE:
        return await _call_doubao_direct(source_url, user_id=user_id, run_id=run_id)
    raise ValueError(f"unsupported CASCADE_UPSTREAM: {upstream}")


def _load_fixture(source_url: str) -> dict[str, Any]:
    digest = hashlib.sha256(source_url.encode("utf-8")).digest()
    path = _HAPPY_FIXTURES[digest[0] % len(_HAPPY_FIXTURES)]
    return json.loads(path.read_text(encoding="utf-8"))


async def _call_toprador(
    source_url: str,
    *,
    user_id: str,
    run_id: str | None,
) -> dict[str, Any]:
    endpoint = os.getenv("TOPRADOR_ENDPOINT") or config.TOPRADOR_ENDPOINT
    api_key = os.getenv("TOPRADOR_API_KEY") or config.TOPRADOR_API_KEY
    if not endpoint:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "toprador_endpoint_missing")

    source_url_hash = _hash_source_url(source_url)
    cached = await _load_toprador_cache_entry(source_url_hash)
    if cached is not None:
        cached_payload, ttl_remaining_s = cached
        await emit(
            EventName.CASCADE_CACHE_HIT,
            user_id=user_id,
            run_id=run_id,
            payload={
                "source_url_hash": source_url_hash,
                "ttl_remaining_s": round(ttl_remaining_s, 3),
                "cache_layer": "sqlite",
            },
        )
        payload = copy.deepcopy(cached_payload)
        payload["_upstream_latency_ms"] = 0
        payload["_upstream_attempts"] = 0
        return payload
    await emit(
        EventName.CASCADE_CACHE_MISS,
        user_id=user_id,
        run_id=run_id,
        payload={"source_url_hash": source_url_hash},
    )

    try:
        circuit_breaker.before_call(_TOPRADOR_BREAKER)
    except HardFailure as exc:
        if exc.debug_detail == "circuit_open":
            await _emit_circuit_open(endpoint, user_id=user_id, run_id=run_id)
        raise
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    start = time.monotonic()
    attempts = 0
    last_exc: HardFailure | None = None
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, 4):
            attempts = attempt
            attempt_start = time.monotonic()
            try:
                resp = await client.post(endpoint, json={"url": source_url}, headers=headers)
            except httpx.TimeoutException as exc:
                last_exc = HardFailure(FailureCode.S7_UPSTREAM_TIMEOUT, str(exc))
                if attempt < 3:
                    await _emit_retry(endpoint, attempt, "timeout", attempt_start,
                                      user_id=user_id, run_id=run_id)
                    await _retry_sleep(attempt)
                    continue
                raise last_exc from exc
            except httpx.TransportError as exc:
                last_exc = HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"transport_error: {exc}")
                if attempt < 3:
                    await _emit_retry(endpoint, attempt, "transport_error", attempt_start,
                                      user_id=user_id, run_id=run_id)
                    await _retry_sleep(attempt)
                    continue
                circuit_breaker.record_failure(_TOPRADOR_BREAKER)
                raise last_exc from exc

            if resp.status_code >= 500:
                last_exc = HardFailure(
                    FailureCode.S8_UPSTREAM_REFUSED,
                    f"upstream_5xx_{resp.status_code}",
                )
                if attempt < 3:
                    await _emit_retry(endpoint, attempt, f"upstream_5xx_{resp.status_code}",
                                      attempt_start, user_id=user_id, run_id=run_id)
                    await _retry_sleep(attempt)
                    continue
                circuit_breaker.record_failure(_TOPRADOR_BREAKER)
                raise last_exc
            break

    if resp.status_code == 429:
        circuit_breaker.record_failure(_TOPRADOR_BREAKER)
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "rate_limit")
    if resp.status_code in (401, 403):
        circuit_breaker.record_failure(_TOPRADOR_BREAKER)
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "auth_refused")
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        circuit_breaker.record_failure(_TOPRADOR_BREAKER)
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"upstream_http_{resp.status_code}") from exc
    try:
        payload = resp.json()
    except ValueError as exc:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "toprador_json_invalid") from exc
    if not isinstance(payload, dict):
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "toprador_json_not_object")

    circuit_breaker.record_success(_TOPRADOR_BREAKER)
    await save_toprador_cache(source_url_hash, copy.deepcopy(payload), _TOPRADOR_CACHE_TTL_S)
    payload = copy.deepcopy(payload)
    payload["_upstream_latency_ms"] = int((time.monotonic() - start) * 1000)
    payload["_upstream_attempts"] = attempts
    return payload


async def _call_mediakit(
    source_url: str,
    *,
    user_id: str,
    run_id: str | None,
) -> dict[str, Any]:
    start = time.monotonic()
    direct_url, resolver_metadata = await resolve_to_direct_media(source_url)
    _enforce_duration_guard(resolver_metadata)

    storyline = await analyze_storyline(
        direct_url,
        user_id=user_id,
        run_id=run_id,
    )
    payload = storyline_to_payload(
        storyline,
        source_url=source_url,
        user_id=user_id,
    )
    payload = await overlay_viral_dims(payload, direct_url)

    # W4D5: best-effort full transcript via MediaKit. Failure → empty string +
    # W17 warning emitted by adapter via the warnings list. Never blocks.
    transcript = await fetch_transcript(direct_url, user_id=user_id)
    payload["full_transcript"] = transcript or ""
    if not transcript:
        upstream_warnings = list(payload.get("warnings") or [])
        upstream_warnings.append({
            "code": "W17_TRANSCRIBE_FAILED",
            "field": "full_transcript",
            "message": "transcribe unavailable; full_transcript left empty",
            "severity": "warn",
        })
        payload["warnings"] = upstream_warnings

    payload["_upstream_latency_ms"] = int((time.monotonic() - start) * 1000)
    payload["_upstream_attempts"] = 1
    return payload


def _enforce_duration_guard(resolver_metadata: dict[str, Any]) -> None:
    """W4D5 duration guard — refuse <5s and >180s sources before upstream spend.

    Extracted from `_call_mediakit` so `_call_doubao_direct` can apply the
    same gate. `duration_s` only surfaces when the resolver actually scraped
    it (`douyin_share` mode); passthrough → empty dict → no-op (dev escape
    hatch only).
    """
    duration_s = resolver_metadata.get("duration_s")
    if not isinstance(duration_s, (int, float)) or duration_s <= 0:
        return
    if duration_s > 180:
        raise HardFailure(
            FailureCode.S10_DURATION_OUT_OF_RANGE,
            f"这条 {int(round(duration_s))} 秒太长,建议先剪到 3 分钟以内再来分析。",
        )
    if duration_s < 5:
        raise HardFailure(
            FailureCode.S10_DURATION_OUT_OF_RANGE,
            f"视频太短了 ({duration_s:.1f}s),没什么可分析的。",
        )


async def _emit_progress(stage: str, percent: int, eta: int, detail: str) -> None:
    """W5D3-T1 — best-effort progress push. Reads ws/thread_id from
    ContextVar (set by agent_runner before invoking the analyze tool).
    Silent on any failure: progress is decoration, never the critical
    path."""
    try:
        from agent.transport.runtime_ctx import get_run_ctx
        from agent.transport.context import send_json
        ctx = get_run_ctx()
        if not ctx:
            return
        ws = ctx.get("ws")
        thread_id = ctx.get("thread_id")
        if ws is None or not thread_id:
            return
        await send_json(
            ws,
            type="analysis_progress",
            thread_id=thread_id,
            stage=stage,
            percent=percent,
            eta_seconds=eta,
            detail=detail,
        )
    except Exception:
        pass


async def _call_doubao_direct(
    source_url: str,
    *,
    user_id: str,
    run_id: str | None,
) -> dict[str, Any]:
    """Single-shot ARK Doubao vision call → contract-shaped payload.

    Bypass for MediaKit storyline hang. Resolver → duration guard → one
    ARK chat completion that returns the entire CascadeAnalysisContract
    JSON. Adapter normalizes downstream so audio/production fallbacks
    (W15/W16) and confidence clamping (W11) still apply.
    """
    start = time.monotonic()
    await _emit_progress("resolve_url", 5, 55, "拉抖音 CDN 直链")
    direct_url, resolver_metadata = await resolve_to_direct_media(source_url)
    _enforce_duration_guard(resolver_metadata)

    await _emit_progress("ark_overlay", 15, 50, "送豆包视觉模型")
    raw = await analyze_video_direct(direct_url, user_id=user_id, run_id=run_id)
    await _emit_progress("ark_overlay", 85, 8, "模型已返回")
    payload: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}

    # Inject contract envelope fields the model doesn't produce. Mirrors
    # `_call_mediakit`'s storyline_to_payload + post-processing shape.
    payload.setdefault("schema_version", "1.0")
    payload["source_url"] = source_url
    payload["analysis_id"] = _analysis_id(user_id, source_url)
    payload.setdefault("created_at", None)  # adapter._ensure_created_at fills
    payload["model"] = f"ark-{config.DOUBAO_MODEL}-direct"
    payload["cost_cny"] = PREDICT_DOUBAO_DIRECT_CNY

    duration_s = resolver_metadata.get("duration_s")
    if isinstance(duration_s, (int, float)) and duration_s > 0:
        payload["duration_s"] = max(1, int(round(float(duration_s))))

    payload["_upstream_latency_ms"] = int((time.monotonic() - start) * 1000)
    payload["_upstream_attempts"] = 1
    # W5D3 CR-P1 — emit a `transcribe` stage between ark return and done so
    # the frontend's third stage label ("整理输出") lights up briefly instead
    # of being skipped. Adapter normalization + scenes timestamp checks all
    # happen after this in the calling cascade tool.
    await _emit_progress("transcribe", 92, 3, "整理时间线 + 字幕对齐")
    await _emit_progress("done", 100, 0, "整理完成")
    return payload


async def _retry_sleep(attempt: int) -> None:
    await asyncio.sleep((2 ** (attempt - 1)) * random.uniform(0.75, 1.25))


async def _emit_retry(
    endpoint: str,
    attempt: int,
    reason: str,
    attempt_start: float,
    *,
    user_id: str,
    run_id: str | None,
) -> None:
    await emit(
        EventName.CASCADE_RETRY,
        user_id=user_id,
        run_id=run_id,
        payload={
            "endpoint": endpoint,
            "attempt": int(attempt),
            "reason": reason,
            "duration_ms": int((time.monotonic() - attempt_start) * 1000),
        },
    )


async def _emit_circuit_open(
    endpoint: str,
    *,
    user_id: str,
    run_id: str | None,
) -> None:
    """Emit cascade_circuit_open with per-endpoint 60s storm-prevention."""
    now = time.monotonic()
    last = _last_circuit_open_emit.get(endpoint)
    if last is not None and now - last < _CIRCUIT_OPEN_EMIT_WINDOW_S:
        return
    _last_circuit_open_emit[endpoint] = now
    state = circuit_breaker._BREAKERS.get(_TOPRADOR_BREAKER)
    consecutive_failures = len(state.failures) if state is not None else 0
    if state is not None and state.opened_at is not None:
        cooldown_s = max(
            0.0,
            state.opened_at + circuit_breaker.COOLDOWN_S - now,
        )
    else:
        cooldown_s = circuit_breaker.COOLDOWN_S
    await emit(
        EventName.CASCADE_CIRCUIT_OPEN,
        user_id=user_id,
        run_id=run_id,
        payload={
            "endpoint": endpoint,
            "consecutive_failures": consecutive_failures,
            "cooldown_s": round(cooldown_s, 3),
        },
    )


def _analysis_id(user_id: str, source_url: str) -> str:
    digest = hashlib.sha256(f"{user_id}\0{source_url}".encode("utf-8")).hexdigest()[:24]
    return f"ana_{digest}"


def _analysis_returned_payload(
    contract: CascadeAnalysisContract,
    *,
    upstream_latency_ms: int = 0,
    upstream_attempts: int = 0,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "analysis_id": contract.analysis_id,
        "source_url": str(contract.source_url),
        "platform": contract.platform.value,
        "cost_cny": contract.cost_cny,
        "duration_s": contract.duration_s,
        "scenes_count": len(contract.scenes),
        "warnings_count": len(contract.warnings),
        "confidence": contract.confidence,
        "had_fallback": any(w.code == WarningCode.W2_FALLBACK_USED.value for w in contract.warnings),
        "model": contract.model,
        "upstream_latency_ms": upstream_latency_ms,
        "upstream_attempts": upstream_attempts,
    }
    minor_indices = [
        warning.field.removeprefix("scenes[").removesuffix("]")
        for warning in contract.warnings
        if warning.code == WarningCode.W14_MINOR_SUBJECT_DETECTED.value
    ]
    if minor_indices:
        payload["minor_audit"] = {
            "hit_count": len(minor_indices),
            "scene_indices": minor_indices,
        }
    return payload


def _recovery_path_id(exc: HardFailure) -> str:
    actions = exc.actions
    return actions[0] if actions else "REPORT"
