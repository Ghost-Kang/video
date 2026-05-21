"""Pre-call cost prediction for Cascade services."""

from __future__ import annotations

from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.cost_guard import PREDICT_REWRITE_CNY


def predict_rewrite_cost(contract: CascadeAnalysisContract, niche: str) -> float:
    scene_factor = max(1, min(len(contract.scenes), 5)) * 0.08
    niche_factor = 0.1 if niche else 0.0
    return round(PREDICT_REWRITE_CNY + scene_factor + niche_factor, 2)
