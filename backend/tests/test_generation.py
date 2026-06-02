"""Image-generation provider tests.

Live provider calls are opt-in via RUN_LIVE_GENERATION_TESTS=1. The default
test suite must stay offline and deterministic.
"""

import asyncio
import os

import pytest

from agent.tools.generation import ApimartProvider, GoogleProvider, get_provider


def test_get_provider_selects_google(monkeypatch):
    # get_provider 现动态读 config.IMAGE_GEN_PROVIDER(支持 seedream/apimart/google + env 切换)。
    monkeypatch.setattr("agent.config.IMAGE_GEN_PROVIDER", "google")

    provider = get_provider()

    assert isinstance(provider, GoogleProvider)


def test_get_provider_selects_apimart_when_configured(monkeypatch):
    # 默认已改 seedream(见 test_image_provider_default);显式 apimart 仍返回 ApimartProvider。
    monkeypatch.setattr("agent.config.IMAGE_GEN_PROVIDER", "apimart")

    provider = get_provider()

    assert isinstance(provider, ApimartProvider)


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_GENERATION_TESTS") != "1",
    reason="live image-generation tests require RUN_LIVE_GENERATION_TESTS=1",
)
def test_live_provider_submit_and_poll():
    """Live smoke: submit + poll through the configured provider."""
    provider = get_provider()
    result = asyncio.run(provider.submit("一只橘猫坐在窗台上看夕阳，水彩画风格"))
    assert "task_id" in result, result

    polled = asyncio.run(provider.poll(result["task_id"]))
    assert "url" in polled or "image_data" in polled, polled
