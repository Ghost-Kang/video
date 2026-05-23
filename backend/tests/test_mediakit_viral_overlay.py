from __future__ import annotations

import asyncio
import json

import httpx

from agent.cascade.adapter import normalize_analysis_result
from agent.cascade.failures import WarningCode
from agent.cascade.mediakit.viral_overlay import (
    MAX_STORYLINE_CONTEXT_CHARS,
    overlay_viral_dims,
)


def _payload() -> dict:
    return {
        "schema_version": "1.0",
        "analysis_id": "ana_mk_test",
        "source_url": "https://example.com/video.mp4",
        "platform": "other",
        "created_at": "2026-05-23T00:00:00+00:00",
        "model": "mediakit-storyline",
        "cost_cny": 0.0,
        "duration_s": 36,
        "confidence": 0.82,
        "viral_analysis": {
            "hook": "宝宝拒绝第一口",
            "pacing": "3 个故事片段推进",
            "climax": "宝宝主动抢勺子",
            "visual_style": "厨房暖光自然记录",
            "emotional_arc": "从焦虑到松一口气",
            "target_audience": "宝宝辅食、营养搭配",
            "engagement_levers": "评论区围绕挑食经验互动",
            "replicable_formula": "先给痛点,中段给做法,最后用宝宝主动吃形成反差。",
        },
        "scenes": [
            {
                "scene_index": 1,
                "timestamp_start": 0.0,
                "timestamp_end": 12.0,
                "scene": "宝宝拒绝第一口",
                "dialogue_and_narration": "你家宝宝是不是也这样,怎么喂都不吃?",
                "visual_content": "宝宝坐在餐椅上转头,桌上有一碗辅食。",
                "subject": None,
                "shot_type": "medium",
                "camera_movement": "static",
                "warnings": [],
            },
            {
                "scene_index": 2,
                "timestamp_start": 12.0,
                "timestamp_end": 24.0,
                "scene": "妈妈蒸苹果泥",
                "dialogue_and_narration": "蒸八分钟,又软又香。",
                "visual_content": "厨房暖光,妈妈把苹果切块后上锅蒸。",
                "subject": None,
                "shot_type": "medium",
                "camera_movement": "static",
                "warnings": [],
            },
            {
                "scene_index": 3,
                "timestamp_start": 24.0,
                "timestamp_end": 36.0,
                "scene": "宝宝主动抢勺子",
                "dialogue_and_narration": "这一口下去,妈妈真的松了一口气。",
                "visual_content": "宝宝笑着伸手抢勺子,妈妈在镜头外笑。",
                "subject": None,
                "shot_type": "medium",
                "camera_movement": "static",
                "warnings": [],
            },
        ],
        "warnings": [],
    }


def _response(status_code: int, payload: dict | None = None) -> httpx.Response:
    request = httpx.Request("POST", "https://amk-ark.cn-beijing.volces.com/api/v1/chat/completions")
    return httpx.Response(status_code, json=payload or {}, request=request)


class _FakeAsyncClient:
    response: httpx.Response | None = None
    exc: Exception | None = None
    calls: int = 0
    last_headers: dict | None = None
    last_json: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url: str, *, json: dict, headers: dict):
        type(self).calls += 1
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
    monkeypatch.setattr("agent.cascade.mediakit.viral_overlay.httpx.AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.response = None
    _FakeAsyncClient.exc = None
    _FakeAsyncClient.calls = 0
    _FakeAsyncClient.last_headers = None
    _FakeAsyncClient.last_json = None


def test_overlay_happy_path_updates_viral_analysis(monkeypatch) -> None:
    _setup(monkeypatch)
    overlay = {
        "hook": "用宝宝拒食痛点开场",
        "pacing": "痛点、做法、反馈三段递进",
        "climax": "宝宝主动抢勺子完成反差",
        "visual_style": "家庭厨房暖光实拍",
        "emotional_arc": "焦虑到放心",
        "target_audience": "被挑食困扰的宝妈",
        "engagement_levers": "引导评论分享辅食经验",
        "replicable_formula": "先抛拒食痛点,再给可复制做法,最后用宝宝反馈收束。",
    }
    _FakeAsyncClient.response = _response(200, {"choices": [{"message": {"content": json.dumps(overlay)}}]})

    result = asyncio.run(overlay_viral_dims(_payload(), "https://cdn.test/v.mp4"))
    contract = normalize_analysis_result(result)

    assert contract.viral_analysis.hook == "用宝宝拒食痛点开场"
    assert contract.viral_analysis.replicable_formula == "先抛拒食痛点,再给可复制做法,最后用宝宝反馈收束。"
    assert contract.model == "mediakit-storyline+ark-doubao-seed-1-6-250615"
    assert _FakeAsyncClient.last_headers == {
        "Authorization": "Bearer ark-test/mk-test",
        "Content-Type": "application/json",
    }
    video_part = _FakeAsyncClient.last_json["messages"][0]["content"][1]["video_url"]
    assert video_part == {
        "url": "https://cdn.test/v.mp4",
        "fps": 1,
        "max_frames": 100,
        "max_pixels": 518400,
    }


def test_overlay_timeout_falls_back_to_storyline_only(monkeypatch) -> None:
    _setup(monkeypatch)
    _FakeAsyncClient.exc = httpx.TimeoutException("too slow")
    original = _payload()

    result = asyncio.run(overlay_viral_dims(original, "https://cdn.test/v.mp4"))
    contract = normalize_analysis_result(result)

    assert contract.viral_analysis.hook == original["viral_analysis"]["hook"]
    assert any(w.code == WarningCode.W2_FALLBACK_USED.value and w.field == "viral_analysis" for w in contract.warnings)


def test_overlay_malformed_json_falls_back_with_warning(monkeypatch) -> None:
    _setup(monkeypatch)
    _FakeAsyncClient.response = _response(200, {"choices": [{"message": {"content": "not json"}}]})

    result = asyncio.run(overlay_viral_dims(_payload(), "https://cdn.test/v.mp4"))
    contract = normalize_analysis_result(result)

    assert contract.viral_analysis.climax == "宝宝主动抢勺子"
    assert any(w.code == WarningCode.W2_FALLBACK_USED.value and "JSON" in w.message for w in contract.warnings)


def test_overlay_truncates_storyline_context_budget(monkeypatch) -> None:
    _setup(monkeypatch)
    _FakeAsyncClient.response = _response(
        200,
        {"choices": [{"message": {"content": json.dumps({"hook": "长文本后仍能覆盖"})}}]},
    )
    payload = _payload()
    payload["scenes"][0]["dialogue_and_narration"] = "很长" * (MAX_STORYLINE_CONTEXT_CHARS + 100)

    asyncio.run(overlay_viral_dims(payload, "https://cdn.test/v.mp4"))

    text_part = _FakeAsyncClient.last_json["messages"][0]["content"][0]["text"]
    assert len(text_part) < MAX_STORYLINE_CONTEXT_CHARS + 2000
    assert "[truncated]" in text_part
