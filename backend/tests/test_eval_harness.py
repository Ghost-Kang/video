"""Tests for the P2-6 eval harness."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent.cascade.eval import (
    EvalReport,
    PerCaseReport,
    PerNicheReport,
    diff_baselines,
    judge_one,
    load_latest_baseline,
    render_markdown,
    run_checks,
    run_eval,
    save_baseline,
)
from agent.cascade.eval.checks import CheckResult, is_passing
from agent.cascade.eval.runner import parse_founder_qualitative


# --- run_checks fires correctly ---------------------------------------------


def _stub_result(**overrides) -> dict:
    base = {
        "script_markdown": (
            "### 改写脚本\n<!-- 保留:X | 改:Y -->\n"
            "1. 一岁宝宝一周辅食不重样,今天换这道试试\n"
            "   画面:暖色家庭厨房俯拍,餐椅特写,食材碗摆台\n"
            "2. 木质砧板特写,妈妈手切食材\n"
            "   画面:木质砧板特写,妈妈手切食材,自然光\n"
            "3. 蒸锅侧拍,蒸汽升腾,食材若隐若现\n"
            "   画面:蒸锅侧拍,蒸汽升腾\n"
            "4. 宝宝面部特写,小手抓勺\n"
            "   画面:宝宝面部特写,小手抓勺"
        ),
        "shots": [
            {"shot_index": 1, "dialogue": "一岁宝宝一周辅食不重样,今天换这道试试", "visual": "暖色家庭厨房俯拍,餐椅特写,食材碗摆台"},
            {"shot_index": 2, "dialogue": "妈妈手切食材", "visual": "木质砧板特写,自然光"},
            {"shot_index": 3, "dialogue": "蒸锅侧拍,蒸汽升腾", "visual": "蒸锅侧拍,蒸汽升腾"},
            {"shot_index": 4, "dialogue": "宝宝面部特写,小手抓勺", "visual": "宝宝面部特写,小手抓勺"},
        ],
        "confidence": 0.85,
        "source_classification": "positive",
        "hook_pattern_id": "H1+H2",
    }
    base.update(overrides)
    return base


def test_run_checks_baomam_passes_well():
    result = _stub_result()
    chks = run_checks(result, "baomam_fushi", source_title="一岁宝宝一周辅食蔬菜不重样")
    by_name = {c.name: c for c in chks}
    assert by_name["script_length_80_600"].passed
    assert by_name["shot_count_3_5"].passed
    assert by_name["hook_p0_compliance"].passed
    assert by_name["hook_p0_compliance"].mandatory
    assert is_passing(chks)


def test_run_checks_fails_when_p0_missing():
    result = _stub_result()
    result["shots"][0]["dialogue"] = "今天分享个家常做法"  # no H1/H2 anchor
    chks = run_checks(result, "baomam_fushi", source_title="蔬菜辅食")
    by_name = {c.name: c for c in chks}
    assert not by_name["hook_p0_compliance"].passed
    assert not is_passing(chks)  # mandatory missing


def test_run_checks_jiating_requires_dish():
    result = _stub_result()
    # Use a jiating-shaped result without dish name
    result["shots"][0]["dialogue"] = "餐厅 88,在家成本不到 15"  # H4 yes, no dish
    chks = run_checks(result, "jiating_chufang")
    by_name = {c.name: c for c in chks}
    assert by_name["hook_p0_compliance"].passed  # H4 fires
    assert not by_name["dish_anchor_present"].passed


# --- judge skips without API key -------------------------------------------


def test_judge_skips_without_api_key(monkeypatch):
    def missing_model():
        raise RuntimeError("LLM_PROVIDER=doubao but ARK_API_KEY missing")

    monkeypatch.setattr("agent.llm_factory.get_chat_model", missing_model)
    result = judge_one(_stub_result(), niche="baomam_fushi")
    assert result.get("skipped") is True
    assert "ARK_API_KEY missing" in result.get("reason", "")


def test_judge_skips_under_env_override(monkeypatch):
    monkeypatch.setenv("CASCADE_EVAL_JUDGE", "skip")
    monkeypatch.setattr(
        "agent.llm_factory.get_chat_model",
        lambda: (_ for _ in ()).throw(RuntimeError("should not load model")),
    )
    result = judge_one(_stub_result(), niche="baomam_fushi")
    assert result.get("skipped") is True


# --- Report serialization round-trip ---------------------------------------


def _stub_case(niche: str = "baomam_fushi", url: str = "https://example.com/v1") -> PerCaseReport:
    return PerCaseReport(
        source_url=url,
        niche=niche,
        rewrite_id="rw_test",
        hook_pattern_id="H1+H2",
        source_classification="positive",
        source_title="test title",
        checks=[
            {"name": "shot_count_3_5", "passed": True, "detail": "count=4", "mandatory": False},  # type: ignore[arg-type]
        ],
        mechanical_pass=True,
        llm_judge={"skipped": True, "reason": "test"},
        founder_qualitative="not_reviewed",
        cost_cny=0.0,
    )


def test_eval_report_json_round_trip():
    report = EvalReport(
        timestamp="2026-05-21T12:00:00Z",
        mode="fixture",
        model="gemini-3-flash-preview",
        prompt_version_hash="deadbeefcafef00d",
        niches=[
            PerNicheReport(
                niche="baomam_fushi",
                cases=[_stub_case()],
                mechanical_pass_rate=1.0,
            )
        ],
        overall_mechanical_pass_rate=1.0,
    )
    raw = report.model_dump_json()
    restored = EvalReport.model_validate_json(raw)
    assert restored.timestamp == report.timestamp
    assert restored.niches[0].cases[0].source_url == "https://example.com/v1"


# --- baseline diff calc -----------------------------------------------------


def test_diff_returns_first_ever_marker():
    report = EvalReport(
        timestamp="2026-05-21T12:00:00Z",
        mode="fixture",
        model="x",
        prompt_version_hash="abc",
        niches=[],
    )
    delta = diff_baselines(report, None)
    assert delta == {"baseline_status": "first-ever"}


def test_diff_computes_metric_deltas():
    baseline = EvalReport(
        timestamp="2026-05-20T12:00:00Z",
        mode="fixture",
        model="x",
        prompt_version_hash="abc",
        niches=[PerNicheReport(niche="baomam_fushi", cases=[], mechanical_pass_rate=0.8)],
        overall_mechanical_pass_rate=0.8,
        overall_judge_realism_avg=3.5,
        overall_judge_ad_risk_count=1,
    )
    current = EvalReport(
        timestamp="2026-05-21T12:00:00Z",
        mode="fixture",
        model="x",
        prompt_version_hash="abc",
        niches=[PerNicheReport(niche="baomam_fushi", cases=[], mechanical_pass_rate=1.0)],
        overall_mechanical_pass_rate=1.0,
        overall_judge_realism_avg=4.0,
        overall_judge_ad_risk_count=0,
    )
    delta = diff_baselines(current, baseline)
    assert delta["mechanical_pass_rate"] > 0
    assert delta["judge_realism_avg"] > 0
    assert delta["judge_ad_risk_count"] == -1
    assert delta["per_niche"]["baomam_fushi"]["mechanical_pass_rate"] > 0


def test_save_load_baseline_round_trip(tmp_path):
    report = EvalReport(
        timestamp="2026-05-21T12:00:00Z",
        mode="fixture",
        model="x",
        prompt_version_hash="abc",
        niches=[],
    )
    saved = save_baseline(report, dir_override=tmp_path)
    assert saved.exists()
    loaded = load_latest_baseline(dir_override=tmp_path)
    assert loaded is not None
    assert loaded.timestamp == "2026-05-21T12:00:00Z"


# --- markdown rendering -----------------------------------------------------


def test_render_markdown_contains_key_sections():
    report = EvalReport(
        timestamp="2026-05-21T12:00:00Z",
        mode="fixture",
        model="x",
        prompt_version_hash="abc",
        niches=[
            PerNicheReport(
                niche="baomam_fushi",
                cases=[_stub_case()],
                mechanical_pass_rate=1.0,
            )
        ],
        overall_mechanical_pass_rate=1.0,
    )
    md = render_markdown(report)
    assert "# P2-6 Eval Report" in md
    assert "Mechanical pass rate" in md
    assert "baomam_fushi" in md


# --- founder qualitative parser --------------------------------------------


def test_parse_founder_qualitative_extracts_ticks(tmp_path):
    doc = tmp_path / "signoff.md"
    doc.write_text(
        "# P2-4 signoff\n\n"
        "## baomam_fushi\n\n"
        "### #1 some title\n\n"
        "- [x] 我会把这个版本发出去 — 通过\n"
        "- [ ] 还需要调整\n\n"
        "### #2 another\n\n"
        "- [ ] 我会把这个版本发出去 — 通过\n"
        "- [x] 还需要调整\n\n"
        "## yuer_richang\n\n"
        "### #1 yet\n\n"
        "- [ ] 我会把这个版本发出去 — 通过\n"
        "- [ ] 还需要调整\n",
        encoding="utf-8",
    )
    result = parse_founder_qualitative(doc)
    assert result[("baomam_fushi", 1)] == "pass"
    assert result[("baomam_fushi", 2)] == "fail"
    assert result[("yuer_richang", 1)] == "not_reviewed"


# --- end-to-end run_eval ---------------------------------------------------


def test_run_eval_smoke(monkeypatch):
    """Drives run_eval end-to-end in fixture mode + skip_judge.

    Relies on the real real_urls_for_p2-4.md (15 entries). Verifies it
    completes, produces 3 niche reports with cases, and aggregates.
    """
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    report = asyncio.run(run_eval(mode="fixture", skip_judge=True))
    assert report.mode == "fixture"
    assert len(report.niches) == 3
    total_cases = sum(len(n.cases) for n in report.niches)
    assert total_cases == 15
    assert 0.0 <= report.overall_mechanical_pass_rate <= 1.0
