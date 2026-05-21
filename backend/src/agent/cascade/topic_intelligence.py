"""Cascade Topic Intelligence contract (TIP v0.2).

Per Karpathy review §14.7 of TOPIC_INTELLIGENCE_DEEPENING_PLAN.md:
**build the contracts BEFORE the models**. Each scored signal must declare:
  - source (where it came from)
  - confidence (how sure)
  - fallback usage (was a default substituted?)
  - user_visible (does the UI render it?)
  - used_in_ranking (does opportunity_score consume it?)

This module is a sibling to `contract.py` (which owns the video-analysis
contract `CascadeAnalysisContract`). They reference each other but neither
imports the other's types directly — they are decoupled.

This module ships TYPES ONLY. The scoring rules (TIP §4.2 opportunity_score
formula), data ingestion (TIP §6.5 / §6.6), and `search_trending` integration
(TIP §6.1) are downstream work owned by Codex/Cursor handoffs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


TIP_SCHEMA_VERSION = "tip-0.2"


class SignalSource(str, Enum):
    """Provenance for every datum that flows into a TopicBrief.

    Required by Karpathy §14.7 — every scored field must declare where it came from.
    """

    HOTSPOT_60S = "hotspot_60s"
    NEWRANK = "newrank"
    TOPRADOR_VIDEO_ANALYSIS = "toprador_video_analysis"
    DOUYIN_HOTSPOT_BAO = "douyin_hotspot_bao"            # 抖音热点宝
    DOUYIN_OFFICIAL_HOT_VIDEOS = "douyin_official_hot_videos"
    XHS_CREATOR_CENTER = "xhs_creator_center"            # 小红书创作者中心
    XHS_PUGONGYING = "xhs_pugongying"                    # 蒲公英
    XHS_SPOTLIGHT = "xhs_spotlight"                      # 聚光
    XHS_QIANFAN = "xhs_qianfan"                          # 千帆
    XHS_THIRD_PARTY = "xhs_third_party"
    USER_MANUAL_INPUT = "user_manual_input"
    OCR_SCREENSHOT = "ocr_screenshot"
    LLM_INFERENCE = "llm_inference"
    RULE_DERIVED = "rule_derived"


class TrendStage(str, Enum):
    """Where in the hype cycle this topic sits."""

    RISING = "rising"
    PEAK = "peak"
    DECLINING = "declining"
    UNKNOWN = "unknown"


Platform = Literal["douyin", "xiaohongshu"]


class ScoreSignal(BaseModel):
    """A scored signal with Karpathy's required 5 attributes.

    Used wherever TIP §3 / §4 talk about a numeric score that flows into
    `opportunity_score` or surfaces in the /topics card.
    """

    model_config = ConfigDict(extra="forbid")

    value: float = Field(..., ge=0.0, le=100.0, description="0..100 score")
    source: SignalSource
    confidence: float = Field(..., ge=0.0, le=1.0, description="System confidence in this value")
    explanation: Optional[str] = Field(
        None,
        max_length=120,
        description="Why this score — 人话 string for UI surfacing",
    )
    user_visible: bool = Field(
        ...,
        description="If False, UI must not render. Internal-only signal. Required — forces explicit choice per Karpathy §14.7.",
    )
    used_in_ranking: bool = Field(
        ...,
        description="If False, does not contribute to opportunity_score aggregation. Required — explicit choice.",
    )
    fallback_used: bool = Field(
        ...,
        description="True if value was substituted from a default. Required — mirrors Cascade adapter no-silent-failure rule.",
    )


class RecommendationSignals(BaseModel):
    """Per TIP §3.1 — the 5 recommendation-system signals shown on every card."""

    model_config = ConfigDict(extra="forbid")

    hook_strength: ScoreSignal
    completion_potential: ScoreSignal
    interaction_potential: ScoreSignal
    share_collect_potential: ScoreSignal
    negative_feedback_risk: ScoreSignal


class BusinessSignals(BaseModel):
    """Per TIP §3.1 — the 4 business signals."""

    model_config = ConfigDict(extra="forbid")

    account_fit: ScoreSignal
    commercial_value: ScoreSignal
    saturation_risk: ScoreSignal
    brand_safety_risk: ScoreSignal


PredictionMethod = Literal["rule", "lightgbm", "transformer", "mock"]


class PlatformPrediction(BaseModel):
    """Per-platform opportunity prediction.

    Phase 1 (TIP §4.2): rule-based — `prediction_method="rule"`.
    Phase 4 (TIP §4.3): LightGBM/XGBoost — `prediction_method="lightgbm"`.
    Phase 5 (TIP §4.4): multimodal Transformer — NOT in roadmap as of v0.2.
    `top_*_prob` fields are populated only when method != "rule".
    """

    model_config = ConfigDict(extra="forbid")

    platform: Platform
    opportunity_score: ScoreSignal
    prediction_method: PredictionMethod
    model_version: str = Field(..., min_length=1, max_length=64)
    top_10_prob: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_1_prob: Optional[float] = Field(None, ge=0.0, le=1.0)
    pred_completion_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    pred_interaction_rate: Optional[float] = Field(None, ge=0.0, le=1.0)


class AccountFit(BaseModel):
    """Per TIP §3.4 — how well a topic fits an account profile."""

    model_config = ConfigDict(extra="forbid")

    fit_score: ScoreSignal
    matched_audience: list[str] = Field(default_factory=list, max_length=10)
    historical_best_dna: list[str] = Field(default_factory=list, max_length=10)
    commercial_goal_match: Literal["high", "medium", "low", "unknown"] = "unknown"
    risk_notes: list[str] = Field(default_factory=list, max_length=10)


class ReplicationBlueprint(BaseModel):
    """Per TIP §6.2 — the actionable replication plan derived from viral mechanism."""

    model_config = ConfigDict(extra="forbid")

    required_materials: list[str] = Field(default_factory=list, max_length=20)
    script_formula: str = Field("", max_length=600)
    shot_plan: list[str] = Field(default_factory=list, max_length=20)
    estimated_difficulty: Literal["low", "medium", "high"] = "medium"


class ViralMechanism(BaseModel):
    """Per TIP §3.3 — structured 'why-it-hit' broken down for replication.

    This is the bridge between CascadeAnalysisContract (raw `viral_analysis`)
    and TopicBrief (canvas-entry payload).
    """

    model_config = ConfigDict(extra="forbid")

    hook_type: Optional[str] = Field(None, max_length=80)
    pain_point: Optional[str] = Field(None, max_length=120)
    emotion_tags: list[str] = Field(default_factory=list, max_length=8)
    comment_trigger: Optional[str] = Field(None, max_length=160)
    replication_requirements: list[str] = Field(default_factory=list, max_length=15)
    risk_notes: list[str] = Field(default_factory=list, max_length=10)
    source: SignalSource = SignalSource.LLM_INFERENCE
    confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_from_analysis_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Foreign key into CascadeAnalysisContract.analysis_id (cross-module reference, not enforced)",
    )


class OfficialSignals(BaseModel):
    """Per TIP §1.1 + §6.5 — 抖音热点宝 / 官方热门视频榜 signals.

    Optional — only present when Douyin official ingestion is wired (TIP §8 Phase 2/3).
    """

    model_config = ConfigDict(extra="forbid")

    source: SignalSource
    official_hotspot_score: ScoreSignal
    is_rising: bool = False
    is_low_follower_hit: bool = False
    is_official_activity: bool = False
    related_video_count: Optional[int] = Field(None, ge=0)
    trend_stage: TrendStage = TrendStage.UNKNOWN
    comment_keywords: list[str] = Field(default_factory=list, max_length=20)


class XhsSignals(BaseModel):
    """Per TIP §1.2 + §6.6 — Xiaohongshu seed-value signals.

    Optional — present only when XHS ingestion is wired (TIP §8 Phase 2/3).
    Note: XHS scoring is distinct from Douyin completion/burst logic.
    """

    model_config = ConfigDict(extra="forbid")

    source: SignalSource
    xhs_seed_score: ScoreSignal
    search_trend_score: ScoreSignal
    collect_rate_score: ScoreSignal
    comment_quality_score: ScoreSignal
    long_tail_growth_score: ScoreSignal
    commercial_conversion_score: ScoreSignal
    note_format: Optional[str] = Field(None, max_length=40, description="攻略清单/教程/测评/etc.")
    recommended_cover_style: Optional[str] = Field(None, max_length=80)


class DeepTopicIntelligence(BaseModel):
    """Per TIP §6.1 — the deep-intelligence block appended to /topics cards.

    Composed via `search_trending` returning this alongside existing topic data.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["tip-0.2"] = TIP_SCHEMA_VERSION
    opportunity_score: ScoreSignal
    recommendation_signals: RecommendationSignals
    business_signals: BusinessSignals
    prediction: PlatformPrediction
    official_signals: Optional[OfficialSignals] = None
    xhs_signals: Optional[XhsSignals] = None
    explain: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="≤3 plain-language one-liners for the card",
    )


class TopicBrief(BaseModel):
    """Per TIP §7.3 — the canvas-entry artifact.

    When a user clicks 'enter canvas' from a /topics card, the canvas receives
    a TopicBrief (not just a topic string). This is the contract that lets the
    canvas know: what to make, why, for whom, with what materials, and what risks.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["tip-0.2"] = TIP_SCHEMA_VERSION
    topic: str = Field(..., min_length=1, max_length=200)
    why_now: list[str] = Field(default_factory=list, max_length=5)
    target_audience: list[str] = Field(default_factory=list, max_length=8)
    viral_mechanism: ViralMechanism
    replication_blueprint: ReplicationBlueprint
    account_fit: Optional[AccountFit] = None
    constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Free-form constraint dictionary; e.g. duration, risk_notes, brand_safety",
    )
    deep_intelligence: DeepTopicIntelligence
    created_at: datetime
    # Cross-module reference. Not a foreign key in the SQL sense.
    derived_from_analysis_id: Optional[str] = Field(
        None,
        max_length=64,
        description="The CascadeAnalysisContract.analysis_id this TopicBrief was derived from, if any.",
    )


class PerformanceSnapshot(BaseModel):
    """Per TIP §5.3 — manual or OCR-imported in TIP Phase 3.

    The data structure that closes the learning loop. Without these, no model
    in TIP Phase 4 can be trained. Per Ilya §14.6: the data structure matters
    more than the model.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["tip-0.2"] = TIP_SCHEMA_VERSION
    platform: Platform
    opus_id: str = Field(..., min_length=1, max_length=64)
    account_id: Optional[str] = Field(None, max_length=64)
    minutes_after_publish: int = Field(..., ge=0)
    captured_at: datetime
    source: SignalSource
    # Counts — all optional because creator-center exports may omit any subset.
    views: Optional[int] = Field(None, ge=0)
    likes: Optional[int] = Field(None, ge=0)
    comments: Optional[int] = Field(None, ge=0)
    shares: Optional[int] = Field(None, ge=0)
    collects: Optional[int] = Field(None, ge=0)
    followers_gain: Optional[int] = Field(None, ge=0)
    completion_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    avg_watch_time_sec: Optional[float] = Field(None, ge=0.0)
    replay_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    negative_feedback_rate: Optional[float] = Field(None, ge=0.0, le=1.0)


__all__ = [
    "TIP_SCHEMA_VERSION",
    "SignalSource",
    "TrendStage",
    "Platform",
    "ScoreSignal",
    "RecommendationSignals",
    "BusinessSignals",
    "PredictionMethod",
    "PlatformPrediction",
    "AccountFit",
    "ReplicationBlueprint",
    "ViralMechanism",
    "OfficialSignals",
    "XhsSignals",
    "DeepTopicIntelligence",
    "TopicBrief",
    "PerformanceSnapshot",
]
