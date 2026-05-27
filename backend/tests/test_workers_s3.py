"""workers/s3.py unit tests.

`upload_bytes_to_s3` 是同步 wrap;`download_and_upload` 走 httpx + upload_bytes。
两者都 swallow 所有异常返 None — 这是 fire-and-forget worker 路径的契约。
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from agent.tools import s3_upload as s3_module
from agent.workers import s3 as workers_s3
from agent.workers.s3 import download_and_upload, upload_bytes_to_s3


# ---------- upload_bytes_to_s3 ----------


class TestUploadBytesToS3:
    def test_happy_path_returns_url(self, monkeypatch):
        captured: dict = {}

        def fake_upload(data: bytes, filename: str) -> str:
            captured["data"] = data
            captured["filename"] = filename
            return "https://s3.example/img.png"

        monkeypatch.setattr(workers_s3, "upload_bytes", fake_upload)

        url = upload_bytes_to_s3(b"\x89PNG", "node-1.png")
        assert url == "https://s3.example/img.png"
        assert captured == {"data": b"\x89PNG", "filename": "node-1.png"}

    def test_upload_exception_returns_none(self, monkeypatch, capsys):
        def boom(data: bytes, filename: str) -> str:
            raise RuntimeError("s3 down")

        monkeypatch.setattr(workers_s3, "upload_bytes", boom)

        url = upload_bytes_to_s3(b"x", "node-1.png")
        assert url is None
        captured = capsys.readouterr()
        assert "上传异常" in captured.out
        assert "node-1.png" in captured.out

    def test_upload_returns_none_propagates(self, monkeypatch):
        # upload_bytes 可能本身返 None(配置缺失等),不算异常,直接透传
        monkeypatch.setattr(workers_s3, "upload_bytes", lambda data, name: None)

        url = upload_bytes_to_s3(b"x", "f.png")
        assert url is None


# ---------- download_and_upload ----------


class _FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}",
                request=httpx.Request("GET", "https://x"),
                response=httpx.Response(self.status_code),
            )


class _FakeAsyncClient:
    """模拟 `async with httpx.AsyncClient(...) as client` 用法。

    用 init 接受任意 kwargs(timeout=30 等),__aenter__/__aexit__ 标准 async ctx,
    get(url) 返回预设的 response 或抛预设异常。
    """

    def __init__(self, *args, **kwargs) -> None:
        # 实例化时不立即知道 response — 由 patch 时设置 class-level mocks
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc) -> None:
        pass

    async def get(self, url: str):
        if _FakeAsyncClient._raise_exc is not None:
            raise _FakeAsyncClient._raise_exc
        return _FakeAsyncClient._response

    # class-level state, monkeypatch via setattr
    _response: _FakeResponse | None = None
    _raise_exc: Exception | None = None


def _setup_httpx(monkeypatch, *, response: _FakeResponse | None = None, raise_exc: Exception | None = None) -> None:
    _FakeAsyncClient._response = response
    _FakeAsyncClient._raise_exc = raise_exc
    monkeypatch.setattr(workers_s3.httpx, "AsyncClient", _FakeAsyncClient)


class TestDownloadAndUpload:
    def test_happy_path(self, monkeypatch):
        _setup_httpx(monkeypatch, response=_FakeResponse(b"\x89PNG_DATA"))

        captured: dict = {}

        def fake_upload(data: bytes, filename: str) -> str:
            captured["data"] = data
            captured["filename"] = filename
            return "https://s3.example/img.png"

        monkeypatch.setattr(workers_s3, "upload_bytes", fake_upload)

        url = asyncio.run(download_and_upload("https://src/img.png", "node-7"))
        assert url == "https://s3.example/img.png"
        assert captured["data"] == b"\x89PNG_DATA"
        assert captured["filename"] == "node-7.png"

    def test_custom_extension(self, monkeypatch):
        _setup_httpx(monkeypatch, response=_FakeResponse(b"VIDEO"))

        captured: dict = {}

        def fake_upload(data: bytes, filename: str) -> str:
            captured["filename"] = filename
            return "https://s3.example/v.mp4"

        monkeypatch.setattr(workers_s3, "upload_bytes", fake_upload)

        url = asyncio.run(download_and_upload("https://src/v.mp4", "node-v", ext="mp4"))
        assert url == "https://s3.example/v.mp4"
        assert captured["filename"] == "node-v.mp4"

    def test_http_4xx_returns_none(self, monkeypatch):
        _setup_httpx(monkeypatch, response=_FakeResponse(b"", status_code=404))
        # upload_bytes shouldn't even be called
        upload_called = False

        def fake_upload(*_args, **_kw):
            nonlocal upload_called
            upload_called = True
            return "no"

        monkeypatch.setattr(workers_s3, "upload_bytes", fake_upload)

        url = asyncio.run(download_and_upload("https://src/x", "node-1"))
        assert url is None
        assert upload_called is False

    def test_http_timeout_returns_none(self, monkeypatch, capsys):
        _setup_httpx(monkeypatch, raise_exc=httpx.ConnectTimeout("slow"))

        url = asyncio.run(download_and_upload("https://src/x", "node-1"))
        assert url is None
        captured = capsys.readouterr()
        assert "上传异常" in captured.out
        assert "node-1" in captured.out

    def test_upload_failure_returns_none(self, monkeypatch):
        # 下载成功,但 upload 抛异常 — 外层捕获 → None
        _setup_httpx(monkeypatch, response=_FakeResponse(b"OK"))

        def boom(data, filename):
            raise RuntimeError("s3 perm denied")

        monkeypatch.setattr(workers_s3, "upload_bytes", boom)

        url = asyncio.run(download_and_upload("https://src/x", "node-1"))
        assert url is None

    def test_upload_returns_none_propagates(self, monkeypatch):
        # 下载成功,upload_bytes 返 None(非异常)— 透传 None
        _setup_httpx(monkeypatch, response=_FakeResponse(b"OK"))
        monkeypatch.setattr(workers_s3, "upload_bytes", lambda data, name: None)

        url = asyncio.run(download_and_upload("https://src/x", "node-1"))
        assert url is None
