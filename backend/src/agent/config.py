"""项目配置

仅记录元信息，从 .env 读取。不包含工厂逻辑。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载项目根目录 .env
_project_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# -------- LLM --------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "doubao").strip().lower()
# W5D3 — ARK_API_KEY / ARK_BASE_URL were previously declared twice (once here
# and once under "视频生成" further down). Single declaration here is the canon;
# the duplicate was leftover from a refactor. Removed.
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_MODEL = os.getenv("DOUBAO_MODEL", "doubao-seed-2-0-pro-260215")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3-flash-preview")

# -------- 图片生成 --------
# B6/D1 (PIPL §38 合规): 默认走境内 Apimart。改写已隔离境内 doubao,生成图也不能
# 裸奔跨境 —— 30 人 Beta 处理真实用户数据,默认 provider 必须境内。跨境 Gemini 仍
# 可经 IMAGE_GEN_PROVIDER=google 显式开启(双轨保留)。
# TODO(合规): 跨境 Gemini 上线前需补「用户跨境数据传输同意」条款 UI/记录,本次未做。
# 2026-06-02: 新增 "seedream"(火山豆包图像生成,**复用 ARK_API_KEY**,境内官方,跟
# 分析/改写/视频 Seedance 同账号同合规)。推荐用它 —— 无需任何新密钥(prod 实测
# ark.cn-beijing.volces.com/api/v3/images/generations + 现有 ARK key 200 出图)。
# 默认 seedream(火山官方境内,用已设的 ARK_API_KEY,无需任何新密钥;比 apimart 中转更
# 合规——后者代理跨境 OpenAI 模型)。可切 apimart(中转)/ google(跨境,需显式)。
IMAGE_GEN_PROVIDER = os.getenv("IMAGE_GEN_PROVIDER", "seedream")  # "seedream"(默认,境内,ARK key) | "apimart"(中转) | "google"(跨境)
IMAGE_GEN_API_KEY = os.getenv("IMAGE_GEN_API_KEY")
IMAGE_GEN_BASE_URL = os.getenv("IMAGE_GEN_BASE_URL", "https://api.apimart.ai")
IMAGE_GEN_MODEL = os.getenv("IMAGE_GEN_MODEL", "gpt-image-2")
IMAGE_GEN_GOOGLE_MODEL = os.getenv("IMAGE_GEN_GOOGLE_MODEL", "gemini-3.1-flash-image-preview")
# Seedream(火山方舟图像)模型;走 ARK_API_KEY + ARK_BASE_URL,无独立密钥。
SEEDREAM_MODEL = os.getenv("SEEDREAM_MODEL", "doubao-seedream-4-0-250828")

# -------- 落地页案例自动发布(auto-showcase)--------
# 用户跑完一条分析,达标即自动做成落地页轮播案例(clip 复制到永久 showcase/ 目录
# + 写 showcase_cases 表),落地页动态 fetch 显示。founder 定:高置信度自动上 + 可下架。
# kill-switch:AUTO_SHOWCASE_ENABLED=0 关闭自动发布(手动 gen_showcase_case 不受影响)。
AUTO_SHOWCASE_ENABLED = os.getenv("AUTO_SHOWCASE_ENABLED", "1").strip() not in ("0", "false", "no", "")
# 质量门槛:置信度下限 —— 低于此不自动上(真实用户视频未经把关公开的风险闸)。
AUTO_SHOWCASE_MIN_CONFIDENCE = float(os.getenv("AUTO_SHOWCASE_MIN_CONFIDENCE", "0.85") or "0.85")
# 自动发布案例数上限 —— 落地页固定按置信度排名展示 ≤10 条(见 showcase_repo
# .list_published + GET /api/showcase 的 limit 钳制),所以自动池也封顶 10:满 10 条后
# 不再自动上(手动 gen_showcase_case 仍可加,但落地页只取置信度 top-10)。
# 已下架(hidden)的不占名额。防 showcase/ 媒体无限增长 + 轮播过长。
AUTO_SHOWCASE_MAX = int(os.getenv("AUTO_SHOWCASE_MAX", "10") or "10")
# 自动发布案例至少需要几幕成功抽到 clip(无 clip 的卡退化成静态,落地页轮播体验差)。
AUTO_SHOWCASE_MIN_CLIPS = int(os.getenv("AUTO_SHOWCASE_MIN_CLIPS", "3") or "3")

# -------- 审核闸门(LangGraph interrupt,canvas 统筹 P2 slice-1)--------
# 把「烧钱的生成工具」从 director.md 的口头约定(「只创建不执行 / 跑过头」)升级为
# LangGraph 原生 interrupt() 审核闸门:Director **自主**调生成工具前 graph 真的暂停,
# 前端弹审核卡,用户确认/拒绝后 Command(resume) 续跑。默认 OFF —— 拆细灰度(D5),
# 先 dark-launch、充分测试再开;开关切换需重启进程(agent 实例池在构造时读)。
# 注意:用户显式点「生成」(CardStack 的 [generate_*] 标记)会被 run_agent 自动批准,
# 不弹二次确认 —— 闸门只拦「自主烧钱」,不拦「用户已点的生成」。
CANVAS_INTERRUPT_GATE = os.getenv("CANVAS_INTERRUPT_GATE", "0").strip().lower() not in ("0", "false", "no", "off", "")
# 受闸门管控的工具名(逗号分隔可覆盖)。默认 = 三个会真的花钱/不可逆的生成工具。
# compose 本身免费,但「合成成片」是叙事终点闸门(plan §3 成片闸门),一并纳入。
INTERRUPT_GATE_TOOLS = frozenset(
    t.strip()
    for t in os.getenv(
        "INTERRUPT_GATE_TOOLS",
        "cascade_generate_first_frame,cascade_generate_shot_video,cascade_compose_film",
    ).split(",")
    if t.strip()
)

# canvas 统筹 P2 ④ — 长会话上下文降本:由 deepagents 内置 summarization middleware 提供
# (无条件挂、profile-aware、非破坏式 offload),无需自建 flag/中间件。详见 main.py 注释。

# -------- 视频生成 --------
VIDEO_GEN_API_KEY = os.getenv("VIDEO_GEN_API_KEY")
VIDEO_GEN_BASE_URL = os.getenv("VIDEO_GEN_BASE_URL")
# ARK_API_KEY + ARK_BASE_URL are declared once under "LLM" above — shared with
# the video generation path (same ARK gateway, same key).
ARK_VIDEO_MODEL = os.getenv("ARK_VIDEO_MODEL", "doubao-seedance-2-0-260128")

# -------- TTS --------
TTS_API_KEY = os.getenv("TTS_API_KEY")
TTS_BASE_URL = os.getenv("TTS_BASE_URL")

# -------- ASR --------
ASR_API_KEY = os.getenv("ASR_API_KEY")
ASR_BASE_URL = os.getenv("ASR_BASE_URL")

# -------- Toprador analysis upstream --------
CASCADE_UPSTREAM = os.getenv("CASCADE_UPSTREAM", "mediakit").strip().lower() or "mediakit"
TOPRADOR_ENDPOINT = os.getenv("TOPRADOR_ENDPOINT", "")
TOPRADOR_API_KEY = os.getenv("TOPRADOR_API_KEY", "")
VOLC_MEDIAKIT_AK = os.getenv("VOLC_MEDIAKIT_AK", "")
STRICT_CROSS_BORDER_REJECT = os.getenv("STRICT_CROSS_BORDER_REJECT", "1") == "1"

# -------- S3 --------
# -------- 内测准入 --------
# Comma-separated list of valid invite codes. Empty = open access (dev mode).
# Production deploy must set this; the WS auth handler rejects unknown codes
# with close(4003) before any LangGraph spend.
INVITE_CODES = frozenset(
    c.strip() for c in os.getenv("INVITE_CODES", "").split(",") if c.strip()
)

# B8-3 / 鉴权 A(每用户独立邀请码)— per-user invite codes that carry a
# SERVER-DERIVED identity. Format: `INVITE_CODE_MAP="code1:userA,code2:userB"`.
# When a request presents a code in this map, the server uses the MAPPED user_id
# as the trusted identity — ignoring whatever user_id the client claims. This
# closes the cost-cap evasion: a caller can no longer rotate user_id/run_id to
# dodge CASCADE_RUN/USER_DAY caps, because their identity is pinned to the code
# they authenticated with (which they can't mint).
#
# Shared INVITE_CODES still work (legacy / dev): a shared code has no mapped
# identity, so user_id falls back to the client's claim (the pre-existing,
# weaker behavior). Migration path: issue one mapped code per beta user, retire
# the shared codes. A code may appear in both; the map wins for identity.
def _parse_invite_code_map(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        code, _, uid = pair.partition(":")
        code, uid = code.strip(), uid.strip()
        if code and uid:
            out[code] = uid
    return out


INVITE_CODE_MAP = _parse_invite_code_map(os.getenv("INVITE_CODE_MAP", ""))


def has_invite_gate() -> bool:
    """True if any invite gate is configured (shared codes OR per-user mapped
    codes). Read live (not a cached constant) so tests that monkeypatch
    INVITE_CODES / INVITE_CODE_MAP take effect. dev/test with both empty → no
    gate (open)."""
    return bool(INVITE_CODES or INVITE_CODE_MAP)


def is_valid_invite(code: str | None) -> bool:
    """True if `code` is an accepted invite — either a shared INVITE_CODES member
    or a per-user mapped code. Single source of truth for both WS + HTTP gates."""
    if not code:
        return False
    return code in INVITE_CODES or code in INVITE_CODE_MAP


def resolve_user_id(code: str | None, claimed_user_id: str) -> str:
    """The trusted user_id for a request authenticated with `code`.

    If `code` is a per-user mapped code → the MAPPED user_id (server-derived,
    the client's claim is ignored — this is the刷钱 fix). Otherwise (shared code
    or no map) → the client's claimed user_id (legacy behavior, unchanged)."""
    if code and code in INVITE_CODE_MAP:
        return INVITE_CODE_MAP[code]
    return claimed_user_id


# Boot-time snapshot of "is any gate configured" — for the fail-closed prod
# guard below ONLY (runs once at import). Runtime gate checks must call
# has_invite_gate() instead (reads live state so tests can monkeypatch).
_HAS_INVITE_GATE_AT_BOOT = bool(INVITE_CODES or INVITE_CODE_MAP)

# W5D3 P1 — fail CLOSED in prod. Previously a misconfigured deploy with
# `INVITE_CODES=""` shipped wide-open and only a stderr WARN appeared in docker
# logs (easy to miss). Now: if ENV=prod and NO invite gate is configured, raise
# on import. The only way to deliberately run prod with no gate is to set
# `CASCADE_AUTH_MODE=open` explicitly (opt-in, documented).
_AUTH_MODE = os.getenv("CASCADE_AUTH_MODE", "").strip().lower()
_LOOKS_PROD = (
    os.getenv("ENV", "").lower() == "prod"
    or "prod" in os.getenv("HOSTNAME", "").lower()
)
if not _HAS_INVITE_GATE_AT_BOOT and _LOOKS_PROD and _AUTH_MODE != "open":
    raise RuntimeError(
        "No invite gate in a prod env. Set INVITE_CODES (comma-separated) "
        "and/or INVITE_CODE_MAP (code:user_id,...) or explicitly opt-in to "
        "open access with CASCADE_AUTH_MODE=open. Boot aborted to prevent "
        "silently shipping an open server."
    )
if not _HAS_INVITE_GATE_AT_BOOT and _LOOKS_PROD and _AUTH_MODE == "open":
    import sys as _sys
    print(
        "[WARN] No invite gate + CASCADE_AUTH_MODE=open — WS auth gate is OFF.",
        file=_sys.stderr,
        flush=True,
    )

# Public flag so the transport layer can fail-closed in prod without
# re-deriving the heuristic.
IS_PROD_LIKE = _LOOKS_PROD

# -------- Admin API token --------
# Separate, stronger gate for cross-user admin reads (GET /api/events,
# /api/creators, /api/health/summary). The invite_code is a shared cohort
# secret; admin data must require a token only the founder holds. Empty in
# dev = open; empty in prod = admin endpoints fail closed (403) until set.
ADMIN_TOKEN = os.getenv("CASCADE_ADMIN_TOKEN", "").strip()

S3_AK = os.getenv("S3_AK", "")
S3_SK = os.getenv("S3_SK", "")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_REGION = os.getenv("S3_REGION", "")
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_BASE_URL = os.getenv("S3_BASE_URL", "")

# -------- 分镜定义 --------
STORYBOARD_COLUMNS = [
    {"key": "no",          "label": "镜号",   "required": True},
    {"key": "scene",       "label": "场景",   "required": False},
    {"key": "duration",    "label": "时长",   "required": False},
    {"key": "camera",      "label": "运镜",   "required": False},
    {"key": "description", "label": "画面描述", "required": True},
    {"key": "transition",  "label": "转场",   "required": False},
    {"key": "audio",       "label": "声音",   "required": False},
]
# 生成 prompt 里的格式说明
STORYBOARD_FORMAT_HINT = " | ".join(c["label"] for c in STORYBOARD_COLUMNS) + "\n" + \
    " | ".join(f"<{c['key']}>" for c in STORYBOARD_COLUMNS)
