"""Single-shot ARK Doubao vision call → full CascadeAnalysisContract payload.

Bypasses MediaKit storyline entirely. The model reads `.mp4` frames + audio
directly via the `video_url` content part and emits the whole contract in one
chat completion. Designed for real Douyin URLs where MediaKit storyline hangs.

The returned dict is contract-shaped but **not pre-validated** — the caller
runs it through `adapter.normalize_analysis_result()` which already handles
W15 audio fallback, W16 production fallback, S-code hard failures, etc.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

from agent import config
from agent.cascade.cost_guard import PREDICT_DOUBAO_DIRECT_CNY as _COST_PREDICT, cost_guard
from agent.cascade.failures import FailureCode, HardFailure


# Re-export for callers that import from this module (avoids forcing them
# to know about cost_guard internals). Value of truth lives in cost_guard.py.
PREDICT_DOUBAO_DIRECT_CNY = _COST_PREDICT


ARK_CHAT_COMPLETIONS_URL = (
    f"{config.ARK_BASE_URL.rstrip('/')}/chat/completions"
)
PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "doubao_direct_analyze.md"
)
# ARK full-contract vision generation (10 viral dims + 14-per-scene + per-scene
# timeline) is heavy: a content-rich ~50s video measured ~119s end-to-end, right
# at the old 120.0 ceiling → S7_UPSTREAM_TIMEOUT fired on the临界 case (both the
# showcase generator AND normal users analyzing busy videos). The upstream agent
# turn allows 180s (RUN_TURN_TIMEOUT_S) and the frontend backstop is 210s, so the
# ARK call was the *tightest* limit, wasting that headroom. Default raised to 165s
# (comfortably inside the 180s turn budget); env-overridable for prod tuning
# without a redeploy.
_TIMEOUT_S = float(os.getenv("DOUBAO_DIRECT_TIMEOUT_S", "165") or "165")
# ARK vision is non-deterministic and occasionally emits a malformed JSON body
# (e.g. a missing delimiter mid-output) that hard-fails the whole analysis. Such
# glitches almost always clear on a re-request, so retry the call a few times
# before giving up. Only invalid-JSON (S5) is retried — auth/timeout/5xx are not.
_MAX_JSON_ATTEMPTS = 3
_RETRY_SLEEP_S = 0.4  # patched to 0 in tests
_VIDEO_FPS = 1
_VIDEO_MAX_FRAMES = 60
_VIDEO_MAX_PIXELS = 518_400  # mirrors viral_overlay.py — keeps token spend honest

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


async def analyze_video_direct(
    direct_mp4_url: str,
    *,
    user_id: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Single-shot ARK call → full CascadeAnalysisContract-shaped dict.

    Reads `doubao_direct_analyze.md`, builds the chat completion with a
    `video_url` content part, parses the model's JSON output, and returns
    the dict. Top-level fields the model does NOT produce (analysis_id,
    source_url, platform, created_at, model, cost_cny, schema_version,
    duration_s) are left for the caller to inject — the caller has the
    resolver metadata + user/run context the client doesn't.

    Raises HardFailure on auth refusal, timeout, transport error, or
    unparseable JSON. The caller normalizes via adapter downstream.
    """
    if not _auth_ready():
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            "doubao_direct: ARK_API_KEY missing",
        )

    # Cost guard mandatory before spend. Raises HardFailure(S8) if caps hit.
    await cost_guard(
        user_id=user_id,
        run_id=run_id or "anonymous",
        predicted_cost_cny=PREDICT_DOUBAO_DIRECT_CNY,
    )

    request_body = _request_body(direct_mp4_url)
    headers = {
        # ARK chat completions standard endpoint expects plain Bearer ARK_API_KEY.
        # The slash-joined token in viral_overlay.py is for the MediaKit *tools*
        # endpoint, NOT /chat/completions. 401 "API key format incorrect" otherwise.
        "Authorization": f"Bearer {config.ARK_API_KEY}",
        "Content-Type": "application/json",
    }

    last_invalid: HardFailure | None = None
    async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
        for attempt in range(1, _MAX_JSON_ATTEMPTS + 1):
            try:
                response = await client.post(
                    ARK_CHAT_COMPLETIONS_URL,
                    json=request_body,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                raise HardFailure(
                    FailureCode.S7_UPSTREAM_TIMEOUT,
                    f"doubao_direct timeout: {exc}",
                ) from exc
            except httpx.TransportError as exc:
                raise HardFailure(
                    FailureCode.S8_UPSTREAM_REFUSED,
                    f"doubao_direct transport_error: {exc}",
                ) from exc

            _raise_for_status(response)  # auth/429/5xx/other → S8, not retried

            try:
                parsed = _parse_response_json(response)
            except HardFailure as exc:
                # Only transient invalid-JSON (S5) is retried; re-request the
                # model — non-determinism usually yields valid JSON next time.
                if exc.code == FailureCode.S5_INVALID_PAYLOAD and attempt < _MAX_JSON_ATTEMPTS:
                    last_invalid = exc
                    print(
                        f"[doubao_direct] invalid JSON (attempt {attempt}/"
                        f"{_MAX_JSON_ATTEMPTS}), retrying: {exc.debug_detail}"
                    )
                    await asyncio.sleep(_RETRY_SLEEP_S * attempt)
                    continue
                raise

            _clamp_confidence(parsed)
            return parsed

    # Exhausted retries on invalid JSON.
    assert last_invalid is not None  # loop always sets it before falling through
    raise last_invalid


# ---------- internals ----------


def _raise_for_status(response: httpx.Response) -> None:
    """Map non-2xx ARK responses to HardFailures. None of these are retried."""
    if response.status_code in (401, 403):
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"auth_refused: {response.status_code}",
        )
    if response.status_code == 429:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "rate_limit")
    if response.status_code >= 500:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"upstream_5xx_{response.status_code}",
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"upstream_http_{response.status_code}",
        ) from exc


def _parse_response_json(response: httpx.Response) -> dict[str, Any]:
    """ARK envelope JSON → the model's parsed contract dict. Raises S5 (which
    the caller retries) when either the envelope or the model's content is not
    valid JSON."""
    try:
        body = response.json()
    except ValueError as exc:
        raise HardFailure(
            FailureCode.S5_INVALID_PAYLOAD,
            "doubao_direct response not JSON",
        ) from exc
    return _parse_model_payload(body)


def _auth_ready() -> bool:
    return bool(str(config.ARK_API_KEY or "").strip())


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _request_body(direct_mp4_url: str) -> dict[str, Any]:
    """Exact ARK chat completion request body.

    Schema mirrors `viral_overlay._request_body` — system message holds the
    prompt, user message holds the `video_url` content part. Same model
    name + content-part shape that's already in production for overlay.
    """
    return {
        "model": config.DOUBAO_MODEL,
        "messages": [
            {"role": "system", "content": _load_prompt()},
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": direct_mp4_url,
                            "fps": _VIDEO_FPS,
                            "max_frames": _VIDEO_MAX_FRAMES,
                            "max_pixels": _VIDEO_MAX_PIXELS,
                        },
                    }
                ],
            },
        ],
        "stream": False,
    }


def _parse_model_payload(response_json: dict[str, Any]) -> dict[str, Any]:
    """Pull the assistant text out of choices[0] and parse as JSON.

    Defensively strips ```json fences in case the model ignores the "no
    markdown" instruction.
    """
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise HardFailure(
            FailureCode.S5_INVALID_PAYLOAD,
            "doubao_direct: choices missing",
        )
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise HardFailure(
            FailureCode.S5_INVALID_PAYLOAD,
            "doubao_direct: choices[0].message missing",
        )
    content = message.get("content")
    text = _content_text(content)
    text = _strip_json_fence(text)
    text = _extract_json_object(text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as first_exc:
        # Robustness (S5 fix): doubao occasionally emits *almost*-valid JSON —
        # trailing commas, or a missing comma between two values. Rather than
        # hard-fail (then burn a full re-request retry, which often repeats the
        # same glitch), attempt a conservative in-house repair first.
        repaired = _repair_json(text)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError:
            raise HardFailure(
                FailureCode.S5_INVALID_PAYLOAD,
                f"doubao_direct: assistant content not JSON: {first_exc}",
            ) from first_exc
    if not isinstance(parsed, dict):
        raise HardFailure(
            FailureCode.S5_INVALID_PAYLOAD,
            "doubao_direct: assistant content is not a JSON object",
        )
    return parsed


def _repair_json(text: str) -> str:
    """Conservative repair of the JSON glitches doubao actually emits. Best-effort
    string surgery — only touches structural punctuation, never values:
      1) trailing commas before } or ]  (``…"a",}`` → ``…"a"}``)
      2) missing comma between adjacent values: ``}{`` ``]"`` ``"[`` etc., and the
         common ``"…" \n "…"`` (newline-separated string members with no comma)
    If a fix doesn't help, json.loads still raises and the caller falls back to S5.
    """
    out = text
    # 1) trailing commas before closing bracket/brace (incl. whitespace between)
    out = re.sub(r",(\s*[}\]])", r"\1", out)
    # 2) missing comma between a closed string/brace/bracket/number and the next
    #    opening quote/brace/bracket across whitespace+newline.
    out = re.sub(r'("\s*)\n(\s*")', r'\1,\n\2', out)          # "a"\n"b" → "a",\n"b"
    out = re.sub(r'([}\]"0-9])\s*\n(\s*[{\["])', r'\1,\n\2', out)  # }\n{ ]\n" etc.
    return out


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    raise HardFailure(
        FailureCode.S5_INVALID_PAYLOAD,
        "doubao_direct: message.content missing",
    )


def _strip_json_fence(text: str) -> str:
    # Strip leading/trailing ```json fences if the model emitted any.
    return _JSON_FENCE_RE.sub("", text).strip()


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise HardFailure(
            FailureCode.S5_INVALID_PAYLOAD,
            "doubao_direct: no JSON object in assistant content",
        )
    return text[start : end + 1]


def _clamp_confidence(payload: dict[str, Any]) -> None:
    """ARK vision sometimes emits confidence outside [0,1] (e.g. 85 = pct).

    Clamp in place. Adapter would also catch out-of-range via Pydantic, but
    catching here keeps the warning specific to W11 territory (computed
    rather than hard-failing the whole contract).
    """
    raw = payload.get("confidence")
    try:
        val = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return
    if val > 1.0 and val <= 100.0:
        # Looks like a percentage. Normalize.
        val = val / 100.0
    payload["confidence"] = max(0.0, min(1.0, val))
