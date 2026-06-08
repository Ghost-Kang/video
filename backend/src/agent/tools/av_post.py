"""视频后期(字幕烧入 / BGM 混音)—— 全程 best-effort:任何失败(ffmpeg 缺失、无字体、无曲目、
下载失败)都返回 None,调用方透传原视频,绝不阻断 Pro run。

字幕:ffmpeg drawtext(需 CJK 字体,自动探测;找不到 → None)。
BGM:从 bgm_root()(data/bgm/<track>.mp3)取曲目混入(缺曲 → None)。曲目文件由 founder 放入。
"""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
import uuid
from pathlib import Path

import httpx

from agent import config
from agent.cascade.mediakit.clip_extractor import media_root

# 节点 voice 选项 → 火山 voice_type(founder 可在控制台核对/调整真实 id)。
_VOICE_MAP = {
    "温柔女声": "BV001_streaming",
    "活力男声": "BV002_streaming",
    "知性女声": "BV700_streaming",
    "童声": "BV051_streaming",
}

_CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/System/Library/Fonts/PingFang.ttc",  # macOS dev
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]


def bgm_root() -> Path:
    """BGM 素材库目录(data/bgm)。founder 放免版权 mp3 进来,文件名 = 曲目选项值 + .mp3。"""
    return media_root().parent / "bgm"


def _find_cjk_font() -> str | None:
    for p in _CJK_FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


async def _download(url: str, dest: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url)
            if r.status_code != 200 or not r.content:
                return False
            Path(dest).write_bytes(r.content)
            return True
    except Exception:  # noqa: BLE001
        return False


async def _run_ffmpeg(args: list[str]) -> bytes | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _out, err = await proc.communicate()
        if proc.returncode != 0:
            print(f"[av_post] ffmpeg rc={proc.returncode}: {err[-300:].decode(errors='ignore')}")
            return None
    except FileNotFoundError:
        print("[av_post] ffmpeg 不在 PATH")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"[av_post] ffmpeg 异常: {e}")
        return None
    return None  # caller reads the output file


def _wrap_caption(text: str, per_line: float = 14.0, max_lines: int = 3) -> str:
    """按视觉宽度换行(CJK≈全宽1.0、其余≈半宽0.5),超 max_lines 截断加…。竖屏短视频字幕用。"""
    text = " ".join((text or "").split())  # 折叠空白
    lines: list[str] = []
    cur, w = "", 0.0
    for ch in text:
        cw = 1.0 if ord(ch) > 0x2E80 else 0.5
        if w + cw > per_line and cur:
            lines.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += cw
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:-1] + "…"
    return "\n".join(lines)


async def burn_subtitle(video_url: str, text: str) -> bytes | None:
    """视频底部烧字幕(长文自动换行 + 居中 + 黑底框)。无字体/失败 → None(透传)。"""
    text = (text or "").strip()
    if not text:
        return None
    font = _find_cjk_font()
    if not font:
        print("[av_post] 无 CJK 字体,字幕透传")
        return None
    with tempfile.TemporaryDirectory() as d:
        src, out = os.path.join(d, "in.mp4"), os.path.join(d, "out.mp4")
        txt = os.path.join(d, "cap.txt")
        if not await _download(video_url, src):
            return None
        Path(txt).write_text(_wrap_caption(text), encoding="utf-8")
        # textfile 传多行(避开转义地狱);fontsize=h/26 给长文留空间;底部留 8% 边距;居中。
        draw = (
            f"drawtext=fontfile='{font}':textfile='{txt}':"
            f"fontcolor=white:fontsize=h/26:line_spacing=8:box=1:boxcolor=black@0.5:boxborderw=12:"
            f"x=(w-text_w)/2:y=h-text_h-(h*0.08)"
        )
        await _run_ffmpeg(["-y", "-i", src, "-vf", draw, "-c:a", "copy", "-c:v", "libx264", "-preset", "veryfast", out])
        p = Path(out)
        return p.read_bytes() if p.exists() and p.stat().st_size > 0 else None


async def mux_bgm(video_url: str, track: str, volume: float = 0.3) -> bytes | None:
    """把 bgm_root()/<track>.mp3 混入视频(保留原声,BGM 压低)。缺曲/失败 → None(透传)。"""
    track = (track or "").strip()
    if not track or track == "none":
        return None
    bgm = bgm_root() / f"{track}.mp3"
    if not bgm.exists():
        print(f"[av_post] BGM 曲目缺失: {bgm}")
        return None
    vol = max(0.0, min(1.0, float(volume)))
    with tempfile.TemporaryDirectory() as d:
        src, out = os.path.join(d, "in.mp4"), os.path.join(d, "out.mp4")
        if not await _download(video_url, src):
            return None
        # 原声 + BGM(压低)混音;-shortest 跟视频时长;视频流直拷。
        await _run_ffmpeg([
            "-y", "-i", src, "-stream_loop", "-1", "-i", str(bgm),
            "-filter_complex", f"[1:a]volume={vol}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-shortest", out,
        ])
        p = Path(out)
        return p.read_bytes() if p.exists() and p.stat().st_size > 0 else None


async def synth_voice(text: str, voice_label: str) -> bytes | None:
    """火山语音(openspeech v1)文本→语音 mp3 bytes。缺 appid/token 或失败 → None。
    注意:用 TTS_APP_ID/TTS_ACCESS_TOKEN(火山语音控制台),**非 ARK_API_KEY**(ARK 无 TTS)。"""
    text = (text or "").strip()
    if not text or not config.TTS_APP_ID or not config.TTS_ACCESS_TOKEN:
        return None
    voice_type = _VOICE_MAP.get(voice_label, voice_label or "BV001_streaming")
    payload = {
        "app": {"appid": config.TTS_APP_ID, "token": config.TTS_ACCESS_TOKEN, "cluster": config.TTS_CLUSTER},
        "user": {"uid": "pro_canvas"},
        "audio": {"voice_type": voice_type, "encoding": "mp3"},
        "request": {"reqid": uuid.uuid4().hex, "text": text[:1500], "operation": "query"},
    }
    headers = {"Authorization": f"Bearer;{config.TTS_ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(config.TTS_TTS_URL, json=payload, headers=headers)
        data = r.json()
        if data.get("code") == 3000 and data.get("data"):
            return base64.b64decode(data["data"])
        print(f"[av_post] TTS code={data.get('code')} msg={data.get('message')}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"[av_post] TTS 异常: {e}")
        return None


async def voiceover(video_url: str, text: str, voice_label: str) -> bytes | None:
    """合成口播并替换视频音轨。无 creds/失败 → None(透传)。"""
    voice = await synth_voice(text, voice_label)
    if not voice:
        return None
    with tempfile.TemporaryDirectory() as d:
        src, vo, out = os.path.join(d, "in.mp4"), os.path.join(d, "vo.mp3"), os.path.join(d, "out.mp4")
        if not await _download(video_url, src):
            return None
        Path(vo).write_bytes(voice)
        # 用口播替换原音轨(分镜视频原声多为占位);-shortest 跟较短的走。
        await _run_ffmpeg(["-y", "-i", src, "-i", vo, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-shortest", out])
        p = Path(out)
        return p.read_bytes() if p.exists() and p.stat().st_size > 0 else None
