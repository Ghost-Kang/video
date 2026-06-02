"""cascade_analyze / cascade_rewrite tool unit tests.

These tools are the LLM's only way to drive the Cascade pipeline from chat.
We mock the underlying services (already tested elsewhere) and verify:

- Tool calls the right service with the right kwargs (user_id from ContextVar).
- Tool pushes the correct WS frame on success.
- HardFailure / LookupError / unknown niche → tool returns `{"error": ...}`,
  never raises (raising kills the LangGraph turn).
- Return shape is the compact dict the LLM sees (NOT the full Pydantic).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import pytest

from agent.cascade.contract import (
    AudioDim,
    CameraMovement,
    CascadeAnalysisContract,
    Platform,
    ProductionDim,
    Scene,
    ShotType,
    ViralAnalysis,
)
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.rewrite_service import RewriteResult, RewriteShot
from agent.tools import cascade as cascade_tools
from agent.tools.cascade import (
    cascade_analyze,
    cascade_ask,
    cascade_generate_first_frame,
    cascade_rewrite,
)
from agent.transport.runtime_ctx import set_run_ctx


# ---------- fakes ----------


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))


def _fake_contract(viral_analysis: ViralAnalysis | None = None) -> CascadeAnalysisContract:
    scenes = [
        Scene(
            scene_index=i,
            timestamp_start=(i - 1) * 5.0,
            timestamp_end=i * 5.0,
            scene=f"scene{i}",
            dialogue_and_narration="word",
            visual_content="visual",
            subject=None,
            shot_type=ShotType.MEDIUM,
            camera_movement=CameraMovement.STATIC,
            first_frame_url=None,
            warnings=[],
        )
        for i in range(1, 4)
    ]
    return CascadeAnalysisContract(
        schema_version="1.0",
        analysis_id="ana_fake",
        source_url="https://douyin.com/video/1",  # type: ignore[arg-type]
        platform=Platform.DOUYIN,
        created_at=datetime.now(timezone.utc),
        model="fake",
        cost_cny=0.1,
        duration_s=15,
        viral_analysis=viral_analysis or ViralAnalysis(
            hook="抓眼球的开场",
            pacing="紧凑",
            climax="反转",
            visual_style="温暖",
            emotional_arc="共情",
            target_audience="宝妈",
            engagement_levers="对比",
            replicable_formula="3 秒钩子 + 转折",
            audio=AudioDim(
                bgm="轻快钢琴",
                voice_pace="中速口播 200 字/分",
                sound_effects="转场 1 次",
            ),
            production=ProductionDim(
                cost_tier="solo_phone",
                estimated_hours=1.0,
                replaceable_anchors=["原片厨房 → 你的厨房"],
            ),
        ),
        scenes=scenes,
        warnings=[],
        confidence=0.85,
    )


def _fake_rewrite_result() -> RewriteResult:
    return RewriteResult(
        rewrite_id="rw_fake",
        analysis_id="ana_fake",
        niche="baomam_fushi",
        script_markdown="### 改写脚本\n1. xxx",
        shots=[
            RewriteShot(shot_index=i, dialogue=f"line{i}", visual=f"visual{i}")
            for i in range(1, 4)
        ],
        parser_warnings=[],
        confidence=0.8,
        cost_cny=0.5,
        model="fake",
    )


# ---------- cascade_analyze ----------


class TestCascadeAnalyze:
    def test_happy_path_returns_compact_dict_and_pushes_ws(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        captured: dict[str, Any] = {}

        async def fake_service(source_url: str, *, user_id: str, run_id=None):
            captured["source_url"] = source_url
            captured["user_id"] = user_id
            captured["run_id"] = run_id
            return _fake_contract()

        monkeypatch.setattr(cascade_tools, "request_shallow_analysis", fake_service)

        result = asyncio.run(cascade_analyze.ainvoke({"source_url": "https://douyin.com/video/abc"}))

        # Service called with ContextVar-sourced user_id
        assert captured == {
            "source_url": "https://douyin.com/video/abc",
            "user_id": "u1",
            "run_id": None,
        }

        # Compact dict for LLM — no full scene list, no full viral_analysis nested
        assert result["analysis_id"] == "ana_fake"
        assert result["confidence"] == 0.85
        assert result["hook"] == "抓眼球的开场"
        assert result["scene_count"] == 3
        assert result["platform"] == "douyin"
        # CRITICAL: the LLM must NOT receive the full scenes list (context bloat)
        assert "scenes" not in result
        # Niche-inference fields must exist (Director relies on them in §0.5).
        # The default fake VA has engagement_levers="对比" which fires H4 → that
        # disqualifies baomam_fushi (H4 ∈ negatives) and hits jiating_chufang's P0.
        assert "detected_hooks" in result
        assert "suggested_niche" in result
        assert "niche_inference_reason" in result
        assert result["detected_hooks"] == ["H4"]
        assert result["suggested_niche"] == "jiating_chufang"
        assert "score=1" in result["niche_inference_reason"]

    def test_baomam_fixture_va_text_infers_baomam_fushi(self, monkeypatch):
        """The synthetic_v1 baomam fixture's viral_analysis text fires H1
        (via "0-3 岁宝宝妈妈" in target_audience), which uniquely points to
        baomam_fushi (jiating's P0 H4/H9 absent, yuer's P0 H8 absent).
        """
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        baomam_va = ViralAnalysis(
            hook="开场 1.2 秒抛出「宝宝拒食三次后第一口吃下」的悬念画面",
            pacing="节奏 4-3-2 秒压缩，越接近结尾镜头越短",
            climax="倒数第二镜：宝宝抢勺子的笑声 + 妈妈惊喜表情",
            visual_style="暖色厨房，木质砧板，自然光，俯拍为主",
            emotional_arc="焦虑（喂不下）→ 尝试（换花样）→ 惊喜（吃下）→ 成就感",
            target_audience="0-3 岁宝宝妈妈，普通家庭厨房环境",
            engagement_levers="评论区抛「你家宝宝几个月开始吃辅食」诱导互动",
            replicable_formula="悬念开场（拒食痛点） + 3 步解决方案（换花样/换温度/换工具） + 反差结尾",
            audio=AudioDim(
                bgm="轻快童谣风钢琴",
                voice_pace="中速口播 200 字/分",
                sound_effects="切苹果 1 次切音",
            ),
            production=ProductionDim(
                cost_tier="solo_phone",
                estimated_hours=1.5,
                replaceable_anchors=["原片厨房 → 你的厨房"],
            ),
        )

        async def fake_service(*args, **kwargs):
            return _fake_contract(viral_analysis=baomam_va)

        monkeypatch.setattr(cascade_tools, "request_shallow_analysis", fake_service)

        result = asyncio.run(cascade_analyze.ainvoke({"source_url": "https://douyin.com/video/abc"}))

        assert result["suggested_niche"] == "baomam_fushi"
        assert "H1" in result["detected_hooks"]
        assert "score=" in result["niche_inference_reason"]

        # WS push
        assert len(ws.sent) == 1
        frame = ws.sent[0]
        assert frame["type"] == "analysis_returned"
        assert frame["thread_id"] == "t1"
        assert frame["analysis"]["analysis_id"] == "ana_fake"
        assert len(frame["analysis"]["scenes"]) == 3  # full payload to frontend

    def test_hard_failure_returns_error_dict_does_not_raise(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        async def boom(*args, **kwargs):
            raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "rate_limit")

        monkeypatch.setattr(cascade_tools, "request_shallow_analysis", boom)

        # Must NOT raise — agent turn would crash
        result = asyncio.run(cascade_analyze.ainvoke({"source_url": "https://douyin.com/video/x"}))

        assert result["error"] == "S8_UPSTREAM_REFUSED"
        assert "繁忙" in result["message"]
        # W5D3 Bug #2 — HardFailure now pushes a structured `analysis_failed`
        # frame so frontend ChatPanel can flip into `failed` state without
        # waiting for the Director's text reply.
        assert len(ws.sent) == 1
        frame = ws.sent[0]
        assert frame["type"] == "analysis_failed"
        assert frame["code"] == "S8_UPSTREAM_REFUSED"
        assert frame["stage"] == "analysis"

    def test_no_ws_in_ctx_returns_data_without_push(self, monkeypatch):
        # ws missing → tool should still return data, just no push
        set_run_ctx({"user_id": "u1", "thread_id": "t1"})

        async def ok(*args, **kwargs):
            return _fake_contract()

        monkeypatch.setattr(cascade_tools, "request_shallow_analysis", ok)
        result = asyncio.run(cascade_analyze.ainvoke({"source_url": "https://douyin.com/video/x"}))
        assert result["analysis_id"] == "ana_fake"

    def test_generic_exception_caught_returns_error(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        async def boom(*args, **kwargs):
            raise RuntimeError("network blew up")

        monkeypatch.setattr(cascade_tools, "request_shallow_analysis", boom)
        result = asyncio.run(cascade_analyze.ainvoke({"source_url": "https://douyin.com/video/x"}))
        assert result["error"] == "S5_INVALID_PAYLOAD"
        assert "network blew up" in result["message"]


# ---------- cascade_rewrite ----------


class TestCascadeRewrite:
    def test_happy_path_returns_compact_dict_and_pushes_ws(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        captured: dict[str, Any] = {}

        async def fake_service(*, analysis_id, niche, user_id, run_id=None, topic=None):
            captured.update(
                analysis_id=analysis_id, niche=niche, user_id=user_id, run_id=run_id, topic=topic
            )
            return _fake_rewrite_result()

        monkeypatch.setattr(cascade_tools, "request_rewrite", fake_service)

        result = asyncio.run(cascade_rewrite.ainvoke({
            "analysis_id": "ana_fake",
            "niche": "baomam_fushi",
        }))

        assert captured == {
            "analysis_id": "ana_fake",
            "niche": "baomam_fushi",
            "user_id": "u1",
            "run_id": None,
            # 不传 topic → 工具把空串归一为 None 再下传 service。
            "topic": None,
        }

        # Compact dict — no shots list (LLM doesn't need to see them)
        assert result["rewrite_id"] == "rw_fake"
        assert result["niche"] == "baomam_fushi"
        assert result["shots_count"] == 3
        assert "shots" not in result

        # WS push carries full rewrite incl. shots
        assert len(ws.sent) == 1
        frame = ws.sent[0]
        assert frame["type"] == "rewrite_returned"
        assert frame["thread_id"] == "t1"
        assert frame["analysis_id"] == "ana_fake"
        assert len(frame["rewrite"]["shots"]) == 3
        assert frame["rewrite"]["script_markdown"].startswith("### 改写脚本")

    def test_generic_niche_with_topic_passes_topic_through(self, monkeypatch):
        # 去 niche 后默认路径:niche="generic" + 一句话主题 topic 透传给 service。
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        captured: dict[str, Any] = {}

        async def fake_service(*, analysis_id, niche, user_id, run_id=None, topic=None):
            captured.update(niche=niche, topic=topic)
            return _fake_rewrite_result()

        monkeypatch.setattr(cascade_tools, "request_rewrite", fake_service)

        result = asyncio.run(cascade_rewrite.ainvoke({
            "analysis_id": "ana_fake",
            "niche": "generic",
            "topic": "  免烤提拉米苏  ",  # 前后空白应被 strip
        }))

        assert "error" not in result
        assert captured["niche"] == "generic"
        assert captured["topic"] == "免烤提拉米苏"

    def test_generic_blank_topic_normalized_to_none(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        captured: dict[str, Any] = {}

        async def fake_service(*, analysis_id, niche, user_id, run_id=None, topic=None):
            captured.update(topic=topic)
            return _fake_rewrite_result()

        monkeypatch.setattr(cascade_tools, "request_rewrite", fake_service)

        result = asyncio.run(cascade_rewrite.ainvoke({
            "analysis_id": "ana_fake",
            "niche": "generic",
            "topic": "   ",  # 纯空白 → None(纯按源片骨架改写)
        }))

        assert "error" not in result
        assert captured["topic"] is None

    def test_unknown_niche_rejected_without_calling_service(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        called = False

        async def fake_service(**_):
            nonlocal called
            called = True
            return _fake_rewrite_result()

        monkeypatch.setattr(cascade_tools, "request_rewrite", fake_service)

        result = asyncio.run(cascade_rewrite.ainvoke({
            "analysis_id": "ana_fake",
            "niche": "music_dance",  # not in SUPPORTED_NICHES
        }))

        assert result["error"] == "UNKNOWN_NICHE"
        assert "music_dance" in result["message"]
        assert called is False
        assert ws.sent == []

    def test_lookup_error_returns_analysis_not_found(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        async def boom(**_):
            raise LookupError("not found")

        monkeypatch.setattr(cascade_tools, "request_rewrite", boom)

        result = asyncio.run(cascade_rewrite.ainvoke({
            "analysis_id": "ana_missing",
            "niche": "baomam_fushi",
        }))

        assert result["error"] == "ANALYSIS_NOT_FOUND"
        assert "ana_missing" in result["message"]
        assert ws.sent == []

    def test_hard_failure_returns_error(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": None})

        async def boom(**_):
            raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "cost cap")

        monkeypatch.setattr(cascade_tools, "request_rewrite", boom)
        result = asyncio.run(cascade_rewrite.ainvoke({
            "analysis_id": "ana_fake",
            "niche": "baomam_fushi",
        }))
        assert result["error"] == "S8_UPSTREAM_REFUSED"


# ---------- cascade_generate_first_frame ----------


class _FakeApimartProvider:
    """Stand-in for ApimartProvider — captures the call and returns canned result."""

    def __init__(self, result: dict) -> None:
        self._result = result
        self.calls: list[dict] = []

    async def generate(self, *, prompt: str, size: str = "16:9", resolution: str = "2k", image_urls=None) -> dict:
        self.calls.append({"prompt": prompt, "size": size, "resolution": resolution})
        return self._result


class TestCascadeGenerateFirstFrame:
    def _install_fakes(
        self,
        monkeypatch,
        *,
        rewrite_json: str | None,
        provider_result: dict,
        cost_guard_raises: HardFailure | None = None,
    ) -> _FakeApimartProvider:
        async def fake_load_rewrite(rewrite_id: str):
            return rewrite_json

        async def fake_cost_guard(*, user_id, run_id, predicted_cost_cny):
            if cost_guard_raises is not None:
                raise cost_guard_raises

        async def fake_emit(*args, **kwargs):
            return None

        provider = _FakeApimartProvider(provider_result)
        monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", fake_load_rewrite)
        monkeypatch.setattr(cascade_tools, "cost_guard", fake_cost_guard)
        monkeypatch.setattr(cascade_tools, "emit", fake_emit)
        monkeypatch.setattr(cascade_tools, "_make_image_provider", lambda: provider)
        return provider

    def test_happy_path_returns_url_and_pushes_ws(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        rewrite_json = _fake_rewrite_result().model_dump_json()
        provider = self._install_fakes(
            monkeypatch,
            rewrite_json=rewrite_json,
            provider_result={"url": "https://cdn/img1.png", "actual_time": 12.3},
        )

        result = asyncio.run(cascade_generate_first_frame.ainvoke({
            "rewrite_id": "rw_fake",
            "shot_index": 2,
        }))

        assert result["shot_index"] == 2
        assert result["image_url"] == "https://cdn/img1.png"
        assert result["cost_cny"] > 0

        # Provider received the matching shot's `visual`.
        assert provider.calls == [{"prompt": "visual2", "size": "16:9", "resolution": "2k"}]

        # WS frame fired with the URL.
        assert len(ws.sent) == 1
        frame = ws.sent[0]
        assert frame["type"] == "shot_first_frame_returned"
        assert frame["thread_id"] == "t1"
        assert frame["rewrite_id"] == "rw_fake"
        assert frame["shot_index"] == 2
        assert frame["image_url"] == "https://cdn/img1.png"

    def test_unknown_rewrite_id_returns_error_without_calling_provider(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        provider = self._install_fakes(
            monkeypatch,
            rewrite_json=None,
            provider_result={"url": "should-not-be-used"},
        )

        result = asyncio.run(cascade_generate_first_frame.ainvoke({
            "rewrite_id": "rw_missing",
            "shot_index": 1,
        }))

        assert result["error"] == "REWRITE_NOT_FOUND"
        assert "rw_missing" in result["message"]
        assert provider.calls == []
        assert ws.sent == []

    def test_invalid_shot_index_returns_error(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        rewrite_json = _fake_rewrite_result().model_dump_json()
        provider = self._install_fakes(
            monkeypatch,
            rewrite_json=rewrite_json,
            provider_result={"url": "should-not-be-used"},
        )

        result = asyncio.run(cascade_generate_first_frame.ainvoke({
            "rewrite_id": "rw_fake",
            "shot_index": 99,
        }))

        assert result["error"] == "SHOT_NOT_FOUND"
        assert "99" in result["message"]
        assert provider.calls == []
        assert ws.sent == []

    def test_provider_timeout_maps_to_s7(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        rewrite_json = _fake_rewrite_result().model_dump_json()
        self._install_fakes(
            monkeypatch,
            rewrite_json=rewrite_json,
            provider_result={"error": "timeout"},
        )

        result = asyncio.run(cascade_generate_first_frame.ainvoke({
            "rewrite_id": "rw_fake",
            "shot_index": 1,
        }))

        assert result["error"] == "S7_UPSTREAM_TIMEOUT"
        assert ws.sent == []

    def test_cost_guard_blocks_before_provider_call(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        rewrite_json = _fake_rewrite_result().model_dump_json()
        provider = self._install_fakes(
            monkeypatch,
            rewrite_json=rewrite_json,
            provider_result={"url": "should-not-be-used"},
            cost_guard_raises=HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "over cap"),
        )

        result = asyncio.run(cascade_generate_first_frame.ainvoke({
            "rewrite_id": "rw_fake",
            "shot_index": 1,
        }))

        assert result["error"] == "S8_UPSTREAM_REFUSED"
        assert provider.calls == []
        # 2026-06-01 生成草稿图 leg:单张草稿图触顶**不再推全局 analysis_failed 帧**
        # —— 那会让前端 CardStack 整屏切到 FailureBanner、把分析+改写全藏掉。错误经返回值
        # 给 Director,在 chat 一句话提示用户(director.md §0.5 复述 message);前端对应镜头
        # 的草稿图区超时回到「重试」。故此处不推任何全局帧。
        assert ws.sent == []


# ---------- cascade_ask (W4D5) ----------


class TestCascadeAsk:
    """Free-form Q&A tool against a stored analysis.

    Coverage:
      - happy path → returns answer + pushes WS frame
      - unknown analysis_id → ANALYSIS_NOT_FOUND, no WS, no LLM call
      - blank question → S5_INVALID_PAYLOAD
      - cost_guard refusal → S8 without LLM call
      - LLM transport blow-up → S8 with message
      - WS frame absent in ctx → still returns answer
    """

    def _install_fakes(
        self,
        monkeypatch,
        *,
        contract,
        llm_answer: str = "这条 BGM 让人想起港片是因为前 3s 用了大提琴下行 + 雨声背景音，节拍接近 90s 港片配乐套路。",
        cost_guard_raises: HardFailure | None = None,
        llm_raises: Exception | None = None,
    ):
        async def fake_load_analysis(analysis_id: str):
            return contract

        async def fake_cost_guard(*, user_id, run_id, predicted_cost_cny):
            if cost_guard_raises is not None:
                raise cost_guard_raises

        async def fake_emit(*args, **kwargs):
            return None

        async def fake_call_ask_llm(prompt: str) -> str:
            if llm_raises is not None:
                raise llm_raises
            return llm_answer

        monkeypatch.setattr(cascade_tools, "load_analysis", fake_load_analysis)
        monkeypatch.setattr(cascade_tools, "cost_guard", fake_cost_guard)
        monkeypatch.setattr(cascade_tools, "emit", fake_emit)
        monkeypatch.setattr(cascade_tools, "_call_ask_llm", fake_call_ask_llm)

    def test_happy_path_returns_answer_and_pushes_ws(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        self._install_fakes(monkeypatch, contract=_fake_contract())

        result = asyncio.run(cascade_ask.ainvoke({
            "analysis_id": "ana_fake",
            "question": "为啥这条 BGM 让我想起 90s 港片",
        }))

        assert "answer" in result
        assert "BGM" in result["answer"]
        assert result["analysis_id"] == "ana_fake"
        assert len(ws.sent) == 1
        frame = ws.sent[0]
        assert frame["type"] == "analysis_answer_returned"
        assert frame["analysis_id"] == "ana_fake"
        assert frame["question"] == "为啥这条 BGM 让我想起 90s 港片"
        assert frame["answer"] == result["answer"]

    def test_unknown_analysis_id_returns_error(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        self._install_fakes(monkeypatch, contract=None)

        result = asyncio.run(cascade_ask.ainvoke({
            "analysis_id": "ana_missing",
            "question": "这条会不会火",
        }))

        assert result["error"] == "ANALYSIS_NOT_FOUND"
        assert "ana_missing" in result["message"]
        assert ws.sent == []

    def test_blank_question_returns_validation_error(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        self._install_fakes(monkeypatch, contract=_fake_contract())

        result = asyncio.run(cascade_ask.ainvoke({
            "analysis_id": "ana_fake",
            "question": "   ",
        }))

        assert result["error"] == "S5_INVALID_PAYLOAD"
        assert ws.sent == []

    def test_cost_guard_blocks_before_llm(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        llm_called = {"hit": False}

        async def fake_load_analysis(_aid):
            return _fake_contract()

        async def fake_cost_guard(*, user_id, run_id, predicted_cost_cny):
            raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "over cap")

        async def fake_call_ask_llm(_prompt):
            llm_called["hit"] = True
            return "should not see this"

        async def fake_emit(*args, **kwargs):
            return None

        monkeypatch.setattr(cascade_tools, "load_analysis", fake_load_analysis)
        monkeypatch.setattr(cascade_tools, "cost_guard", fake_cost_guard)
        monkeypatch.setattr(cascade_tools, "_call_ask_llm", fake_call_ask_llm)
        monkeypatch.setattr(cascade_tools, "emit", fake_emit)

        result = asyncio.run(cascade_ask.ainvoke({
            "analysis_id": "ana_fake",
            "question": "这条 BGM 用了什么乐器",
        }))

        assert result["error"] == "S8_UPSTREAM_REFUSED"
        assert llm_called["hit"] is False
        # W5D3 Bug #2 — HardFailure pushes structured analysis_failed frame
        # (stage="ask") even when cost guard blocks before LLM spend.
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "analysis_failed"
        assert ws.sent[0]["stage"] == "ask"

    def test_llm_failure_maps_s8(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        self._install_fakes(
            monkeypatch,
            contract=_fake_contract(),
            llm_raises=RuntimeError("provider returned 500"),
        )

        result = asyncio.run(cascade_ask.ainvoke({
            "analysis_id": "ana_fake",
            "question": "这条节奏适合做长视频吗",
        }))

        assert result["error"] == "S8_UPSTREAM_REFUSED"
        assert "500" in result["message"]
        assert ws.sent == []

    def test_no_ws_in_ctx_still_returns_answer(self, monkeypatch):
        # ws missing → tool should still return data, no push happens
        set_run_ctx({"user_id": "u1", "thread_id": "", "run_id": "run1"})

        self._install_fakes(monkeypatch, contract=_fake_contract())

        result = asyncio.run(cascade_ask.ainvoke({
            "analysis_id": "ana_fake",
            "question": "这条用户哪些情绪节点最容易流失",
        }))
        assert "answer" in result
        assert result["analysis_id"] == "ana_fake"

    def test_answer_truncated_at_300_chars(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        long_answer = "测" * 1000
        self._install_fakes(monkeypatch, contract=_fake_contract(), llm_answer=long_answer)

        result = asyncio.run(cascade_ask.ainvoke({
            "analysis_id": "ana_fake",
            "question": "这条节奏适合做长视频吗",
        }))
        assert len(result["answer"]) == 300
        # WS frame answer also bounded
        assert len(ws.sent[0]["answer"]) == 300

    def test_question_truncated_in_ws_frame(self, monkeypatch):
        ws = FakeWS()
        set_run_ctx({"user_id": "u1", "thread_id": "t1", "ws": ws, "run_id": "run1"})

        self._install_fakes(monkeypatch, contract=_fake_contract())

        long_q = "为啥" * 300  # 600 chars
        asyncio.run(cascade_ask.ainvoke({"analysis_id": "ana_fake", "question": long_q}))

        # WS push echoes the question but bounded at 200.
        assert len(ws.sent[0]["question"]) == 200
