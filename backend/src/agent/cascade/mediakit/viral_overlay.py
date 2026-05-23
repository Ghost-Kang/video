"""ARK video-understanding overlay for MediaKit storyline payloads."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx

from agent import config
from agent.cascade.failures import WarningCode


ARK_CHAT_COMPLETIONS_URL = "https://amk-ark.cn-beijing.volces.com/api/v1/chat/completions"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "mediakit_viral_analysis_overlay.md"
MAX_STORYLINE_CONTEXT_CHARS = 200_000
_PROMPT_TEMPLATE_MARGIN_CHARS = 4_096
_TIMEOUT_S = 45.0

_VIRAL_KEYS = (
    "hook",
    "pacing",
    "climax",
    "visual_style",
    "emotional_arc",
    "target_audience",
    "engagement_levers",
    "replicable_formula",
)
_FIELD_LIMITS = {
    "hook": 80,
    "pacing": 80,
    "climax": 80,
    "visual_style": 80,
    "emotional_arc": 80,
    "target_audience": 80,
    "engagement_levers": 80,
    "replicable_formula": 120,
}


async def overlay_viral_dims(contract_dict: dict[str, Any], video_url: str) -> dict[str, Any]:
    """Overlay viral-analysis dimensions with one ARK video-understanding call."""
    payload = deepcopy(contract_dict)
    if not _auth_ready():
        return _fallback(payload, "missing ARK_API_KEY or VOLC_MEDIAKIT_AK")

    request_json = _request_body(payload, video_url)
    headers = {
        "Authorization": f"Bearer {config.ARK_API_KEY}/{config.VOLC_MEDIAKIT_AK}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(ARK_CHAT_COMPLETIONS_URL, json=request_json, headers=headers)
        response.raise_for_status()
        overlay = _parse_overlay_response(response.json())
    except (httpx.HTTPError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _fallback(payload, f"ARK viral overlay failed: {exc}")

    if not overlay:
        return _fallback(payload, "ARK viral overlay returned no usable fields")

    viral = dict(payload.get("viral_analysis") or {})
    for key, value in overlay.items():
        if key in _VIRAL_KEYS and isinstance(value, str) and value.strip():
            viral[key] = _truncate(value, _FIELD_LIMITS[key])
    payload["viral_analysis"] = viral
    payload["model"] = _model_name(payload.get("model"))
    return payload


def _auth_ready() -> bool:
    return bool(str(config.ARK_API_KEY or "").strip() and str(config.VOLC_MEDIAKIT_AK or "").strip())


def _request_body(contract_dict: dict[str, Any], video_url: str) -> dict[str, Any]:
    prompt = _load_prompt().replace("{{storyline_context}}", _storyline_context(contract_dict))
    return {
        "model": config.DOUBAO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": video_url,
                            "fps": 1,
                            "max_frames": 100,
                            "max_pixels": 518400,
                        },
                    },
                ],
            }
        ],
        "stream": False,
    }


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _storyline_context(contract_dict: dict[str, Any]) -> str:
    viral = contract_dict.get("viral_analysis") if isinstance(contract_dict.get("viral_analysis"), dict) else {}
    scenes = contract_dict.get("scenes") if isinstance(contract_dict.get("scenes"), list) else []
    lines = [
        f"source_url: {contract_dict.get('source_url', '')}",
        f"duration_s: {contract_dict.get('duration_s', '')}",
        "current_viral_analysis:",
        json.dumps(viral, ensure_ascii=False, sort_keys=True),
        "scenes:",
    ]
    for scene in scenes[:12]:
        if not isinstance(scene, dict):
            continue
        lines.append(
            json.dumps(
                {
                    "index": scene.get("scene_index"),
                    "start": scene.get("timestamp_start"),
                    "end": scene.get("timestamp_end"),
                    "scene": scene.get("scene"),
                    "visual_content": scene.get("visual_content"),
                    "dialogue_and_narration": scene.get("dialogue_and_narration"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    context = "\n".join(lines)
    limit = max(1, MAX_STORYLINE_CONTEXT_CHARS - _PROMPT_TEMPLATE_MARGIN_CHARS)
    if len(context) <= limit:
        return context
    return context[: limit - 32].rstrip() + "\n[truncated]"


def _parse_overlay_response(response_json: dict[str, Any]) -> dict[str, str]:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("choices missing")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    text = _content_text(content)
    parsed = json.loads(_extract_json_object(text))
    if not isinstance(parsed, dict):
        raise ValueError("overlay content is not an object")
    return {
        key: value.strip()
        for key, value in parsed.items()
        if key in _VIRAL_KEYS and isinstance(value, str) and value.strip()
    }


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    raise ValueError("message.content missing")


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("JSON object missing")
    return text[start : end + 1]


def _fallback(payload: dict[str, Any], message: str) -> dict[str, Any]:
    warnings = list(payload.get("warnings") or [])
    warnings.append(
        {
            "code": WarningCode.W2_FALLBACK_USED.value,
            "field": "viral_analysis",
            "message": message[:400],
            "severity": "warn",
        }
    )
    payload["warnings"] = warnings
    return payload


def _model_name(existing: Any) -> str:
    base = existing if isinstance(existing, str) and existing.strip() else "mediakit-storyline"
    suffix = f"+ark-{config.DOUBAO_MODEL}"
    if suffix in base:
        return base
    return f"{base}{suffix}"


def _truncate(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."
