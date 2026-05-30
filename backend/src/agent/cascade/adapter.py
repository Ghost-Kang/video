"""Cascade analysis adapter (P0-4).

normalize_analysis_result(raw) takes a best-effort JSON-like payload from any
upstream analyzer and returns a fully-validated CascadeAnalysisContract,
applying every fallback rule from docs/TOPRADOR_SCHEMA.md §5.

Karpathy review rule: never fail silently. Every fallback emits a Warning_.
Every unrecoverable issue raises HardFailure with a stable FailureCode.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from agent import config
from agent.cascade.contract import (
    AudioDim,
    CameraMovement,
    CascadeAnalysisContract,
    Platform,
    ProductionDim,
    Scene,
    SCHEMA_VERSION,
    Severity,
    ShotType,
    ViralAnalysis,
    Warning_,
)
from agent.cascade.failures import FailureCode, HardFailure, WarningCode
from agent.cascade.minor_audit import detect_minor_subjects


# toprador 爆点 10 维 fallback。2026-05-30 对齐 toprador:分析不再因缺
# replicable_formula 硬失败(那是改写专用字段,改写已暂挂)。
_VIRAL_FALLBACKS: dict[str, str] = {
    "summary": "未识别爆点总结",
    "theme": "未识别主题",
    "target_audience": "未识别目标人群",
    "material_benefit": "未识别素材利益点",
    "hook": "未识别开场钩子",
    "main_elements": "未识别主要元素",
    "micro_innovation": "未识别微创新方向",
    "pain_points": "未识别痛点需求",
    "emotion_trigger": "未识别情绪触发",
    "bgm_style": "未识别 BGM 风格",
}

# 每维允许的最大长度(与 contract.ViralAnalysis 对齐,留 1:1 防 ValidationError)。
_VIRAL_MAXLEN: dict[str, int] = {
    "summary": 400, "theme": 120, "target_audience": 200, "material_benefit": 300,
    "hook": 300, "main_elements": 300, "micro_innovation": 400, "pain_points": 300,
    "emotion_trigger": 200, "bgm_style": 200,
}

# 逐幕描述字段(toprador 视频分析维度)缺失时的兜底 + 最大长度。
_SCENE_TEXT_FALLBACKS: dict[str, str] = {
    "theme": "", "segment_note": "", "segment_description": "", "emotion": "",
    "visual_summary": "", "audio_summary": "", "audio_content": "无",
    "cinematography": "", "camera_position": "", "actors": "无",
    "on_screen_text": "无", "visual_presentation_style": "", "scene": "",
    "props_list": "无", "costume": "无", "lighting_and_color": "",
}
_SCENE_TEXT_MAXLEN: dict[str, int] = {
    "theme": 120, "segment_note": 300, "segment_description": 600, "emotion": 80,
    "visual_summary": 120, "audio_summary": 120, "audio_content": 600,
    "cinematography": 200, "camera_position": 120, "actors": 200,
    "on_screen_text": 400, "visual_presentation_style": 120, "scene": 300,
    "props_list": 300, "costume": 300, "lighting_and_color": 300,
}

# W4D5 audio 3-axis fallbacks. Phrase mirrors the prompt's `<n/a — storyline 未呈现>`
# fingerprint so dashboards filtering by W15 see consistent strings.
_AUDIO_FALLBACK = {
    "bgm": "n/a — storyline 未呈现",
    "voice_pace": "n/a — storyline 未呈现",
    "sound_effects": "n/a — storyline 未呈现",
}
# W4D5 production complexity fallback. solo_phone is the safe default for the
# Phase 1 创作者画像 — when in doubt assume one person + a phone.
_PRODUCTION_FALLBACK = {
    "cost_tier": "solo_phone",
    "estimated_hours": 1.0,
    "replaceable_anchors": [],
}

_KNOWN_PII_KEYS = frozenset({
    "author_uid", "author_handle", "author_avatar_url", "uid",
    # Added per Stage 4 compliance audit (PIPL minimization)
    "author_id", "author_nickname", "author_name",
    "ip_address", "user_ip", "user_phone",
})

_CROSS_BORDER_HOSTS = frozenset({"youtube.com", "youtu.be", "tiktok.com", "instagram.com"})

# Generated ULID-ish IDs use this prefix to make their provenance obvious in logs.
_AUTO_ID_PREFIX = "ana_auto_"


def normalize_analysis_result(raw: Any) -> CascadeAnalysisContract:
    """Normalize an upstream payload into the Cascade contract.

    Raises HardFailure for unrecoverable conditions; emits Warning_ entries
    on the returned contract for every silent substitution.
    """
    if not isinstance(raw, dict):
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"expected dict, got {type(raw).__name__}")

    warnings: list[Warning_] = []
    # Defensive copy — never mutate the caller's payload.
    data: dict[str, Any] = dict(raw)

    _strip_metadata(data)
    _strip_pii(data, warnings)

    _ensure_schema_version(data)
    _ensure_analysis_id(data, warnings)
    _ensure_source_url(data, warnings)
    _ensure_platform(data, warnings)
    _ensure_created_at(data)
    _ensure_model(data)
    _ensure_cost(data, warnings)
    _ensure_duration(data)

    # toprador 对齐:顶层一句话总览。缺失/非串则置空(contract 默认 "")。
    vs = data.get("video_summary")
    data["video_summary"] = vs.strip()[:600] if isinstance(vs, str) else ""

    _normalize_viral_analysis(data, warnings)
    _normalize_scenes(data, warnings)
    _audit_minor_subjects(data, warnings)
    _ensure_confidence(data, warnings)

    # Merge any pre-existing top-level warnings the upstream may have included.
    upstream_warnings = data.get("warnings") or []
    if isinstance(upstream_warnings, list):
        for w in upstream_warnings:
            if isinstance(w, dict) and "code" in w and "field" in w and "message" in w:
                w.setdefault("severity", Severity.WARN.value)
                warnings.append(Warning_(**w))
    data["warnings"] = [w.model_dump(mode="json") for w in warnings]

    # 防御:模型偶尔多吐 toprador 习惯键(total_duration/scene_count 顶层,
    # scene_id/time_range 逐幕)。contract 是 extra="forbid",白名单过滤掉,
    # 否则一个杂键就让整条分析 S5 失败。
    _scene_fields = set(Scene.model_fields.keys())
    if isinstance(data.get("scenes"), list):
        data["scenes"] = [
            {k: v for k, v in s.items() if k in _scene_fields} if isinstance(s, dict) else s
            for s in data["scenes"]
        ]
    _top_fields = set(CascadeAnalysisContract.model_fields.keys())
    data = {k: v for k, v in data.items() if k in _top_fields}

    try:
        return CascadeAnalysisContract(**data)
    except ValidationError as e:
        # Last-mile: anything still invalid is a payload problem we couldn't salvage.
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, str(e)) from e


# ---------- field-level normalizers ----------


def _strip_metadata(data: dict[str, Any]) -> None:
    """Silently remove leading-underscore keys.

    Convention: any top-level key starting with `_` is fixture / debug metadata
    that is not part of the contract. Stripping is silent — no warning.
    """
    for key in [k for k in data.keys() if isinstance(k, str) and k.startswith("_")]:
        del data[key]


def _strip_pii(data: dict[str, Any], warnings: list[Warning_]) -> None:
    """Silently remove known PII keys (per contract §7). One audit-warning emitted if anything was stripped."""
    stripped = False
    for key in list(data.keys()):
        if key in _KNOWN_PII_KEYS:
            del data[key]
            stripped = True
    if stripped:
        warnings.append(
            Warning_(
                code=WarningCode.W10_AUTHOR_PII_STRIPPED.value,
                field="<root>",
                message="upstream PII keys stripped",
                severity=Severity.INFO,
            )
        )


def _ensure_schema_version(data: dict[str, Any]) -> None:
    # Karpathy rule: schema_version is mandatory. Missing OR explicit-empty is a HARD failure —
    # an upstream that omits or blanks this field is signalling active corruption.
    if "schema_version" not in data:
        raise HardFailure(FailureCode.S2_VERSION_MISMATCH, "schema_version field missing")
    raw_version = data["schema_version"]
    if not isinstance(raw_version, str) or not raw_version.strip():
        raise HardFailure(FailureCode.S2_VERSION_MISMATCH, f"schema_version is blank: {raw_version!r}")
    if not raw_version.startswith("1."):
        raise HardFailure(
            FailureCode.S2_VERSION_MISMATCH,
            f"schema_version={raw_version!r}; only 1.x is accepted in Phase 1",
        )


def _ensure_analysis_id(data: dict[str, Any], warnings: list[Warning_]) -> None:
    aid = data.get("analysis_id")
    if not isinstance(aid, str) or not aid.strip():
        data["analysis_id"] = f"{_AUTO_ID_PREFIX}{uuid.uuid4().hex[:16]}"
        warnings.append(
            Warning_(
                code=WarningCode.W1_AUTO_ID.value,
                field="analysis_id",
                message="upstream did not provide analysis_id; generated locally",
                severity=Severity.INFO,
            )
        )


def _ensure_source_url(data: dict[str, Any], warnings: list[Warning_]) -> None:
    url = data.get("source_url")
    if not isinstance(url, str) or not url.strip():
        raise HardFailure(FailureCode.S1_NO_SOURCE_URL, "source_url missing or blank")
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise HardFailure(FailureCode.S1_NO_SOURCE_URL, f"source_url unparseable: {e}") from e
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HardFailure(
            FailureCode.S1_NO_SOURCE_URL,
            f"source_url must be http(s) with a host; got {url!r}",
        )
    host = parsed.netloc.lower()
    # Match either exact host or "www.X" style suffix.
    if any(host == h or host.endswith("." + h) for h in _CROSS_BORDER_HOSTS):
        if config.STRICT_CROSS_BORDER_REJECT:
            raise HardFailure(
                FailureCode.S9_CROSS_BORDER_BLOCKED,
                f"cross-border platform blocked: {host}",
            )
        warnings.append(
            Warning_(
                code=WarningCode.W9_CROSS_BORDER_SOURCE.value,
                field="source_url",
                message=f"cross-border platform: {host}",
                severity=Severity.INFO,
            )
        )


def _ensure_platform(data: dict[str, Any], warnings: list[Warning_]) -> None:
    p = data.get("platform")
    if not isinstance(p, str):
        data["platform"] = Platform.OTHER.value
    elif p not in {member.value for member in Platform}:
        data["platform"] = Platform.OTHER.value
    else:
        data["platform"] = p

    sniffed = _platform_from_url(str(data.get("source_url") or ""))
    if sniffed and data["platform"] != sniffed:
        original = data["platform"]
        data["platform"] = sniffed
        warnings.append(
            Warning_(
                code=WarningCode.W13_PLATFORM_URL_MISMATCH.value,
                field="platform",
                message=f"platform {original!r} disagrees with source_url host; using {sniffed!r}",
                severity=Severity.WARN,
            )
        )


def _platform_from_url(source_url: str) -> str | None:
    try:
        host = urlparse(source_url).netloc.lower()
    except ValueError:
        return None
    if (
        host == "xiaohongshu.com"
        or host.endswith(".xiaohongshu.com")
        or host == "xhslink.com"
        or host.endswith(".xhslink.com")
    ):
        return Platform.XIAOHONGSHU.value
    if host == "douyin.com" or host.endswith(".douyin.com"):
        return Platform.DOUYIN.value
    return None


def _ensure_created_at(data: dict[str, Any]) -> None:
    if "created_at" not in data or not data["created_at"]:
        data["created_at"] = datetime.now(timezone.utc).isoformat()


def _ensure_model(data: dict[str, Any]) -> None:
    if not isinstance(data.get("model"), str) or not data["model"].strip():
        data["model"] = "unknown"


def _ensure_cost(data: dict[str, Any], warnings: list[Warning_]) -> None:
    cost = data.get("cost_cny")
    if cost is None:
        data["cost_cny"] = 0.0
        warnings.append(
            Warning_(
                code=WarningCode.W8_COST_UNKNOWN.value,
                field="cost_cny",
                message="upstream did not report cost; G6 Phase 1 Gate measurement may be incomplete",
                severity=Severity.WARN,
            )
        )
        return
    try:
        cost_f = float(cost)
    except (TypeError, ValueError) as e:
        raise HardFailure(FailureCode.S6_NEGATIVE_COST, f"cost_cny not numeric: {cost!r}") from e
    if cost_f < 0:
        raise HardFailure(FailureCode.S6_NEGATIVE_COST, f"cost_cny={cost_f}")
    data["cost_cny"] = cost_f


def _ensure_duration(data: dict[str, Any]) -> None:
    d = data.get("duration_s")
    if d is None:
        # Derive from the last scene's timestamp_end if we can; otherwise mark 1 (Pydantic min)
        scenes = data.get("scenes")
        if isinstance(scenes, list) and scenes:
            last = scenes[-1]
            if isinstance(last, dict) and "timestamp_end" in last:
                try:
                    data["duration_s"] = max(1, int(round(float(last["timestamp_end"]))))
                    return
                except (TypeError, ValueError):
                    pass
        data["duration_s"] = 1


def _normalize_viral_analysis(data: dict[str, Any], warnings: list[Warning_]) -> None:
    va = data.get("viral_analysis")
    if not isinstance(va, dict):
        # toprador 对齐:整块缺失不再硬失败,给一份全兜底块 + 一条 warning。
        va = {}
        warnings.append(
            Warning_(
                code=WarningCode.W2_FALLBACK_USED.value,
                field="viral_analysis",
                message="viral_analysis block missing; used full fallback",
                severity=Severity.WARN,
            )
        )

    for key, fallback in _VIRAL_FALLBACKS.items():
        val = va.get(key)
        if not isinstance(val, str) or not val.strip():
            va[key] = fallback
            warnings.append(
                Warning_(
                    code=WarningCode.W2_FALLBACK_USED.value,
                    field=f"viral_analysis.{key}",
                    message=f"absent or blank; used fallback {fallback!r}",
                    severity=Severity.WARN,
                )
            )
        else:
            va[key] = val.strip()[: _VIRAL_MAXLEN[key]]

    # 遗留字段:存在则规整裁剪,缺失保持默认(改写暂挂期不强制)。
    for legacy in ("pacing", "climax", "visual_style", "emotional_arc",
                   "engagement_levers", "replicable_formula"):
        lv = va.get(legacy)
        va[legacy] = lv.strip()[:200] if isinstance(lv, str) else ""
    # audio/production 仍照旧兜底(无害,供暂挂的改写 + 既有 W15/W16 用例)。
    _normalize_audio_dim(va, warnings)
    _normalize_production_dim(va, warnings)

    data["viral_analysis"] = va
    # validate now so we get a focused error rather than a top-level one
    try:
        ViralAnalysis(**va)
    except ValidationError as e:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"viral_analysis: {e}") from e


def _normalize_audio_dim(va: dict[str, Any], warnings: list[Warning_]) -> None:
    """Backfill ViralAnalysis.audio with W15 warning if upstream omits the block.

    Three axes (bgm / voice_pace / sound_effects). Per-axis fallback when the
    full block is present but a single field is missing — partial fallback
    still emits W15 once with the offending axes listed.
    """
    raw = va.get("audio")
    if not isinstance(raw, dict):
        va["audio"] = dict(_AUDIO_FALLBACK)
        warnings.append(
            Warning_(
                code=WarningCode.W15_AUDIO_FALLBACK.value,
                field="viral_analysis.audio",
                message="audio block missing; used default 3-axis fallback",
                severity=Severity.WARN,
            )
        )
        return
    fixed: dict[str, str] = {}
    missing: list[str] = []
    for key, fallback in _AUDIO_FALLBACK.items():
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            fixed[key] = val.strip()[:80]
        else:
            fixed[key] = fallback
            missing.append(key)
    va["audio"] = fixed
    if missing:
        warnings.append(
            Warning_(
                code=WarningCode.W15_AUDIO_FALLBACK.value,
                field="viral_analysis.audio",
                message=f"audio axes missing → fallback: {missing}",
                severity=Severity.WARN,
            )
        )


def _normalize_production_dim(va: dict[str, Any], warnings: list[Warning_]) -> None:
    """Backfill ViralAnalysis.production with W16 warning when upstream omits it.

    Unlike audio, we don't emit a partial warning for individual missing axes —
    `replaceable_anchors` legitimately empties out (the prompt allows zero
    anchors) and `cost_tier` has a hard Literal so any junk falls to default.
    Only the whole-block-missing case warns.
    """
    raw = va.get("production")
    if not isinstance(raw, dict):
        va["production"] = dict(_PRODUCTION_FALLBACK)
        warnings.append(
            Warning_(
                code=WarningCode.W16_PRODUCTION_FALLBACK.value,
                field="viral_analysis.production",
                message="production block missing; used solo_phone fallback",
                severity=Severity.WARN,
            )
        )
        return
    fixed: dict[str, Any] = {}
    tier = raw.get("cost_tier")
    if isinstance(tier, str) and tier in {"solo_phone", "small_team", "post_heavy"}:
        fixed["cost_tier"] = tier
    else:
        fixed["cost_tier"] = "solo_phone"
    hours = raw.get("estimated_hours")
    try:
        hours_f = float(hours) if hours is not None else 1.0
    except (TypeError, ValueError):
        hours_f = 1.0
    fixed["estimated_hours"] = max(0.0, min(100.0, hours_f))
    anchors = raw.get("replaceable_anchors")
    if isinstance(anchors, list):
        # Keep only string items, trim, drop empties, cap at 10.
        clean = [str(a).strip()[:200] for a in anchors if isinstance(a, str) and str(a).strip()]
        fixed["replaceable_anchors"] = clean[:10]
    else:
        fixed["replaceable_anchors"] = []
    va["production"] = fixed


def _normalize_scenes(data: dict[str, Any], warnings: list[Warning_]) -> None:
    scenes_raw = data.get("scenes")
    if not isinstance(scenes_raw, list):
        raise HardFailure(FailureCode.S4_SCENES_LEN_OUT_OF_RANGE, "scenes not a list")

    # W5D2: 0-scene 仍然 hard fail — 说明上游完全没分析出内容,继续没意义。
    if len(scenes_raw) == 0:
        raise HardFailure(
            FailureCode.S4_SCENES_LEN_OUT_OF_RANGE,
            "scenes length 0",
        )
    # 1-2 scene 时复制最后一帧 pad 到 3,emit warning。豆包视觉模型偶尔在
    # 短/单镜视频上只返回 1-2 段,但下游 contract 需要 ≥3。pad 后用户看到
    # 的分析略冗余但流程不中断;UI 可以选择不显示重复段。
    original_count = len(scenes_raw)
    if original_count < 3:
        pad_source = dict(scenes_raw[-1])
        while len(scenes_raw) < 3:
            clone = dict(pad_source)
            # 调 scene_index 避免后续验证报重复;timestamp 沿用原值,前端
            # 渲染时按 scene_index 排序仍然合理。
            clone["scene_index"] = len(scenes_raw) + 1
            scenes_raw.append(clone)
        warnings.append(
            Warning_(
                code=WarningCode.W18_SCENES_PADDED.value,
                field="scenes",
                message=f"upstream returned {original_count} scenes; padded to 3",
                severity=Severity.WARN,
            )
        )

    if len(scenes_raw) > 12:
        kept = scenes_raw[:12]
        warnings.append(
            Warning_(
                code=WarningCode.W3_SCENES_TRUNCATED.value,
                field="scenes",
                message=f"truncated from {len(scenes_raw)} to 12",
                severity=Severity.WARN,
            )
        )
        scenes_raw = kept

    # First, sort by timestamp_start if necessary.
    def _ts(s: dict) -> float:
        try:
            return float(s.get("timestamp_start", 0.0))
        except (TypeError, ValueError):
            return 0.0

    needs_sort = False
    for i in range(1, len(scenes_raw)):
        if _ts(scenes_raw[i]) < _ts(scenes_raw[i - 1]):
            needs_sort = True
            break
    if needs_sort:
        scenes_raw = sorted(scenes_raw, key=_ts)
        warnings.append(
            Warning_(
                code=WarningCode.W5_TIMESTAMPS_SORTED.value,
                field="scenes",
                message="timestamps were not monotonic; reordered",
                severity=Severity.INFO,
            )
        )

    normalized: list[dict] = []
    for i, s in enumerate(scenes_raw, start=1):
        if not isinstance(s, dict):
            raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"scenes[{i - 1}] not a dict")
        ns = dict(s)
        ns["scene_index"] = i

        # 分镜标题 theme（toprador 对齐：取代旧的 scene label 作为标题）
        title = ns.get("theme")
        if not isinstance(title, str) or not title.strip():
            ns["theme"] = f"镜头 {i}"
            warnings.append(
                Warning_(
                    code=WarningCode.W4_GENERIC_SCENE_LABEL.value,
                    field=f"scenes[{i - 1}].theme",
                    message="scene theme absent; used generic",
                    severity=Severity.WARN,
                )
            )
        else:
            ns["theme"] = title.strip()[:120]

        # dialogue may be empty — that's OK (silent scene)
        d = ns.get("dialogue_and_narration")
        ns["dialogue_and_narration"] = d.strip()[:2000] if isinstance(d, str) else ""

        # visual_content is required non-empty
        vc = ns.get("visual_content")
        if not isinstance(vc, str) or not vc.strip():
            # Salvage: derive from theme / visual_summary / segment_description
            salvage = (
                (ns.get("visual_summary") if isinstance(ns.get("visual_summary"), str) else "")
                or (ns.get("segment_description") if isinstance(ns.get("segment_description"), str) else "")
                or ns["theme"]
            )
            ns["visual_content"] = (salvage or ns["theme"]).strip()[:800] or ns["theme"]
            warnings.append(
                Warning_(
                    code=WarningCode.W2_FALLBACK_USED.value,
                    field=f"scenes[{i - 1}].visual_content",
                    message="visual_content absent; derived from theme/summary",
                    severity=Severity.WARN,
                )
            )
        else:
            ns["visual_content"] = vc.strip()[:800]

        # toprador 逐幕描述维度：缺失填兜底,存在则裁剪到 contract 上限。
        for fkey, fdefault in _SCENE_TEXT_FALLBACKS.items():
            fv = ns.get(fkey)
            if isinstance(fv, str) and fv.strip():
                ns[fkey] = fv.strip()[: _SCENE_TEXT_MAXLEN[fkey]]
            else:
                ns[fkey] = fdefault

        # subject — optional. Distinguish three cases:
        #   - absent: leave None silently (true optional)
        #   - present-but-wrong-type: drop + warn (schema §5)
        #   - present-as-string: normalize
        if "subject" in ns:
            subj = ns["subject"]
            if subj is None:
                ns["subject"] = None
            elif isinstance(subj, str):
                ns["subject"] = subj.strip()[:80] if subj.strip() else None
            else:
                ns["subject"] = None
                warnings.append(
                    Warning_(
                        code=WarningCode.W2_FALLBACK_USED.value,
                        field=f"scenes[{i - 1}].subject",
                        message=f"subject was {type(subj).__name__}; expected string. dropped.",
                        severity=Severity.WARN,
                    )
                )
        else:
            ns["subject"] = None

        # enums — schema §5 distinguishes:
        #   - missing/unknown-enum-string: silent default (would be "too noisy")
        #   - present but wrong type: drop + warning
        for enum_key, enum_cls, default in (
            ("shot_type", ShotType, ShotType.MEDIUM.value),
            ("camera_movement", CameraMovement, CameraMovement.STATIC.value),
        ):
            valid_values = {m.value for m in enum_cls}
            if enum_key not in ns:
                ns[enum_key] = default
                continue
            val = ns[enum_key]
            if isinstance(val, str):
                ns[enum_key] = val if val in valid_values else default
            else:
                # wrong type — emit a warning per schema §5
                ns[enum_key] = default
                warnings.append(
                    Warning_(
                        code=WarningCode.W2_FALLBACK_USED.value,
                        field=f"scenes[{i - 1}].{enum_key}",
                        message=f"{enum_key} was {type(val).__name__}; expected string. used {default!r}.",
                        severity=Severity.WARN,
                    )
                )

        # first_frame_url — keep if it's a string; HEAD-check is a future enhancement
        # (Phase 0 keeps this synchronous and dependency-free)
        ff = ns.get("first_frame_url")
        ns["first_frame_url"] = ff if isinstance(ff, str) and ff.startswith(("http://", "https://")) else None

        ns.setdefault("warnings", [])
        normalized.append(ns)

    # Re-sort + index-rewrite done. Now:
    #  1. clamp negative starts to 0 (with warning if changed)
    #  2. clamp end > duration_s back to duration_s (with warning)
    #  3. ensure end > start; on inversion, bump end and emit warning
    #  4. if any bump pushes a scene's end past the next scene's start, re-sort + warn
    duration_s = float(data.get("duration_s") or 0)
    any_clamped = False
    # W5D2 fix: collect scenes that fail timestamp clamping and drop them at
    # the end, instead of hard-failing the whole analysis. Live cohort hit
    # this when Doubao emitted a scene at start >= duration_s.
    drop_indices: list[int] = []
    for i, s in enumerate(normalized):
        try:
            start = float(s.get("timestamp_start", 0.0))
            end = float(s.get("timestamp_end", start + 0.1))
        except (TypeError, ValueError) as e:
            raise HardFailure(
                FailureCode.S5_INVALID_PAYLOAD,
                f"scenes[{i}] timestamps not numeric: {e}",
            ) from e

        new_start = max(0.0, start)
        if new_start != start:
            warnings.append(
                Warning_(
                    code=WarningCode.W12_TIMESTAMP_CLAMPED.value,
                    field=f"scenes[{i}].timestamp_start",
                    message=f"start {start} < 0; clamped to 0",
                    severity=Severity.WARN,
                )
            )
            any_clamped = True

        new_end = end
        if duration_s > 0 and new_end > duration_s:
            warnings.append(
                Warning_(
                    code=WarningCode.W12_TIMESTAMP_CLAMPED.value,
                    field=f"scenes[{i}].timestamp_end",
                    message=f"end {end} > duration_s {duration_s}; clamped",
                    severity=Severity.WARN,
                )
            )
            new_end = duration_s
            any_clamped = True

        if new_end <= new_start:
            # Zero or inverted duration — bump and warn. Cap at duration_s if known.
            bumped = new_start + 0.1
            if duration_s > 0:
                bumped = min(bumped, duration_s)
            if bumped <= new_start:
                # W5D2: start >= duration_s — scene unsalvageable. Drop it
                # instead of hard-failing the whole analysis. If after all
                # drops we end up with < 3 scenes, the pad pass at the head
                # will have already padded; if more scenes drop after pad,
                # we re-pad at the end of this function.
                warnings.append(
                    Warning_(
                        code=WarningCode.W18_SCENES_PADDED.value,
                        field=f"scenes[{i}]",
                        message=f"dropped: start {new_start} >= duration_s {duration_s}",
                        severity=Severity.WARN,
                    )
                )
                drop_indices.append(i)
                continue
            warnings.append(
                Warning_(
                    code=WarningCode.W12_TIMESTAMP_CLAMPED.value,
                    field=f"scenes[{i}].timestamp_end",
                    message=f"end {end} <= start {new_start}; bumped to {bumped}",
                    severity=Severity.WARN,
                )
            )
            new_end = bumped
            any_clamped = True

        s["timestamp_start"] = new_start
        s["timestamp_end"] = new_end

    # If the bumps disturbed monotonicity (e.g., scene i's bumped end > scene i+1's start),
    # re-sort and re-index. Emit W5_TIMESTAMPS_SORTED if order actually changes.
    if any_clamped and len(normalized) > 1:
        before = [s["timestamp_start"] for s in normalized]
        normalized = sorted(normalized, key=lambda s: s["timestamp_start"])
        after = [s["timestamp_start"] for s in normalized]
        if before != after:
            warnings.append(
                Warning_(
                    code=WarningCode.W5_TIMESTAMPS_SORTED.value,
                    field="scenes",
                    message="post-clamp re-sort changed scene order",
                    severity=Severity.INFO,
                )
            )
        # W5D2: instead of hard-failing on lingering overlap, snap scene i's
        # start to scene i-1's end. Cohort beats correctness here — UI can
        # render slightly-skewed timestamps fine, contract still validates.
        for i in range(1, len(normalized)):
            prev_end = normalized[i - 1]["timestamp_end"]
            if normalized[i]["timestamp_start"] < prev_end:
                warnings.append(
                    Warning_(
                        code=WarningCode.W12_TIMESTAMP_CLAMPED.value,
                        field=f"scenes[{i}].timestamp_start",
                        message=f"snapped from {normalized[i]['timestamp_start']} to prev end {prev_end}",
                        severity=Severity.WARN,
                    )
                )
                normalized[i]["timestamp_start"] = prev_end
                if normalized[i]["timestamp_end"] <= prev_end:
                    normalized[i]["timestamp_end"] = prev_end + 0.1
        # Re-index 1..N after sort
        for idx, s in enumerate(normalized, start=1):
            s["scene_index"] = idx

    # Drop the unsalvageable scenes collected during the timestamp pass.
    if drop_indices:
        normalized = [s for i, s in enumerate(normalized) if i not in set(drop_indices)]
        # Re-index 1..N after drop
        for idx, s in enumerate(normalized, start=1):
            s["scene_index"] = idx
        # W5D3 CR-P0 — degenerate case: ALL scenes had timestamp_start >=
        # duration_s, so the drop pass emptied the list. The original pad
        # loop's `and normalized` guard is correct to prevent IndexError but
        # silently no-ops, leaving the contract to hard-fail later at
        # `scenes: list[Scene] = Field(..., min_length=3)` validation. That's
        # the *same failure* W5D2's recovery was supposed to prevent. Raise an
        # explicit HardFailure so the user gets a real hint instead of a
        # silent S5_INVALID_PAYLOAD.
        if not normalized:
            raise HardFailure(
                FailureCode.S5_INVALID_PAYLOAD,
                "all scenes had timestamp_start >= duration_s; nothing to pad from",
            )
        # Post-drop pad — if drops left us below 3, clone last scene to hit min.
        while len(normalized) < 3:
            clone = dict(normalized[-1])
            clone["scene_index"] = len(normalized) + 1
            normalized.append(clone)
            warnings.append(
                Warning_(
                    code=WarningCode.W18_SCENES_PADDED.value,
                    field="scenes",
                    message=f"post-drop pad: added clone of last scene to reach min 3",
                    severity=Severity.WARN,
                )
            )

    data["scenes"] = normalized


def _audit_minor_subjects(data: dict[str, Any], warnings: list[Warning_]) -> None:
    scene_indices = detect_minor_subjects(data.get("scenes") or [])
    for scene_index in scene_indices:
        warnings.append(
            Warning_(
                code=WarningCode.W14_MINOR_SUBJECT_DETECTED.value,
                field=f"scenes[{scene_index}]",
                message="minor subject keyword detected",
                severity=Severity.INFO,
            )
        )


def _ensure_confidence(data: dict[str, Any], warnings: list[Warning_]) -> None:
    c = data.get("confidence")
    if c is None:
        # Heuristic: start at 1.0 and subtract 0.1 per warning, clamped.
        computed = max(0.0, min(1.0, 1.0 - 0.1 * len(warnings)))
        data["confidence"] = computed
        warnings.append(
            Warning_(
                code=WarningCode.W7_CONFIDENCE_COMPUTED.value,
                field="confidence",
                message=f"upstream did not provide confidence; computed = {computed:.2f}",
                severity=Severity.INFO,
            )
        )
        return
    try:
        c_f = float(c)
    except (TypeError, ValueError) as e:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"confidence not numeric: {c!r}") from e
    clamped = max(0.0, min(1.0, c_f))
    if clamped != c_f:
        warnings.append(
            Warning_(
                code=WarningCode.W11_CONFIDENCE_CLAMPED.value,
                field="confidence",
                message=f"confidence {c_f} clamped to {clamped}",
                severity=Severity.WARN,
            )
        )
    data["confidence"] = clamped
