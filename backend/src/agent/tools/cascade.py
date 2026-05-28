"""Cascade tools for the Director agent.

Wraps `request_shallow_analysis` + `request_rewrite` as LangChain `@tool`s so the
Director can drive the Cascade pipeline directly from chat. Both tools:

- Read per-turn context (user_id / thread_id / ws) via `RUN_CTX` ContextVar — set
  by `run_agent` at the start of every WS turn (see `transport/runtime_ctx.py`).
- Push a side-channel WS frame after success so the frontend CardStack updates
  in real time (`analysis_returned` / `rewrite_returned`).
- Catch `HardFailure` and return `{"error": ..., "message": ...}` instead of
  raising — raising inside a graph tool kills the whole turn.
- Return a compact dict (not the full Pydantic) so the LLM doesn't blow its
  context window quoting the analysis back. The WS frame carries the full
  payload to the frontend.

Tool docstrings are LLM-visible — they describe trigger conditions, parameter
constraints, and expected behavior to the model, not the human reader.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.tools import tool

from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.cost_guard import (
    PREDICT_ASK_CNY,
    PREDICT_SHOT_IMAGE_CNY,
    cost_guard,
)
from agent.cascade.event_names import EventName
from agent.cascade.events import emit
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.hook_taxonomy import detect_hooks_in_text, infer_niche_from_hooks
from agent.cascade.rewrite_service import (
    SUPPORTED_NICHES,
    RewriteResult,
    request_rewrite,
)
from agent.cascade.storage import load_analysis, load_rewrite_by_id
from agent.llm_factory import current_model_name, get_chat_model
from agent.tools.generation import ApimartProvider
from agent.transport.runtime_ctx import get_run_ctx


async def _push_ws(payload: dict[str, Any]) -> None:
    """Best-effort WS frame push. Swallows send errors (connection may be gone)."""
    ctx = get_run_ctx()
    ws = ctx.get("ws")
    if ws is None:
        return
    try:
        await ws.send(json.dumps(payload, ensure_ascii=False))
    except Exception:
        # WS may have closed mid-tool — don't bring down the agent turn.
        pass


async def _push_failure_frame(
    code: str,
    hint: str,
    actions: list[str],
    request_id: str = "",
    stage: str = "analysis",
) -> None:
    """W5D3 Bug #2 — push structured analysis_failed WS frame from tool
    HardFailure paths. Lets frontend setFailure cleanly without relying on
    the agent_runner outer except (which only fires for uncaught exceptions,
    not tools that catch HardFailure and return error dicts to the LLM)."""
    ctx = get_run_ctx()
    thread_id = ctx.get("thread_id")
    if not thread_id:
        return
    await _push_ws(
        {
            "type": "analysis_failed",
            "thread_id": thread_id,
            "code": code,
            "hint": hint,
            "actions": actions,
            "request_id": request_id,
            "stage": stage,
        }
    )


def _hardfailure_payload(exc: HardFailure) -> dict[str, Any]:
    """Pack a HardFailure into the shape AnalysisFailedEvent expects."""
    return {
        "code": exc.code.value,
        "hint": exc.hint,
        "actions": list(exc.actions),
        "request_id": exc.request_id,
    }


def _viral_text_for_niche_inference(contract: Any) -> str:
    """Concatenate the viral_analysis fields most likely to carry niche-signal hooks.

    Why these fields (and not just `hook + replicable_formula`):
      - `hook` is capped at 80 chars and is often pure scene description.
      - `replicable_formula` is the recipe, not necessarily hook-tagged.
      - `pacing`, `target_audience`, `engagement_levers` frequently include
        age-range / audience markers (e.g. "0-3 岁宝宝妈妈") that fire H1, and
        emotional-arc patterns that fire H8 — both load-bearing for niche
        disambiguation against the synthetic_v1 fixtures.

    We intentionally exclude scene-level dialogue to keep false positives down
    (e.g. baomam fixture dialogue "不是也这样,怎么喂都不吃" false-fires H9 and
    creates a tie with jiating_chufang).
    """
    va = contract.viral_analysis
    return " ".join((
        va.hook,
        va.replicable_formula,
        va.pacing,
        va.target_audience,
        va.engagement_levers,
        va.emotional_arc,
    ))


def _compact_analysis(contract: Any) -> dict[str, Any]:
    """Compact dict for the LLM — only what it needs to chain into rewrite.

    Includes `suggested_niche` derived from H-pattern detection. Note: W4D5
    (2026-05-27) the Director no longer auto-rewrites on `suggested_niche`;
    the frontend NicheCTA surfaces it for the user to pick. The field is kept
    so future flows (e.g. featured-card auto-classification) can reuse it.
    """
    hook_text = _viral_text_for_niche_inference(contract)
    detected = detect_hooks_in_text(hook_text)
    suggested_niche, infer_reason = infer_niche_from_hooks(detected)
    return {
        "analysis_id": contract.analysis_id,
        "confidence": contract.confidence,
        "hook": contract.viral_analysis.hook,
        "replicable_formula": contract.viral_analysis.replicable_formula,
        "scene_count": len(contract.scenes),
        "duration_s": contract.duration_s,
        "platform": contract.platform.value,
        "warnings_count": len(contract.warnings),
        "detected_hooks": detected,
        "suggested_niche": suggested_niche,
        "niche_inference_reason": infer_reason,
    }


@tool
async def cascade_analyze(source_url: str) -> dict:
    """分析一条抖音/小红书爆款链接，返回 analysis_id 给后续 rewrite 使用。

    **何时调用**：用户消息里出现以下任一域名时，立即调用，不要先发问：
    - douyin.com/video/...
    - v.douyin.com/...
    - xhslink.com/...
    - xiaohongshu.com/explore/...

    **参数**：source_url - 用户给的原始链接 (str)。原样传入，不要做任何 sanitize。

    **返回**：
    - 成功：{"analysis_id": "ana_...", "confidence": 0.0~1.0, "hook": "...",
              "replicable_formula": "...", "scene_count": int, "duration_s": int,
              "platform": "douyin|xiaohongshu|other", "warnings_count": int,
              "detected_hooks": ["H1", ...],
              "suggested_niche": "baomam_fushi" | "yuer_richang" | "jiating_chufang" | null,
              "niche_inference_reason": "..."}
    - 失败：{"error": "FAILURE_CODE", "message": "人话错误描述"}

    **suggested_niche** 字段：基于钩子模式自动推断的赛道，仅供参考，**不要**用它
    自动调 cascade_rewrite——分析阶段只做分析（director.md §0.5），改写要等用户
    主动触发（§0.6）。

    成功后系统会自动推送 analysis 到前端 CardStack 渲染。你只需在 chat 里说
    一句「分析好了」之类的话，**不要把分析内容复述给用户**。

    **重要**：返回值里的 analysis_id 系统会持久化，后续用户触发 rewrite 时
    会自动取最近一条。你不需要在 chat 里复述 analysis_id。
    """
    ctx = get_run_ctx()
    user_id = ctx.get("user_id") or "anonymous"
    thread_id = ctx.get("thread_id") or ""
    run_id = ctx.get("run_id")

    try:
        contract = await request_shallow_analysis(
            source_url,
            user_id=user_id,
            run_id=run_id,
        )
    except HardFailure as exc:
        # W5D3 Bug #2: also push structured WS frame so frontend setFailure
        # fires (Director chat reply alone doesn't trigger failed state).
        p = _hardfailure_payload(exc)
        await _push_failure_frame(p["code"], p["hint"], p["actions"], p["request_id"], stage="analysis")
        return {
            "error": exc.code.value,
            "message": exc.hint or "分析失败，请稍后重试",
        }
    except Exception as exc:  # pragma: no cover - defensive; service is robust
        return {
            "error": "S5_INVALID_PAYLOAD",
            "message": f"分析过程出错: {exc}",
        }

    if thread_id:
        await _push_ws({
            "type": "analysis_returned",
            "thread_id": thread_id,
            "analysis": contract.model_dump(mode="json"),
        })

    return _compact_analysis(contract)


@tool
async def cascade_rewrite(analysis_id: str, niche: str) -> dict:
    """按指定赛道(niche)把已分析的视频改写成新脚本，返回脚本和分镜。

    **何时调用**：刚调完 cascade_analyze 拿到 analysis_id，并且已经知道用户的
    赛道(niche)时，立刻调用。不要等用户再确认一次。

    **参数**：
    - analysis_id (str)：必须是 cascade_analyze 返回的 "ana_xxx" 格式。
    - niche (str)：必须严格是以下三个值之一，其他值会被拒绝：
        - "baomam_fushi" (宝妈辅食)
        - "yuer_richang" (育儿日常)
        - "jiating_chufang" (家庭厨房)

    **返回**：
    - 成功：{"rewrite_id": "rw_...", "analysis_id": "ana_...", "niche": "...",
              "script_markdown": "...", "shots_count": int, "confidence": float,
              "cost_cny": float}
    - 失败：{"error": "FAILURE_CODE", "message": "..."} 或
            {"error": "UNKNOWN_NICHE", "message": "..."} 或
            {"error": "ANALYSIS_NOT_FOUND", "message": "..."}

    成功后系统会自动把脚本和分镜推到前端 CardStack 渲染。chat 回复保持极简
    一句话即可，**不要复述脚本内容**——前端会显示完整版本。

    **缓存**：同一 (analysis_id, niche, user_id) 在 24 小时内返回同一个结果，
    重复调用不会额外计费。
    """
    if niche not in SUPPORTED_NICHES:
        return {
            "error": "UNKNOWN_NICHE",
            "message": f"未知赛道 '{niche}'。合法值: {sorted(SUPPORTED_NICHES)}",
        }

    ctx = get_run_ctx()
    user_id = ctx.get("user_id") or "anonymous"
    thread_id = ctx.get("thread_id") or ""
    run_id = ctx.get("run_id")

    try:
        result = await request_rewrite(
            analysis_id=analysis_id,
            niche=niche,  # type: ignore[arg-type]  # Literal validated above
            user_id=user_id,
            run_id=run_id,
        )
    except LookupError:
        return {
            "error": "ANALYSIS_NOT_FOUND",
            "message": f"找不到 analysis_id={analysis_id}，请先 cascade_analyze",
        }
    except HardFailure as exc:
        p = _hardfailure_payload(exc)
        await _push_failure_frame(p["code"], p["hint"], p["actions"], p["request_id"], stage="rewrite")
        return {
            "error": exc.code.value,
            "message": exc.hint or "改写失败，请稍后重试",
        }
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "error": "S5_INVALID_PAYLOAD",
            "message": f"改写过程出错: {exc}",
        }

    if thread_id:
        await _push_ws({
            "type": "rewrite_returned",
            "thread_id": thread_id,
            "analysis_id": analysis_id,
            "rewrite": result.model_dump(mode="json"),
        })

    return {
        "rewrite_id": result.rewrite_id,
        "analysis_id": result.analysis_id,
        "niche": result.niche,
        "script_markdown": result.script_markdown,
        "shots_count": len(result.shots),
        "confidence": result.confidence,
        "cost_cny": result.cost_cny,
    }


def _make_image_provider() -> ApimartProvider:
    """Provider factory for first-frame generation.

    Hardcoded to Apimart for Phase 1: it's the cheap submit+poll path the rest
    of Cascade already uses for shot images. Wrapped (not modified) so we can
    swap to Google later without touching the tool logic.
    """
    return ApimartProvider()


@tool
async def cascade_generate_first_frame(rewrite_id: str, shot_index: int) -> dict:
    """为已改写脚本中的指定镜头生成一张首帧图，返回图片 URL。

    **何时调用**：
    - 用户消息以 `[generate_first_frame: shot_index=<N>]` 开头 → 立刻调本工具，
      `shot_index` 取标记里的 N，`rewrite_id` 取**最近一次 cascade_rewrite** 返回的 rw_xxx。
    - 用户自然语言说「为镜头 X 生成首帧」/「镜头 3 配个图」类话 → 同样调本工具。

    **参数**：
    - rewrite_id (str)：必须是 `rw_` 开头、由 `cascade_rewrite` 返回过的 id。
    - shot_index (int)：1-based 镜号，必须在该 rewrite 的 shots 范围内（1..shots_count）。

    **返回**：
    - 成功：{"shot_index": N, "image_url": "https://...", "cost_cny": float}
    - 失败：{"error": "REWRITE_NOT_FOUND" | "SHOT_NOT_FOUND" | "S7_UPSTREAM_TIMEOUT"
              | "S8_UPSTREAM_REFUSED" | "S5_INVALID_PAYLOAD", "message": "..."}

    成功后系统会自动推 WS 帧 `shot_first_frame_returned` 让对应 ShotCard 渲染图片。
    chat 回复极简一句话即可，例如「镜头 N 首帧好了。」**不要把 URL 复述给用户**。

    **成本**：每次调用约 ¥1.50（Apimart 单图）。被 cost_guard 兜底，超额会返回 S8 错误。
    """
    ctx = get_run_ctx()
    user_id = ctx.get("user_id") or "anonymous"
    thread_id = ctx.get("thread_id") or ""
    run_id = ctx.get("run_id")

    # 1. Resolve rewrite + shot
    raw = await load_rewrite_by_id(rewrite_id)
    if raw is None:
        return {
            "error": "REWRITE_NOT_FOUND",
            "message": f"找不到 rewrite_id={rewrite_id}，请先 cascade_rewrite",
        }
    try:
        rewrite = RewriteResult.model_validate_json(raw)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "error": "S5_INVALID_PAYLOAD",
            "message": f"rewrite 解析失败: {exc}",
        }

    shot = next((s for s in rewrite.shots if s.shot_index == shot_index), None)
    if shot is None:
        return {
            "error": "SHOT_NOT_FOUND",
            "message": (
                f"镜号 {shot_index} 不在 rewrite={rewrite_id} 的范围内"
                f"（合法 1..{len(rewrite.shots)}）"
            ),
        }

    # 2. Cost guard — refuse before spend.
    try:
        await cost_guard(user_id=user_id, run_id=run_id or "anonymous", predicted_cost_cny=PREDICT_SHOT_IMAGE_CNY)
    except HardFailure as exc:
        p = _hardfailure_payload(exc)
        await _push_failure_frame(p["code"], p["hint"], p["actions"], p["request_id"], stage="first_frame")
        return {
            "error": exc.code.value,
            "message": exc.hint or "本轮额度不足，先把已生成的内容用起来",
        }

    # 3. Provider call. Wrap, don't modify — see _make_image_provider docstring.
    provider = _make_image_provider()
    prompt = shot.visual
    try:
        result = await provider.generate(prompt=prompt, size="16:9", resolution="2k")
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "error": "S5_INVALID_PAYLOAD",
            "message": f"生图调用出错: {exc}",
        }

    if "error" in result:
        err = str(result.get("error", ""))
        code = "S7_UPSTREAM_TIMEOUT" if err == "timeout" else "S8_UPSTREAM_REFUSED"
        return {"error": code, "message": err or "生图失败"}

    image_url = result.get("url")
    if not image_url:
        return {"error": "S5_INVALID_PAYLOAD", "message": "上游未返回 url"}

    # 4. Push WS frame so the matching ShotCard re-renders live.
    if thread_id:
        await _push_ws({
            "type": "shot_first_frame_returned",
            "thread_id": thread_id,
            "rewrite_id": rewrite_id,
            "shot_index": shot_index,
            "image_url": image_url,
        })

    # 5. Emit telemetry. Cost in fen for accounting (cost_guard reads payload.cost_fen).
    try:
        await emit(
            EventName.SHOT_FIRST_FRAME_RETURNED,
            user_id=user_id,
            run_id=run_id,
            payload={
                "rewrite_id": rewrite_id,
                "shot_index": shot_index,
                "cost_cny": PREDICT_SHOT_IMAGE_CNY,
            },
        )
    except Exception:
        # Telemetry must never break the user-visible return path.
        pass

    return {
        "shot_index": shot_index,
        "image_url": image_url,
        "cost_cny": PREDICT_SHOT_IMAGE_CNY,
    }


# ---------- cascade_ask (W4D5) ----------


_ASK_SYSTEM_PROMPT = (
    "你是一位中文短视频分析师, 基于给定 analysis JSON 回答用户问题, "
    "不超过 300 字, 不要复述已有字段。只用给定 analysis 里能 grounded 的事实, "
    "不要瞎编原片里没有的东西。"
)
# Hard length caps — keep the LLM context tight + cap WS frame size.
_ASK_QUESTION_MAX = 200
_ASK_ANSWER_MAX = 300
_ASK_TRANSCRIPT_PREVIEW = 500


def _ask_prompt(contract: Any, question: str) -> str:
    """Pack viral_analysis + first 3 scenes + transcript-head into a tight prompt.

    Token budget rationale: ~700 chars for viral_analysis JSON, ~600 chars
    for 3 scene summaries, ~500 chars transcript preview, ~200 chars
    question = ~2k input chars (≈ 1k tokens for Chinese). With ~300-char
    answer cap, one call ≈ ¥0.05 on Doubao-seed pricing.
    """
    va_json = contract.viral_analysis.model_dump_json()
    scene_lines = []
    for scene in contract.scenes[:3]:
        scene_lines.append(
            f"#{scene.scene_index} [{scene.timestamp_start:.0f}-{scene.timestamp_end:.0f}s] "
            f"{scene.scene} | 画面: {scene.visual_content} | 对白: {scene.dialogue_and_narration[:60]}"
        )
    transcript = contract.full_transcript[:_ASK_TRANSCRIPT_PREVIEW] if contract.full_transcript else "（无逐字稿）"
    return (
        f"## analysis (viral_analysis JSON)\n{va_json}\n\n"
        f"## 前 3 镜头\n" + "\n".join(scene_lines) + "\n\n"
        f"## 逐字脚本前 500 字\n{transcript}\n\n"
        f"## 用户问题\n{question.strip()[:_ASK_QUESTION_MAX]}\n\n"
        f"请直接答, 不超过 300 字, 不要复述字段名。"
    )


async def _call_ask_llm(prompt: str) -> str:
    """One-shot LLM call. Returns the answer text (truncated to 300 chars)."""
    from langchain_core.messages import HumanMessage, SystemMessage

    model = get_chat_model()
    messages = [SystemMessage(content=_ASK_SYSTEM_PROMPT), HumanMessage(content=prompt)]
    result = await model.ainvoke(messages)
    text = getattr(result, "content", "") or ""
    if isinstance(text, list):
        # Some providers return a list of content parts; join the text parts.
        text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
    return str(text).strip()[:_ASK_ANSWER_MAX]


@tool
async def cascade_ask(analysis_id: str, question: str) -> dict:
    """对某条 analysis 做自由 Q&A，返回 ≤300 字中文回答。

    **何时调用**：
    - 用户消息开头带 `[ask: <question>]` 标记 → 立刻调本工具，`question` 取标记里的
      内容，`analysis_id` 取**最近一次 cascade_analyze** 返回的 ana_id。
    - 用户在 chat 里自然提问且明显**不是**改写也不是生图 → 同样调本工具。
      触发例子：
        - 「为啥这条 BGM 让我想起 90s 港片」
        - 「这条用户哪些情绪节点最容易流失」
        - 「这种风格适合我做吗」
        - 「原片摆盘有什么细节我没看出来」

    **参数**：
    - analysis_id (str)：cascade_analyze 返回的 `ana_xxx`。
    - question (str)：用户的中文问题，≤200 字。超出会被截断。

    **返回**：
    - 成功：{"answer": "≤300 字中文回答", "analysis_id": "ana_xxx"}
    - 失败：{"error": "ANALYSIS_NOT_FOUND" | "S5_INVALID_PAYLOAD" | "S8_UPSTREAM_REFUSED",
              "message": "人话"}

    **回 chat 时**：把 `answer` 字段**原文回给用户**，**不要**再加套话或复述问题。
    系统会同时推 WS 帧 `analysis_answer_returned` 让前端 chat 渲染样式化气泡（如果它愿意）。

    **成本**：每次 ¥0.05；被 cost_guard 兜底，超额会返回 S8。
    """
    ctx = get_run_ctx()
    user_id = ctx.get("user_id") or "anonymous"
    thread_id = ctx.get("thread_id") or ""
    run_id = ctx.get("run_id")

    if not isinstance(analysis_id, str) or not analysis_id.strip():
        return {"error": "S5_INVALID_PAYLOAD", "message": "analysis_id 不能为空"}
    if not isinstance(question, str) or not question.strip():
        return {"error": "S5_INVALID_PAYLOAD", "message": "question 不能为空"}

    contract = await load_analysis(analysis_id.strip())
    if contract is None:
        return {
            "error": "ANALYSIS_NOT_FOUND",
            "message": f"找不到 analysis_id={analysis_id}，请先 cascade_analyze",
        }

    # Cost guard — refuse before LLM spend.
    try:
        await cost_guard(
            user_id=user_id,
            run_id=run_id or "anonymous",
            predicted_cost_cny=PREDICT_ASK_CNY,
        )
    except HardFailure as exc:
        p = _hardfailure_payload(exc)
        await _push_failure_frame(p["code"], p["hint"], p["actions"], p["request_id"], stage="ask")
        return {
            "error": exc.code.value,
            "message": exc.hint or "本轮额度不足，先把已生成的内容用起来",
        }

    prompt = _ask_prompt(contract, question)
    try:
        raw_answer = await _call_ask_llm(prompt)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive; LLM transport varies
        return {
            "error": "S8_UPSTREAM_REFUSED",
            "message": f"自由提问 LLM 调用失败: {exc}",
        }

    # Defense in depth: even if `_call_ask_llm` returns more than 300 chars
    # (test-double monkeypatching, or future LLM that ignores the system
    # prompt's length cap), enforce here so the WS frame stays bounded.
    answer = (raw_answer or "").strip()[:_ASK_ANSWER_MAX]
    if not answer:
        return {"error": "S5_INVALID_PAYLOAD", "message": "LLM 返回了空回答"}

    if thread_id:
        await _push_ws({
            "type": "analysis_answer_returned",
            "thread_id": thread_id,
            "analysis_id": contract.analysis_id,
            "question": question.strip()[:_ASK_QUESTION_MAX],
            "answer": answer,
        })

    # Emit cost telemetry — sum_generation_cost reads cost_cny for the cap.
    try:
        await emit(
            EventName.ANALYSIS_ANSWER_RETURNED,
            user_id=user_id,
            run_id=run_id,
            payload={
                "analysis_id": contract.analysis_id,
                "question_chars": len(question),
                "answer_chars": len(answer),
                "cost_cny": PREDICT_ASK_CNY,
                "model": current_model_name(),
            },
        )
    except Exception:
        # Telemetry must never break the user-visible return path.
        pass

    return {"answer": answer, "analysis_id": contract.analysis_id}


__all__ = [
    "cascade_analyze",
    "cascade_rewrite",
    "cascade_generate_first_frame",
    "cascade_ask",
]
