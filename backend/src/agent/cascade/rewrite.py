"""Niche rewrite — the moat ticket (P1-3 prompts owner = Claude).

Public entry: `rewrite_for_niche(contract, niche) -> dict` matching the
RewriteResult schema in rewrite_service.py. The chain layer wraps this and
takes care of caching, cost cap, and event emission.

Upstream is switchable via env:
- CASCADE_REWRITE_UPSTREAM=fixture (default for tests): deterministic
  rewrite synthesized from the source contract — no LLM call.
- CASCADE_REWRITE_UPSTREAM=llm: call the configured chat LLM with the
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

from agent.cascade import hook_taxonomy
from agent.cascade.contract import CascadeAnalysisContract


_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_NICHE_LABELS: dict[str, str] = {
    "baomam_fushi": "宝妈辅食",
    "yuer_richang": "育儿日常",
    "jiating_chufang": "家庭厨房",
    # D3 — 去 niche 定位(929cb21 清理宝妈/育儿/厨房后)。"generic" = 单一通用
    # 代笔路径,适配任意短视频;由用户填的一句话主题(extras["topic"])驱动,
    # 而非赛道模板。三套旧 niche 保留兼容(现有数据/测试),新内容走 generic。
    "generic": "通用",
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


async def rewrite_for_niche(
    contract: CascadeAnalysisContract,
    niche: str,
    *,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a dict shaped like RewriteResult.

    `extras` carries founder-annotated source metadata (per the URL file
    `real_urls_for_p2-4.md` v2.0):
      - hook_pattern_id: str  (e.g. "H1+H2+H3")
      - source_classification: "positive" | "negative_ref" | "edge_case"
      - source_title: str
      - source_author: str
    Unused fields are ignored; defaults applied for missing.
    """
    if niche not in _NICHE_LABELS:
        raise ValueError(f"unsupported niche: {niche}")

    extras = extras or {}
    upstream = os.getenv("CASCADE_REWRITE_UPSTREAM", "fixture").strip().lower() or "fixture"
    if upstream == "fixture":
        return _fixture_rewrite(contract, niche, extras)
    if upstream == "llm":
        return await _llm_rewrite(contract, niche, extras)
    raise ValueError(f"unsupported CASCADE_REWRITE_UPSTREAM: {upstream}")


def load_prompt(niche: str) -> str:
    """Read the niche prompt template. Public for tooling/inspection."""
    if niche not in _NICHE_LABELS:
        raise ValueError(f"unsupported niche: {niche}")
    return (_PROMPTS_DIR / f"rewrite_{niche}.md").read_text(encoding="utf-8")


def _fixture_rewrite(
    contract: CascadeAnalysisContract,
    niche: str,
    extras: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic in-process rewrite. Used by tests and as a safe default.

    Honors founder extras (hook_pattern_id / source_classification) when
    provided so the offline runner can produce URL-specific, classification-
    aware fixture outputs for the P2-4 signoff round.
    """
    label = _NICHE_LABELS[niche]
    hook_pattern_id = str(extras.get("hook_pattern_id") or "")
    classification = str(extras.get("source_classification") or "positive").lower()
    if classification not in {"positive", "negative_ref", "edge_case"}:
        classification = "positive"
    source_title = str(extras.get("source_title") or "")
    source_author = str(extras.get("source_author") or "")

    warnings: list[str] = []
    if classification == "negative_ref":
        warnings.append("source_classification=negative_ref: rewrite injects an H1-H8 hook to avoid the bare-title antipattern")
    elif classification == "edge_case":
        warnings.append("source_classification=edge_case: information density preserved; brand names and efficacy claims removed")

    scenes = contract.scenes[:4]
    if len(scenes) < 3:
        scenes = list(contract.scenes[:3]) + [contract.scenes[-1]] * (3 - len(contract.scenes))

    # Per-shot visual templates — diversified so the visual_diversity check
    # (#6, pairwise Jaccard ≤ 0.5) passes. Each tuple slot is unique to its
    # shot index; we attach the cleaned scene visual to keep some source flavor
    # but lead with the niche-shot-specific anchor.
    visual_palette: tuple[str, ...] = {
        "baomam_fushi": (
            "暖色家庭厨房俯拍,餐椅特写,食材碗摆台",
            "木质砧板特写,妈妈手切食材,自然光",
            "蒸锅侧拍,蒸汽升腾,食材若隐若现",
            "宝宝面部特写,小手抓勺,餐桌一角",
        ),
        "yuer_richang": (
            "夜灯昏黄,卧室广角,凌晨时钟若隐若现",
            "妈妈侧脸特写,自拍角度,情绪沉重",
            "孩子局部特写,小手或睡颜,被子细节",
            "母子靠在一起中景,日光从窗外漏进",
        ),
        "jiating_chufang": (
            "自家厨房台面俯拍,菜单照对比,价签特写",
            "砧板食材近景,刀工手部特写,光线侧射",
            "炒锅侧拍,火光跳跃,油烟升腾",
            "成品装盘近景,斜 45° 蒸汽特写,拉丝/出汁",
        ),
        # D3 generic — niche-agnostic shot anchors; topic 注入由下方 note + LLM
        # 路径承担,fixture 这里给中性可拍构图,避免赛道味。
        "generic": (
            "主体正面中景,自然光,主角开场直面镜头",
            "关键细节特写,手部动作或物件,浅景深",
            "过程/对比镜头,前后或步骤切换,节奏推进",
            "成果/反应特写,情绪落点,收尾召唤互动",
        ),
    }[niche]

    shots = []
    for i, scene in enumerate(scenes, start=1):
        dialogue = _clean(scene.dialogue_and_narration) or _default_dialogue(niche, i)
        anchor_visual = visual_palette[(i - 1) % len(visual_palette)]
        # Combine anchor with a brief slice of the scene's own visual to
        # keep URL-specific flavor without inflating overlap.
        scene_visual = _clean(scene.visual_content)[:60]
        visual = f"{anchor_visual} · {scene_visual}" if scene_visual else anchor_visual
        shots.append({"shot_index": i, "dialogue": dialogue[:160], "visual": visual[:160]})

    # Per-niche P0 hook injection in shot 1 — guaranteed compliance with
    # check #8. Positive sources also get this nudge (not just negative_ref)
    # because the synthesized contracts are generic.
    if shots:
        source_dish = (
            hook_taxonomy.extract_dish_from_title(source_title)
            or hook_taxonomy.DEFAULT_DISH.get(niche, "家常菜")
        )
        # Pick a P0 template deterministically from the source URL hash if available
        templates = hook_taxonomy.P0_SHOT_1_TEMPLATES.get(niche, ())
        if templates:
            seed = hash(str(extras.get("source_title") or contract.analysis_id)) % len(templates)
            shot1_template = templates[seed]
            shot1_dialogue = shot1_template.format(dish=source_dish)
            shots[0]["dialogue"] = shot1_dialogue[:160]
            warnings.append(f"shot 1 anchored to P0 hook template ({niche})")

    # For jiating, additionally inject H9 (评论区二次梗钩) in shot 2 if not
    # already present. Required by jiating priority map (P0=H4+H9).
    if niche == "jiating_chufang" and len(shots) >= 2:
        if not hook_taxonomy.HOOK_PATTERNS["H9"].search(shots[1]["dialogue"]):
            seed = hash(contract.analysis_id) % len(hook_taxonomy.H9_SEED_LINES)
            shots[1]["dialogue"] = hook_taxonomy.H9_SEED_LINES[seed][:160]
            warnings.append("shot 2 anchored to H9 (评论区二次梗钩)")

    # Nutrient-category guard for baomam_fushi: when the source title hints
    # at a single nutrient category, scrub cross-category food names from
    # the dialogues built off generic scene templates. Prevents the F-1-b
    # "胡萝卜 → 苹果" anti-pattern that the synthetic_v1 fixtures produce
    # (their scene_v1 happy paths mix vegetable + fruit).
    if niche == "baomam_fushi":
        source_cats = {
            cat for cat, foods in hook_taxonomy.NUTRIENT_CATEGORIES.items()
            if any(f in source_title for f in foods)
        }
        if len(source_cats) == 1:
            keep_cat = next(iter(source_cats))
            forbidden_foods: list[str] = []
            for cat, foods in hook_taxonomy.NUTRIENT_CATEGORIES.items():
                if cat == keep_cat:
                    continue
                forbidden_foods.extend(foods)
            replaced_any = False
            for shot in shots:
                for food in forbidden_foods:
                    if food in shot["dialogue"]:
                        shot["dialogue"] = shot["dialogue"].replace(food, "食材")
                        replaced_any = True
                    if food in shot["visual"]:
                        shot["visual"] = shot["visual"].replace(food, "食材")
                        replaced_any = True
            if replaced_any:
                warnings.append(f"nutrient guard: cross-category foods scrubbed to keep '{keep_cat}'")

    topic = str(extras.get("topic") or "").strip()
    change_desc = f"改:贴合你的主题「{topic}」" if topic else f"改:换成{label}视角和家庭场景"
    note_parts = [
        f"保留:{contract.viral_analysis.replicable_formula[:40]}",
        f"hook_pattern_id={hook_pattern_id or '(unset)'}",
        f"classification={classification}",
        change_desc,
    ]
    note = "<!-- " + " | ".join(note_parts) + " -->"
    body_lines = [note]
    for shot in shots:
        body_lines.append(f"{shot['shot_index']}. {shot['dialogue']}")
        body_lines.append(f"   画面:{shot['visual']}")
    script_markdown = "### 改写脚本\n" + "\n".join(body_lines)
    # D5: 长度 80–400 字。script_markdown 含「台词+画面」合并,逐镜 4-5 镜会到
    # 200-350,放宽到 400 容纳画面描述(台词本身仍是短口播)。
    if len(script_markdown) < 80:
        script_markdown += "\n" + (f"({label}版,贴近自家场景。" * 3)
    if len(script_markdown) > 400:
        script_markdown = script_markdown[:397] + "..."

    # confidence ceiling for negative_ref per prompt spec
    base_confidence = max(0.5, min(1.0, contract.confidence - 0.05))
    if classification == "negative_ref":
        base_confidence = min(base_confidence, 0.6)
        warnings.append("confidence capped at 0.6 (negative_ref source)")

    # Per-call nanosecond seed avoids rewrite_id PK collisions on bulk runs.
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
        "parser_warnings": warnings,
        "confidence": base_confidence,
        "cost_cny": 0.42,
        "model": contract.model,
        "hook_pattern_id": hook_pattern_id,
        "source_classification": classification,
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
    if niche == "jiating_chufang":
        return "在家也能做出餐厅的味道,这次你试试看"
    # generic — niche 无关的开场/互动兜底
    return ("先别划走,这条我替你拆明白了" if shot_index == 1 else "你会怎么做,评论区聊聊")


_JSON_RETRY_NUDGE = (
    "\n\n你刚才的输出不是合法 JSON。请只输出合法 JSON 对象,不要任何 markdown 围栏、"
    "解释或前缀。仅返回 schema 中描述的字段。"
)


def _invoke_llm(prompt: str) -> str:
    """Call the LLM and return raw text. Separated for testability (mockable)."""
    try:
        from agent.llm_factory import get_chat_model
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("LLM dependencies unavailable; set CASCADE_REWRITE_UPSTREAM=fixture") from exc

    model = get_chat_model()
    result = model.invoke([{"role": "user", "content": prompt}])
    raw = result.content if hasattr(result, "content") else str(result)
    return raw if isinstance(raw, str) else _join_content_parts(raw)


async def _llm_rewrite(
    contract: CascadeAnalysisContract,
    niche: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Live LLM path. Loads the niche prompt and parses the model's JSON response.

    Hardening (per claude_llm_P2-4.md):
    - Largest-object JSON extraction (model may embed example JSON in commentary)
    - 1-shot retry on malformed output with a clarifying nudge
    - Post-hoc forbidden-term scrub via _clean(), with parser_warnings recording
    - Confidence ceiling: any hard-constraint violation forces confidence ≤ 0.4
    - cost_cny estimate from prompt + response length
    - founder extras (hook_pattern_id / source_classification / source_title /
      source_author) substituted into prompt placeholders + forced onto output
    """
    extras = extras or {}
    template = load_prompt(niche)
    contract_json = json.dumps(contract.model_dump(mode="json"), ensure_ascii=False, indent=2)
    prompt = template.replace("{CONTRACT_JSON}", contract_json)
    prompt = prompt.replace("{HOOK_PATTERN_ID}", str(extras.get("hook_pattern_id") or ""))
    prompt = prompt.replace("{SOURCE_CLASSIFICATION}", str(extras.get("source_classification") or "positive"))
    prompt = prompt.replace("{SOURCE_TITLE}", str(extras.get("source_title") or ""))
    prompt = prompt.replace("{SOURCE_AUTHOR}", str(extras.get("source_author") or ""))
    # D3 — 用户填的一句话主题(generic 通用代笔路径用;旧 niche prompt 无 {TOPIC}
    # 占位则此 replace 为 no-op,向后兼容)。空主题替换为中性提示。
    prompt = prompt.replace("{TOPIC}", str(extras.get("topic") or "(未指定,沿用原片主题)"))

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

    data = _normalize_llm_output(data, contract, niche, raw_text, prompt, extras)
    return data


def _normalize_llm_output(
    data: dict[str, Any],
    contract: CascadeAnalysisContract,
    niche: str,
    raw_text: str,
    prompt: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Coerce + harden raw LLM dict before returning."""
    extras = extras or {}
    warnings: list[str] = list(data.get("parser_warnings") or [])

    # Identity fields — model can hallucinate; force agreement with the input contract.
    data["analysis_id"] = contract.analysis_id
    data["niche"] = niche
    from agent.llm_factory import current_model_name

    data["model"] = current_model_name()

    # Founder-annotated source metadata — force onto output for downstream
    # signoff / eval traceability. The prompt also tells the LLM to echo
    # these, but we override here to be safe.
    incoming_hook = str(extras.get("hook_pattern_id") or "")
    incoming_class = str(extras.get("source_classification") or "positive").lower()
    if incoming_class not in {"positive", "negative_ref", "edge_case"}:
        incoming_class = "positive"
    data["hook_pattern_id"] = incoming_hook
    data["source_classification"] = incoming_class
    if incoming_class == "edge_case":
        warnings.append("source_classification=edge_case: brand/efficacy claims removed; information density preserved")

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
        or not (80 <= len(data["script_markdown"]) <= 400)  # D5: 80–400(台词+画面合并)
    )
    if hard_violation:
        confidence = min(confidence, 0.4)
        warnings.append("confidence capped at 0.4 (hard constraint violated)")
    if incoming_class == "negative_ref":
        confidence = min(confidence, 0.6)
        warnings.append("confidence capped at 0.6 (negative_ref source)")
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

    # Whitelist-filter to RewriteResult's allowed keys. The model (esp. under
    # the ghostwriter prompts) may emit extra QA fields like `self_check`; the
    # downstream RewriteResult / RewriteShot models are extra="forbid", so any
    # stray key would crash validation the moment we run on the live LLM path.
    # Strip silently — these are model scratch fields, not creator-facing data.
    data = {k: v for k, v in data.items() if k in _RESULT_KEYS}
    data["shots"] = [
        {k: v for k, v in (shot or {}).items() if k in _SHOT_KEYS}
        for shot in (data.get("shots") or [])
    ]
    return data


_RESULT_KEYS: frozenset[str] = frozenset(
    {
        "rewrite_id",
        "analysis_id",
        "niche",
        "script_markdown",
        "shots",
        "parser_warnings",
        "confidence",
        "cost_cny",
        "model",
        "hook_pattern_id",
        "source_classification",
    }
)
_SHOT_KEYS: frozenset[str] = frozenset({"shot_index", "dialogue", "visual"})


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
