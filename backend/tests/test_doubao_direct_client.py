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
    responses: list[httpx.Response] | None = None  # per-call sequence (retry tests)
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
        if type(self).responses is not None:
            # Return the response for this call index; clamp to last so an
            # all-invalid run keeps returning the final element.
            seq = type(self).responses
            return seq[min(type(self).calls - 1, len(seq) - 1)]
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
    # Neutralize retry backoff so retry tests run instantly.
    monkeypatch.setattr(
        "agent.cascade.mediakit.doubao_direct_client._RETRY_SLEEP_S", 0
    )
    _FakeAsyncClient.response = None
    _FakeAsyncClient.responses = None
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
    # ARK call timeout asserted via the AsyncClient constructor kwarg. Raised
    # 120→165s (busy ~50s video measured ~119s, was hitting the old ceiling);
    # env-overridable via DOUBAO_DIRECT_TIMEOUT_S. Must stay < RUN_TURN_TIMEOUT_S.
    assert _FakeAsyncClient.last_timeout == doubao_direct_client._TIMEOUT_S == 165.0


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


def test_timeout_ordering_invariant() -> None:
    """The ARK call timeout must stay STRICTLY below the agent-turn timeout, which
    in turn stays below the frontend hard-timeout backstop. If ARK ≥ turn, the
    turn aborts mid-ARK-call and the user never gets the S7 (or a slow-but-valid
    result), wasting the headroom the turn budget was meant to give. This pins the
    fix for the ~119s busy-video timeout: ARK 165 < turn 180 (< frontend 210)."""
    from agent.transport.agent_runner import RUN_TURN_TIMEOUT_S

    assert doubao_direct_client._TIMEOUT_S < RUN_TURN_TIMEOUT_S, (
        f"ARK timeout {doubao_direct_client._TIMEOUT_S}s must be < turn "
        f"{RUN_TURN_TIMEOUT_S}s so the ARK call can finish (or cleanly S7) "
        f"inside the turn budget"
    )


def _bad_json_response() -> httpx.Response:
    request = httpx.Request("POST", doubao_direct_client.ARK_CHAT_COMPLETIONS_URL)
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": "not really json {{{"}}]},
        request=request,
    )


def test_malformed_json_retries_then_maps_s5(monkeypatch) -> None:
    """Persistently invalid JSON → retried _MAX_JSON_ATTEMPTS times, then S5."""
    _setup(monkeypatch)
    _FakeAsyncClient.response = _bad_json_response()

    with pytest.raises(HardFailure) as exc:
        asyncio.run(
            analyze_video_direct(
                "https://cdn.test/v.mp4",
                user_id="user_1",
                run_id="run_1",
            )
        )
    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD
    assert _FakeAsyncClient.calls == doubao_direct_client._MAX_JSON_ATTEMPTS


def test_invalid_json_retried_then_succeeds(monkeypatch) -> None:
    """A transient malformed-JSON response is retried; the next valid response
    yields the parsed contract (the founder-reported flakiness fallback)."""
    _setup(monkeypatch)
    _FakeAsyncClient.responses = [
        _bad_json_response(),
        _ark_response(200, _model_payload()),
    ]

    result = asyncio.run(
        analyze_video_direct(
            "https://cdn.test/v.mp4",
            user_id="user_1",
            run_id="run_1",
        )
    )
    assert len(result["scenes"]) == 3
    assert _FakeAsyncClient.calls == 2  # one retry


def test_auth_failure_is_not_retried(monkeypatch) -> None:
    """Non-JSON failures (auth) must fail fast — no retry spend."""
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
    assert _FakeAsyncClient.calls == 1


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


# --- S5 robustness: _repair_json (2026-06-01, eval exposed doubao JSON glitches) ---


import pytest as _pytest  # noqa: E402
from agent.cascade.mediakit.doubao_direct_client import _repair_json  # noqa: E402


@_pytest.mark.parametrize(
    "bad",
    [
        '{"a": "x", "b": "y",}',            # trailing comma before }
        '{"a": [1, 2, 3,]}',                # trailing comma before ]
        '{"a": "x"\n"b": "y"}',             # missing comma between newline-sep strings
        '{"scenes": [{"i":1}\n{"i":2}]}',   # missing comma between objects
    ],
)
def test_repair_json_fixes_common_doubao_glitches(bad):
    # the bad input must NOT parse, but the repaired one must
    with _pytest.raises(json.JSONDecodeError):
        json.loads(bad)
    json.loads(_repair_json(bad))  # raises if repair failed


def test_repair_json_leaves_valid_json_parseable():
    good = '{"a": "x", "scenes": [{"i": 1}, {"i": 2}]}'
    assert json.loads(_repair_json(good)) == json.loads(good)
