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
import sys
from typing import Any, Sequence

from langchain_core.tools import tool
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.cost_guard import (
    PREDICT_ASK_CNY,
    PREDICT_SHOT_IMAGE_CNY,
    PREDICT_VIDEO_SECOND_CNY,
    cost_guard,
)
from agent.cascade.mediakit.clip_extractor import media_root
from agent.cascade.event_names import EventName
from agent.cascade.events import emit
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.hook_taxonomy import detect_hooks_in_text, infer_niche_from_hooks
from agent.cascade.rewrite_service import (
    SUPPORTED_NICHES,
    RewriteResult,
    request_rewrite,
)
from agent.cascade.storage import (
    load_analysis,
    load_film,
    load_rewrite_by_id,
    load_shot_assets,
    load_shot_image,
    record_analysis,
    record_film,
    record_rewrite,
    record_shot_image,
    record_shot_video,
)
from agent.llm_factory import current_model_name, get_chat_model
from agent.tools.compose import _download, compose_local_files
from agent.tools.generation import get_provider as _get_image_provider, image_gen_ready
from agent.tools.video_generation import SeedanceProvider
from agent.transport.runtime_ctx import get_run_ctx


async def _push_ws(payload: dict[str, Any]) -> None:
    """Best-effort WS frame push for tool-emitted frames (analysis_returned /
    rewrite_returned / analysis_failed / shot_first_frame_returned).

    W5D4 P0-A — route through `notify.send_to_user` (live-registry lookup) instead
    of the ws captured into RUN_CTX at run-start. A run lives 20–50s; if its
    socket died and the browser reconnected on a new ws, the old code pushed
    these (the *result* frames!) to the dead socket and they vanished — the
    dominant "卡 95% / 拆解空白" cause. The registry resolves the current live
    socket at send time. `fallback_ws` keeps the no-registry test path working.
    """
    from agent.transport import notify

    ctx = get_run_ctx()
    user_id = ctx.get("user_id")
    if not user_id:
        return
    await notify.send_to_user(user_id, payload, fallback_ws=ctx.get("ws"))


async def _push_shot_error(rewrite_id: str, shot_index: int, message: str) -> None:
    """Per-shot draft-image failure → flip *that* shot to 失败/重试 instantly via the
    shot_first_frame_returned frame's `error` field. Deliberately NOT a global
    analysis_failed (that nukes the whole result page) and not silent (the frontend
    would otherwise sit on its spinner until the 75s timeout). thread_id empty =
    RUN_CTX absent (non-WS caller) → skip, the return value still informs the caller."""
    thread_id = get_run_ctx().get("thread_id") or ""
    if not thread_id:
        return
    await _push_ws({
        "type": "shot_first_frame_returned",
        "thread_id": thread_id,
        "rewrite_id": rewrite_id,
        "shot_index": shot_index,
        "image_url": "",
        "error": message,
    })


async def _push_failure_frame(
    code: str,
    hint: str,
    actions: Sequence[str],
    request_id: str = "",
    stage: str = "analysis",
) -> None:
    """W5D3 Bug #2 — push structured analysis_failed WS frame from tool
    HardFailure paths. Lets frontend setFailure cleanly without relying on
    the agent_runner outer except (which only fires for uncaught exceptions,
    not tools that catch HardFailure and return error dicts to the LLM).

    Empty thread_id means RUN_CTX was never set — that's always a programming
    bug (tool called outside a WS turn). Log to stderr so the next CI / dev
    run catches it; we still return without raising so we don't break the
    agent loop on this kind of misuse.
    """
    ctx = get_run_ctx()
    thread_id = ctx.get("thread_id")
    if not thread_id:
        print(
            f"[BUG] _push_failure_frame called outside RUN_CTX "
            f"(code={code}, stage={stage}) — silently dropping frame",
            file=sys.stderr,
            flush=True,
        )
        return
    # W5D4 review B5 — record the failure on the live run context so run_agent
    # marks the run lifecycle `failed` (not `done`) after the stream completes.
    # The tool caught this HardFailure and returns an error dict to the LLM, so
    # the agent loop ends normally and would otherwise be recorded `done` — a
    # reconnecting client then replays a "done" with no failure and loses the
    # recovery hint. We mutate the ctx dict in place on purpose: a child frame's
    # `set_run_ctx(...)` wouldn't propagate *up* to run_agent's frame, but the
    # dict object is shared across the task, so an in-place write is visible
    # there. First failure in a turn wins (don't clobber an earlier stage's).
    if ctx.get("tool_failure") is None:
        ctx["tool_failure"] = {
            "code": code,
            "hint": hint,
            "actions": list(actions),
            "request_id": request_id,
        }
    await _push_ws(
        {
            "type": "analysis_failed",
            "thread_id": thread_id,
            "code": code,
            "hint": hint,
            "actions": list(actions),  # copy — caller may mutate
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
        # W5D4 — record the thread→analysis pointer BEFORE the push so a reload
        # right after completion can replay it even if the WS frame is lost.
        try:
            await record_analysis(user_id, thread_id, contract.analysis_id)
        except Exception:  # persistence is best-effort; never block the result
            pass
        await _push_ws({
            "type": "analysis_returned",
            "thread_id": thread_id,
            "analysis": contract.model_dump(mode="json"),
        })

    return _compact_analysis(contract)


@tool
async def cascade_rewrite(analysis_id: str, niche: str, topic: str = "") -> dict:
    """把已分析的视频改写成创作者自己的版本(脚本 + 分镜)。

    **何时调用**：刚调完 cascade_analyze 拿到 analysis_id，用户主动要「改成我的
    版本」时，立刻调用。不要等用户再确认一次。

    **参数**：
    - analysis_id (str)：必须是 cascade_analyze 返回的 "ana_xxx" 格式。
    - niche (str)：改写路径，合法值：
        - "generic" (通用代笔，**去 niche 后的默认**——任何题材都走这个)
        - "baomam_fushi" / "yuer_richang" / "jiating_chufang" (旧 3 赛道，向后兼容)
      其他值会被拒绝。**默认用 "generic"**，除非用户明确点了旧赛道。
    - topic (str, 可选)：用户给的一句话主题(如「免烤提拉米苏」)。**仅 generic 路径
      使用**，把改写导向这个题材;留空则纯按源片骨架通用改写。旧 3 赛道忽略此参数。

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
            # generic 路径用一句话主题导向;空串归一为 None(service 把 None 当无主题)。
            topic=(topic.strip() or None),
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
        # W5D4 — persist thread→rewrite pointer before push (reload replay).
        try:
            await record_rewrite(user_id, thread_id, result.rewrite_id)
        except Exception:
            pass
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


def _make_image_provider():
    """Provider factory for first-frame generation — switches on IMAGE_GEN_PROVIDER
    (seedream 火山 / apimart 中转 / google 跨境). Wrapped so the tool logic doesn't
    care which backend生图; all expose `.generate(prompt, size, resolution, image_urls)
    → {url}|{error}`. 2026-06-02: 默认推荐 seedream(复用 ARK key,境内合规一致)。"""
    return _get_image_provider()


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

    # 1b. Fail fast + friendly when 生图 isn't configured (prod missing
    # IMAGE_GEN_API_KEY) — don't burn a provider round-trip that returns a cryptic
    # "invalid API key", and don't make the user sit on the spinner until the 75s
    # frontend timeout. Push a per-shot error so the card flips to 失败/重试 at once.
    if not image_gen_ready():
        msg = "草稿图功能还没开通(管理员需配置生图密钥),其他都能正常用"
        await _push_shot_error(rewrite_id, shot_index, msg)
        return {"error": "IMAGE_GEN_NOT_CONFIGURED", "message": msg}

    # 2. Cost guard — refuse before spend. Per-shot error (NOT a global failure
    # frame: that nukes the whole result page; NOT silent: else the card spins to
    # the 75s timeout). Director also surfaces the return value in chat.
    try:
        await cost_guard(user_id=user_id, run_id=run_id or "anonymous", predicted_cost_cny=PREDICT_SHOT_IMAGE_CNY)
    except HardFailure as exc:
        msg = exc.hint or "本轮额度不足，先把已生成的内容用起来"
        await _push_shot_error(rewrite_id, shot_index, msg)
        return {"error": exc.code.value, "message": msg}

    # 3. Provider call. Wrap, don't modify — see _make_image_provider docstring.
    provider = _make_image_provider()
    prompt = shot.visual
    _RETRY_MSG = "这张草稿图没生成成功,点重试试试"
    try:
        result = await provider.generate(prompt=prompt, size="16:9", resolution="2k")
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        await _push_shot_error(rewrite_id, shot_index, _RETRY_MSG)
        return {"error": "S5_INVALID_PAYLOAD", "message": f"生图调用出错: {exc}"}

    if "error" in result:
        err = str(result.get("error", ""))
        code = "S7_UPSTREAM_TIMEOUT" if err == "timeout" else "S8_UPSTREAM_REFUSED"
        await _push_shot_error(rewrite_id, shot_index, _RETRY_MSG)
        return {"error": code, "message": err or "生图失败"}

    image_url = result.get("url")
    if not image_url:
        await _push_shot_error(rewrite_id, shot_index, _RETRY_MSG)
        return {"error": "S5_INVALID_PAYLOAD", "message": "上游未返回 url"}

    # 3b. Persist the 草稿图 URL — the video leg (cascade_generate_shot_video) reads
    # it for image-grounding, and session reload replays it. Best-effort.
    try:
        await record_shot_image(rewrite_id, shot_index, image_url)
    except Exception:
        pass

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


# ---------- cascade_generate_shot_video + cascade_compose_film (视频闭环) ----------


_SHOT_VIDEO_SECONDS = 5  # 单镜短片时长(秒);成本 = 秒 × PREDICT_VIDEO_SECOND_CNY ≈ ¥1.5
_VIDEO_RETRY_MSG = "这条视频没生成成功,点重试试试"


async def _push_shot_video(
    user_id: str,
    thread_id: str,
    rewrite_id: str,
    shot_index: int,
    *,
    video_url: str = "",
    error: str | None = None,
) -> None:
    """Push shot_video_returned to user_id via the live registry. Safe to call from
    a background poll task (does NOT read RUN_CTX — that turn is long gone; user_id/
    thread_id are captured at submit time)."""
    if not thread_id or not user_id:
        return
    from agent.transport import notify

    await notify.send_to_user(
        user_id,
        {
            "type": "shot_video_returned",
            "thread_id": thread_id,
            "rewrite_id": rewrite_id,
            "shot_index": shot_index,
            "video_url": video_url,
            "error": error,
        },
    )


async def _poll_shot_video(
    provider: SeedanceProvider,
    task_id: str,
    user_id: str,
    thread_id: str,
    rewrite_id: str,
    shot_index: int,
) -> None:
    """后台轮询 Seedance 任务 → 成功下载落 /media 持久 → 持久化 + 推帧。失败推单镜 error。
    脱离 agent turn 存活(asyncio.create_task);用捕获的 user_id/thread_id,不读 RUN_CTX。"""
    try:
        result = await provider.poll(task_id)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[shot_video] poll 异常 rewrite={rewrite_id} shot={shot_index}: {exc}")
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, error=_VIDEO_RETRY_MSG)
        return

    src_url = result.get("video_url") if isinstance(result, dict) else None
    if not src_url:
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, error=_VIDEO_RETRY_MSG)
        return

    # ARK 视频 URL 会过期 → 必须落 /media 持久(合成段读本地文件)。下载失败=视频失败
    # (不回退临时 URL,否则过期后合成/重看全断)。
    try:
        out_dir = media_root() / rewrite_id
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"shot_{shot_index}.mp4"
        await _download(src_url, str(dest))
        public_url = f"/media/{rewrite_id}/shot_{shot_index}.mp4"
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[shot_video] 落盘失败 rewrite={rewrite_id} shot={shot_index}: {exc}")
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, error=_VIDEO_RETRY_MSG)
        return

    try:
        await record_shot_video(rewrite_id, shot_index, public_url)
    except Exception:
        pass
    await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, video_url=public_url)
    try:
        await emit(
            EventName.SHOT_VIDEO_RETURNED,
            user_id=user_id,
            run_id=None,
            payload={
                "rewrite_id": rewrite_id,
                "shot_index": shot_index,
                "cost_cny": _SHOT_VIDEO_SECONDS * PREDICT_VIDEO_SECOND_CNY,
            },
        )
    except Exception:
        pass


@tool
async def cascade_generate_shot_video(rewrite_id: str, shot_index: int) -> dict:
    """根据某镜的草稿图生成一段图生视频(image-grounded,约几分钟,完成后自动推送)。

    **何时调用**：
    - 用户消息以 `[generate_shot_video: shot_index=<N>]` 开头 → 立刻调本工具,
      `shot_index` 取标记里的 N,`rewrite_id` 取**最近一次 cascade_rewrite** 的 rw_xxx。
    - 用户自然语言说「把镜头 X 生成视频」/「这条做成视频」类话 → 同样调本工具。

    **前置**:该镜必须**已经生成过草稿图**(cascade_generate_first_frame)——视频是
    image-grounded,以草稿图为首帧。没有草稿图会返回 NO_SHOT_IMAGE。

    **参数**：rewrite_id(rw_ 开头)、shot_index(1-based,在该 rewrite 镜头范围内)。

    **返回**：
    - 已提交:{"shot_index": N, "task_id": "...", "status": "submitted", "message": "..."}
      ——视频要几分钟,后台生成,好了系统自动推帧渲染。**chat 回复一句「在生成第 N 条镜头
      的视频了,几分钟后自动出现」即可,不要轮询、不要复述。**
    - 已有缓存:{"shot_index": N, "video_url": "...", "cached": true}
    - 失败:{"error": "...", "message": "..."}

    **成本**：约 ¥1.5(5 秒,Seedance)。cost_guard 兜底。
    """
    ctx = get_run_ctx()
    user_id = ctx.get("user_id") or "anonymous"
    thread_id = ctx.get("thread_id") or ""
    run_id = ctx.get("run_id")

    raw = await load_rewrite_by_id(rewrite_id)
    if raw is None:
        return {"error": "REWRITE_NOT_FOUND", "message": f"找不到 rewrite_id={rewrite_id},请先 cascade_rewrite"}
    try:
        rewrite = RewriteResult.model_validate_json(raw)
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": "S5_INVALID_PAYLOAD", "message": f"rewrite 解析失败: {exc}"}

    shot = next((s for s in rewrite.shots if s.shot_index == shot_index), None)
    if shot is None:
        return {
            "error": "SHOT_NOT_FOUND",
            "message": f"镜号 {shot_index} 不在 rewrite={rewrite_id} 范围内(合法 1..{len(rewrite.shots)})",
        }

    # 幂等:已生成过该镜视频 → 直接回推已存 URL,不重复烧钱。
    assets = {a["shot_index"]: a for a in await load_shot_assets(rewrite_id)}
    existing = assets.get(shot_index)
    if existing and existing.get("video_url"):
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, video_url=existing["video_url"])
        return {"shot_index": shot_index, "video_url": existing["video_url"], "cached": True}

    # image-grounded → 必须先有草稿图。
    image_url = (existing or {}).get("image_url") or await load_shot_image(rewrite_id, shot_index)
    if not image_url:
        msg = "先生成这条镜头的草稿图,再用它生成视频"
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, error=msg)
        return {"error": "NO_SHOT_IMAGE", "message": msg}

    # cost guard(5s)。触顶 → 推单镜 error(不 nuke 结果页),Director 也在 chat 提示。
    try:
        await cost_guard(
            user_id=user_id,
            run_id=run_id or "anonymous",
            predicted_cost_cny=_SHOT_VIDEO_SECONDS * PREDICT_VIDEO_SECOND_CNY,
        )
    except HardFailure as exc:
        msg = exc.hint or "本轮额度不足,先把已生成的用起来"
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, error=msg)
        return {"error": exc.code.value, "message": msg}

    # 提交 Seedance(图生视频)。提交快(~1-2s);poll 慢(几分钟)→ 丢后台。
    provider = SeedanceProvider()
    try:
        submitted = await provider.submit(
            prompt=shot.visual,
            duration=_SHOT_VIDEO_SECONDS,
            ratio="16:9",
            image_urls=[image_url],
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, error=_VIDEO_RETRY_MSG)
        return {"error": "S5_INVALID_PAYLOAD", "message": f"生视频调用出错: {exc}"}

    if "error" in submitted:
        await _push_shot_video(user_id, thread_id, rewrite_id, shot_index, error=_VIDEO_RETRY_MSG)
        return {"error": "S8_UPSTREAM_REFUSED", "message": submitted.get("error", "生视频提交失败")}

    task_id = submitted.get("task_id")
    # 后台轮询 → 落盘 → 持久化 → 推帧。脱离本 turn 存活。
    asyncio.create_task(_poll_shot_video(provider, task_id, user_id, thread_id, rewrite_id, shot_index))

    return {
        "shot_index": shot_index,
        "task_id": task_id,
        "status": "submitted",
        "message": "已开始生成视频,约几分钟,好了自动出现",
    }


async def _push_film(user_id: str, thread_id: str, rewrite_id: str, *, film_url: str = "", error: str | None = None) -> None:
    if not thread_id or not user_id:
        return
    from agent.transport import notify

    await notify.send_to_user(
        user_id,
        {"type": "film_returned", "thread_id": thread_id, "rewrite_id": rewrite_id, "film_url": film_url, "error": error},
    )


async def _compose_film_bg(user_id: str, thread_id: str, rewrite_id: str, local_paths: list[str]) -> None:
    """后台:本地分镜片 ffmpeg 拼接 → 落 /media/<rid>/film.mp4 → 持久化 + 推帧。"""
    try:
        data = await compose_local_files(local_paths)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[film] 合成异常 rewrite={rewrite_id}: {exc}")
        await _push_film(user_id, thread_id, rewrite_id, error="合成失败,稍后重试")
        return
    if not data:
        await _push_film(user_id, thread_id, rewrite_id, error="合成失败,稍后重试")
        return
    try:
        out_dir = media_root() / rewrite_id
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "film.mp4"
        dest.write_bytes(data)
        film_url = f"/media/{rewrite_id}/film.mp4"
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[film] 落盘失败 rewrite={rewrite_id}: {exc}")
        await _push_film(user_id, thread_id, rewrite_id, error="合成失败,稍后重试")
        return
    try:
        await record_film(rewrite_id, film_url)
    except Exception:
        pass
    await _push_film(user_id, thread_id, rewrite_id, film_url=film_url)
    try:
        await emit(EventName.FILM_RETURNED, user_id=user_id, run_id=None, payload={"rewrite_id": rewrite_id})
    except Exception:
        pass


@tool
async def cascade_compose_film(rewrite_id: str) -> dict:
    """把该 rewrite 已生成的逐镜视频按镜号拼成一条整片(本地 ffmpeg 合成,完成后自动推送)。

    **何时调用**：
    - 用户消息以 `[compose_film]` 开头 → 立刻调本工具,`rewrite_id` 取最近一次 cascade_rewrite 的 rw_xxx。
    - 用户说「合成整片」/「拼成一条」类话 → 同样调本工具。

    **前置**:至少有 1 条镜头视频(cascade_generate_shot_video)。

    **返回**:
    - 已提交:{"status": "composing", "shots": N, "message": "..."} —— 合成要点时间,后台做,
      好了自动推帧。chat 一句「在合成整片了,稍等」即可。
    - 已有缓存:{"film_url": "...", "cached": true}
    - 失败:{"error": "...", "message": "..."}

    **成本**:免费(本地 ffmpeg 拼接,无模型调用)。
    """
    ctx = get_run_ctx()
    user_id = ctx.get("user_id") or "anonymous"
    thread_id = ctx.get("thread_id") or ""

    raw = await load_rewrite_by_id(rewrite_id)
    if raw is None:
        return {"error": "REWRITE_NOT_FOUND", "message": f"找不到 rewrite_id={rewrite_id},请先 cascade_rewrite"}

    # 幂等:已合成 → 直接回推。
    existing_film = await load_film(rewrite_id)
    if existing_film:
        await _push_film(user_id, thread_id, rewrite_id, film_url=existing_film)
        return {"film_url": existing_film, "cached": True}

    assets = await load_shot_assets(rewrite_id)
    # 视频 URL 都是 /media/<rid>/shot_<i>.mp4(本地持久)→ 还原本地路径按镜号排序。
    root = media_root()
    local_paths: list[str] = []
    for a in sorted(assets, key=lambda x: x["shot_index"]):
        vu = a.get("video_url")
        if not vu:
            continue
        rel = vu[len("/media/"):] if vu.startswith("/media/") else None
        if rel:
            local_paths.append(str(root / rel))
    if not local_paths:
        return {"error": "NO_SHOT_VIDEOS", "message": "还没有镜头视频,先把镜头生成视频再合成整片"}

    asyncio.create_task(_compose_film_bg(user_id, thread_id, rewrite_id, local_paths))
    return {"status": "composing", "shots": len(local_paths), "message": "在合成整片了,稍等几十秒自动出现"}


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
    "cascade_generate_shot_video",
    "cascade_compose_film",
    "cascade_ask",
]
