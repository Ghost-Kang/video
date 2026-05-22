"""Eval runner — orchestrates one full eval pass.

Loads source contracts via the same path as `scripts/p2-4_run_real_urls.py`
(parses `real_urls_for_p2-4.md` v2.0 metadata + synthesizes contracts).
Calls `rewrite_for_niche`, runs mechanical checks, optionally calls the
LLM judge, parses founder qualitative signoff (if present), and aggregates
into an `EvalReport`.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import importlib
import importlib.util
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.eval import checks as checks_mod
from agent.cascade.eval.baselines import diff_baselines, load_latest_baseline, save_baseline
from agent.cascade.eval.judge import judge_one
from agent.cascade.eval.report import (
    EvalReport,
    PerCaseReport,
    PerNicheReport,
    aggregate_niche,
    aggregate_overall,
    compute_prompt_version_hash,
    render_markdown,
)
from agent.cascade.rewrite import rewrite_for_niche
from agent.llm_factory import current_model_name


NICHES = ("baomam_fushi", "yuer_richang", "jiating_chufang")


# We load the URL parser + contract synthesizer from the p2-4 runner so the
# two stay in lock-step. The runner script isn't importable as a module
# (lives under scripts/) so we add it to sys.path dynamically.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_p24_helpers():
    """Import parse_url_entries + synthesize_contract_from_entry lazily.

    Filename has a hyphen so it isn't a valid package name; load via
    importlib.util.spec_from_file_location and register in sys.modules
    so the URLEntry dataclass can resolve `__module__` at runtime.
    """
    name = "p2_4_runner"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / "p2-4_run_real_urls.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_URL_FILE = _REPO_ROOT / "docs" / "nexus" / "founder_log" / "real_urls_for_p2-4.md"


# --- Founder signoff parsing -----------------------------------------------

_SECTION_HEADER = re.compile(r"^##\s+(baomam_fushi|yuer_richang|jiating_chufang)\s*$")
_CASE_HEADER = re.compile(r"^###\s+#?(\d+)\b")
_CHECK_PASS = re.compile(r"^- \[x\]\s+我会把这个版本发出去")
_CHECK_FAIL = re.compile(r"^- \[x\]\s+还需要调整")


def parse_founder_qualitative(signoff_path: Path) -> dict[tuple[str, int], str]:
    """Parse the founder signoff doc and return {(niche, case_index): status}.

    status ∈ {pass, fail, not_reviewed}. Pass when the "通过" checkbox is
    ticked, fail when "还需要调整" is ticked, not_reviewed otherwise.
    """
    if not signoff_path.exists():
        return {}
    text = signoff_path.read_text(encoding="utf-8")
    out: dict[tuple[str, int], str] = {}
    current_niche: str | None = None
    current_idx: int | None = None
    seen_keys: set[tuple[str, int]] = set()
    state_pass = False
    state_fail = False

    def commit():
        if current_niche is not None and current_idx is not None:
            key = (current_niche, current_idx)
            if state_pass:
                out[key] = "pass"
            elif state_fail:
                out[key] = "fail"
            else:
                out[key] = "not_reviewed"
            seen_keys.add(key)

    for line in text.splitlines():
        m_section = _SECTION_HEADER.match(line.strip())
        if m_section:
            commit()
            current_niche = m_section.group(1)
            current_idx = None
            state_pass = False
            state_fail = False
            continue

        m_case = _CASE_HEADER.match(line.strip())
        if m_case:
            commit()
            current_idx = int(m_case.group(1))
            state_pass = False
            state_fail = False
            continue

        if _CHECK_PASS.match(line):
            state_pass = True
        if _CHECK_FAIL.match(line):
            state_fail = True

    commit()
    return out


# --- Main entry -------------------------------------------------------------


async def run_eval(
    niches: Iterable[str] = NICHES,
    *,
    mode: str | None = None,
    baseline_dir: Path | None = None,
    skip_judge: bool = False,
    signoff_path: Path | None = None,
) -> EvalReport:
    """Run one full eval pass and return the EvalReport.

    `mode` overrides CASCADE_REWRITE_UPSTREAM for this run. None keeps env value.
    `skip_judge` forces judge_one to return skipped (handy for offline runs).
    """
    helpers = _load_p24_helpers()
    entries_by_niche = helpers.parse_url_entries(_URL_FILE)

    signoff_map: dict[tuple[str, int], str] = {}
    if signoff_path is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        signoff_path = _REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-4_qualitative_signoff_{date_str}.md"
    signoff_map = parse_founder_qualitative(signoff_path)

    import os as _os

    if mode in {"fixture", "llm"}:
        _os.environ["CASCADE_REWRITE_UPSTREAM"] = mode
    upstream_mode = _os.environ.get("CASCADE_REWRITE_UPSTREAM", "fixture")

    per_niche_reports: list[PerNicheReport] = []
    for niche in niches:
        entries = entries_by_niche.get(niche, [])
        cases: list[PerCaseReport] = []
        for entry in entries:
            contract: CascadeAnalysisContract = helpers.synthesize_contract_from_entry(entry)
            extras = {
                "hook_pattern_id": entry.hook_pattern_id,
                "source_classification": entry.classification,
                "source_title": entry.title,
                "source_author": entry.author,
            }
            try:
                result = await rewrite_for_niche(contract, niche, extras=extras)
            except Exception as exc:
                # Record execution failure as a single failed check
                cases.append(_failure_case(entry, niche, exc))
                continue

            chks = checks_mod.run_checks(result, niche, source_title=entry.title)
            judge = {"skipped": True, "reason": "skip_judge=True"} if skip_judge else judge_one(
                result,
                niche=niche,
                source_title=entry.title,
                source_formula=contract.viral_analysis.replicable_formula,
            )
            founder_q = signoff_map.get((niche, entry.index), "not_reviewed")
            cases.append(
                PerCaseReport(
                    source_url=entry.url,
                    niche=niche,
                    rewrite_id=str(result.get("rewrite_id", "")),
                    hook_pattern_id=str(result.get("hook_pattern_id") or ""),
                    source_classification=str(result.get("source_classification") or "positive"),
                    source_title=entry.title,
                    checks=[
                        # Convert dataclass to dict-shaped record
                        {  # type: ignore[arg-type]
                            "name": c.name,
                            "passed": c.passed,
                            "detail": c.detail,
                            "mandatory": c.mandatory,
                        }
                        for c in chks
                    ],
                    mechanical_pass=checks_mod.is_passing(chks),
                    llm_judge=judge,
                    founder_qualitative=founder_q,
                    cost_cny=float(result.get("cost_cny") or 0.0),
                )
            )

        per_niche_reports.append(aggregate_niche(niche, cases))

    mech_rate, realism_avg, ad_risk = aggregate_overall(per_niche_reports)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prompt_hash = compute_prompt_version_hash()

    report = EvalReport(
        timestamp=timestamp,
        mode=upstream_mode,
        model=current_model_name(),
        prompt_version_hash=prompt_hash,
        niches=per_niche_reports,
        overall_mechanical_pass_rate=mech_rate,
        overall_judge_realism_avg=realism_avg,
        overall_judge_ad_risk_count=ad_risk,
    )

    baseline = load_latest_baseline(baseline_dir)
    report.delta_from_baseline = diff_baselines(report, baseline)
    return report


def _failure_case(entry, niche: str, exc: Exception) -> PerCaseReport:
    return PerCaseReport(
        source_url=entry.url,
        niche=niche,
        rewrite_id="",
        hook_pattern_id=entry.hook_pattern_id,
        source_classification=entry.classification,
        source_title=entry.title,
        checks=[
            {  # type: ignore[arg-type]
                "name": "execution",
                "passed": False,
                "detail": f"{exc.__class__.__name__}: {exc}",
                "mandatory": True,
            }
        ],
        mechanical_pass=False,
        llm_judge={"skipped": True, "reason": "rewrite_for_niche raised"},
        founder_qualitative="not_reviewed",
        cost_cny=0.0,
    )


__all__ = ["run_eval", "parse_founder_qualitative"]
