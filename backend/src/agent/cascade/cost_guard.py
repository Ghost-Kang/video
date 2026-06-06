"""Phase 1 cost guard.

Hardcoded predictions (per-call upper-bound):
- shallow analysis: ¥1.20  (MediaKit storyline ¥1.00/min × 60s + ARK Chat overlay ~¥0.10 + buffer)
- rewrite: ¥1.00            (Doubao seed-1.6 LLM rewrite per niche)
- shot image: ¥1.50         (Apimart / Google image gen per shot)

The analysis prediction was raised 2026-05-23 from ¥0.50 → ¥1.20 after
MediaKit official pricing doc surfaced: 剧情故事线分析 = ¥1.00/min input
duration (not the ¥0.10-0.20 PM had estimated when writing P5-3 brief
e3e2739). Phase 1 typical short-video = 60s = 1 min input → ¥1.00
storyline alone, plus ARK Chat viral overlay ~¥0.10 tokens, total ≈ ¥1.10.
¥1.20 PREDICT keeps a ~9% buffer for low-bitrate longer clips.

CASCADE_RUN_CAP_CNY default = ¥25.0 (env override). 2026-06-06: this is the
RUNAWAY CIRCUIT BREAKER, not the primary throttle. Once agent_runner started
minting a real per-turn run_id (audit #1-7 根因 A — run_id was hardcoded None,
so the per-run sum was always ~0 and this cap never bit), a low ¥3 cap would
START killing legitimate turns: a single full film turn is ~¥18-20 (5 images
¥7.5 + 5×5s video ¥7.5 + analysis ¥1.2 + rewrite ¥1.0). ¥25 holds one legal
full turn with buffer while still tripping a retry storm / accidental loop.
The PRIMARY throttle is the per-user-day cap ¥30. Founder finalizes both via
env once pricing tiers land (phase2_pricing_cost_analysis ❓7).

NOTE (known residual): generation cost is charged at enqueue but RECORDED at
completion (video records in the background poll). So a BURST of video enqueues
inside one turn isn't tightly capped per-run — sum_generation_cost only sees
costs recorded by prior completed work. The ¥30/day cap backstops it; tight
within-turn capping would need provisional reservation (out of scope here).

Per-user day is measured by UTC calendar day.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.storage import sum_generation_cost


# Raised 2026-05-23 from 0.5 → 1.20 per MediaKit official pricing
# (剧情故事线分析 = ¥1.00/min input duration + ARK overlay ~¥0.10)
PREDICT_ANALYSIS_CNY = 1.2
PREDICT_REWRITE_CNY = 1.0
PREDICT_SHOT_IMAGE_CNY = 1.5
# W4D5 additions
# - Transcribe: MediaKit extract-audio-text per call ≈ ¥0.30
# - Cascade ask: one LLM round-trip on capped context ≈ ¥0.05
PREDICT_TRANSCRIBE_CNY = 0.30
PREDICT_ASK_CNY = 0.05
# 2026-05-27 doubao_direct upstream — single ARK Doubao seed-1.6 vision call
# replacing MediaKit storyline+overlay+transcribe (which hangs). One chat
# completion with fps=1/max_frames=60 video_url ≈ ¥0.50 (input video tokens
# dominate; assistant JSON is ~1.5k tokens negligible).
PREDICT_DOUBAO_DIRECT_CNY = 0.50
# B3 (Phase 2) — generation leg per-second video upper bound. Seedance/Kling
# image-grounded video bill by output duration; a conservative ¥0.30/s keeps a
# buffer over current provider rates. Used by predict_generation_cost so the
# enqueue-time guard caps long clips before the worker spends real money.
PREDICT_VIDEO_SECOND_CNY = 0.30


def predict_generation_cost(kind: str, *, n_images: int = 0, video_seconds: float = 0.0) -> float:
    """Upper-bound ¥ prediction for a generation enqueue (B3).

    - image: ``n_images × PREDICT_SHOT_IMAGE_CNY``
    - video: ``video_seconds × PREDICT_VIDEO_SECOND_CNY``
    - composite/script: 0 (no external paid provider call at enqueue)

    Used by the enqueue-time cost_guard so retry×N + restart-reenqueue can't burn
    real money unbounded (the leg previously had zero spend guard). Charged once
    at enqueue, NOT per retry (retries reuse the already-committed budget).
    """
    if kind == "image":
        return max(0, n_images) * PREDICT_SHOT_IMAGE_CNY
    if kind == "video":
        return max(0.0, video_seconds) * PREDICT_VIDEO_SECOND_CNY
    return 0.0


def _run_cap() -> float:
    # Default ¥25 = runaway circuit breaker sized to hold one legal full film turn
    # (~¥18-20). See module docstring — raised from ¥3 on 2026-06-06 when run_id
    # became real (a ¥3 per-run cap would otherwise kill legit multi-shot turns).
    return float(os.environ.get("CASCADE_RUN_CAP_CNY", "25.0"))


def _user_day_cap() -> float:
    return float(os.environ.get("CASCADE_USER_DAY_CAP_CNY", "30.0"))


def _utc_day_start() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


async def cost_guard(user_id: str, run_id: str, predicted_cost_cny: float) -> None:
    run_consumed = await _run_cost(run_id)
    user_today_consumed = await _user_today_cost(user_id)
    run_cap = _run_cap()
    user_cap = _user_day_cap()

    if run_consumed + predicted_cost_cny > run_cap:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"run {run_id} cost {run_consumed + predicted_cost_cny:.2f} > cap {run_cap}",
        )
    if user_today_consumed + predicted_cost_cny > user_cap:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"user {user_id} day cost {user_today_consumed + predicted_cost_cny:.2f} > cap {user_cap}",
        )


async def cost_status(user_id: str, run_id: str) -> dict:
    run_cost = await _run_cost(run_id)
    user_cost = await _user_today_cost(user_id)
    run_cap = _run_cap()
    user_cap = _user_day_cap()
    run_pct = run_cost / run_cap if run_cap else 1.0
    user_pct = user_cost / user_cap if user_cap else 1.0
    return {
        "run_cost_cny": round(run_cost, 2),
        "run_cap_cny": run_cap,
        "run_pct": round(run_pct, 3),
        "user_today_cost_cny": round(user_cost, 2),
        "user_day_cap_cny": user_cap,
        "user_pct": round(user_pct, 3),
        "warn": run_pct + 1e-9 >= 0.8 or user_pct + 1e-9 >= 0.8,
        "day_boundary": "UTC calendar day",
    }


async def _run_cost(run_id: str) -> float:
    return await sum_generation_cost(run_id=run_id)


async def _user_today_cost(user_id: str) -> float:
    return await sum_generation_cost(user_id=user_id, since=_utc_day_start())
