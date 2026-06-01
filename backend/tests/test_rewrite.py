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


# --- D3: generic (去 niche) 通用代笔 prompt + 一句话主题 ---


def test_generic_prompt_exists_with_topic_and_contract_placeholders():
    text = load_prompt("generic")
    assert len(text) > 200
    assert "硬约束" in text
    assert "{CONTRACT_JSON}" in text
    assert "{TOPIC}" in text  # 主题占位符,通用路径核心


def test_generic_fixture_rewrite_runs_and_respects_topic():
    """generic niche 走 fixture 路径不抛(不再 KeyError on visual_palette),
    且用户一句话主题注入到改写稿的 rationale note。"""
    # reuse any existing fixture contract as the source
    src = _fixture_paths("baomam_fushi")[0]
    contract = _load_contract(src)
    result = asyncio.run(
        rewrite_for_niche(contract, "generic", extras={"topic": "三分钟搞定的减脂早餐"})
    )
    assert result["niche"] == "generic"
    assert 3 <= len(result["shots"]) <= 5
    assert 80 <= len(result["script_markdown"]) <= 400  # D5 bound (台词+画面合并)
    # topic surfaced in the rationale marker
    assert "三分钟搞定的减脂早餐" in result["script_markdown"]
    # no forbidden brand/jargon terms leaked
    text = _all_text(result)
    for term in FORBIDDEN_TERMS:
        assert term not in text, f"forbidden term leaked: {term}"


def test_generic_fixture_rewrite_without_topic_is_fine():
    """无主题(topic 缺省)也不应抛——沿用原片主题的中性兜底。"""
    src = _fixture_paths("yuer_richang")[0]
    contract = _load_contract(src)
    result = asyncio.run(rewrite_for_niche(contract, "generic"))
    assert result["niche"] == "generic"
    assert 3 <= len(result["shots"]) <= 5


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


def test_h8_matches_scene_based_emotional_resonance_p5_1a():
    """P5-1a 2026-05-23: H8 should fire on scene-based emotional resonance
    LLM rewrites (凌晨/半夜 + 哭闹/醒 + 第N次) — not just literal emotion
    words. Sources: p2-6_baseline_20260523T054123Z.json yuer_richang
    failing cases where LLM self_check correctly tagged H8 but the
    original strict regex missed."""
    # Real LLM outputs that previously failed hook_p0_compliance
    assert "H8" in hook_taxonomy.detect_hooks_in_text("凌晨三点,这是他今晚第四次醒了")
    assert "H8" in hook_taxonomy.detect_hooks_in_text("凌晨三点，他又哭了，这是今晚第五次")
    # New scene patterns
    assert "H8" in hook_taxonomy.detect_hooks_in_text("半夜两点又醒了")
    assert "H8" in hook_taxonomy.detect_hooks_in_text("我快崩溃了")
    assert "H8" in hook_taxonomy.detect_hooks_in_text("这是第三次哭")
    # False-positive guards — these should NOT match H8
    assert "H8" not in hook_taxonomy.detect_hooks_in_text("一周不重样 7 道辅食")
    assert "H8" not in hook_taxonomy.detect_hooks_in_text("千万别用宽油")
    assert "H8" not in hook_taxonomy.detect_hooks_in_text("我女儿今天又来厨房捣乱")
    assert "H8" not in hook_taxonomy.detect_hooks_in_text("做了三次才成功")


def test_p5_2_brand_restriction_present_in_all_niche_prompts():
    """P5-2 2026-05-23: each niche prompt must mention the strengthened
    brand/IP restriction with both ❌ category examples AND the
    output-final-check directive. Locks the prompt structure so a future
    refactor doesn't silently drop the广告法 safeguard.

    Source: judge LLM caught brand placement (安抚海马玩具 / 《晚安月亮》绘本)
    on 2026-05-23 yuer baseline; existing "严禁品牌名" line was too abstract.
    """
    import pathlib
    prompts_dir = pathlib.Path(__file__).resolve().parent.parent / "src" / "agent" / "prompts"
    for niche in ("baomam_fushi", "yuer_richang", "jiating_chufang"):
        text = (prompts_dir / f"rewrite_{niche}.md").read_text(encoding="utf-8")
        # Must explicitly reference 广告法 §10 + §16
        assert "广告法 §10 + §16" in text, f"{niche}: missing 广告法 reference"
        # Must contain ❌ + ✅ contrastive examples (concrete > abstract)
        assert "❌" in text and "✅" in text, f"{niche}: missing ❌/✅ contrastive examples"
        # Must include the pre-output self-check directive
        assert "输出前最后一道自检" in text, f"{niche}: missing 自检 directive"
        # Must list at least 3 ❌ categories (品牌 / 商品 / IP / 餐厅 / 作品 etc.)
        bad_count = text.count("❌")
        assert bad_count >= 3, f"{niche}: only {bad_count} ❌ examples; expected ≥3"


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
