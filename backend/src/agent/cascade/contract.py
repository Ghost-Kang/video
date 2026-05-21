"""Cascade analysis contract (P0-3).

Pydantic types that mirror docs/TOPRADOR_SCHEMA.md §1-§3.
The TypeScript mirror is in frontend/src/types/cascade.ts — keep in sync.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


SCHEMA_VERSION = "1.0"


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


class ViralAnalysis(BaseModel):
    """The 'why-it-hit' block. All 8 dimensions required; replicable_formula is HARD."""

    model_config = ConfigDict(extra="forbid")

    hook: str = Field(..., max_length=80)
    pacing: str = Field(..., max_length=80)
    climax: str = Field(..., max_length=80)
    visual_style: str = Field(..., max_length=80)
    emotional_arc: str = Field(..., max_length=80)
    target_audience: str = Field(..., max_length=80)
    engagement_levers: str = Field(..., max_length=80)
    replicable_formula: str = Field(..., min_length=1, max_length=120)

    @field_validator("replicable_formula")
    @classmethod
    def _formula_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("replicable_formula is HARD-required and must not be blank")
        return v


class Scene(BaseModel):
    """One shot in the source video."""

    model_config = ConfigDict(extra="forbid")

    scene_index: int = Field(..., ge=1)
    timestamp_start: float = Field(..., ge=0.0)
    timestamp_end: float = Field(..., gt=0.0)
    scene: str = Field(..., min_length=1, max_length=120)
    dialogue_and_narration: str = Field(..., max_length=2000)  # may be empty
    visual_content: str = Field(..., min_length=1, max_length=200)
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
    analysis_id: str = Field(..., min_length=1, max_length=64)
    source_url: HttpUrl
    platform: Platform
    created_at: datetime
    model: str = Field(..., min_length=1, max_length=120)
    cost_cny: float = Field(..., ge=0.0)
    duration_s: int = Field(..., ge=1, le=600)
    viral_analysis: ViralAnalysis
    scenes: list[Scene] = Field(..., min_length=3, max_length=12)
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
