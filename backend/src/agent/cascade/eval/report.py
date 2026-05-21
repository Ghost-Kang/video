"""EvalReport Pydantic schema + markdown renderer."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


class CheckRecord(BaseModel):
    """Serializable mirror of eval.checks.CheckResult."""

    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    detail: str = ""
    mandatory: bool = False


class PerCaseReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str
    niche: str
    rewrite_id: str
    hook_pattern_id: str = ""
    source_classification: str = "positive"
    source_title: str = ""
    checks: list[CheckRecord]
    mechanical_pass: bool
    llm_judge: dict[str, Any] = Field(default_factory=dict)
    founder_qualitative: str = "not_reviewed"  # pass | fail | not_reviewed
    cost_cny: float = 0.0


class PerNicheReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niche: str
    cases: list[PerCaseReport]
    mechanical_pass_rate: float = 0.0
    judge_realism_avg: float = 0.0
    judge_kept_formula_yes_rate: float = 0.0
    judge_ad_risk_count: int = 0
    founder_pass_rate: float = 0.0


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str  # UTC ISO
    mode: str  # fixture | llm
    model: str  # e.g. gemini-3-flash-preview
    prompt_version_hash: str  # sha256[:16] of rewrite_*.md
    niches: list[PerNicheReport]
    overall_mechanical_pass_rate: float = 0.0
    overall_judge_realism_avg: float = 0.0
    overall_judge_ad_risk_count: int = 0
    delta_from_baseline: dict[str, Any] = Field(default_factory=dict)


def compute_prompt_version_hash() -> str:
    """sha256[:16] over the concatenated bytes of all rewrite_*.md prompts."""
    h = hashlib.sha256()
    for path in sorted(_PROMPTS_DIR.glob("rewrite_*.md")):
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


# --- Aggregation helpers ----------------------------------------------------


def aggregate_niche(niche: str, cases: list[PerCaseReport]) -> PerNicheReport:
    if not cases:
        return PerNicheReport(niche=niche, cases=[])
    n = len(cases)
    mech_passes = sum(1 for c in cases if c.mechanical_pass)
    judged = [c for c in cases if not c.llm_judge.get("skipped", True)]
    realism_avg = (
        sum(int(c.llm_judge.get("realism_1to5", 3)) for c in judged) / len(judged)
        if judged
        else 0.0
    )
    kept_yes = sum(1 for c in judged if c.llm_judge.get("kept_formula") == "yes")
    kept_rate = kept_yes / len(judged) if judged else 0.0
    ad_risks = sum(1 for c in cases if c.llm_judge.get("ad_risk") == "yes")
    founder_pass = sum(1 for c in cases if c.founder_qualitative == "pass")
    founder_total = sum(1 for c in cases if c.founder_qualitative != "not_reviewed")
    return PerNicheReport(
        niche=niche,
        cases=cases,
        mechanical_pass_rate=mech_passes / n,
        judge_realism_avg=round(realism_avg, 2),
        judge_kept_formula_yes_rate=round(kept_rate, 2),
        judge_ad_risk_count=ad_risks,
        founder_pass_rate=(founder_pass / founder_total) if founder_total else 0.0,
    )


def aggregate_overall(niches: list[PerNicheReport]) -> tuple[float, float, int]:
    all_cases = [c for n in niches for c in n.cases]
    if not all_cases:
        return 0.0, 0.0, 0
    mech_rate = sum(1 for c in all_cases if c.mechanical_pass) / len(all_cases)
    judged = [c for c in all_cases if not c.llm_judge.get("skipped", True)]
    realism = (
        sum(int(c.llm_judge.get("realism_1to5", 3)) for c in judged) / len(judged)
        if judged
        else 0.0
    )
    ad_risk = sum(1 for c in all_cases if c.llm_judge.get("ad_risk") == "yes")
    return round(mech_rate, 2), round(realism, 2), ad_risk


# --- Markdown rendering -----------------------------------------------------


def render_markdown(report: EvalReport) -> str:
    lines = [
        "# P2-6 Eval Report",
        "",
        f"**Timestamp**: {report.timestamp}",
        f"**Mode**: {report.mode}",
        f"**Model**: {report.model}",
        f"**Prompt version hash**: `{report.prompt_version_hash}`",
        "",
        "## Overall",
        "",
        f"- Mechanical pass rate: **{report.overall_mechanical_pass_rate:.2%}**",
        f"- Judge realism avg: {report.overall_judge_realism_avg:.2f} / 5",
        f"- Judge ad-risk hits: {report.overall_judge_ad_risk_count}",
    ]

    if report.delta_from_baseline:
        lines.append("")
        lines.append("### Delta from baseline")
        lines.append("")
        for k, v in report.delta_from_baseline.items():
            lines.append(f"- `{k}`: {v}")

    for niche_report in report.niches:
        lines += [
            "",
            f"## {niche_report.niche}",
            "",
            f"- Mechanical pass rate: **{niche_report.mechanical_pass_rate:.2%}** "
            f"({sum(1 for c in niche_report.cases if c.mechanical_pass)}/{len(niche_report.cases)})",
            f"- Judge realism avg: {niche_report.judge_realism_avg:.2f}",
            f"- Judge kept_formula=yes rate: {niche_report.judge_kept_formula_yes_rate:.2%}",
            f"- Judge ad-risk hits: {niche_report.judge_ad_risk_count}",
            f"- Founder qualitative pass rate: {niche_report.founder_pass_rate:.2%}",
            "",
        ]
        for case in niche_report.cases:
            mark = "✅" if case.mechanical_pass else "❌"
            judge_summary = (
                "(skipped)"
                if case.llm_judge.get("skipped")
                else f"realism={case.llm_judge.get('realism_1to5','?')}/5, "
                     f"kept={case.llm_judge.get('kept_formula','?')}, "
                     f"ad_risk={case.llm_judge.get('ad_risk','?')}"
            )
            fails = [c.name for c in case.checks if not c.passed]
            fail_text = f" failed: {fails}" if fails else ""
            lines.append(
                f"- {mark} {case.source_url} `[{case.source_classification}]` "
                f"hooks=`{case.hook_pattern_id or '?'}` · judge: {judge_summary} · "
                f"founder: `{case.founder_qualitative}`{fail_text}"
            )
    return "\n".join(lines) + "\n"
