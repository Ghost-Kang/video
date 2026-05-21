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
    """For each of the 5 fixtures in a niche, count passes — require ≥4/5."""
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
