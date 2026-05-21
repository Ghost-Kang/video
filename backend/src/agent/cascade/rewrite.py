"""Niche rewrite — the moat ticket (P1-3 prompts owner = Claude).

Public entry: `rewrite_for_niche(contract, niche) -> dict` matching the
RewriteResult schema in rewrite_service.py. The chain layer wraps this and
takes care of caching, cost cap, and event emission.

Upstream is switchable via env:
- CASCADE_REWRITE_UPSTREAM=fixture (default for tests): deterministic
  rewrite synthesized from the source contract — no LLM call.
- CASCADE_REWRITE_UPSTREAM=llm: call ChatGoogleGenerativeAI with the
  niche prompt template + contract JSON, parse JSON, validate shape.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from agent.cascade.contract import CascadeAnalysisContract


_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_NICHE_LABELS: dict[str, str] = {
    "baomam_fushi": "宝妈辅食",
    "yuer_richang": "育儿日常",
    "jiating_chufang": "家庭厨房",
}

# Brand-guardrail forbidden terms (subset; the prompt enforces the full list).
# Whatever ends up in the rewritten output is checked against this in tests.
FORBIDDEN_TERMS: tuple[str, ...] = (
    "AI",
    "智能",
    "算法",
    "平台",
    "神器",
    "必备",
    "营养师",
    "米其林",
    "权威",
)


async def rewrite_for_niche(contract: CascadeAnalysisContract, niche: str) -> dict[str, Any]:
    """Return a dict shaped like RewriteResult."""
    if niche not in _NICHE_LABELS:
        raise ValueError(f"unsupported niche: {niche}")

    upstream = os.getenv("CASCADE_REWRITE_UPSTREAM", "fixture").strip().lower() or "fixture"
    if upstream == "fixture":
        return _fixture_rewrite(contract, niche)
    if upstream == "llm":
        return await _llm_rewrite(contract, niche)
    raise ValueError(f"unsupported CASCADE_REWRITE_UPSTREAM: {upstream}")


def load_prompt(niche: str) -> str:
    """Read the niche prompt template. Public for tooling/inspection."""
    if niche not in _NICHE_LABELS:
        raise ValueError(f"unsupported niche: {niche}")
    return (_PROMPTS_DIR / f"rewrite_{niche}.md").read_text(encoding="utf-8")


def _fixture_rewrite(contract: CascadeAnalysisContract, niche: str) -> dict[str, Any]:
    """Deterministic in-process rewrite. Used by tests and as a safe default.

    Construction rules:
    - Take the first 4 source scenes, rewrite into 4 shots.
    - Dialogue: family-perspective rephrase of the scene dialogue.
    - Visual: family-kitchen rephrase of visual_content.
    - script_markdown starts with a one-line "保留 X / 改 Y" rationale.
    - Drop forbidden terms by simple substitution.
    """
    label = _NICHE_LABELS[niche]
    scenes = contract.scenes[:4]
    if len(scenes) < 3:
        scenes = list(contract.scenes[:3]) + [contract.scenes[-1]] * (3 - len(contract.scenes))

    shots = []
    for i, scene in enumerate(scenes, start=1):
        dialogue = _clean(scene.dialogue_and_narration) or _default_dialogue(niche, i)
        visual = _clean(scene.visual_content)
        if niche == "baomam_fushi":
            visual = _ensure_phrase(visual, "暖色家庭厨房")
        elif niche == "yuer_richang":
            visual = _ensure_phrase(visual, "家里温暖灯光")
        else:
            visual = _ensure_phrase(visual, "自家厨房台面")
        shots.append({"shot_index": i, "dialogue": dialogue[:160], "visual": visual[:160]})

    note = (
        f"<!-- 保留:{contract.viral_analysis.replicable_formula[:40]} | "
        f"改:换成{label}视角和家庭场景 -->"
    )
    body_lines = [note]
    for shot in shots:
        body_lines.append(f"{shot['shot_index']}. {shot['dialogue']}")
        body_lines.append(f"   画面:{shot['visual']}")
    script_markdown = "### 改写脚本\n" + "\n".join(body_lines)
    # Pad to satisfy length [80, 600] in case the contract was very terse.
    if len(script_markdown) < 80:
        script_markdown += "\n" + (f"({label}版,贴近自家场景。" * 3)
    if len(script_markdown) > 600:
        script_markdown = script_markdown[:597] + "..."

    # Per-call nanosecond seed keeps back-to-back calls for the same
    # (analysis_id, niche) — e.g. two users sharing one analysis — from
    # colliding on the rewrites.rewrite_id PRIMARY KEY.
    seed = time.time_ns()
    digest = hashlib.sha256(
        f"{contract.analysis_id}\0{niche}\0{seed}\0{script_markdown}".encode("utf-8")
    ).hexdigest()[:16]

    return {
        "rewrite_id": f"rw_{digest}",
        "analysis_id": contract.analysis_id,
        "niche": niche,
        "script_markdown": script_markdown,
        "shots": shots,
        "parser_warnings": [],
        "confidence": max(0.5, min(1.0, contract.confidence - 0.05)),
        "cost_cny": 0.42,
        "model": contract.model,
    }


_FORBIDDEN_SUBS: dict[str, str] = {
    "AI": "我",
    "智能": "顺手",
    "算法": "节奏",
    "平台": "镜头",
    "神器": "小工具",
    "必备": "常用",
    "营养师": "我自己",
    "米其林": "餐厅",
    "权威": "经验",
}


def _clean(text: str) -> str:
    """Strip brand/forbidden terms with safe replacements."""
    out = text
    for needle, repl in _FORBIDDEN_SUBS.items():
        out = out.replace(needle, repl)
    return out.strip()


def _ensure_phrase(text: str, phrase: str) -> str:
    return text if phrase in text else f"{phrase},{text}"


def _default_dialogue(niche: str, shot_index: int) -> str:
    if niche == "baomam_fushi":
        return ("这次换个做法,看看宝宝吃不吃" if shot_index == 1 else "你家宝宝吃这个吗,评论区告诉我")
    if niche == "yuer_richang":
        return ("当妈第 N 次破防,但他这句话又把我治愈了" if shot_index == 1 else "你被娃哪句话戳过")
    return "在家也能做出餐厅的味道,这次你试试看"


_JSON_RETRY_NUDGE = (
    "\n\n你刚才的输出不是合法 JSON。请只输出合法 JSON 对象,不要任何 markdown 围栏、"
    "解释或前缀。仅返回 schema 中描述的字段。"
)


def _invoke_llm(prompt: str) -> str:
    """Call the LLM and return raw text. Separated for testability (mockable)."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        from agent.config import LLM_MODEL
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("LLM dependencies unavailable; set CASCADE_REWRITE_UPSTREAM=fixture") from exc

    model = ChatGoogleGenerativeAI(model=LLM_MODEL)
    result = model.invoke([{"role": "user", "content": prompt}])
    raw = result.content if hasattr(result, "content") else str(result)
    return raw if isinstance(raw, str) else _join_content_parts(raw)


async def _llm_rewrite(contract: CascadeAnalysisContract, niche: str) -> dict[str, Any]:
    """Live LLM path. Loads the niche prompt and parses the model's JSON response.

    Hardening (per claude_llm_P2-4.md):
    - Largest-object JSON extraction (model may embed example JSON in commentary)
    - 1-shot retry on malformed output with a clarifying nudge
    - Post-hoc forbidden-term scrub via _clean(), with parser_warnings recording
    - Confidence ceiling: any hard-constraint violation forces confidence ≤ 0.4
    - cost_cny estimate from prompt + response length
    """
    template = load_prompt(niche)
    contract_json = json.dumps(contract.model_dump(mode="json"), ensure_ascii=False, indent=2)
    prompt = template.replace("{CONTRACT_JSON}", contract_json)

    raw_text = _invoke_llm(prompt)
    try:
        data = _extract_json(raw_text)
    except (ValueError, json.JSONDecodeError):
        # One retry with explicit nudge
        retry_text = _invoke_llm(prompt + _JSON_RETRY_NUDGE)
        try:
            data = _extract_json(retry_text)
        except (ValueError, json.JSONDecodeError) as exc:
            from agent.cascade.failures import FailureCode, HardFailure
            raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "LLM rewrite output not parseable") from exc
        raw_text = retry_text

    data = _normalize_llm_output(data, contract, niche, raw_text, prompt)
    return data


def _normalize_llm_output(
    data: dict[str, Any],
    contract: CascadeAnalysisContract,
    niche: str,
    raw_text: str,
    prompt: str,
) -> dict[str, Any]:
    """Coerce + harden raw LLM dict before returning."""
    warnings: list[str] = list(data.get("parser_warnings") or [])

    # Identity fields — model can hallucinate; force agreement with the input contract.
    data["analysis_id"] = contract.analysis_id
    data["niche"] = niche
    data.setdefault("model", contract.model)

    if "rewrite_id" not in data or not str(data.get("rewrite_id", "")).startswith("rw_"):
        digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
        data["rewrite_id"] = f"rw_{digest}"

    # Shot count clamp.
    shots = data.get("shots") or []
    if len(shots) > 5:
        shots = shots[:5]
        warnings.append(f"shots truncated from {len(data.get('shots') or [])} to 5")
    if len(shots) < 3:
        warnings.append(f"shots count {len(shots)} below niche minimum 3 — caller will reject")
    data["shots"] = shots

    # Forbidden-term scrub on script and shot text. _clean already does substitution;
    # we just track if anything changed so the founder sees it.
    original_script = data.get("script_markdown", "")
    cleaned_script = _clean(original_script)
    if cleaned_script != original_script:
        warnings.append("forbidden terms scrubbed from script_markdown")
    data["script_markdown"] = cleaned_script

    for shot in shots:
        orig_dialogue = shot.get("dialogue", "")
        orig_visual = shot.get("visual", "")
        new_dialogue = _clean(orig_dialogue)
        new_visual = _clean(orig_visual)
        if new_dialogue != orig_dialogue or new_visual != orig_visual:
            warnings.append(f"forbidden terms scrubbed from shot {shot.get('shot_index', '?')}")
        shot["dialogue"] = new_dialogue
        shot["visual"] = new_visual

    # Confidence calibration.
    confidence = float(data.get("confidence", 0.0) or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    hard_violation = (
        len(shots) < 3
        or len(shots) > 5
        or any(w.startswith("forbidden terms scrubbed") for w in warnings)
        or not (80 <= len(data["script_markdown"]) <= 600)
    )
    if hard_violation:
        confidence = min(confidence, 0.4)
        warnings.append("confidence capped at 0.4 (hard constraint violated)")
    data["confidence"] = confidence

    # Cost estimate. Defaults reflect Gemini Flash pricing in CNY per 1K tokens;
    # config can override.
    in_price = float(os.getenv("LLM_INPUT_PRICE_CNY_PER_1K", "0.005"))
    out_price = float(os.getenv("LLM_OUTPUT_PRICE_CNY_PER_1K", "0.020"))
    tokens_in = max(1, len(prompt) // 4)
    tokens_out = max(1, len(raw_text) // 4)
    estimated_cost = (tokens_in / 1000.0) * in_price + (tokens_out / 1000.0) * out_price
    # Round up to 4 decimal places; ensure positive.
    data["cost_cny"] = max(0.0001, round(estimated_cost, 4))

    data["parser_warnings"] = warnings
    return data


def _join_content_parts(parts: Any) -> str:
    if isinstance(parts, list):
        return "\n".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in parts)
    return str(parts)


_JSON_PATTERN = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the largest valid JSON object out of the model output.

    Model may embed example JSON in commentary before the real answer. Iterate
    candidate matches and pick the longest that parses cleanly. Falls back to
    the first matching greedy object if none parse — caller handles the raise.
    """
    candidates: list[str] = []
    # Greedy match (might span multiple objects)
    greedy = _JSON_PATTERN.search(text)
    if greedy:
        candidates.append(greedy.group(0))

    # Bracket-balance scan for individual JSON objects
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(text[start : i + 1])
                start = -1

    # Try parsing each candidate; keep the largest that succeeds.
    best: dict[str, Any] | None = None
    best_len = -1
    for cand in candidates:
        try:
            parsed = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and len(cand) > best_len:
            best = parsed
            best_len = len(cand)

    if best is None:
        raise ValueError("rewrite LLM returned no valid JSON object")
    return best
