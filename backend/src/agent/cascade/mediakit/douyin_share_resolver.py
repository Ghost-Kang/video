"""Douyin share-page resolver: page URL → direct .mp4 URL + metadata.

Why this exists
---------------
MediaKit needs a direct media URL it can ffprobe. Feeding it
`https://www.douyin.com/video/<id>` (the page URL the user pastes) fails:
the page is React-rendered, anti-bot protected, and ships no media src.

`yt-dlp` also fails on www.douyin.com (cookies/anti-bot in our 2026-05-27
probe). What does work is the **mobile share page** at

    https://www.iesdouyin.com/share/video/<video_id>/

It's SSR'd and embeds `play_addr.url_list[0]` pointing at
`aweme.snssdk.com/aweme/v1/playwm/?...` which 302-redirects to a real .mp4
on `douyinvod.com` CDN. Mobile UA is required; no cookies needed.

The SSR HTML also embeds `desc` (title), `nickname` (author), `duration`,
and a `cover` block — we surface those as metadata so analysis services
can use them without re-fetching the page.

Contract
--------
Public API is `resolve_douyin_url(page_url)`. On success returns
`(direct_media_url, metadata_dict)`. On failure raises HardFailure with a
stable FailureCode that maps to the existing UI banner system:

- `S5_INVALID_PAYLOAD` — input wasn't a recognised Douyin URL, or SSR
  HTML didn't contain `play_addr` (private / deleted / format changed).
- `S8_UPSTREAM_REFUSED` — network error reaching iesdouyin.com.

Tests assert behaviour with offline SSR HTML fixtures so the unit suite
stays hermetic.
"""

from __future__ import annotations

import codecs
import json
import re
from typing import Any

import httpx

from agent.cascade.failures import FailureCode, HardFailure


# Mobile UA — `www.iesdouyin.com/share/video/...` only returns the SSR
# HTML with `play_addr` to mobile clients. Desktop UA gets a redirect to
# the React app.
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
)

_TIMEOUT_S = 10.0

# Regex set
# ---------
# `_VIDEO_ID_RE` accepts both the share page form and the full page form.
# `_PLAY_ADDR_RE` lifts the first `url_list[0]` inside the nearest
# `play_addr` object. SSR HTML escapes slashes as `\\u002F` so we
# unicode-unescape the captured string before returning.
# `_DESC_RE`, `_NICKNAME_RE`, `_COVER_RE` are best-effort; if any miss,
# we degrade to `None` rather than failing the whole resolution.
# `_DURATION_RE` looks for a `"duration":` value within ~200 chars of
# `play_addr` — defensive narrow window avoids matching unrelated
# `duration` keys elsewhere in the JSON blob.
_VIDEO_ID_RE = re.compile(
    r"(?:www\.douyin\.com/video/|iesdouyin\.com/share/video/)(\d+)"
)
_PLAY_ADDR_RE = re.compile(
    r'"play_addr"\s*:\s*\{[^{}]*?"url_list"\s*:\s*\[\s*"([^"]+)"',
    re.DOTALL,
)
_DESC_RE = re.compile(r'"desc"\s*:\s*"([^"]*)"')
_NICKNAME_RE = re.compile(r'"nickname"\s*:\s*"([^"]*)"')
_COVER_RE = re.compile(
    r'"cover"\s*:\s*\{[^{}]*?"url_list"\s*:\s*\[\s*"([^"]+)"',
    re.DOTALL,
)
# Duration: find the play_addr block then the next `"duration":` integer.
# Greedy `.*?` capped at 4000 chars so we never wander into a different
# JSON object's `duration` field (e.g. music duration).
_DURATION_RE = re.compile(
    r'"play_addr"\s*:.{0,4000}?"duration"\s*:\s*(\d+)',
    re.DOTALL,
)


def _unescape_url(raw: str) -> str:
    """Convert SSR-escaped URL (`\\u002F`, `\\/`) → clean URL string."""
    # Collapse `\/` → `/` first (JSON convention, not a Python escape).
    cleaned = raw.replace("\\/", "/")
    # Then decode unicode escapes (/ etc.).
    try:
        return codecs.decode(cleaned, "unicode_escape")
    except UnicodeDecodeError:
        return cleaned


def _extract_video_id(page_url: str) -> str:
    m = _VIDEO_ID_RE.search(page_url)
    if not m:
        raise HardFailure(
            FailureCode.S5_INVALID_PAYLOAD,
            f"not a recognised douyin video URL: {page_url!r}",
        )
    return m.group(1)


def _parse_ssr_html(html: str) -> tuple[str, dict[str, Any]]:
    """Return (direct_url, metadata) from iesdouyin SSR HTML.

    Raises HardFailure(S5_INVALID_PAYLOAD) if play_addr is missing.
    """
    play_match = _PLAY_ADDR_RE.search(html)
    if not play_match:
        raise HardFailure(
            FailureCode.S5_INVALID_PAYLOAD,
            "douyin SSR has no play_addr — video may be private/deleted",
        )
    direct_url = _unescape_url(play_match.group(1))

    def _try(pat: re.Pattern[str]) -> str | None:
        m = pat.search(html)
        if not m:
            return None
        try:
            # JSON-string decode for unicode escapes in titles
            return json.loads(f'"{m.group(1)}"')
        except json.JSONDecodeError:
            return m.group(1)

    desc = _try(_DESC_RE)
    nickname = _try(_NICKNAME_RE)
    cover_raw = _COVER_RE.search(html)
    cover_url = _unescape_url(cover_raw.group(1)) if cover_raw else None

    duration_ms: int | None = None
    dur_match = _DURATION_RE.search(html)
    if dur_match:
        try:
            duration_ms = int(dur_match.group(1))
        except ValueError:
            duration_ms = None

    # Convert ms → seconds (float) for downstream consumers. We keep
    # `duration_ms` for backwards-compat (older test fixtures key on it),
    # and surface `duration_s: float` per W4D5 contract.
    duration_s: float | None
    if duration_ms is not None and duration_ms >= 0:
        duration_s = duration_ms / 1000.0
    else:
        duration_s = None

    metadata: dict[str, Any] = {
        "desc": desc,
        "author_nickname": nickname,
        "duration_ms": duration_ms,
        "duration_s": duration_s,
        "cover_url": cover_url,
    }
    return direct_url, metadata


async def _fetch_share_html(video_id: str) -> str:
    url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": _MOBILE_UA},
        ) as client:
            response = await client.get(url)
    except httpx.TimeoutException as exc:
        raise HardFailure(
            FailureCode.S7_UPSTREAM_TIMEOUT,
            f"iesdouyin share page timeout: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"iesdouyin share page network error: {exc}",
        ) from exc

    if response.status_code != 200:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"iesdouyin returned HTTP {response.status_code}",
        )
    return response.text


async def resolve_douyin_url(page_url: str) -> tuple[str, dict[str, Any]]:
    """Resolve a Douyin page URL → (direct .mp4 URL, metadata).

    metadata keys:
      - desc:             video title / description (str | None)
      - author_nickname:  uploader display name (str | None)
      - duration_ms:      reported duration in milliseconds (int | None)
                          Caller MUST treat as best-effort; SSR HTML's
                          duration field has been observed both as ms and
                          as seconds — convert defensively.
      - duration_s:       reported duration in seconds (float | None).
                          Derived as `duration_ms / 1000.0`; W4D5
                          analysis_service relies on this to enforce
                          the 5s-180s window before any LLM spend.
      - cover_url:        thumbnail / cover image URL (str | None)
      - video_id:         numeric Douyin video id (str)

    Raises HardFailure(S5_INVALID_PAYLOAD) on bad input or unparsable HTML,
    HardFailure(S7_UPSTREAM_TIMEOUT) on timeout,
    HardFailure(S8_UPSTREAM_REFUSED) on other network failures.
    """
    video_id = _extract_video_id(page_url)
    html = await _fetch_share_html(video_id)
    direct_url, metadata = _parse_ssr_html(html)
    metadata["video_id"] = video_id
    # Follow the 302 to the final douyinvod.com CDN URL. The intermediate
    # aweme.snssdk.com/playwm URL doesn't work as a vision-model input —
    # Doubao's backend fetcher times out connecting to aweme.snssdk.com.
    # The final douyinvod.com URL is a plain time-signed mp4 that ARK can pull.
    direct_url = await _resolve_to_final_cdn(direct_url)
    return direct_url, metadata


async def _resolve_to_final_cdn(url: str) -> str:
    """Follow 302 chain on the aweme.snssdk.com playwm endpoint.

    Returns the final URL after redirects. On any failure, returns the input
    URL unchanged — downstream may still try and fail loudly.
    """
    try:
        async with httpx.AsyncClient(
            timeout=10.0, follow_redirects=True
        ) as client:
            response = await client.head(url, headers={"User-Agent": _MOBILE_UA})
            return str(response.url)
    except (httpx.HTTPError, OSError):
        return url
