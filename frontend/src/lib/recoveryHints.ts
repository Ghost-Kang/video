/** UI-facing recovery hints — mirror of backend failures.RECOVERY_HINTS */
export const RECOVERY_HINTS: Record<string, string> = {
  S1_NO_SOURCE_URL:
    "这条链接系统读不到。换一条爆款链接试试，或者从下面今日精选里挑一条。",
  S2_VERSION_MISMATCH: "系统升级了一下底层格式。点这里刷新一次就好。",
  S3_NO_FORMULA:
    "这条视频没看出能复刻的套路（可能太特殊或太短）。换一条更有规律的爆款。",
  S4_SCENES_LEN_OUT_OF_RANGE:
    "这条视频镜头太少（3 个以下）或太多（超过 12 个），系统暂时处理不了。选一条 15-60 秒、节奏正常的视频再试。",
  S5_INVALID_PAYLOAD:
    "系统读这条视频时遇到了奇怪的数据。换一条试试，或者点反馈告诉我们这条的链接。",
  S6_NEGATIVE_COST: "系统内部统计出了点小问题。直接重试一次就行。",
  S7_UPSTREAM_TIMEOUT:
    "分析超时了。可能视频太长，也可能服务繁忙。等 30 秒重试，或者换一条更短的。",
  S8_UPSTREAM_REFUSED:
    "系统暂时繁忙。1 分钟后重试，或者从今日精选里挑一条（这些是已经分析好的）。",
  S11_INTERNAL_ERROR:
    "系统出了点小问题，我们已经记录下来了。直接重试一次，或者换一条链接试试。",
  W1_AUTO_ID: "（系统已自动编号）",
  W2_FALLBACK_USED: "这部分系统没完全看懂，用了通用判断，可能不太准。",
  W3_SCENES_TRUNCATED: "这条视频镜头较多，系统只取了前 12 个。",
  W4_GENERIC_SCENE_LABEL: "这一段画面描述较弱，你可能想自己改一下。",
  W5_TIMESTAMPS_SORTED: "（系统帮你把镜头顺序对齐了）",
  W6_FIRST_FRAME_UNREACHABLE: "原视频的画面读不到了，但文字分析还在。",
  W7_CONFIDENCE_COMPUTED: "（系统对这条分析的把握一般，仅供参考）",
  W8_COST_UNKNOWN: "（这条的成本统计暂时缺失，不影响使用）",
  W9_CROSS_BORDER_SOURCE: "（这是境外平台的视频，分析结果仅供参考）",
  W10_AUTHOR_PII_STRIPPED: "",
};
