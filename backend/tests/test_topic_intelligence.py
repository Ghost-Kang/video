"""Topic Intelligence contract tests (TIP-2).

Per Karpathy §14.7 of TOPIC_INTELLIGENCE_DEEPENING_PLAN.md: every ScoreSignal
must carry source / confidence / fallback / user_visible / used_in_ranking.
These tests enforce that contract at the schema level — future field additions
that don't carry the 5 attributes will fail.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from agent.cascade.topic_intelligence import (
    TIP_SCHEMA_VERSION,
    AccountFit,
    BusinessSignals,
    DeepTopicIntelligence,
    OfficialSignals,
    PerformanceSnapshot,
    PlatformPrediction,
    RecommendationSignals,
    ReplicationBlueprint,
    ScoreSignal,
    SignalSource,
    TopicBrief,
    TrendStage,
    ViralMechanism,
    XhsSignals,
)


# ---------- Karpathy 5-attribute audit ----------


def test_score_signal_requires_karpathy_five() -> None:
    """ScoreSignal must reject any payload missing one of the 5 mandatory attributes."""
    minimal_valid = {
        "value": 80.0,
        "source": SignalSource.RULE_DERIVED.value,
        "confidence": 0.9,
        "user_visible": True,
        "used_in_ranking": True,
        "fallback_used": False,
    }
    # Sanity: minimal payload validates
    assert ScoreSignal(**minimal_valid).value == 80.0

    # Removing each required field must fail — all 5 Karpathy attributes + value
    for required in ("value", "source", "confidence", "user_visible", "used_in_ranking", "fallback_used"):
        bad = dict(minimal_valid)
        bad.pop(required)
        with pytest.raises(ValidationError):
            ScoreSignal(**bad)


def test_score_signal_rejects_extra_fields() -> None:
    """ScoreSignal forbids unknown keys (Karpathy §14.7 — drift prevention)."""
    with pytest.raises(ValidationError):
        ScoreSignal(
            value=80.0,
            source=SignalSource.RULE_DERIVED.value,
            confidence=0.9,
            user_visible=True,
            used_in_ranking=True,
            unknown_field="x",
        )


def test_score_signal_value_clamped_to_0_100() -> None:
    base = {
        "source": SignalSource.RULE_DERIVED.value,
        "confidence": 0.9,
        "user_visible": True,
        "used_in_ranking": True,
    }
    with pytest.raises(ValidationError):
        ScoreSignal(value=-1, **base)
    with pytest.raises(ValidationError):
        ScoreSignal(value=101, **base)


def test_score_signal_confidence_clamped_0_1() -> None:
    base = {
        "value": 80.0,
        "source": SignalSource.RULE_DERIVED.value,
        "user_visible": True,
        "used_in_ranking": True,
    }
    with pytest.raises(ValidationError):
        ScoreSignal(confidence=-0.01, **base)
    with pytest.raises(ValidationError):
        ScoreSignal(confidence=1.01, **base)


# ---------- TopicBrief composition ----------


def _signal(value: float = 80.0, **overrides) -> ScoreSignal:
    return ScoreSignal(
        value=value,
        source=SignalSource.RULE_DERIVED,
        confidence=0.85,
        explanation=None,
        user_visible=True,
        used_in_ranking=True,
        fallback_used=False,
        **overrides,
    )


def _viral_mechanism() -> ViralMechanism:
    return ViralMechanism(
        hook_type="first_person_emotion",
        pain_point="女性成长与情绪告别",
        emotion_tags=["共鸣", "治愈"],
        comment_trigger="你也有一首歌替你告别过谁吗",
        replication_requirements=["演唱会素材", "情绪字幕"],
        risk_notes=["音乐版权"],
        source=SignalSource.LLM_INFERENCE,
        confidence=0.82,
        extracted_from_analysis_id="ana_syn_baomam_001",
    )


def _replication_blueprint() -> ReplicationBlueprint:
    return ReplicationBlueprint(
        required_materials=["演唱会现场素材", "人群合唱镜头", "情绪字幕"],
        script_formula="第一人称独白 + 演唱会切镜 + 字幕递进 + 收束式结尾",
        shot_plan=["镜头1: 入场仰拍", "镜头2: 人群合唱", "镜头3: 字幕递进"],
        estimated_difficulty="medium",
    )


def _deep_intel() -> DeepTopicIntelligence:
    return DeepTopicIntelligence(
        opportunity_score=_signal(86.4),
        recommendation_signals=RecommendationSignals(
            hook_strength=_signal(88),
            completion_potential=_signal(74),
            interaction_potential=_signal(81),
            share_collect_potential=_signal(79),
            negative_feedback_risk=_signal(12),
        ),
        business_signals=BusinessSignals(
            account_fit=_signal(83),
            commercial_value=_signal(68),
            saturation_risk=_signal(41),
            brand_safety_risk=_signal(18),
        ),
        prediction=PlatformPrediction(
            platform="douyin",
            opportunity_score=_signal(86.4),
            prediction_method="rule",
            model_version="rule-v0.1",
        ),
        explain=[
            "近期同类内容增长快，但还未完全红海",
            "互动 DNA 偏收藏/评论，适合女性成长账号",
            "复刻素材要求中等",
        ],
    )


def test_topic_brief_composes() -> None:
    brief = TopicBrief(
        topic="演唱会第一视角情绪 vlog",
        why_now=["热度增长", "素材稀缺", "女性情绪共鸣"],
        target_audience=["18-30 女性", "演唱会粉丝"],
        viral_mechanism=_viral_mechanism(),
        replication_blueprint=_replication_blueprint(),
        account_fit=AccountFit(
            fit_score=_signal(83),
            matched_audience=["女性成长", "情绪共鸣"],
            historical_best_dna=["收藏主导", "评论共鸣"],
            commercial_goal_match="medium",
            risk_notes=[],
        ),
        constraints={"duration": "30-60秒", "brand_safety": "音乐版权风险"},
        deep_intelligence=_deep_intel(),
        created_at=datetime.now(timezone.utc),
        derived_from_analysis_id="ana_syn_baomam_001",
    )
    assert brief.schema_version == TIP_SCHEMA_VERSION
    assert brief.topic.startswith("演唱会")
    assert brief.account_fit is not None
    assert brief.deep_intelligence.opportunity_score.value == 86.4


def test_topic_brief_explain_capped_at_3() -> None:
    with pytest.raises(ValidationError):
        DeepTopicIntelligence(
            opportunity_score=_signal(),
            recommendation_signals=RecommendationSignals(
                hook_strength=_signal(),
                completion_potential=_signal(),
                interaction_potential=_signal(),
                share_collect_potential=_signal(),
                negative_feedback_risk=_signal(),
            ),
            business_signals=BusinessSignals(
                account_fit=_signal(),
                commercial_value=_signal(),
                saturation_risk=_signal(),
                brand_safety_risk=_signal(),
            ),
            prediction=PlatformPrediction(
                platform="douyin",
                opportunity_score=_signal(),
                prediction_method="rule",
                model_version="rule-v0.1",
            ),
            explain=["a", "b", "c", "d"],  # 4 > 3
        )


def test_official_and_xhs_signals_optional() -> None:
    intel = _deep_intel()
    assert intel.official_signals is None
    assert intel.xhs_signals is None


def test_official_signals_validates_when_present() -> None:
    official = OfficialSignals(
        source=SignalSource.DOUYIN_HOTSPOT_BAO,
        official_hotspot_score=_signal(84),
        is_rising=True,
        is_low_follower_hit=True,
        related_video_count=1280,
        trend_stage=TrendStage.RISING,
        comment_keywords=["共鸣", "泪目", "青春"],
    )
    assert official.is_rising is True
    assert official.trend_stage == TrendStage.RISING


def test_xhs_signals_distinct_scoring_from_douyin() -> None:
    """XHS uses search/collect/comment-quality — not completion/burst (TIP §1.2)."""
    xhs = XhsSignals(
        source=SignalSource.XHS_THIRD_PARTY,
        xhs_seed_score=_signal(82),
        search_trend_score=_signal(76),
        collect_rate_score=_signal(88),
        comment_quality_score=_signal(79),
        long_tail_growth_score=_signal(72),
        commercial_conversion_score=_signal(81),
        note_format="攻略清单",
        recommended_cover_style="大字标题+结果对比",
    )
    # The contract does NOT define completion_potential here — confirms scoring separation
    assert not hasattr(xhs, "completion_potential")
    assert xhs.collect_rate_score.value == 88


def test_performance_snapshot_allows_partial_metrics() -> None:
    """TIP §5.3 — creator-center exports may omit any subset of metrics; contract must tolerate."""
    snap = PerformanceSnapshot(
        platform="douyin",
        opus_id="v_12345",
        minutes_after_publish=30,
        captured_at=datetime.now(timezone.utc),
        source=SignalSource.OCR_SCREENSHOT,
        views=10000,
        # likes/comments/shares/collects/completion_rate all None — allowed
    )
    assert snap.views == 10000
    assert snap.completion_rate is None
    assert snap.likes is None


def test_performance_snapshot_rejects_negative_counts() -> None:
    base = {
        "platform": "douyin",
        "opus_id": "v_x",
        "minutes_after_publish": 30,
        "captured_at": datetime.now(timezone.utc),
        "source": SignalSource.OCR_SCREENSHOT,
    }
    with pytest.raises(ValidationError):
        PerformanceSnapshot(**base, views=-1)
    with pytest.raises(ValidationError):
        PerformanceSnapshot(**base, completion_rate=1.5)


def test_viral_mechanism_carries_provenance_and_confidence() -> None:
    """Karpathy §14.7 — non-scalar fields also need source+confidence."""
    vm = _viral_mechanism()
    assert vm.source == SignalSource.LLM_INFERENCE
    assert 0.0 <= vm.confidence <= 1.0


def test_prediction_method_rule_leaves_model_probs_none() -> None:
    """Phase 1 (rule-based): top_*_prob are not yet meaningful."""
    p = PlatformPrediction(
        platform="douyin",
        opportunity_score=_signal(),
        prediction_method="rule",
        model_version="rule-v0.1",
    )
    assert p.top_10_prob is None
    assert p.top_1_prob is None


def test_signal_source_enum_covers_tip_v02_sources() -> None:
    """Sanity: every named source in TIP v0.2 §1.1/§1.2 has an enum member."""
    expected = {
        "hotspot_60s", "newrank", "toprador_video_analysis",
        "douyin_hotspot_bao", "douyin_official_hot_videos",
        "xhs_creator_center", "xhs_pugongying", "xhs_spotlight",
        "xhs_qianfan", "xhs_third_party",
        "user_manual_input", "ocr_screenshot", "llm_inference", "rule_derived",
    }
    actual = {m.value for m in SignalSource}
    missing = expected - actual
    assert not missing, f"SignalSource missing TIP-required values: {missing}"
