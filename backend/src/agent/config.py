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
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_MODEL = os.getenv("DOUBAO_MODEL", "doubao-seed-2-0-pro")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3-flash-preview")

# -------- 图片生成 --------
IMAGE_GEN_PROVIDER = os.getenv("IMAGE_GEN_PROVIDER", "google")  # "apimart" | "google"
IMAGE_GEN_API_KEY = os.getenv("IMAGE_GEN_API_KEY")
IMAGE_GEN_BASE_URL = os.getenv("IMAGE_GEN_BASE_URL", "https://api.apimart.ai")
IMAGE_GEN_MODEL = os.getenv("IMAGE_GEN_MODEL", "gpt-image-2")
IMAGE_GEN_GOOGLE_MODEL = os.getenv("IMAGE_GEN_GOOGLE_MODEL", "gemini-3.1-flash-image-preview")

# -------- 视频生成 --------
VIDEO_GEN_API_KEY = os.getenv("VIDEO_GEN_API_KEY")
VIDEO_GEN_BASE_URL = os.getenv("VIDEO_GEN_BASE_URL")
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
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
