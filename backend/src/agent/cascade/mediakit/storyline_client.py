"""MediaKit analyze-video-storyline client.

This is P5-3 Sub-phase A: submit a MediaKit storyline task, poll it to
completion, and cache the raw `result` payload for later adapter phases.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import time
from typing import Any

import httpx

from agent import config
from agent.cascade import circuit_breaker
from agent.cascade.events import emit
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.storage import (
    _load_toprador_cache_entry,
    save_toprador_cache,
)


MEDIAKIT_BASE_URL = "https://mediakit.cn-beijing.volces.com/api/v1"
STORYLINE_TOOL_URL = f"{MEDIAKIT_BASE_URL}/tools/analyze-video-storyline"
TASK_URL = f"{MEDIAKIT_BASE_URL}/tasks"
STORYLINE_BREAKER = "mediakit_storyline"
STORYLINE_CACHE_TTL_S = 24 * 60 * 60
_MAX_ATTEMPTS = 3


def _cache_key(video_url: str) -> str:
    digest = hashlib.sha1(video_url.encode("utf-8")).hexdigest()[:12]
    return f"mediakit_storyline::{digest}"


def _headers() -> dict[str, str]:
    token = config.VOLC_MEDIAKIT_AK
    if not token:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "mediakit_key_missing")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def submit_storyline_task(
    video_urls: list[str],
    *,
    enable_snapshot: bool = True,
) -> str:
    """Submit an analyze-video-storyline task and return its task_id."""
    if not video_urls:
        raise HardFailure(FailureCode.S1_NO_SOURCE_URL, "mediakit_video_urls_empty")
    payload = {
        "video_urls": video_urls,
        "enable_snapshot": enable_snapshot,
    }
    body = await _post_json(STORYLINE_TOOL_URL, payload, user_id="system", run_id=None)
    task_id = body.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "mediakit_storyline_task_id_missing")
    return task_id


async def poll_task(
    task_id: str,
    *,
    timeout_s: float = 600.0,
    poll_interval_s: float = 10.0,
) -> dict[str, Any]:
    """Poll a MediaKit task until completion and return the raw result object."""
    if not task_id.strip():
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "mediakit_task_id_empty")
    deadline = time.monotonic() + timeout_s
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            if time.monotonic() >= deadline:
                raise HardFailure(FailureCode.S7_UPSTREAM_TIMEOUT, "mediakit_task_poll_timeout")
            body = await _get_json(client, f"{TASK_URL}/{task_id}")
            status = str(body.get("status") or "").lower()
            if status in {"completed", "done", "succeeded", "success"}:
                result = body.get("result")
                if not isinstance(result, dict):
                    raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "mediakit_task_result_missing")
                return result
            if status in {"failed", "error", "canceled", "cancelled"}:
                detail = body.get("error") or body.get("message") or "mediakit_task_failed"
                raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, str(detail))
            await asyncio.sleep(poll_interval_s)


async def analyze_storyline(
    video_url: str,
    *,
    user_id: str,
    run_id: str | None,
    timeout_s: float = 600.0,
    poll_interval_s: float = 10.0,
) -> dict[str, Any]:
    """Return cached or freshly polled MediaKit storyline result for one video URL."""
    if not video_url.strip():
        raise HardFailure(FailureCode.S1_NO_SOURCE_URL, "mediakit_video_url_empty")

    cache_key = _cache_key(video_url)
    cached = await _load_toprador_cache_entry(cache_key)
    if cached is not None:
        payload, ttl_remaining_s = cached
        await emit(
            "cascade_cache_hit",
            user_id=user_id,
            run_id=run_id,
            payload={
                "source_url_hash": cache_key,
                "ttl_remaining_s": round(ttl_remaining_s, 3),
                "cache_layer": "sqlite",
            },
        )
        return copy.deepcopy(payload)

    await emit(
        "cascade_cache_miss",
        user_id=user_id,
        run_id=run_id,
        payload={"source_url_hash": cache_key},
    )
    task_id = await submit_storyline_task([video_url], enable_snapshot=True)
    result = await poll_task(task_id, timeout_s=timeout_s, poll_interval_s=poll_interval_s)
    await save_toprador_cache(cache_key, copy.deepcopy(result), STORYLINE_CACHE_TTL_S)
    return result


async def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    user_id: str,
    run_id: str | None,
) -> dict[str, Any]:
    circuit_breaker.before_call(STORYLINE_BREAKER)
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            started = time.monotonic()
            try:
                response = await client.post(url, json=payload, headers=_headers())
            except httpx.TimeoutException as exc:
                if attempt < _MAX_ATTEMPTS:
                    await _emit_retry(url, attempt, "timeout", started, user_id=user_id, run_id=run_id)
                    await _retry_sleep(attempt)
                    continue
                raise HardFailure(FailureCode.S7_UPSTREAM_TIMEOUT, str(exc)) from exc
            except httpx.TransportError as exc:
                if attempt < _MAX_ATTEMPTS:
                    await _emit_retry(url, attempt, "transport_error", started, user_id=user_id, run_id=run_id)
                    await _retry_sleep(attempt)
                    continue
                circuit_breaker.record_failure(STORYLINE_BREAKER)
                raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"transport_error: {exc}") from exc

            if response.status_code >= 500 and attempt < _MAX_ATTEMPTS:
                await _emit_retry(
                    url,
                    attempt,
                    f"upstream_5xx_{response.status_code}",
                    started,
                    user_id=user_id,
                    run_id=run_id,
                )
                await _retry_sleep(attempt)
                continue

            body = _response_json(response)
            if response.status_code >= 500:
                circuit_breaker.record_failure(STORYLINE_BREAKER)
                raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"upstream_5xx_{response.status_code}")
            if response.status_code in (401, 403):
                circuit_breaker.record_failure(STORYLINE_BREAKER)
                raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "auth_refused")
            if not bool(body.get("success", response.is_success)):
                circuit_breaker.record_failure(STORYLINE_BREAKER)
                raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, str(body.get("error") or body))
            circuit_breaker.record_success(STORYLINE_BREAKER)
            return body

    raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "mediakit_unreachable")


async def _get_json(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    try:
        response = await client.get(url, headers=_headers())
    except httpx.TimeoutException as exc:
        raise HardFailure(FailureCode.S7_UPSTREAM_TIMEOUT, str(exc)) from exc
    except httpx.TransportError as exc:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"transport_error: {exc}") from exc
    body = _response_json(response)
    if response.status_code in (401, 403):
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "auth_refused")
    if response.status_code >= 500:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"upstream_5xx_{response.status_code}")
    return body


def _response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "mediakit_json_invalid") from exc
    if not isinstance(body, dict):
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "mediakit_json_not_object")
    return body


async def _emit_retry(
    endpoint: str,
    attempt: int,
    reason: str,
    started: float,
    *,
    user_id: str,
    run_id: str | None,
) -> None:
    await emit(
        "cascade_retry",
        user_id=user_id,
        run_id=run_id,
        payload={
            "endpoint": endpoint,
            "attempt": int(attempt),
            "reason": reason,
            "duration_ms": int((time.monotonic() - started) * 1000),
        },
    )


async def _retry_sleep(attempt: int) -> None:
    await asyncio.sleep(2 ** (attempt - 1))
