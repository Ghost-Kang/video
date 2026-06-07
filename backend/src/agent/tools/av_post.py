"""视频后期(字幕烧入 / BGM 混音)—— 全程 best-effort:任何失败(ffmpeg 缺失、无字体、无曲目、
下载失败)都返回 None,调用方透传原视频,绝不阻断 Pro run。

字幕:ffmpeg drawtext(需 CJK 字体,自动探测;找不到 → None)。
BGM:从 bgm_root()(data/bgm/<track>.mp3)取曲目混入(缺曲 → None)。曲目文件由 founder 放入。
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import httpx

from agent.cascade.mediakit.clip_extractor import media_root

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


def _esc_drawtext(text: str) -> str:
    # drawtext 文本转义:冒号/单引号/反斜杠/百分号。
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


async def burn_subtitle(video_url: str, text: str) -> bytes | None:
    """视频底部烧一行字幕。无字体/失败 → None(透传)。"""
    text = (text or "").strip()
    if not text:
        return None
    font = _find_cjk_font()
    if not font:
        print("[av_post] 无 CJK 字体,字幕透传")
        return None
    with tempfile.TemporaryDirectory() as d:
        src, out = os.path.join(d, "in.mp4"), os.path.join(d, "out.mp4")
        if not await _download(video_url, src):
            return None
        draw = (
            f"drawtext=fontfile='{font}':text='{_esc_drawtext(text)}':"
            f"fontcolor=white:fontsize=h/18:box=1:boxcolor=black@0.5:boxborderw=10:"
            f"x=(w-text_w)/2:y=h-(text_h*2.2)"
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
