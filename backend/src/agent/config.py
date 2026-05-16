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
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3-flash-preview")

# -------- 图片生成 --------
IMAGE_GEN_API_KEY = os.getenv("IMAGE_GEN_API_KEY")
IMAGE_GEN_BASE_URL = os.getenv("IMAGE_GEN_BASE_URL")

# -------- 视频生成 --------
VIDEO_GEN_API_KEY = os.getenv("VIDEO_GEN_API_KEY")
VIDEO_GEN_BASE_URL = os.getenv("VIDEO_GEN_BASE_URL")

# -------- TTS --------
TTS_API_KEY = os.getenv("TTS_API_KEY")
TTS_BASE_URL = os.getenv("TTS_BASE_URL")

# -------- ASR --------
ASR_API_KEY = os.getenv("ASR_API_KEY")
ASR_BASE_URL = os.getenv("ASR_BASE_URL")
