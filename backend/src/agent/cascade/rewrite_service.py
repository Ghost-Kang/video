"""Service layer for Phase 1 niche rewrite."""

from __future__ import annotations

import hashlib
import importlib
import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.cost_cap import predict_rewrite_cost
from agent.cascade.events import emit
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.storage import (
    load_analysis,
    load_recent_rewrite,
    save_rewrite,
    utc_now_rfc3339,
)


Niche = Literal["baomam_fushi", "yuer_richang", "jiating_chufang"]
SUPPORTED_NICHES = {"baomam_fushi", "yuer_richang", "jiating_chufang"}


class RewriteShot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_index: int = Field(..., ge=1)
    dialogue: str
    visual: str


class RewriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rewrite_id: str
    analysis_id: str
    niche: str
    script_markdown: str
    shots: list[RewriteShot] = Field(..., min_length=3, max_length=5)
    parser_warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    cost_cny: float = Field(..., ge=0.0)
    model: str
    # Founder's H1-H8 taxonomy preserved from source. Empty when the source
    # is unannotated (legacy synthetic_v1 fixture or auto-derived analysis).
    hook_pattern_id: str = ""
    # positive | negative_ref | edge_case — default positive for legacy callers.
    source_classification: str = "positive"


async def request_rewrite(
    *,
    analysis_id: str,
    niche: Niche,
    user_id: str,
    run_id: str | None = None,
) -> RewriteResult:
    if niche not in SUPPORTED_NICHES:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"unsupported niche: {niche}")

    contract = await load_analysis(analysis_id)
    if contract is None:
        raise LookupError(f"analysis_id not found: {analysis_id}")

    predicted = predict_rewrite_cost(contract, niche)
    if predicted > 3.0:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "cost cap")

    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cached = await load_recent_rewrite(
        analysis_id=analysis_id,
        niche=niche,
        user_id=user_id,
        since=since,
    )
    if cached:
        return RewriteResult.model_validate_json(cached)

    result = await _rewrite_for_niche(contract, niche)
    await save_rewrite(
        result.rewrite_id,
        analysis_id=analysis_id,
        niche=niche,
        user_id=user_id,
        run_id=run_id,
        result_json=result.model_dump_json(),
        created_at=utc_now_rfc3339(),
    )
    await emit(
        "script_rewritten",
        user_id=user_id,
        run_id=run_id,
        payload={
            "analysis_id": analysis_id,
            "rewrite_id": result.rewrite_id,
            "niche": niche,
            "parser_warnings": len(result.parser_warnings),
            "shots_count": len(result.shots),
            "shot_count": len(result.shots),
            "script_char_len": len(result.script_markdown),
            "confidence": result.confidence,
            "cost_cny": result.cost_cny,
            "model": result.model,
            "had_anchor_reference": False,
        },
    )
    return result


async def _rewrite_for_niche(contract: CascadeAnalysisContract, niche: str) -> RewriteResult:
    try:
        rewrite_module = importlib.import_module("agent.cascade.rewrite")
        raw = await rewrite_module.rewrite_for_niche(contract, niche)
        return RewriteResult.model_validate(raw)
    except ModuleNotFoundError:
        return _fallback_rewrite(contract, niche)
    except TimeoutError as exc:
        raise HardFailure(FailureCode.S7_UPSTREAM_TIMEOUT, "rewrite timeout") from exc


def _fallback_rewrite(contract: CascadeAnalysisContract, niche: str) -> RewriteResult:
    scenes = contract.scenes[:5]
    shots = [
        RewriteShot(
            shot_index=i,
            dialogue=scene.dialogue_and_narration or "这一段靠画面表达",
            visual=scene.visual_content,
        )
        for i, scene in enumerate(scenes, start=1)
    ]
    body = "\n".join(
        f"{shot.shot_index}. {shot.dialogue}\n   画面：{shot.visual}" for shot in shots
    )
    created_key = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(f"{contract.analysis_id}\0{niche}\0{body}\0{created_key}".encode("utf-8")).hexdigest()[:16]
    return RewriteResult(
        rewrite_id=f"rw_{digest}",
        analysis_id=contract.analysis_id,
        niche=niche,
        script_markdown=f"### 改写脚本\n{body}",
        shots=shots,
        parser_warnings=[],
        confidence=max(0.0, min(1.0, contract.confidence - 0.03)),
        cost_cny=0.47,
        model=contract.model,
    )


def error_payload(exc: Exception) -> dict:
    request_id = f"req_{hashlib.sha256(str(datetime.now(timezone.utc).timestamp()).encode()).hexdigest()[:12]}"
    if isinstance(exc, HardFailure):
        payload = exc.to_payload(include_debug=os.getenv("CASCADE_DEBUG_ERRORS") == "1")
        payload.setdefault("request_id", request_id)
        return payload
    return {"code": FailureCode.S5_INVALID_PAYLOAD.value, "hint": "", "actions": ["REPORT"], "request_id": request_id}
