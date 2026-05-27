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

CASCADE_RUN_CAP_CNY = ¥3.0 (env override) still accommodates a single
analysis + rewrite + shot pass (¥1.20 + ¥1.00 + ¥1.50 = ¥3.70 ← exceeds
¥3.0 cap; raise cap to ¥4.5 via env if first concierge first-run trips).
Per-user-day cap ¥30 = ~25 full runs/day, ample for Phase 1.

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


def _run_cap() -> float:
    return float(os.environ.get("CASCADE_RUN_CAP_CNY", "3.0"))


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
