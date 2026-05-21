"""Mocked-LLM tests for the rewrite.py LLM path (P2-4 hardening).

Patches `agent.cascade.rewrite._invoke_llm` so no API key is needed in CI.
Covers JSON extraction, retry, forbidden-term scrub, confidence cap,
cost estimate, identity-field coercion.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.rewrite import (
    _extract_json,
    rewrite_for_niche,
)
from agent.cascade.rewrite_service import RewriteResult


FIX_DIR = Path(__file__).resolve().parent.parent / "src" / "agent" / "cascade" / "fixtures" / "rewrite_smoke"


def _load(niche: str = "baomam_fushi", n: int = 1) -> CascadeAnalysisContract:
    raw = json.loads((FIX_DIR / niche / f"ref_{n:03d}.json").read_text(encoding="utf-8"))
    cleaned = {k: v for k, v in raw.items() if not k.startswith("_")}
    return CascadeAnalysisContract.model_validate(cleaned)


def _valid_llm_payload(analysis_id: str = "ana_smk_baomam_fushi_001") -> dict:
    return {
        "rewrite_id": "rw_abcdef0123456789",
        "analysis_id": analysis_id,
        "niche": "baomam_fushi",
        "script_markdown": (
            "### 改写脚本\n<!-- 保留:悬念开场 | 改:换成家庭厨房视角 -->\n"
            "1. 你家宝宝是不是也这样,怎么喂都不吃?\n"
            "   画面:暖色家庭厨房,餐椅特写\n"
            "2. 试试换成苹果泥,颜色更亮\n"
            "   画面:砧板苹果切块特写\n"
            "3. 蒸 8 分钟,又软又香\n"
            "   画面:蒸锅冒蒸汽\n"
            "4. 看,自己张嘴了!\n"
            "   画面:宝宝张嘴接勺子"
        ),
        "shots": [
            {"shot_index": 1, "dialogue": "你家宝宝是不是也这样,怎么喂都不吃?", "visual": "暖色家庭厨房,餐椅特写"},
            {"shot_index": 2, "dialogue": "试试换成苹果泥,颜色更亮", "visual": "砧板苹果切块特写"},
            {"shot_index": 3, "dialogue": "蒸 8 分钟,又软又香", "visual": "蒸锅冒蒸汽"},
            {"shot_index": 4, "dialogue": "看,自己张嘴了!", "visual": "宝宝张嘴接勺子"},
        ],
        "parser_warnings": [],
        "confidence": 0.86,
        "cost_cny": 0.0,
        "model": "doubao-seed-2-0-pro",
    }


def _patch_llm(monkeypatch, *outputs: str) -> list[int]:
    """Patch _invoke_llm to return the given outputs in sequence. Returns call counter."""
    counter = [0]

    def fake(prompt: str) -> str:
        idx = min(counter[0], len(outputs) - 1)
        counter[0] += 1
        return outputs[idx]

    monkeypatch.setattr("agent.cascade.rewrite._invoke_llm", fake)
    monkeypatch.setenv("CASCADE_REWRITE_UPSTREAM", "llm")
    return counter


# --- _extract_json unit tests ---


def test_extract_json_picks_largest_object():
    text = '示例 {"x": 1} 实际 {"rewrite_id": "rw_a", "script_markdown": "abc", "shots": [], "padding": "lots more"}'
    out = _extract_json(text)
    assert out.get("rewrite_id") == "rw_a"


def test_extract_json_strips_markdown_fence():
    text = "好的:\n```json\n{\"a\": 1, \"b\": 2}\n```"
    out = _extract_json(text)
    assert out == {"a": 1, "b": 2}


def test_extract_json_raises_on_no_object():
    with pytest.raises(ValueError):
        _extract_json("just text, no braces here")


def test_extract_json_raises_on_invalid_payload():
    with pytest.raises(ValueError):
        _extract_json("{ not valid json")


# --- _llm_rewrite via rewrite_for_niche ---


def test_llm_happy_path(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    counter = _patch_llm(monkeypatch, json.dumps(payload, ensure_ascii=False))

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert counter[0] == 1
    assert result["analysis_id"] == contract.analysis_id  # forced match
    assert result["niche"] == "baomam_fushi"  # forced match
    assert result["rewrite_id"].startswith("rw_")
    assert result["confidence"] == 0.86  # unchanged (no violation)
    assert result["cost_cny"] > 0  # estimated, not zero
    assert result["parser_warnings"] == []

    # Round-trips through RewriteResult
    validated = RewriteResult.model_validate(result)
    assert 3 <= len(validated.shots) <= 5


def test_llm_markdown_fenced_output(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    fenced = f"这是改写结果:\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    counter = _patch_llm(monkeypatch, fenced)

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert counter[0] == 1
    assert result["confidence"] == 0.86


def test_llm_multiple_json_candidates_picks_real_one(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    mixed = f"参考示例 {{\"x\": 1}} 你的输出 {json.dumps(payload, ensure_ascii=False)}"
    _patch_llm(monkeypatch, mixed)

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert result["rewrite_id"] == payload["rewrite_id"]
    # Sanity: shots not empty
    assert len(result["shots"]) == 4


def test_llm_malformed_then_valid_retry(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    counter = _patch_llm(
        monkeypatch,
        "Sorry, I cannot output JSON here.",  # first attempt: bad
        json.dumps(payload, ensure_ascii=False),  # retry: good
    )

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert counter[0] == 2  # one retry
    assert result["rewrite_id"] == payload["rewrite_id"]


def test_llm_malformed_twice_raises_hard_failure(monkeypatch):
    contract = _load("baomam_fushi", 1)
    _patch_llm(monkeypatch, "no json", "still no json")

    with pytest.raises(HardFailure) as exc:
        asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD


def test_llm_forbidden_term_scrubbed_and_confidence_capped(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    # Inject forbidden term into the first shot
    payload["shots"][0]["dialogue"] = "这是 AI 帮你想的台词,神器一般"
    payload["script_markdown"] = payload["script_markdown"].replace("家庭厨房", "AI 智能厨房")
    payload["confidence"] = 0.9
    _patch_llm(monkeypatch, json.dumps(payload, ensure_ascii=False))

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    # AI and 神器 should be replaced
    assert "AI" not in result["script_markdown"]
    assert "神器" not in result["shots"][0]["dialogue"]
    # Hard violation triggers confidence cap
    assert result["confidence"] <= 0.4
    # Warnings recorded
    assert any("forbidden" in w for w in result["parser_warnings"])
    assert any("confidence capped" in w for w in result["parser_warnings"])


def test_llm_shot_count_over_limit_truncated(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    payload["shots"] = payload["shots"] + [
        {"shot_index": 5, "dialogue": "多余一", "visual": "多余画面一"},
        {"shot_index": 6, "dialogue": "多余二", "visual": "多余画面二"},
        {"shot_index": 7, "dialogue": "多余三", "visual": "多余画面三"},
    ]
    _patch_llm(monkeypatch, json.dumps(payload, ensure_ascii=False))

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert len(result["shots"]) == 5
    assert any("truncated" in w for w in result["parser_warnings"])


def test_llm_cost_estimate_scales_with_input(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    long_output = json.dumps(payload, ensure_ascii=False) + " " + ("padding " * 1000)
    _patch_llm(monkeypatch, long_output)

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    # Longer output should push estimated cost above the small-output floor
    assert result["cost_cny"] > 0.001


def test_llm_identity_fields_forced_to_match_input(monkeypatch):
    """Model hallucinates wrong analysis_id / niche — service overrides."""
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    payload["analysis_id"] = "ana_hallucinated_bogus"
    payload["niche"] = "wrong_niche"
    _patch_llm(monkeypatch, json.dumps(payload, ensure_ascii=False))

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert result["analysis_id"] == contract.analysis_id
    assert result["niche"] == "baomam_fushi"


def test_llm_missing_rewrite_id_generated(monkeypatch):
    contract = _load("baomam_fushi", 1)
    payload = _valid_llm_payload(contract.analysis_id)
    payload.pop("rewrite_id")
    _patch_llm(monkeypatch, json.dumps(payload, ensure_ascii=False))

    result = asyncio.run(rewrite_for_niche(contract, "baomam_fushi"))
    assert result["rewrite_id"].startswith("rw_")
    assert len(result["rewrite_id"]) == 19  # rw_ + 16 hex
