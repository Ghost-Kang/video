"""Cascade Phase 0/1 contract module.

This package owns the upstream-analysis contract that Cascade enforces.
Karpathy review consensus: stabilize the contract first; the adapter
normalizes any conforming-or-near-conforming upstream into this shape.

See docs/TOPRADOR_SCHEMA.md for the canonical specification.
"""

from agent.cascade.contract import (
    SCHEMA_VERSION,
    CascadeAnalysisContract,
    Scene,
    ViralAnalysis,
    Warning_,
    Severity,
    Platform,
    ShotType,
    CameraMovement,
)
from agent.cascade.failures import (
    ACTION_LABELS,
    FailureCode,
    HTTP_STATUS,
    HardFailure,
    RecoveryAction,
    RECOVERY_ACTIONS,
    RECOVERY_HINTS,
    WarningCode,
)

__all__ = [
    "SCHEMA_VERSION",
    "CascadeAnalysisContract",
    "Scene",
    "ViralAnalysis",
    "Warning_",
    "Severity",
    "Platform",
    "ShotType",
    "CameraMovement",
    "FailureCode",
    "WarningCode",
    "HardFailure",
    "RecoveryAction",
    "ACTION_LABELS",
    "HTTP_STATUS",
    "RECOVERY_ACTIONS",
    "RECOVERY_HINTS",
]
