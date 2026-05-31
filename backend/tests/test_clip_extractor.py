from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import pytest

from agent.cascade.mediakit import clip_extractor


class _Scene:
    """Minimal scene-like object (extract reads scene_index + timestamps)."""

    def __init__(self, idx: int, start: float, end: float) -> None:
        self.scene_index = idx
        self.timestamp_start = start
        self.timestamp_end = end


def test_media_root_follows_db_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    assert clip_extractor.media_root() == tmp_path / "media"


def test_extract_empty_without_ffmpeg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    monkeypatch.setattr(clip_extractor, "_ffmpeg_bin", lambda: None)
    out = asyncio.run(
        clip_extractor.extract_scene_clips("https://x/y.mp4", [_Scene(1, 0.0, 5.0)], "ana_1")
    )
    assert out == {}


def test_extract_empty_without_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    monkeypatch.setattr(clip_extractor, "_ffmpeg_bin", lambda: "/usr/bin/ffmpeg")
    assert asyncio.run(clip_extractor.extract_scene_clips("", [], "ana_1")) == {}
    assert asyncio.run(clip_extractor.extract_scene_clips("https://x/y.mp4", [], "ana_1")) == {}


def test_extract_empty_when_download_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    monkeypatch.setattr(clip_extractor, "_ffmpeg_bin", lambda: "/usr/bin/ffmpeg")

    async def fail_dl(_url: str, _dest: Path) -> bool:
        return False

    monkeypatch.setattr(clip_extractor, "_download_source", fail_dl)
    out = asyncio.run(
        clip_extractor.extract_scene_clips("https://x/y.mp4", [_Scene(1, 0.0, 5.0)], "ana_1")
    )
    assert out == {}


def test_extract_maps_indices_when_ffmpeg_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Download + ffmpeg stubbed to succeed → relative /media urls keyed by
    scene_index; a scene whose clip cut fails is skipped."""
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    monkeypatch.setattr(clip_extractor, "_ffmpeg_bin", lambda: "/usr/bin/ffmpeg")

    async def ok_dl(_url: str, dest: Path) -> bool:
        dest.write_bytes(b"fakemp4")
        return True

    async def clip(_ff, _src, _start, _end, dest: Path) -> bool:
        # scene 2's clip "fails"
        if dest.name == "scene_2.mp4":
            return False
        dest.write_bytes(b"clip")
        return True

    async def poster(_ff, _src, _start, dest: Path) -> bool:
        dest.write_bytes(b"jpg")
        return True

    monkeypatch.setattr(clip_extractor, "_download_source", ok_dl)
    monkeypatch.setattr(clip_extractor, "_ffmpeg_clip", clip)
    monkeypatch.setattr(clip_extractor, "_ffmpeg_poster", poster)

    out = asyncio.run(
        clip_extractor.extract_scene_clips(
            "https://x/y.mp4",
            [_Scene(1, 0.0, 5.0), _Scene(2, 5.0, 10.0)],
            "ana_xyz",
        )
    )
    assert out == {1: ("/media/ana_xyz/scene_1.mp4", "/media/ana_xyz/scene_1.jpg")}
    # bulky source is cleaned up; clips remain
    out_dir = clip_extractor.media_root() / "ana_xyz"
    assert not (out_dir / "_source.mp4").exists()
    assert (out_dir / "scene_1.mp4").exists()


def test_sweep_old_media(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    root = clip_extractor.media_root()
    old = root / "ana_old"
    old.mkdir(parents=True)
    (old / "scene_1.mp4").write_bytes(b"x")
    stale = time.time() - 100 * 3600
    os.utime(old, (stale, stale))
    fresh = root / "ana_fresh"
    fresh.mkdir(parents=True)

    removed = clip_extractor.sweep_old_media(max_age_h=48)
    assert removed == 1
    assert not old.exists()
    assert fresh.exists()
