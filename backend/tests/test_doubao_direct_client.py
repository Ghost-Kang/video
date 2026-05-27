"""Tests for the doubao_direct single-shot ARK vision client."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.mediakit import doubao_direct_client
from agent.cascade.mediakit.doubao_direct_client import (
    PREDICT_DOUBAO_DIRECT_CNY,
    analyze_video_direct,
)


def _model_payload() -> dict:
    """Minimal valid contract-shaped JSON the model is expected to emit."""
    return {
        "viral_analysis": {
            "hook": "H8 凌晨第三次醒了开场",
            "pacing": "前 3s 钩子 → 中段两步 → 尾部反差",
            "climax": "第 22 秒妈妈终于睡着",
            "visual_style": "夜光居家自然记录",
            "emotional_arc": "疲惫 → 崩溃 → 释然",
            "target_audience": "0-1 岁宝妈,睡眠剥夺中",
            "engagement_levers": "评论区抛'你家几月睡整觉'",
            "replicable_formula": "钩子<凌晨情绪> → 中段<两步动作> → 结尾<反差成品>",
            "audio": {
                "bgm": "钢琴渐强 3 处转点",
                "voice_pace": "中速口播 220 字/分",
                "sound_effects": "结尾 0.5s 原声留白",
            },
            "production": {
                "cost_tier": "solo_phone",
                "estimated_hours": 1.5,
                "replaceable_anchors": ["原片夜灯 → 你的晨光"],
            },
        },
        "scenes": [
            {
                "scene_index": 1,
                "timestamp_start": 0.0,
                "timestamp_end": 10.0,
                "scene": "镜头一",
                "dialogue_and_narration": "怎么又醒了。",
                "visual_content": "妈妈在床边抱着宝宝。",
                "subject": "妈妈+宝宝",
                "shot_type": "medium",
                "camera_movement": "static",
                "first_frame_url": None,
            },
            {
                "scene_index": 2,
                "timestamp_start": 10.0,
                "timestamp_end": 20.0,
                "scene": "镜头二",
                "dialogue_and_narration": "再哄一次。",
                "visual_content": "妈妈轻拍宝宝。",
                "subject": "妈妈",
                "shot_type": "close_up",
                "camera_movement": "static",
                "first_frame_url": None,
            },
            {
                "scene_index": 3,
                "timestamp_start": 20.0,
                "timestamp_end": 30.0,
                "scene": "镜头三",
                "dialogue_and_narration": "终于睡了。",
                "visual_content": "宝宝闭眼,妈妈靠在墙上。",
                "subject": "妈妈+宝宝",
                "shot_type": "medium",
                "camera_movement": "static",
                "first_frame_url": None,
            },
        ],
        "full_transcript": "怎么又醒了\n再哄一次\n终于睡了",
        "confidence": 0.78,
    }


def _ark_response(status_code: int, model_json: dict | None = None, body: dict | None = None) -> httpx.Response:
    """Build a fake ARK chat-completion response wrapping the model's JSON."""
    request = httpx.Request("POST", doubao_direct_client.ARK_CHAT_COMPLETIONS_URL)
    if body is not None:
        return httpx.Response(status_code, json=body, request=request)
    if model_json is None:
        return httpx.Response(status_code, json={}, request=request)
    content = json.dumps(model_json, ensure_ascii=False)
    return httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": content}}]},
        request=request,
    )


class _FakeAsyncClient:
    response: httpx.Response | None = None
    exc: Exception | None = None
    calls: int = 0
    last_headers: dict | None = None
    last_json: dict | None = None
    last_url: str | None = None
    last_timeout: float | None = None

    def __init__(self, *args, **kwargs):
        type(self).last_timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url: str, *, json: dict, headers: dict):
        type(self).calls += 1
        type(self).last_url = url
        type(self).last_headers = headers
        type(self).last_json = json
        if self.exc:
            raise self.exc
        assert self.response is not None
        return self.response


def _setup(monkeypatch) -> None:
    monkeypatch.setattr("agent.config.ARK_API_KEY", "ark-test")
    monkeypatch.setattr("agent.config.VOLC_MEDIAKIT_AK", "mk-test")
    monkeypatch.setattr("agent.config.DOUBAO_MODEL", "doubao-seed-1-6-250615")
    monkeypatch.setattr(
        "agent.cascade.mediakit.doubao_direct_client.httpx.AsyncClient",
        _FakeAsyncClient,
    )

    async def _no_op_cost_guard(**_kwargs):
        return None

    monkeypatch.setattr(
        "agent.cascade.mediakit.doubao_direct_client.cost_guard",
        _no_op_cost_guard,
    )
    _FakeAsyncClient.response = None
    _FakeAsyncClient.exc = None
    _FakeAsyncClient.calls = 0
    _FakeAsyncClient.last_headers = None
    _FakeAsyncClient.last_json = None
    _FakeAsyncClient.last_url = None
    _FakeAsyncClient.last_timeout = None


def test_happy_path_parses_full_contract_shape(monkeypatch) -> None:
    _setup(monkeypatch)
    _FakeAsyncClient.response = _ark_response(200, _model_payload())

    result = asyncio.run(
        analyze_video_direct(
            "https://cdn.test/v.mp4",
            user_id="user_1",
            run_id="run_1",
        )
    )

    assert set(result) >= {
        "viral_analysis",
        "scenes",
        "full_transcript",
        "confidence",
    }
    assert len(result["scenes"]) == 3
    assert result["viral_analysis"]["replicable_formula"].startswith("钩子")
    # Auth + request shape verified end-to-end.
    assert _FakeAsyncClient.last_headers == {
        "Authorization": "Bearer ark-test",
        "Content-Type": "application/json",
    }
    assert _FakeAsyncClient.last_url.endswith("/chat/completions")
    body = _FakeAsyncClient.last_json
    assert body["model"] == "doubao-seed-1-6-250615"
    assert body["stream"] is False
    user_msg = body["messages"][1]
    assert user_msg["role"] == "user"
    video_part = user_msg["content"][0]
    assert video_part["type"] == "video_url"
    assert video_part["video_url"]["url"] == "https://cdn.test/v.mp4"
    assert video_part["video_url"]["fps"] == 1
    assert video_part["video_url"]["max_frames"] == 60
    # 120s timeout asserted via the AsyncClient constructor kwarg
    assert _FakeAsyncClient.last_timeout == 120.0


def test_strips_json_fence_defensively(monkeypatch) -> None:
    _setup(monkeypatch)
    fenced = "```json\n" + json.dumps(_model_payload(), ensure_ascii=False) + "\n```"
    request = httpx.Request("POST", doubao_direct_client.ARK_CHAT_COMPLETIONS_URL)
    _FakeAsyncClient.response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": fenced}}]},
        request=request,
    )

    result = asyncio.run(
        analyze_video_direct(
            "https://cdn.test/v.mp4",
            user_id="user_1",
            run_id="run_1",
        )
    )
    assert len(result["scenes"]) == 3


def test_clamps_confidence_when_model_emits_percentage(monkeypatch) -> None:
    _setup(monkeypatch)
    payload = _model_payload()
    payload["confidence"] = 85  # percentage style
    _FakeAsyncClient.response = _ark_response(200, payload)

    result = asyncio.run(
        analyze_video_direct(
            "https://cdn.test/v.mp4",
            user_id="user_1",
            run_id="run_1",
        )
    )
    assert result["confidence"] == pytest.approx(0.85)


def test_auth_refused_maps_s8(monkeypatch) -> None:
    _setup(monkeypatch)
    _FakeAsyncClient.response = _ark_response(401, body={"error": "unauthorized"})

    with pytest.raises(HardFailure) as exc:
        asyncio.run(
            analyze_video_direct(
                "https://cdn.test/v.mp4",
                user_id="user_1",
                run_id="run_1",
            )
        )
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert "auth_refused" in str(exc.value)


def test_timeout_maps_s7(monkeypatch) -> None:
    _setup(monkeypatch)
    _FakeAsyncClient.exc = httpx.TimeoutException("ARK slow")

    with pytest.raises(HardFailure) as exc:
        asyncio.run(
            analyze_video_direct(
                "https://cdn.test/v.mp4",
                user_id="user_1",
                run_id="run_1",
            )
        )
    assert exc.value.code == FailureCode.S7_UPSTREAM_TIMEOUT


def test_malformed_json_maps_s5(monkeypatch) -> None:
    _setup(monkeypatch)
    request = httpx.Request("POST", doubao_direct_client.ARK_CHAT_COMPLETIONS_URL)
    _FakeAsyncClient.response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "not really json {{{"}}]},
        request=request,
    )

    with pytest.raises(HardFailure) as exc:
        asyncio.run(
            analyze_video_direct(
                "https://cdn.test/v.mp4",
                user_id="user_1",
                run_id="run_1",
            )
        )
    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD


def test_missing_api_key_short_circuits_before_http(monkeypatch) -> None:
    _setup(monkeypatch)
    monkeypatch.setattr("agent.config.ARK_API_KEY", "")

    with pytest.raises(HardFailure) as exc:
        asyncio.run(
            analyze_video_direct(
                "https://cdn.test/v.mp4",
                user_id="user_1",
                run_id="run_1",
            )
        )
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert _FakeAsyncClient.calls == 0


def test_cost_guard_constant_aligned_with_module() -> None:
    """The re-exported PREDICT_DOUBAO_DIRECT_CNY must match cost_guard's value."""
    from agent.cascade import cost_guard as cg

    assert PREDICT_DOUBAO_DIRECT_CNY == cg.PREDICT_DOUBAO_DIRECT_CNY == 0.50
