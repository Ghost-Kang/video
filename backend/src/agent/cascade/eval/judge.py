"""LLM judge for eval harness — half-automated qualitative scoring.

Asks an independent LLM (Gemini Flash by default) three structured
questions per rewrite:
  1. kept_formula: yes/no/partial (does it preserve the source's
     replicable_formula?)
  2. realism_1to5: integer 1-5 (would a real creator post this?)
  3. ad_risk: yes/no + 命中 fragment (any brand name / efficacy
     claim / regulatory red flag?)

When `GOOGLE_API_KEY` is not configured, returns `{skipped: True}` so
the rest of the harness can still produce a baseline.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping


_JSON_PATTERN = re.compile(r"\{[\s\S]*?\}")


JUDGE_PROMPT_TEMPLATE = """你是一个独立的中文短视频改写质量评审。
请基于以下信息,对改写输出给出结构化判断,输出严格 JSON 不带任何 markdown 围栏或解释。

源 niche: {niche}
源 hook_pattern_id: {hook_pattern_id}
源 标题: {source_title}
源 replicable_formula: {formula}

改写 script_markdown:
{script}

改写 shots:
{shots}

请回答以下三个问题,输出 JSON:

{{
  "kept_formula": "yes" | "no" | "partial",
  "kept_formula_reason": "一句话理由,≤ 30 字",
  "realism_1to5": 1-5 整数,
  "realism_reason": "一句话理由,≤ 30 字",
  "ad_risk": "yes" | "no",
  "ad_risk_fragment": "命中片段,若 ad_risk=yes 必填,否则空字符串"
}}
"""


def judge_one(
    result: Mapping[str, Any],
    *,
    niche: str,
    source_title: str = "",
    source_formula: str = "",
) -> dict[str, Any]:
    """Call the judge LLM (when configured) or return a skipped sentinel.

    `result` is a rewrite output dict (RewriteResult-shaped).
    """
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        return {"skipped": True, "reason": "no GOOGLE_API_KEY in env"}
    if os.getenv("CASCADE_EVAL_JUDGE", "live").strip().lower() == "skip":
        return {"skipped": True, "reason": "CASCADE_EVAL_JUDGE=skip"}

    try:
        return _live_judge(
            result,
            niche=niche,
            source_title=source_title,
            source_formula=source_formula,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return {"skipped": True, "reason": f"judge call failed: {exc.__class__.__name__}"}


def _live_judge(
    result: Mapping[str, Any],
    *,
    niche: str,
    source_title: str,
    source_formula: str,
) -> dict[str, Any]:
    from langchain_google_genai import ChatGoogleGenerativeAI

    from agent.config import LLM_MODEL

    shots_text = "\n".join(
        f"{s.get('shot_index', '?')}. {s.get('dialogue', '')} | 画面:{s.get('visual', '')}"
        for s in (result.get("shots") or [])
    )
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        niche=niche,
        hook_pattern_id=result.get("hook_pattern_id") or "(unset)",
        source_title=source_title or "(unknown)",
        formula=source_formula or "(unknown)",
        script=result.get("script_markdown", ""),
        shots=shots_text,
    )

    model = ChatGoogleGenerativeAI(model=LLM_MODEL)
    response = model.invoke([{"role": "user", "content": prompt}])
    raw = response.content if hasattr(response, "content") else str(response)
    if not isinstance(raw, str):
        raw = " ".join(part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in raw)

    parsed = _extract_first_json(raw)
    if parsed is None:
        return {"skipped": True, "reason": "judge LLM returned no JSON"}

    # Coerce + clamp values
    parsed.setdefault("kept_formula", "partial")
    parsed.setdefault("realism_1to5", 3)
    try:
        parsed["realism_1to5"] = max(1, min(5, int(parsed["realism_1to5"])))
    except (TypeError, ValueError):
        parsed["realism_1to5"] = 3
    parsed.setdefault("ad_risk", "no")
    parsed.setdefault("ad_risk_fragment", "")
    parsed["skipped"] = False
    return parsed


def _extract_first_json(text: str) -> dict[str, Any] | None:
    for match in _JSON_PATTERN.finditer(text):
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None
