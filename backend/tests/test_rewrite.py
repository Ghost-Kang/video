"""Smoke tests for rewrite_for_niche (P1-3).

Loads each of the 15 fixture contracts under cascade/fixtures/rewrite_smoke,
runs the fixture-mode rewrite, and applies the mechanical acceptance checks
from docs/nexus/handoff/claude_prompts_P1-3.md §3:

  - script length in [80, 600]
  - shots has 3-5 items
  - no forbidden brand/jargon terms in script or shots
  - confidence >= 0.5
  - script_markdown carries the "保留" + "改" rationale marker
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent.cascade import hook_taxonomy
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.rewrite import FORBIDDEN_TERMS, load_prompt, rewrite_for_niche


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "src" / "agent" / "cascade" / "fixtures" / "rewrite_smoke"
NICHES = ("baomam_fushi", "yuer_richang", "jiating_chufang")


def _fixture_paths(niche: str) -> list[Path]:
    paths = sorted((FIXTURES_ROOT / niche).glob("ref_*.json"))
    assert len(paths) >= 5, f"{niche}: expected ≥5 fixtures, got {len(paths)}"
    return paths


def _load_contract(path: Path) -> CascadeAnalysisContract:
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Strip the underscore-prefixed provenance fields the adapter would
    # normally drop — the contract model uses extra="forbid".
    cleaned = {k: v for k, v in raw.items() if not k.startswith("_")}
    return CascadeAnalysisContract.model_validate(cleaned)


# --- Per-niche fixture coverage and prompt presence ---


@pytest.mark.parametrize("niche", NICHES)
def test_each_niche_has_at_least_five_fixtures(niche):
    paths = _fixture_paths(niche)
    assert len(paths) >= 5


@pytest.mark.parametrize("niche", NICHES)
def test_prompt_file_exists_and_non_empty(niche):
    text = load_prompt(niche)
    assert len(text) > 200
    # Sanity: the niche-specific hardcoded constraint section is present.
    assert "硬约束" in text
    assert "{CONTRACT_JSON}" in text


# --- Mechanical acceptance checks (the §3 bar) ---


def _all_text(result: dict) -> str:
    parts = [result.get("script_markdown", "")]
    for shot in result.get("shots", []):
        parts.append(shot.get("dialogue", ""))
        parts.append(shot.get("visual", ""))
    return "\n".join(parts)


@pytest.mark.parametrize("niche", NICHES)
def test_mechanical_acceptance_per_niche(niche):
    """For each of the 5 fixtures in a niche, count passes — require ≥4/5.

    Original 5 checks from claude_prompts_P1-3.md §3.
    """
    paths = _fixture_paths(niche)
    passes = 0
    failures: list[str] = []
    for path in paths:
        contract = _load_contract(path)
        result = asyncio.run(rewrite_for_niche(contract, niche))
        problems: list[str] = []

        script = result.get("script_markdown", "")
        if not (80 <= len(script) <= 600):
            problems.append(f"script length {len(script)} not in [80, 600]")

        shots = result.get("shots", [])
        if not (3 <= len(shots) <= 5):
            problems.append(f"shots count {len(shots)} not in [3, 5]")

        text = _all_text(result)
        leaked = [term for term in FORBIDDEN_TERMS if term in text]
        if leaked:
            problems.append(f"forbidden terms leaked: {leaked}")

        if result.get("confidence", 0.0) < 0.5:
            problems.append(f"confidence {result.get('confidence')} < 0.5")

        if "保留" not in script or "改" not in script:
            problems.append("script_markdown missing 保留/改 rationale marker")

        if problems:
            failures.append(f"{path.name}: {problems}")
        else:
            passes += 1

    assert passes >= 4, (
        f"{niche}: only {passes}/{len(paths)} fixtures passed mechanical checks. "
        f"Failures:\n" + "\n".join(failures)
    )


# --- Founder-curated checks (p2-4_hooks_taxonomy.md §4) ---------------------


@pytest.mark.parametrize("niche", NICHES)
def test_visual_diversity_per_niche(niche):
    """#6: pairwise token overlap between shot visuals ≤ 50% — require ≥4/5."""
    paths = _fixture_paths(niche)
    passes = 0
    failures: list[str] = []
    for path in paths:
        contract = _load_contract(path)
        result = asyncio.run(
            rewrite_for_niche(
                contract,
                niche,
                extras={"source_title": "", "source_classification": "positive"},
            )
        )
        ok, detail = hook_taxonomy.visual_diversity(result)
        if ok:
            passes += 1
        else:
            failures.append(f"{path.name}: {detail}")
    assert passes >= 4, f"{niche} visual_diversity: {passes}/{len(paths)}. Fails:\n" + "\n".join(failures)


@pytest.mark.parametrize("niche", NICHES)
def test_hook_p0_compliance_per_niche(niche):
    """#8 (mandatory): shot 1 hits at least one P0 hook for this niche — require ≥4/5."""
    paths = _fixture_paths(niche)
    passes = 0
    failures: list[str] = []
    for path in paths:
        contract = _load_contract(path)
        result = asyncio.run(
            rewrite_for_niche(
                contract,
                niche,
                extras={"source_title": "", "source_classification": "positive"},
            )
        )
        ok, detail = hook_taxonomy.hook_p0_compliance(result, niche)
        if ok:
            passes += 1
        else:
            failures.append(f"{path.name}: {detail}")
    assert passes >= 4, f"{niche} hook_p0_compliance: {passes}/{len(paths)}. Fails:\n" + "\n".join(failures)


@pytest.mark.parametrize("niche", NICHES)
def test_negative_hook_absence_per_niche(niche):
    """#10: niche's negative hooks must not fire — require ≥4/5."""
    paths = _fixture_paths(niche)
    passes = 0
    failures: list[str] = []
    for path in paths:
        contract = _load_contract(path)
        result = asyncio.run(rewrite_for_niche(contract, niche))
        ok, detail = hook_taxonomy.negative_hook_absence(result, niche)
        if ok:
            passes += 1
        else:
            failures.append(f"{path.name}: {detail}")
    assert passes >= 4, f"{niche} negative_hook_absence: {passes}/{len(paths)}. Fails:\n" + "\n".join(failures)


def test_dish_anchor_for_jiating():
    """F-3-a: jiating shot 1 must include a 菜名 — require ≥4/5."""
    paths = _fixture_paths("jiating_chufang")
    passes = 0
    failures: list[str] = []
    for path in paths:
        contract = _load_contract(path)
        result = asyncio.run(rewrite_for_niche(contract, "jiating_chufang"))
        ok, detail = hook_taxonomy.dish_anchor_present(result, "jiating_chufang")
        if ok:
            passes += 1
        else:
            failures.append(f"{path.name}: {detail}")
    assert passes >= 4, f"jiating dish_anchor: {passes}/{len(paths)}. Fails:\n" + "\n".join(failures)


def test_nutrient_category_for_baomam():
    """#7 (mandatory): baomam rewrite must not introduce out-of-category foods."""
    paths = _fixture_paths("baomam_fushi")
    passes = 0
    failures: list[str] = []
    # Use source titles that hint at one nutrient category
    title_hints = ["一岁宝宝一周辅食蔬菜不重样", "六月龄宝宝肉泥添加", "宝宝一周米糊不重样"]
    for i, path in enumerate(paths):
        contract = _load_contract(path)
        title = title_hints[i % len(title_hints)]
        result = asyncio.run(
            rewrite_for_niche(
                contract,
                "baomam_fushi",
                extras={"source_title": title, "source_classification": "positive"},
            )
        )
        ok, detail = hook_taxonomy.nutrient_category_consistency(result, "baomam_fushi", title)
        if ok:
            passes += 1
        else:
            failures.append(f"{path.name} (source={title!r}): {detail}")
    assert passes >= 4, f"baomam nutrient_category: {passes}/{len(paths)}. Fails:\n" + "\n".join(failures)


def test_hook_taxonomy_detects_known_examples():
    """Unit test for hook_taxonomy detectors."""
    assert "H1" in hook_taxonomy.detect_hooks_in_text("六月龄宝宝辅食添加的顺序")
    assert "H2" in hook_taxonomy.detect_hooks_in_text("一周辅食不重样")
    assert "H4" in hook_taxonomy.detect_hooks_in_text("餐厅 88 我做 12")
    assert "H8" in hook_taxonomy.detect_hooks_in_text("当妈以后才发现")
    assert "H9" in hook_taxonomy.detect_hooks_in_text("为什么牛肉要逆纹切")
    assert "H1" not in hook_taxonomy.detect_hooks_in_text("新手妈妈带娃日记")


# --- API surface checks ---


def test_unsupported_niche_raises():
    contract = _load_contract(_fixture_paths("baomam_fushi")[0])
    with pytest.raises(ValueError):
        asyncio.run(rewrite_for_niche(contract, "bogus"))


def test_rewrite_result_shape_validates_via_service_model():
    """The dict we return must pass through RewriteResult.model_validate without help."""
    from agent.cascade.rewrite_service import RewriteResult

    contract = _load_contract(_fixture_paths("baomam_fushi")[0])
    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    validated = RewriteResult.model_validate(result)
    assert validated.rewrite_id.startswith("rw_")
    assert validated.niche == "baomam_fushi"
    assert 3 <= len(validated.shots) <= 5
