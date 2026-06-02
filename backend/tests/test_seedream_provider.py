"""SeedreamProvider(火山豆包图像,复用 ARK key)单测 + provider 选择/就绪。"""

from __future__ import annotations

import asyncio

import httpx

from agent.tools import generation as gen
from agent.tools.generation import SeedreamProvider


def test_size_map_16x9_2k():
    p = SeedreamProvider()
    assert p._size("16:9", "2k") == "2560x1440"
    assert p._size("16:9", "4k") == "3840x2160"
    assert p._size("1:1", "2k") == "2048x2048"
    assert p._size("weird", "x") == "2048x2048"  # 兜底


def test_generate_builds_ark_request_and_parses_url(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"data": [{"url": "https://ark/img.jpeg", "size": "2560x1440"}]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, *, headers, json):
            captured["url"] = url
            captured["json"] = json
            captured["auth"] = headers.get("Authorization")
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    p = SeedreamProvider()
    out = asyncio.run(p.generate("一只橘猫", size="16:9", resolution="2k"))

    assert out == {"url": "https://ark/img.jpeg"}
    assert captured["url"].endswith("/images/generations")
    assert captured["json"]["size"] == "2560x1440"
    assert captured["json"]["response_format"] == "url"
    assert captured["json"]["watermark"] is False
    assert captured["auth"].startswith("Bearer ")
    assert "image" not in captured["json"]  # 文生图无参考图


def test_generate_image_to_image_passes_image(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"data": [{"url": "https://ark/i2i.jpeg"}]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, *, headers, json):
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    out = asyncio.run(SeedreamProvider().generate("改背景", image_urls=["https://x/a.jpg"]))
    assert out["url"] == "https://ark/i2i.jpeg"
    assert captured["json"]["image"] == "https://x/a.jpg"  # 单图传字符串


def test_generate_non200_returns_error(monkeypatch):
    class _Resp:
        status_code = 400

        def json(self):
            return {"error": {"code": "BadRequest"}}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    out = asyncio.run(SeedreamProvider().generate("x"))
    assert "error" in out


def test_provider_selection_and_readiness(monkeypatch):
    from agent import config

    monkeypatch.setattr(config, "IMAGE_GEN_PROVIDER", "seedream")
    monkeypatch.setattr(config, "ARK_API_KEY", "ark-key")
    assert isinstance(gen.get_provider(), SeedreamProvider)
    assert gen.image_gen_ready() is True

    monkeypatch.setattr(config, "ARK_API_KEY", "")
    assert gen.image_gen_ready() is False  # seedream 缺 ARK key → 未就绪

    monkeypatch.setattr(config, "IMAGE_GEN_PROVIDER", "apimart")
    monkeypatch.setattr(config, "IMAGE_GEN_API_KEY", "ak")
    assert gen.image_gen_ready() is True
