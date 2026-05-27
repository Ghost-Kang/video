"""URL resolver: Douyin / 小红书 page URL → direct .mp4 URL.

MediaKit cannot consume short-video platform page URLs (confirmed via
2026-05-23 probe: feeding Douyin URL → MediaKit's internal ffprobe got
HTML, task failed). We need an upstream resolver step.

W4D5 (2026-05-27) update — `douyin_share` mode landed. Scrapes
`iesdouyin.com/share/video/<id>/` SSR HTML for `play_addr.url_list[0]`,
no cookies / yt-dlp / desktop UA required. See
`douyin_share_resolver.py` for the contract + regex set.

Three other strategies remain stubs pending founder接续协议 with toprador:
1. toprador HTTP endpoint  → call POST /api/resolve-url
2. toprador Python import   → from toprador.resolver import resolve

Switch strategies with `TOPRADOR_RESOLVER_MODE`:
  - `passthrough` (default)        — return input as-is
  - `douyin_share`                  — live SSR scrape (real Douyin)
  - `toprador_http` / `toprador_pyimport` — placeholders, raise S8
"""

from __future__ import annotations

import os
from typing import Any

from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.mediakit.douyin_share_resolver import resolve_douyin_url


PASSTHROUGH_MODE = "passthrough"
TOPRADOR_HTTP_MODE = "toprador_http"
TOPRADOR_PYIMPORT_MODE = "toprador_pyimport"
DOUYIN_SHARE_MODE = "douyin_share"

_KNOWN_MODES = frozenset(
    {
        PASSTHROUGH_MODE,
        TOPRADOR_HTTP_MODE,
        TOPRADOR_PYIMPORT_MODE,
        DOUYIN_SHARE_MODE,
    }
)


def _active_mode() -> str:
    mode = os.getenv("TOPRADOR_RESOLVER_MODE", PASSTHROUGH_MODE).strip().lower()
    if mode not in _KNOWN_MODES:
        return PASSTHROUGH_MODE
    return mode


async def resolve_to_direct_media(page_url: str) -> tuple[str, dict[str, Any]]:
    """Resolve a short-video page URL to (direct media URL, metadata).

    W4D5 signature change — used to return `str`, now returns
    `(direct_url, metadata)`. Existing call sites must unpack. For
    passthrough mode the metadata dict is empty `{}`.

    Default (`passthrough`) returns input as-is + empty metadata;
    downstream MediaKit will likely fail on the HTML page, which is the
    explicit cost of running without a real resolver.

    `douyin_share` mode surfaces metadata keys
    `{video_id, desc, author_nickname, duration_s, duration_ms, cover_url}`
    — see `douyin_share_resolver.resolve_douyin_url` for details.
    The W4D5 duration guard in `analysis_service._call_mediakit` reads
    `duration_s` from this dict to refuse <5s / >180s sources before
    incurring MediaKit spend.

    Toprador modes still raise S8 — placeholder until founder接续协议 lands.
    """
    mode = _active_mode()
    if mode == PASSTHROUGH_MODE:
        return page_url, {}
    if mode == DOUYIN_SHARE_MODE:
        direct_url, metadata = await resolve_douyin_url(page_url)
        return direct_url, metadata
    if mode == TOPRADOR_HTTP_MODE:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            "toprador_http resolver接续 not yet wired (founder W3D3 TBD)",
        )
    if mode == TOPRADOR_PYIMPORT_MODE:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            "toprador_pyimport resolver接续 not yet wired (founder W3D3 TBD)",
        )
    # _active_mode 已 guard, unreachable
    return page_url, {}
