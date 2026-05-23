"""URL resolver: Douyin / 小红书 page URL → direct .mp4 URL.

MediaKit cannot consume short-video platform page URLs (confirmed via
2026-05-23 probe: feeding Douyin URL → MediaKit's internal ffprobe got
HTML, task failed). We need an upstream resolver step.

Founder W3D3 decision: "老 toprador 有 URL resolver 这块逻辑,保留该模块
(不丢)". So toprador's resolver survives the P5-3 pivot. The接续协议
(独立 endpoint / Python module import / micro-service) is待 founder
confirm — until then, this module exposes the resolver contract and a
passthrough stub.

Contract (any implementation must satisfy):

    async def resolve_to_direct_media(page_url: str) -> str:
        '''Return a direct .mp4 / .mov URL MediaKit can consume.
        Raise HardFailure(S5_INVALID_PAYLOAD) if resolution fails.'''

Three impl strategies waiting for founder:
1. toprador HTTP endpoint  → call POST /api/resolve-url
2. toprador Python import   → from toprador.resolver import resolve
3. micro-service            → call internal service URL

Until选定, callers receive PASSTHROUGH (return input as-is).
This unblocks all downstream sub-phase A/B/C code + tests; integrators
flip the strategy when toprador接续协议 lands.
"""

from __future__ import annotations

import os

from agent.cascade.failures import FailureCode, HardFailure


PASSTHROUGH_MODE = "passthrough"
TOPRADOR_HTTP_MODE = "toprador_http"
TOPRADOR_PYIMPORT_MODE = "toprador_pyimport"

_KNOWN_MODES = frozenset({PASSTHROUGH_MODE, TOPRADOR_HTTP_MODE, TOPRADOR_PYIMPORT_MODE})


def _active_mode() -> str:
    mode = os.getenv("TOPRADOR_RESOLVER_MODE", PASSTHROUGH_MODE).strip().lower()
    if mode not in _KNOWN_MODES:
        return PASSTHROUGH_MODE
    return mode


async def resolve_to_direct_media(page_url: str) -> str:
    """Resolve a short-video page URL to a direct media URL.

    Until founder confirms toprador接续协议, this passthrough returns
    the input as-is. Callers expecting `https://...mp4` may receive
    `https://www.douyin.com/video/...` and downstream MediaKit may then
    fail; that's the explicit cost of running without a real resolver.

    Switch strategy by setting `TOPRADOR_RESOLVER_MODE`:
      - `passthrough` (default, no-op)
      - `toprador_http` (POST to TOPRADOR_RESOLVE_ENDPOINT — TBD)
      - `toprador_pyimport` (import toprador.resolver — TBD)
    """
    mode = _active_mode()
    if mode == PASSTHROUGH_MODE:
        return page_url
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
    # _active_mode 已 guard,unreachable
    return page_url
