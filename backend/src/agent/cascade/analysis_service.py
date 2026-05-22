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
from agent.cascade.events import emit
from agent.cascade.failures import FailureCode, HardFailure, WarningCode
from agent.cascade.storage import (
    load_analysis,
    load_analysis_for_source,
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
_TOPRADOR_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_TOPRADOR_BREAKER = "toprador"


async def request_shallow_analysis(
    source_url: str,
    *,
    user_id: str,
    run_id: str | None = None,
) -> CascadeAnalysisContract:
    """Entry point. Calls upstream or fixture, normalizes, persists, emits event."""
    existing = await load_analysis_for_source(user_id, source_url)
    if existing is not None:
        return existing

    try:
        raw = await _load_upstream_payload(source_url)
        raw = copy.deepcopy(raw)
        upstream_latency_ms = int(raw.pop("_upstream_latency_ms", 0) or 0)
        upstream_attempts = int(raw.pop("_upstream_attempts", 0) or 0)
        raw["source_url"] = source_url
        raw["analysis_id"] = _analysis_id(user_id, source_url)
        contract = normalize_analysis_result(raw)
    except HardFailure as exc:
        await emit(
            "failure_emitted",
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
        await emit("analysis_returned",
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


async def _load_upstream_payload(source_url: str) -> dict[str, Any]:
    upstream = os.getenv("CASCADE_UPSTREAM", "fixture").strip().lower() or "fixture"
    if upstream == "fixture":
        return _load_fixture(source_url)
    if upstream == "toprador":
        return await _call_toprador(source_url)
    raise ValueError(f"unsupported CASCADE_UPSTREAM: {upstream}")


def _load_fixture(source_url: str) -> dict[str, Any]:
    digest = hashlib.sha256(source_url.encode("utf-8")).digest()
    path = _HAPPY_FIXTURES[digest[0] % len(_HAPPY_FIXTURES)]
    return json.loads(path.read_text(encoding="utf-8"))


async def _call_toprador(source_url: str) -> dict[str, Any]:
    endpoint = os.getenv("TOPRADOR_ENDPOINT") or config.TOPRADOR_ENDPOINT
    api_key = os.getenv("TOPRADOR_API_KEY") or config.TOPRADOR_API_KEY
    if not endpoint:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "toprador_endpoint_missing")

    now = time.monotonic()
    cached = _TOPRADOR_CACHE.get(source_url)
    if cached and cached[0] > now:
        payload = copy.deepcopy(cached[1])
        payload["_upstream_latency_ms"] = 0
        payload["_upstream_attempts"] = 0
        return payload

    circuit_breaker.before_call(_TOPRADOR_BREAKER)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    start = time.monotonic()
    attempts = 0
    last_exc: HardFailure | None = None
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, 4):
            attempts = attempt
            try:
                resp = await client.post(endpoint, json={"url": source_url}, headers=headers)
            except httpx.TimeoutException as exc:
                last_exc = HardFailure(FailureCode.S7_UPSTREAM_TIMEOUT, str(exc))
                if attempt < 3:
                    await _retry_sleep(attempt)
                    continue
                raise last_exc from exc
            except httpx.TransportError as exc:
                last_exc = HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"transport_error: {exc}")
                if attempt < 3:
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
    _TOPRADOR_CACHE[source_url] = (
        time.monotonic() + _TOPRADOR_CACHE_TTL_S,
        copy.deepcopy(payload),
    )
    payload = copy.deepcopy(payload)
    payload["_upstream_latency_ms"] = int((time.monotonic() - start) * 1000)
    payload["_upstream_attempts"] = attempts
    return payload


async def _retry_sleep(attempt: int) -> None:
    await asyncio.sleep((2 ** (attempt - 1)) * random.uniform(0.75, 1.25))


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
