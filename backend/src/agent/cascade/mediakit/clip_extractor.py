"""Best-effort per-scene clip extraction for the doubao_direct pipeline.

After the analysis contract is built, cut a short mp4 clip + poster frame for
each scene from the source video and store them under the media volume so the
frontend can show "this is what this shot looks like".

Entirely best-effort: any failure (download, ffmpeg missing, timeout, odd
codec) just yields no clip for that scene — the analysis itself never blocks or
fails. (We learned the hard way with the MediaKit storyline hang; clip
extraction must never become a critical path.)

Clips are stream-copied (`-c copy`), not re-encoded: douyin sources are already
h264/aac, so remuxing a [start, end] window is near-instant and keeps the added
latency small. Cuts are keyframe-aligned (start may snap to the nearest
keyframe) — fine for "what does this shot look like".

Storage: `media_root()/<analysis_id>/scene_<i>.mp4|.jpg`, served by nginx at
`/media/<analysis_id>/...` (see docker-compose frontend volume + nginx.conf).
"""

from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path

import httpx

from agent.cascade.persistence.db import db_path


# iPhone UA — douyinvod.com CDN only serves the .mp4 to mobile clients (mirrors
# douyin_share_resolver._MOBILE_UA).
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

_DOWNLOAD_TIMEOUT_S = 45.0
_FFMPEG_TIMEOUT_S = 25.0
_MAX_SOURCE_BYTES = 80 * 1024 * 1024  # sources are ≤180s short video
_PUBLIC_MEDIA_PREFIX = "/media"  # nginx `location ^~ /media/` serves the volume


def media_root() -> Path:
    """Filesystem dir where clips/posters are written. Sibling of the DB so it
    rides the same `/app/data` host volume in prod (and the CASCADE_DB_PATH dir
    in tests)."""
    return db_path().parent / "media"


def _ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


async def extract_scene_clips(
    direct_url: str,
    scenes: list,  # list[Scene]
    analysis_id: str,
    *,
    duration_s: float | None = None,
) -> dict[int, tuple[str, str]]:
    """Download the source once, cut one clip + poster per scene.

    Returns ``{scene_index: (clip_rel_url, poster_rel_url)}`` for scenes that
    succeeded (poster_rel_url is "" when only the clip cut). Best-effort:
    returns ``{}`` (never raises) on any top-level failure.
    """
    ffmpeg = _ffmpeg_bin()
    if not ffmpeg or not direct_url or not scenes:
        return {}

    out_dir = media_root() / analysis_id
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {}

    src = out_dir / "_source.mp4"
    if not await _download_source(direct_url, src):
        _safe_unlink(src)
        return {}

    results: dict[int, tuple[str, str]] = {}
    try:
        for scene in scenes:
            idx = int(getattr(scene, "scene_index", 0) or 0)
            start = max(0.0, float(scene.timestamp_start))
            end = float(scene.timestamp_end)
            if idx <= 0 or end <= start:
                continue
            clip_name = f"scene_{idx}.mp4"
            poster_name = f"scene_{idx}.jpg"
            clip_ok = await _ffmpeg_clip(ffmpeg, src, start, end, out_dir / clip_name)
            if not clip_ok:
                continue
            poster_ok = await _ffmpeg_poster(ffmpeg, src, start, out_dir / poster_name)
            clip_url = f"{_PUBLIC_MEDIA_PREFIX}/{analysis_id}/{clip_name}"
            poster_url = (
                f"{_PUBLIC_MEDIA_PREFIX}/{analysis_id}/{poster_name}" if poster_ok else ""
            )
            results[idx] = (clip_url, poster_url)
    finally:
        _safe_unlink(src)  # keep clips+posters, drop the bulky source
    return results


async def _download_source(url: str, dest: Path) -> bool:
    written = 0
    try:
        async with httpx.AsyncClient(
            timeout=_DOWNLOAD_TIMEOUT_S, follow_redirects=True
        ) as client:
            async with client.stream(
                "GET", url, headers={"User-Agent": _MOBILE_UA}
            ) as resp:
                if resp.status_code != 200:
                    return False
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(256 * 1024):
                        written += len(chunk)
                        if written > _MAX_SOURCE_BYTES:
                            return False
                        f.write(chunk)
    except Exception:
        return False
    return written > 0


async def _ffmpeg_clip(ffmpeg: str, src: Path, start: float, end: float, dest: Path) -> bool:
    dur = max(0.1, end - start)
    args = [
        ffmpeg, "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}",
        "-c", "copy", "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        str(dest),
    ]
    return await _run(args, dest)


async def _ffmpeg_poster(ffmpeg: str, src: Path, start: float, dest: Path) -> bool:
    args = [
        ffmpeg, "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(src), "-frames:v", "1",
        "-q:v", "3", "-vf", "scale='min(720,iw)':-2",
        str(dest),
    ]
    return await _run(args, dest)


async def _run(args: list[str], dest: Path) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except Exception:
        return False
    try:
        await asyncio.wait_for(proc.wait(), timeout=_FFMPEG_TIMEOUT_S)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return False
    except Exception:
        return False
    try:
        return proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0
    except OSError:
        return False


def _safe_unlink(p: Path) -> None:
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def sweep_old_media(max_age_h: float = 48.0) -> int:
    """Best-effort retention: delete media dirs older than ``max_age_h``.

    Returns the count removed. Called opportunistically at server boot. Clips
    are a convenience layer; the contract degrades gracefully when files vanish
    (frontend falls back to poster / no player on 404). Mirrors toprador's
    '24h 中间产物清理'."""
    root = media_root()
    if not root.exists():
        return 0
    cutoff = time.time() - max_age_h * 3600
    removed = 0
    try:
        for child in root.iterdir():
            try:
                if child.is_dir() and child.stat().st_mtime < cutoff:
                    shutil.rmtree(child, ignore_errors=True)
                    removed += 1
            except OSError:
                continue
    except OSError:
        return removed
    return removed
