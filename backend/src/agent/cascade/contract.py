"""Cascade analysis contract (P0-3).

Pydantic types that mirror docs/TOPRADOR_SCHEMA.md §1-§3.
The TypeScript mirror is in frontend/src/types/cascade.ts — keep in sync.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


SCHEMA_VERSION = "1.0"

# Cache-invalidation revision for the *analysis pipeline* (prompt + dimension
# set), distinct from the wire-format SCHEMA_VERSION above. Bump this whenever a
# prompt/dimension change makes previously-cached analyses stale, so the
# permanent analysis cache (analyses table, no TTL) stops serving pre-change
# results that would render with missing dimensions. Stored analyses carry
# their revision in CascadeAnalysisContract.pipeline_revision; a missing/older
# value is treated as a cache miss and regenerated (analysis_service).
#   1 → pre-toprador (legacy dims: pacing/climax/visual_style/emotional_arc/…)
#   2 → toprador-aligned (10 viral dims + 14 scene dims)
ANALYSIS_PIPELINE_REVISION = 2


class Platform(str, Enum):
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"
    OTHER = "other"


class ShotType(str, Enum):
    CLOSE_UP = "close_up"
    MEDIUM = "medium"
    WIDE = "wide"
    AERIAL = "aerial"
    POV = "pov"
    UNKNOWN = "unknown"


class CameraMovement(str, Enum):
    STATIC = "static"
    PUSH = "push"
    PULL = "pull"
    PAN = "pan"
    TILT = "tilt"
    TRACKING = "tracking"
    HANDHELD = "handheld"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class Warning_(BaseModel):
    """A non-fatal observation about the analysis. Codes are stable; UI maps them to plain Chinese."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Stable warning code, e.g. W2_FALLBACK_USED. See failures.py.")
    field: str = Field(..., description="Dotted JSON path of the field this warning is about.")
    message: str = Field(..., max_length=400)
    severity: Severity = Severity.WARN


class AudioDim(BaseModel):
    """Audio 3-axis breakdown (W4D5 addition).

    Required on every analysis. Adapter supplies sensible fallbacks + a
    W_AUDIO_FALLBACK warning when upstream omits the block, so old
    fixtures and degraded LLM calls still parse.
    """

    model_config = ConfigDict(extra="forbid")

    bgm: str = Field(..., max_length=80)               # 节奏/风格/情绪基调
    voice_pace: str = Field(..., max_length=80)        # 语速/口播 vs 字幕/腔调
    sound_effects: str = Field(..., max_length=80)     # 转场音/强调音/原声


class ProductionDim(BaseModel):
    """Production complexity breakdown (W4D5 addition).

    Tells the creator how much effort the source video takes to replicate
    and what concrete elements they can swap in. Required; adapter falls
    back when upstream omits it.
    """

    model_config = ConfigDict(extra="forbid")

    cost_tier: Literal["solo_phone", "small_team", "post_heavy"] = "solo_phone"
    estimated_hours: float = Field(..., ge=0.0, le=100.0)
    replaceable_anchors: list[str] = Field(default_factory=list, max_length=10)


class ViralAnalysis(BaseModel):
    """The 'why-it-hit' block — toprador-aligned 爆点分析 (10 dimensions).

    2026-05-30: re-aligned to toprador's creator-facing dimension set (summary /
    theme / target_audience / material_benefit / hook / main_elements /
    micro_innovation / pain_points / emotion_trigger / bgm_style). The old
    film-analysis fields (pacing/climax/visual_style/emotional_arc/
    engagement_levers/replicable_formula) + audio/production are kept OPTIONAL
    for backward-compat with the suspended 改写 path and old fixtures; they are
    no longer produced by the prompt nor rendered.
    """

    model_config = ConfigDict(extra="forbid")

    # ── toprador 爆点 10 维(分析渲染用)─────────────────────────────
    summary: str = Field("", max_length=400)            # 爆点总结
    theme: str = Field("", max_length=120)              # 主题类型
    target_audience: str = Field("", max_length=200)    # 目标人群
    material_benefit: str = Field("", max_length=300)   # 素材利益点
    hook: str = Field("", max_length=300)               # 钩子(干净人话,无 H 码)
    main_elements: str = Field("", max_length=300)      # 主要视频元素
    micro_innovation: str = Field("", max_length=400)   # 微创新方向
    pain_points: str = Field("", max_length=300)        # 痛点需求
    emotion_trigger: str = Field("", max_length=200)    # 情绪触发
    bgm_style: str = Field("", max_length=200)          # BGM 风格

    # ── 遗留字段(改写暂挂期保留,不产出/不渲染)──────────────────────
    pacing: str = Field("", max_length=200)
    climax: str = Field("", max_length=200)
    visual_style: str = Field("", max_length=200)
    emotional_arc: str = Field("", max_length=200)
    engagement_levers: str = Field("", max_length=200)
    replicable_formula: str = Field("", max_length=200)
    audio: Optional[AudioDim] = None
    production: Optional[ProductionDim] = None


class Scene(BaseModel):
    """One shot in the source video — toprador-aligned 视频分析 dimensions.

    Numeric timeline (scene_index + timestamp_start/end) is kept (better than
    toprador's "MM:SS - MM:SS" string for clipping/sorting). Descriptive
    dimensions mirror toprador's per-shot fields and render as the 视频分析 grid.
    """

    model_config = ConfigDict(extra="forbid")

    scene_index: int = Field(..., ge=1)
    timestamp_start: float = Field(..., ge=0.0)
    timestamp_end: float = Field(..., gt=0.0)
    # 分镜标题/说明
    theme: str = Field("", max_length=120)                 # 分镜主题/标题
    segment_note: str = Field("", max_length=300)          # 分段说明(作用/位置)
    segment_description: str = Field("", max_length=600)   # 分段描述(发生了什么)
    dialogue_and_narration: str = Field(..., max_length=2000)  # 片段和口播,可空
    emotion: str = Field("", max_length=80)                # 情感基调
    # 视觉/听觉
    visual_summary: str = Field("", max_length=120)        # 视觉内容概括(一句话)
    visual_content: str = Field(..., min_length=1, max_length=800)  # 视觉内容(详细)
    audio_summary: str = Field("", max_length=120)         # 听觉内容概括
    audio_content: str = Field("", max_length=600)         # 听觉内容(详细)
    # 美术/拍摄网格
    cinematography: str = Field("", max_length=200)        # 摄影(运镜/手法)
    camera_position: str = Field("", max_length=120)       # 机位(景别)
    actors: str = Field("", max_length=200)                # 演员
    on_screen_text: str = Field("", max_length=400)        # 画面文字
    visual_presentation_style: str = Field("", max_length=120)  # 画面表现形式
    scene: str = Field("", max_length=300)                 # 场景/环境/布置
    props_list: str = Field("", max_length=300)            # 道具清单
    costume: str = Field("", max_length=300)               # 服装造型
    lighting_and_color: str = Field("", max_length=300)    # 光影与色彩要求
    # 遗留(可选,不渲染)
    subject: Optional[str] = Field(None, max_length=80)
    shot_type: ShotType = ShotType.MEDIUM
    camera_movement: CameraMovement = CameraMovement.STATIC
    first_frame_url: Optional[HttpUrl] = None
    warnings: list[Warning_] = Field(default_factory=list)

    @field_validator("timestamp_end")
    @classmethod
    def _end_after_start(cls, v: float, info) -> float:
        start = info.data.get("timestamp_start")
        if start is not None and v <= start:
            raise ValueError(f"timestamp_end ({v}) must be > timestamp_start ({start})")
        return v


class CascadeAnalysisContract(BaseModel):
    """The shape Cascade demands from any upstream video analyzer.

    Anything that does not validate against this contract is rejected
    by the adapter (see adapter.py), with the exact failure code from failures.py.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., pattern=r"^1\.[0-9]+$", description="Only 1.x accepted.")
    # Cache-invalidation marker — see ANALYSIS_PIPELINE_REVISION. Optional so
    # analyses persisted before this field existed parse as None (→ stale →
    # regenerated). Stamped by analysis_service before persistence; upstreams
    # and fixtures don't set it.
    pipeline_revision: Optional[int] = Field(default=None)
    analysis_id: str = Field(..., min_length=1, max_length=64)
    source_url: HttpUrl
    platform: Platform
    created_at: datetime
    model: str = Field(..., min_length=1, max_length=120)
    cost_cny: float = Field(..., ge=0.0)
    duration_s: int = Field(..., ge=1, le=600)
    # toprador-aligned: 一句话「这是什么视频」总览,渲染在爆点分析最上方做定位锚。
    video_summary: str = Field("", max_length=600)
    viral_analysis: ViralAnalysis
    scenes: list[Scene] = Field(..., min_length=3, max_length=12)
    # W4D5: full逐字脚本 (MediaKit transcribe). Optional — may be empty when
    # transcribe failed or wasn't called. Capped to keep WS frames sane.
    full_transcript: str = Field("", max_length=20000)
    warnings: list[Warning_] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("scenes")
    @classmethod
    def _scene_indices_sequential(cls, v: list[Scene]) -> list[Scene]:
        for i, s in enumerate(v, start=1):
            if s.scene_index != i:
                raise ValueError(
                    f"scenes[{i - 1}].scene_index = {s.scene_index}; expected {i} (1-based, contiguous)"
                )
        return v

    @field_validator("scenes")
    @classmethod
    def _timestamps_monotonic(cls, v: list[Scene]) -> list[Scene]:
        prev_end = 0.0
        for i, s in enumerate(v):
            if s.timestamp_start < prev_end:
                raise ValueError(
                    f"scenes[{i}].timestamp_start ({s.timestamp_start}) < previous timestamp_end ({prev_end}); "
                    "adapter must sort before validation"
                )
            prev_end = s.timestamp_end
        return v
