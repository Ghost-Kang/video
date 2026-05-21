"""Mechanical checks for the P2-6 eval harness.

Single source: composes the 10 standard checks defined in
`p2-4_hooks_taxonomy.md §4` + the original P1-3 §3 checks + the
jiating-only 菜名 anchor (F-3-a). Same shape every caller (runner,
test, eval) consumes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agent.cascade import hook_taxonomy
from agent.cascade.rewrite import FORBIDDEN_TERMS


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    mandatory: bool = False


# IDs that map onto the taxonomy doc §4 numbering for traceability.
MANDATORY_CHECK_NAMES: frozenset[str] = frozenset({
    "nutrient_category_consistency",  # #7
    "hook_p0_compliance",              # #8
    "dish_anchor_present",             # F-3-a (jiating only; bypassed elsewhere)
})


def run_checks(result: Mapping[str, Any], niche: str, source_title: str = "") -> list[CheckResult]:
    """Return ordered list of CheckResult for one rewrite output."""
    out: list[CheckResult] = []
    script = result.get("script_markdown", "") or ""
    shots = result.get("shots", []) or []
    classification = str(result.get("source_classification") or "positive")

    out.append(CheckResult("script_length_80_600", 80 <= len(script) <= 600, f"len={len(script)}"))
    out.append(CheckResult("shot_count_3_5", 3 <= len(shots) <= 5, f"count={len(shots)}"))

    text_all = script + "\n" + "\n".join(
        (s.get("dialogue", "") + " " + s.get("visual", "")) for s in shots
    )
    leaked = [t for t in FORBIDDEN_TERMS if t in text_all]
    out.append(CheckResult("no_forbidden_terms", not leaked, f"leaked={leaked}"))

    confidence = float(result.get("confidence", 0.0) or 0.0)
    if classification == "negative_ref":
        passed = 0.4 <= confidence <= 0.6
        out.append(CheckResult("confidence_in_range", passed, f"conf={confidence:.2f} (negative_ref cap)"))
    else:
        out.append(CheckResult("confidence_ge_0_5", confidence >= 0.5, f"conf={confidence:.2f}"))

    out.append(CheckResult(
        "rationale_marker_present",
        "保留" in script and "改" in script,
        "checked '保留' + '改' in script",
    ))

    # Taxonomy §4 #6
    passed, detail = hook_taxonomy.visual_diversity(result)
    out.append(CheckResult("visual_diversity_score", passed, detail))

    # Taxonomy §4 #7 (mandatory for baomam)
    passed, detail = hook_taxonomy.nutrient_category_consistency(result, niche, source_title)
    out.append(CheckResult(
        "nutrient_category_consistency",
        passed,
        detail,
        mandatory=(niche == "baomam_fushi"),
    ))

    # Taxonomy §4 #8 (mandatory)
    passed, detail = hook_taxonomy.hook_p0_compliance(result, niche)
    out.append(CheckResult("hook_p0_compliance", passed, detail, mandatory=True))

    # Taxonomy §4 #9
    passed, detail = hook_taxonomy.hook_diversity(result)
    out.append(CheckResult("hook_diversity", passed, detail))

    # Taxonomy §4 #10
    passed, detail = hook_taxonomy.negative_hook_absence(result, niche)
    out.append(CheckResult("negative_hook_absence", passed, detail))

    # F-3-a (jiating mandatory; n/a elsewhere)
    passed, detail = hook_taxonomy.dish_anchor_present(result, niche)
    out.append(CheckResult(
        "dish_anchor_present",
        passed,
        detail,
        mandatory=(niche == "jiating_chufang"),
    ))

    return out


def pass_count(checks: list[CheckResult]) -> int:
    return sum(1 for c in checks if c.passed)


def is_passing(checks: list[CheckResult], standard_threshold: int = 8) -> bool:
    """Bar (per p2-4_hooks_taxonomy.md §4): ≥ standard_threshold/10 standard checks
    pass AND every mandatory check passes.
    """
    standard = [c for c in checks if c.name != "dish_anchor_present"]
    standard_passes = sum(1 for c in standard if c.passed)
    mandatory_ok = all(c.passed for c in checks if c.mandatory)
    return standard_passes >= standard_threshold and mandatory_ok
