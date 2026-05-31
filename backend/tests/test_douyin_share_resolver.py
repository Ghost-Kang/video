"""Unit tests for Douyin share-page resolver (W4D5).

Hermetic — no network. We mock httpx.AsyncClient with a fake that
returns offline fixture HTML scraped from a real iesdouyin response
(redacted to a single example video id).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.mediakit import douyin_share_resolver as dsr


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _make_response(
    status_code: int = 200, body: str = "", url: str = "https://www.iesdouyin.com/share/video/1/"
) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(status_code, text=body, request=request)


class _FakeAsyncClient:
    """Configurable stand-in for httpx.AsyncClient.

    Set class-level attrs `response` or `exc` before invoking the resolver.
    Reset between tests via the autouse fixture.
    """

    response: httpx.Response | None = None
    exc: Exception | None = None
    last_url: str | None = None
    last_headers: dict | None = None

    def __init__(self, *args, **kwargs):
        # Only record the FIRST AsyncClient's headers — that's the SSR GET.
        # The HEAD-follow client comes second and has no headers in __init__
        # (we pass UA on the .head() call); don't let it clobber the assertion.
        if type(self).last_headers is None:
            type(self).last_headers = kwargs.get("headers")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url: str):
        type(self).last_url = url
        if self.exc:
            raise self.exc
        assert self.response is not None, "test forgot to set _FakeAsyncClient.response"
        return self.response

    async def head(self, url: str, headers: dict | None = None):
        # Resolver follows the playwm 302 chain to the final CDN. Tests don't
        # need to assert this hop — return a fake response whose `.url` matches
        # the input so metadata is unchanged. If `head_response` is set on the
        # class, use that instead.
        head_resp = getattr(type(self), "head_response", None)
        if head_resp is not None:
            return head_resp
        return _make_response(200, "", url=url)


@pytest.fixture(autouse=True)
def _reset_fake_client(monkeypatch):
    """Patch httpx.AsyncClient → _FakeAsyncClient, reset state per test."""
    _FakeAsyncClient.response = None
    _FakeAsyncClient.exc = None
    _FakeAsyncClient.last_url = None
    _FakeAsyncClient.last_headers = None
    monkeypatch.setattr(dsr.httpx, "AsyncClient", _FakeAsyncClient)
    yield


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_returns_direct_url_and_metadata():
    _FakeAsyncClient.response = _make_response(200, _load_fixture("douyin_share_sample.html"))

    direct_url, metadata = asyncio.run(
        dsr.resolve_douyin_url("https://www.douyin.com/video/7643415855329561897")
    )

    assert direct_url.startswith("https://aweme.snssdk.com/aweme/v1/playwm/")
    assert "\\u" not in direct_url and "\\/" not in direct_url
    assert metadata["video_id"] == "7643415855329561897"
    assert metadata["desc"] is not None and "铓鱼侠" in metadata["desc"]
    assert metadata["author_nickname"] == "人民日报"
    # First duration encountered after play_addr is the inner video duration.
    assert metadata["duration_ms"] == 52000
    # W4D5: duration_s (float seconds) derived from duration_ms for the
    # analysis-level duration guard. 52000ms → 52.0s.
    assert metadata["duration_s"] == 52.0
    assert metadata["cover_url"] is not None
    assert "douyinpic" in metadata["cover_url"]


def test_happy_path_accepts_share_url_form():
    _FakeAsyncClient.response = _make_response(200, _load_fixture("douyin_share_sample.html"))

    direct_url, metadata = asyncio.run(
        dsr.resolve_douyin_url(
            "https://www.iesdouyin.com/share/video/7643415855329561897/"
        )
    )

    assert direct_url.endswith("&ratio=720p")
    assert metadata["video_id"] == "7643415855329561897"


def test_accepts_app_share_text_with_full_url():
    """用户直接粘 App「分享 → 复制链接」的整段文案(里面是完整 www.douyin.com/video URL)。"""
    _FakeAsyncClient.response = _make_response(200, _load_fixture("douyin_share_sample.html"))
    share_text = (
        "7.65 复制打开抖音，看看【人民日报的作品】 "
        "https://www.douyin.com/video/7643415855329561897 啊巴拉巴拉 # 美好"
    )
    _direct, metadata = asyncio.run(dsr.resolve_douyin_url(share_text))
    assert metadata["video_id"] == "7643415855329561897"


def test_follows_v_douyin_shortlink_in_share_text():
    """App 分享出来的 v.douyin.com 短链 + 文案:跟随 302 拿到含 id 的规范 URL。

    单个 fake response 同时服务两跳:第一跳(短链 get)读 .url(= 规范 URL,含 id),
    第二跳(SSR get)读 .text(= SSR HTML)。"""
    _FakeAsyncClient.response = _make_response(
        200,
        _load_fixture("douyin_share_sample.html"),
        url="https://www.douyin.com/video/7643415855329561897",
    )
    share_text = (
        "7.65 复制打开抖音，看看【人民日报的作品】 https://v.douyin.com/iRabc123/ 复制此链接"
    )
    _direct, metadata = asyncio.run(dsr.resolve_douyin_url(share_text))
    assert metadata["video_id"] == "7643415855329561897"


def test_shortlink_that_does_not_resolve_falls_back_to_s5():
    """短链跟随后仍拿不到 id(风控/失效)→ 走原有 S5,前端给引导。"""
    _FakeAsyncClient.response = _make_response(200, "", url="https://www.douyin.com/")
    with pytest.raises(HardFailure) as excinfo:
        asyncio.run(dsr.resolve_douyin_url("https://v.douyin.com/iRdead404/"))
    assert excinfo.value.code == FailureCode.S5_INVALID_PAYLOAD


def test_hits_iesdouyin_with_mobile_ua():
    _FakeAsyncClient.response = _make_response(200, _load_fixture("douyin_share_sample.html"))

    asyncio.run(
        dsr.resolve_douyin_url("https://www.douyin.com/video/7643415855329561897")
    )

    assert _FakeAsyncClient.last_url == (
        "https://www.iesdouyin.com/share/video/7643415855329561897/"
    )
    assert "iPhone" in (_FakeAsyncClient.last_headers or {}).get("User-Agent", "")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://www.bilibili.com/video/BV1xyz",
        "https://www.douyin.com/user/MS4wLjABAAAA",
        "not a url at all",
        "https://www.douyin.com/video/",  # no id
    ],
)
def test_invalid_url_raises_s5(bad_url):
    with pytest.raises(HardFailure) as excinfo:
        asyncio.run(dsr.resolve_douyin_url(bad_url))
    assert excinfo.value.code == FailureCode.S5_INVALID_PAYLOAD


# ---------------------------------------------------------------------------
# SSR HTML missing play_addr
# ---------------------------------------------------------------------------


def test_missing_play_addr_raises_s5():
    _FakeAsyncClient.response = _make_response(
        200, _load_fixture("douyin_share_no_play_addr.html")
    )
    with pytest.raises(HardFailure) as excinfo:
        asyncio.run(
            dsr.resolve_douyin_url("https://www.douyin.com/video/7643415855329561897")
        )
    assert excinfo.value.code == FailureCode.S5_INVALID_PAYLOAD
    assert "play_addr" in excinfo.value.debug_detail


# ---------------------------------------------------------------------------
# Network failures
# ---------------------------------------------------------------------------


def test_network_error_raises_s8():
    _FakeAsyncClient.exc = httpx.ConnectError("dns failure")
    with pytest.raises(HardFailure) as excinfo:
        asyncio.run(
            dsr.resolve_douyin_url("https://www.douyin.com/video/7643415855329561897")
        )
    assert excinfo.value.code == FailureCode.S8_UPSTREAM_REFUSED


def test_timeout_raises_s7():
    _FakeAsyncClient.exc = httpx.ReadTimeout("slow upstream")
    with pytest.raises(HardFailure) as excinfo:
        asyncio.run(
            dsr.resolve_douyin_url("https://www.douyin.com/video/7643415855329561897")
        )
    assert excinfo.value.code == FailureCode.S7_UPSTREAM_TIMEOUT


def test_non_200_status_raises_s8():
    _FakeAsyncClient.response = _make_response(403, "<html>forbidden</html>")
    with pytest.raises(HardFailure) as excinfo:
        asyncio.run(
            dsr.resolve_douyin_url("https://www.douyin.com/video/7643415855329561897")
        )
    assert excinfo.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert "403" in excinfo.value.debug_detail


# ---------------------------------------------------------------------------
# url_resolver integration — verifies the new mode is wired correctly
# ---------------------------------------------------------------------------


def test_url_resolver_douyin_share_mode_returns_direct(monkeypatch):
    from agent.cascade.mediakit import url_resolver

    _FakeAsyncClient.response = _make_response(200, _load_fixture("douyin_share_sample.html"))
    monkeypatch.setenv("TOPRADOR_RESOLVER_MODE", "douyin_share")

    # W4D5: resolve_to_direct_media now returns (url, metadata) tuple.
    direct_url, metadata = asyncio.run(
        url_resolver.resolve_to_direct_media(
            "https://www.douyin.com/video/7643415855329561897"
        )
    )
    assert direct_url.startswith("https://aweme.snssdk.com/aweme/v1/playwm/")
    # Metadata must propagate from douyin_share_resolver — duration_s is what
    # the analysis_service duration guard depends on.
    assert metadata["duration_s"] == 52.0


def test_url_resolver_passthrough_still_default(monkeypatch):
    from agent.cascade.mediakit import url_resolver

    monkeypatch.delenv("TOPRADOR_RESOLVER_MODE", raising=False)
    page_url = "https://www.douyin.com/video/7643415855329561897"
    # W4D5: passthrough returns (url, {}) — empty metadata signals "no
    # resolver-side duration available; service-level guard is a no-op."
    direct_url, metadata = asyncio.run(url_resolver.resolve_to_direct_media(page_url))
    assert direct_url == page_url
    assert metadata == {}
