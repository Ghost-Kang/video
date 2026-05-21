"""Baseline persistence + diff for the P2-6 eval harness.

Baselines live under `docs/nexus/founder_log/p2-6_baseline_<UTC>.json`.
They're plain JSON serializations of `EvalReport`. Loading the latest =
glob the dir and pick the file with the highest sortable timestamp.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.cascade.eval.report import EvalReport


REPO_ROOT = Path(__file__).resolve().parents[5]
BASELINES_DIR = REPO_ROOT / "docs" / "nexus" / "founder_log"


def save_baseline(report: EvalReport, dir_override: Path | None = None) -> Path:
    target_dir = dir_override or BASELINES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp_safe = report.timestamp.replace(":", "").replace("-", "").replace(".", "_")
    path = target_dir / f"p2-6_baseline_{timestamp_safe}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_latest_baseline(dir_override: Path | None = None) -> EvalReport | None:
    source_dir = dir_override or BASELINES_DIR
    candidates = sorted(source_dir.glob("p2-6_baseline_*.json"))
    if not candidates:
        return None
    raw = candidates[-1].read_text(encoding="utf-8")
    return EvalReport.model_validate_json(raw)


def diff_baselines(current: EvalReport, baseline: EvalReport | None) -> dict[str, Any]:
    """Return per-metric delta. Negative = regression."""
    if baseline is None:
        return {"baseline_status": "first-ever"}

    delta: dict[str, Any] = {
        "baseline_timestamp": baseline.timestamp,
        "mechanical_pass_rate": round(
            current.overall_mechanical_pass_rate - baseline.overall_mechanical_pass_rate, 4
        ),
        "judge_realism_avg": round(
            current.overall_judge_realism_avg - baseline.overall_judge_realism_avg, 4
        ),
        "judge_ad_risk_count": current.overall_judge_ad_risk_count - baseline.overall_judge_ad_risk_count,
    }

    by_niche_current = {n.niche: n for n in current.niches}
    by_niche_base = {n.niche: n for n in baseline.niches}
    per_niche: dict[str, dict[str, float | int]] = {}
    for niche in set(by_niche_current) | set(by_niche_base):
        c = by_niche_current.get(niche)
        b = by_niche_base.get(niche)
        if c is None:
            per_niche[niche] = {"status": "removed"}
            continue
        if b is None:
            per_niche[niche] = {"status": "new", "mechanical_pass_rate": c.mechanical_pass_rate}
            continue
        per_niche[niche] = {
            "mechanical_pass_rate": round(c.mechanical_pass_rate - b.mechanical_pass_rate, 4),
            "judge_realism_avg": round(c.judge_realism_avg - b.judge_realism_avg, 4),
            "judge_ad_risk_count": c.judge_ad_risk_count - b.judge_ad_risk_count,
            "founder_pass_rate": round(c.founder_pass_rate - b.founder_pass_rate, 4),
        }
    delta["per_niche"] = per_niche
    return delta
