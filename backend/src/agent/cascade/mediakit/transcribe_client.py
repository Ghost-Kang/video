"""MediaKit extract-audio-text client — W4D5 transcribe pipeline.

Why this exists
---------------
Cascade analysis benefits enormously from a full逐字脚本 (verbatim
transcript). The MediaKit storyline endpoint we already call only returns
per-clip dialogue snippets — it doesn't give us the entire script. This
client wraps the dedicated `extract-audio-text` MediaKit tool which
returns the full text with per-utterance line breaks.

Endpoint assumption
-------------------
We POST to `MEDIAKIT_BASE_URL/tools/extract-audio-text` with `{video_urls:
[url]}` and expect a sync response carrying either `result.text` or
`result.utterances`. **This is a best-effort assumption based on the
storyline endpoint shape** — docs/nexus/founder_log/p5-3a_mediakit_schemas
documented the storyline contract but not transcribe, so we degrade
gracefully on any 4xx/5xx/parse failure rather than blocking analysis.

Contract
--------
`fetch_transcript(video_url, user_id) -> str`:
- returns the joined transcript (utterances separated by `\n`) on success
- returns `""` on any failure (auth missing, HTTP error, timeout, schema
  mismatch). Caller is responsible for emitting `W17_TRANSCRIBE_FAILED`.
- never raises. The analysis flow must not block on transcribe.

Cost: ~¥0.30 per call (PREDICT_TRANSCRIBE_CNY). Gated by cost_guard at
callsite.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from agent import config
from agent.cascade.cost_guard import PREDICT_TRANSCRIBE_CNY, cost_guard
from agent.cascade.events import emit
from agent.cascade.event_names import EventName
from agent.cascade.failures import HardFailure
from agent.cascade.mediakit.storyline_client import MEDIAKIT_BASE_URL


TRANSCRIBE_TOOL_URL = f"{MEDIAKIT_BASE_URL}/tools/extract-audio-text"
_TIMEOUT_S = 60.0


async def fetch_transcript(
    video_url: str,
    *,
    user_id: str,
    run_id: str | None = None,
) -> str:
    """Best-effort transcript fetch. Returns "" on any failure — never raises.

    Cost-guarded: if the user has blown their per-run or per-day cap, we
    refuse to call MediaKit and return "" (analysis still proceeds without
    a transcript).
    """
    token = str(config.VOLC_MEDIAKIT_AK or "").strip()
    if not token:
        return ""

    # Cost guard — refuse if cap would be exceeded. Failure here returns ""
    # (we do NOT propagate; analysis must continue).
    try:
        await cost_guard(
            user_id=user_id,
            run_id=run_id or "anonymous",
            predicted_cost_cny=PREDICT_TRANSCRIBE_CNY,
        )
    except HardFailure:
        return ""

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"video_urls": [video_url]}

    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(TRANSCRIBE_TOOL_URL, json=body, headers=headers)
    except (httpx.HTTPError, OSError):
        return ""

    if response.status_code != 200:
        return ""

    try:
        payload = response.json()
    except ValueError:
        return ""

    transcript = _extract_transcript(payload)

    # Emit cost telemetry only on a real (>0 char) success so we don't
    # over-charge against the day cap for empty payloads.
    if transcript:
        try:
            await emit(
                EventName.GENERATION_COST,
                user_id=user_id,
                run_id=run_id,
                payload={
                    "kind": "mediakit_transcribe",
                    "cost_cny": PREDICT_TRANSCRIBE_CNY,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                },
            )
        except Exception:
            # Telemetry must never break the user-visible return path.
            pass

    return transcript


def _extract_transcript(payload: Any) -> str:
    """Pull the transcript text out of MediaKit's response.

    We try, in order:
      1. `result.text` — joined transcript string (preferred shape)
      2. `result.utterances[].text` — per-utterance, joined with `\n`
      3. `data.text` / `text` — flat fallback for older endpoint shapes

    Returns "" if none match. Capped at the contract's 20_000-char ceiling.
    """
    if not isinstance(payload, dict):
        return ""

    candidates: list[Any] = [
        payload.get("result"),
        payload.get("data"),
        payload,
    ]
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        text = cand.get("text")
        if isinstance(text, str) and text.strip():
            return _cap(text.strip())
        utterances = cand.get("utterances")
        if isinstance(utterances, list):
            lines = [
                str(u.get("text", "")).strip()
                for u in utterances
                if isinstance(u, dict) and str(u.get("text", "")).strip()
            ]
            if lines:
                return _cap("\n".join(lines))
    return ""


def _cap(text: str) -> str:
    """Hard-cap to contract.full_transcript max_length (20_000 chars)."""
    limit = 20_000
    if len(text) <= limit:
        return text
    return text[: limit - 16].rstrip() + "\n…[truncated]"


__all__ = ["fetch_transcript"]
