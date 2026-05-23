"""Map MediaKit storyline results into the Cascade analysis payload shape."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from agent.cascade.failures import FailureCode, HardFailure


def storyline_to_payload(
    storyline_result: dict[str, Any],
    *,
    source_url: str,
    user_id: str,
) -> dict[str, Any]:
    """Convert MediaKit `analyze-video-storyline` result into adapter input."""
    if not isinstance(storyline_result, dict):
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "mediakit_storyline_result_not_object")
    clips = storyline_result.get("storyline_clips")
    if not isinstance(clips, list) or not clips:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, "mediakit_storyline_clips_missing")

    source_info = _first_dict(storyline_result.get("source_video_info")) or {}
    highlights = [item for item in storyline_result.get("storyline_highlights") or [] if isinstance(item, dict)]
    duration_s = _duration(storyline_result, clips)
    scenes = [_scene_from_clip(clip, index) for index, clip in enumerate(_sorted_clips(clips), start=1)]
    scores = [_as_float(clip.get("clip_score")) for clip in clips if isinstance(clip, dict)]
    scores = [score for score in scores if score is not None]

    return {
        "schema_version": "1.0",
        "analysis_id": _analysis_id(user_id, source_url),
        "source_url": source_url,
        "platform": _platform_from_url(source_url),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "mediakit-storyline",
        "cost_cny": 0.0,
        "duration_s": duration_s,
        "confidence": _confidence(len(scenes), duration_s, scores),
        "viral_analysis": _viral_analysis(source_info, highlights, scenes),
        "scenes": scenes,
        "warnings": [],
    }


def _scene_from_clip(clip: Any, index: int) -> dict[str, Any]:
    if not isinstance(clip, dict):
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"mediakit_clip_{index}_not_object")
    start = _as_float(clip.get("clip_start_time"))
    end = _as_float(clip.get("clip_end_time"))
    if start is None or end is None:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"mediakit_clip_{index}_timestamps_missing")
    title = _text(clip.get("clip_title")) or f"片段 {index}"
    summary = _text(clip.get("clip_summary")) or title
    dialogue = _text(clip.get("clip_dialogue"))
    scene = {
        "scene_index": index,
        "timestamp_start": max(0.0, start),
        "timestamp_end": max(start + 0.1, end),
        "scene": _truncate(title, 120),
        "dialogue_and_narration": _truncate(dialogue, 2000),
        "visual_content": _truncate(summary, 200),
        "subject": None,
        "shot_type": "medium",
        "camera_movement": "static",
        "warnings": [],
    }
    snapshot_url = _text(clip.get("clip_snapshot_url"))
    if snapshot_url:
        scene["first_frame_url"] = snapshot_url
    return scene


def _viral_analysis(
    source_info: dict[str, Any],
    highlights: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> dict[str, str]:
    title = _text(source_info.get("source_video_title"))
    summary = _text(source_info.get("source_video_summary"))
    tags = source_info.get("source_video_tag") or []
    tag_text = "、".join(str(tag) for tag in tags[:5]) if isinstance(tags, list) else _text(tags)
    highlight_text = "；".join(
        _text(item.get("highlight_summary") or item.get("highlight_title"))
        for item in highlights[:3]
        if _text(item.get("highlight_summary") or item.get("highlight_title"))
    )
    first_scene = scenes[0]["scene"] if scenes else ""
    last_scene = scenes[-1]["scene"] if scenes else ""
    return {
        "hook": _truncate(title or first_scene or "故事线开场钩子待补充", 80),
        "pacing": _truncate(f"{len(scenes)} 个故事片段推进", 80),
        "climax": _truncate(last_scene or "结尾爆点待补充", 80),
        "visual_style": _truncate(scenes[0]["visual_content"] if scenes else "自然视频风格", 80),
        "emotional_arc": _truncate(highlight_text or summary or "情绪起伏待补充", 80),
        "target_audience": _truncate(tag_text or "目标人群待补充", 80),
        "engagement_levers": _truncate("评论区围绕剧情细节与结果反馈互动", 80),
        "replicable_formula": _truncate(summary or highlight_text or first_scene or "故事线拆解后复刻开场、过程和结尾反差", 120),
    }


def _analysis_id(user_id: str, source_url: str) -> str:
    digest = hashlib.sha1(f"{user_id}:{source_url}".encode("utf-8")).hexdigest()[:20]
    return f"ana_mk_{digest}"


def _platform_from_url(source_url: str) -> str:
    host = urlparse(source_url).netloc.lower()
    if host == "douyin.com" or host.endswith(".douyin.com"):
        return "douyin"
    if host == "xiaohongshu.com" or host.endswith(".xiaohongshu.com") or host.endswith("xhslink.com"):
        return "xiaohongshu"
    return "other"


def _duration(storyline_result: dict[str, Any], clips: list[Any]) -> int:
    duration = _as_float(storyline_result.get("duration"))
    if duration is None:
        ends = [_as_float(clip.get("clip_end_time")) for clip in clips if isinstance(clip, dict)]
        duration = max((end for end in ends if end is not None), default=1.0)
    return max(1, int(round(duration)))


def _confidence(scene_count: int, duration_s: int, scores: list[float]) -> float:
    scene_factor = min(1.0, scene_count / 5.0)
    duration_factor = 1.0 if duration_s <= 180 else 0.85
    score_factor = min(1.0, (sum(scores) / len(scores)) / 5.0) if scores else 0.7
    return round(max(0.0, min(1.0, 0.2 + 0.4 * scene_factor + 0.4 * score_factor)) * duration_factor, 3)


def _sorted_clips(clips: list[Any]) -> list[dict[str, Any]]:
    dicts = [clip for clip in clips if isinstance(clip, dict)]
    return sorted(dicts, key=lambda clip: _as_float(clip.get("clip_start_time")) or 0.0)


def _first_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truncate(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"
