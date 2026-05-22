"""Cascade failure taxonomy (P0-6).

Every failure mode in upstream analysis is enumerated here with a stable code
and a UI-facing recovery hint. Karpathy review rule: 100% of failures must have
a known next step for the user.

S-codes are HARD failures (adapter raises HardFailure).
W-codes are warnings (adapter records, does not raise; UI surfaces).
"""

from __future__ import annotations

import uuid
from enum import Enum


class FailureCode(str, Enum):
    """Hard failures — adapter raises HardFailure with one of these codes.

    Each failure must have a UI banner that tells the user what to do next.
    """

    S1_NO_SOURCE_URL = "S1_NO_SOURCE_URL"
    S2_VERSION_MISMATCH = "S2_VERSION_MISMATCH"
    S3_NO_FORMULA = "S3_NO_FORMULA"
    S4_SCENES_LEN_OUT_OF_RANGE = "S4_SCENES_LEN_OUT_OF_RANGE"
    S5_INVALID_PAYLOAD = "S5_INVALID_PAYLOAD"  # JSON parse failure / wrong types
    S6_NEGATIVE_COST = "S6_NEGATIVE_COST"
    S7_UPSTREAM_TIMEOUT = "S7_UPSTREAM_TIMEOUT"
    S8_UPSTREAM_REFUSED = "S8_UPSTREAM_REFUSED"  # rate limit, auth, etc.


class RecoveryAction(str, Enum):
    """Stable identifiers for UI recovery buttons. Frontend resolves these to localized labels."""

    RETRY_SAME_URL = "RETRY_SAME_URL"
    RETRY_SAME_URL_AFTER_30S = "RETRY_SAME_URL_AFTER_30S"
    RETRY_SAME_URL_AFTER_60S = "RETRY_SAME_URL_AFTER_60S"
    RETRY_WITH_NEW_URL = "RETRY_WITH_NEW_URL"
    PICK_FROM_FEATURED = "PICK_FROM_FEATURED"
    RELOAD = "RELOAD"
    REPORT = "REPORT"


# UI-facing labels for recovery actions. Brand Guardian §4 rule: no English jargon for users.
ACTION_LABELS: dict[str, str] = {
    RecoveryAction.RETRY_SAME_URL.value: "再试一次",
    RecoveryAction.RETRY_SAME_URL_AFTER_30S.value: "30 秒后重试",
    RecoveryAction.RETRY_SAME_URL_AFTER_60S.value: "1 分钟后重试",
    RecoveryAction.RETRY_WITH_NEW_URL.value: "换一条爆款链接",
    RecoveryAction.PICK_FROM_FEATURED.value: "从今日精选挑一条",
    RecoveryAction.RELOAD.value: "刷新页面",
    RecoveryAction.REPORT.value: "告诉我们这条",
}


class WarningCode(str, Enum):
    """Soft warnings — adapter records, UI may surface."""

    W1_AUTO_ID = "W1_AUTO_ID"
    W2_FALLBACK_USED = "W2_FALLBACK_USED"
    W3_SCENES_TRUNCATED = "W3_SCENES_TRUNCATED"
    W4_GENERIC_SCENE_LABEL = "W4_GENERIC_SCENE_LABEL"
    W5_TIMESTAMPS_SORTED = "W5_TIMESTAMPS_SORTED"
    W6_FIRST_FRAME_UNREACHABLE = "W6_FIRST_FRAME_UNREACHABLE"
    W7_CONFIDENCE_COMPUTED = "W7_CONFIDENCE_COMPUTED"
    W8_COST_UNKNOWN = "W8_COST_UNKNOWN"
    W9_CROSS_BORDER_SOURCE = "W9_CROSS_BORDER_SOURCE"
    W10_AUTHOR_PII_STRIPPED = "W10_AUTHOR_PII_STRIPPED"  # silent; included for audit
    W11_CONFIDENCE_CLAMPED = "W11_CONFIDENCE_CLAMPED"
    W12_TIMESTAMP_CLAMPED = "W12_TIMESTAMP_CLAMPED"
    W13_PLATFORM_URL_MISMATCH = "W13_PLATFORM_URL_MISMATCH"


# UI-facing 人话 recovery hints. Brand Guardian §4 rule: no English jargon, no
# field names. The user sees these; engineers see the codes.
RECOVERY_HINTS: dict[str, str] = {
    # HARD failures — banner + 3-option recovery (per Karpathy)
    FailureCode.S1_NO_SOURCE_URL.value: (
        "这条链接系统读不到。换一条爆款链接试试，或者从下面今日精选里挑一条。"
    ),
    FailureCode.S2_VERSION_MISMATCH.value: (
        "系统升级了一下底层格式。点这里刷新一次就好。"
    ),
    FailureCode.S3_NO_FORMULA.value: (
        "这条视频没看出能复刻的套路（可能太特殊或太短）。换一条更有规律的爆款。"
    ),
    FailureCode.S4_SCENES_LEN_OUT_OF_RANGE.value: (
        "这条视频镜头太少（3 个以下）或太多（超过 12 个），系统暂时处理不了。"
        "选一条 15-60 秒、节奏正常的视频再试。"
    ),
    FailureCode.S5_INVALID_PAYLOAD.value: (
        "系统读这条视频时遇到了奇怪的数据。换一条试试，或者点反馈告诉我们这条的链接。"
    ),
    FailureCode.S6_NEGATIVE_COST.value: (
        "系统内部统计出了点小问题。直接重试一次就行。"
    ),
    FailureCode.S7_UPSTREAM_TIMEOUT.value: (
        "分析超时了。可能视频太长，也可能服务繁忙。等 30 秒重试，或者换一条更短的。"
    ),
    FailureCode.S8_UPSTREAM_REFUSED.value: (
        "系统暂时繁忙。1 分钟后重试，或者从今日精选里挑一条（这些是已经分析好的）。"
    ),

    # Soft warnings — inline labels on the card, not banners
    WarningCode.W1_AUTO_ID.value: "（系统已自动编号）",
    WarningCode.W2_FALLBACK_USED.value: "这部分系统没完全看懂，用了通用判断，可能不太准。",
    WarningCode.W3_SCENES_TRUNCATED.value: "这条视频镜头较多，系统只取了前 12 个。",
    WarningCode.W4_GENERIC_SCENE_LABEL.value: "这一段画面描述较弱，你可能想自己改一下。",
    WarningCode.W5_TIMESTAMPS_SORTED.value: "（系统帮你把镜头顺序对齐了）",
    WarningCode.W6_FIRST_FRAME_UNREACHABLE.value: "原视频的画面读不到了，但文字分析还在。",
    WarningCode.W7_CONFIDENCE_COMPUTED.value: "（系统对这条分析的把握一般，仅供参考）",
    WarningCode.W8_COST_UNKNOWN.value: "（这条的成本统计暂时缺失，不影响使用）",
    WarningCode.W9_CROSS_BORDER_SOURCE.value: "（这是境外平台的视频，分析结果仅供参考）",
    WarningCode.W10_AUTHOR_PII_STRIPPED.value: "",  # silent; never shown
    WarningCode.W11_CONFIDENCE_CLAMPED.value: "（系统对置信度做了取整，不影响使用）",
    WarningCode.W12_TIMESTAMP_CLAMPED.value: "（系统把镜头时间对齐到了视频时长内）",
    WarningCode.W13_PLATFORM_URL_MISMATCH.value: "（系统按链接修正了平台类型）",
}


# Recovery actions: each HARD failure offers up to 3 user actions in the UI.
# The frontend reads this map by failure code and renders the corresponding labelled buttons.
RECOVERY_ACTIONS: dict[str, list[str]] = {
    FailureCode.S1_NO_SOURCE_URL.value: [
        RecoveryAction.RETRY_WITH_NEW_URL.value,
        RecoveryAction.PICK_FROM_FEATURED.value,
        RecoveryAction.REPORT.value,
    ],
    FailureCode.S2_VERSION_MISMATCH.value: [
        RecoveryAction.RELOAD.value,
        RecoveryAction.REPORT.value,
    ],
    FailureCode.S3_NO_FORMULA.value: [
        RecoveryAction.RETRY_WITH_NEW_URL.value,
        RecoveryAction.PICK_FROM_FEATURED.value,
        RecoveryAction.REPORT.value,
    ],
    FailureCode.S4_SCENES_LEN_OUT_OF_RANGE.value: [
        RecoveryAction.RETRY_WITH_NEW_URL.value,
        RecoveryAction.PICK_FROM_FEATURED.value,
        RecoveryAction.REPORT.value,
    ],
    FailureCode.S5_INVALID_PAYLOAD.value: [
        RecoveryAction.RETRY_SAME_URL.value,
        RecoveryAction.RETRY_WITH_NEW_URL.value,
        RecoveryAction.REPORT.value,
    ],
    FailureCode.S6_NEGATIVE_COST.value: [
        RecoveryAction.RETRY_SAME_URL.value,
        RecoveryAction.REPORT.value,
    ],
    FailureCode.S7_UPSTREAM_TIMEOUT.value: [
        RecoveryAction.RETRY_SAME_URL_AFTER_30S.value,
        RecoveryAction.RETRY_WITH_NEW_URL.value,
        RecoveryAction.REPORT.value,
    ],
    FailureCode.S8_UPSTREAM_REFUSED.value: [
        RecoveryAction.RETRY_SAME_URL_AFTER_60S.value,
        RecoveryAction.PICK_FROM_FEATURED.value,
        RecoveryAction.REPORT.value,
    ],
}


# HTTP status routing — required by Stage 4 API audit (no silent invention by Codex).
# User-input errors → 4xx; internal accounting bugs → 500; upstream availability → 5xx.
HTTP_STATUS: dict[str, int] = {
    FailureCode.S1_NO_SOURCE_URL.value: 400,        # malformed request
    FailureCode.S2_VERSION_MISMATCH.value: 422,     # semantic mismatch
    FailureCode.S3_NO_FORMULA.value: 422,           # semantic — content didn't yield formula
    FailureCode.S4_SCENES_LEN_OUT_OF_RANGE.value: 422,
    FailureCode.S5_INVALID_PAYLOAD.value: 422,
    FailureCode.S6_NEGATIVE_COST.value: 500,        # adapter-internal bug
    FailureCode.S7_UPSTREAM_TIMEOUT.value: 504,     # gateway timeout
    FailureCode.S8_UPSTREAM_REFUSED.value: 503,     # gateway unavailable
}


class HardFailure(Exception):
    """Raised by the adapter when an analysis payload cannot be salvaged.

    Carries the stable code so callers (server, frontend) can render the
    correct banner + recovery actions without parsing the message.

    `debug_detail` is server-side only — it may contain field paths or stack
    fragments unsafe to render in the UI directly. Use `request_id` to correlate
    server logs with the user-visible payload.
    """

    def __init__(self, code: FailureCode, debug_detail: str = ""):
        self.code = code
        self.debug_detail = debug_detail
        self.request_id = uuid.uuid4().hex[:16]
        super().__init__(f"{code.value}: {debug_detail}" if debug_detail else code.value)

    @property
    def hint(self) -> str:
        return RECOVERY_HINTS.get(self.code.value, "")

    @property
    def actions(self) -> list[str]:
        return RECOVERY_ACTIONS.get(self.code.value, [RecoveryAction.REPORT.value])

    @property
    def http_status(self) -> int:
        return HTTP_STATUS.get(self.code.value, 500)

    def to_payload(self, *, include_debug: bool = False) -> dict:
        """Frontend-ready dict. `include_debug` controls whether server-side detail leaks.

        Default (production): {code, hint, actions, request_id} only.
        With include_debug=True (dev / staging): adds debug_detail.
        """
        payload: dict = {
            "code": self.code.value,
            "hint": self.hint,
            "actions": self.actions,
            "request_id": self.request_id,
        }
        if include_debug and self.debug_detail:
            payload["debug_detail"] = self.debug_detail
        return payload
