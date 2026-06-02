"""Tests for the 视频闭环 tools: cascade_generate_shot_video + cascade_compose_film."""

from __future__ import annotations

import asyncio

import pytest

from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.rewrite_service import RewriteResult, RewriteShot
from agent.tools import cascade as cascade_tools
from agent.tools.cascade import (
    _compose_film_bg,
    _poll_shot_video,
    cascade_compose_film,
    cascade_generate_shot_video,
)
from agent.transport import notify
from agent.transport.runtime_ctx import set_run_ctx


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        import json

        self.sent.append(json.loads(data))


def _rewrite_json(shots: int = 3) -> str:
    rw = RewriteResult(
        rewrite_id="rw_vid",
        analysis_id="ana_x",
        niche="generic",
        script_markdown="### 改写脚本\n1. ...",
        shots=[RewriteShot(shot_index=i, dialogue=f"台词{i}", visual=f"画面{i}") for i in range(1, shots + 1)],
        confidence=0.9,
        cost_cny=0.02,
        model="test",
    )
    return rw.model_dump_json()


class _FakeSeedance:
    def __init__(self, submit_result: dict, poll_result: dict) -> None:
        self._submit_result = submit_result
        self._poll_result = poll_result
        self.submit_calls: list[dict] = []

    async def submit(self, *, prompt, duration, ratio, image_urls=None, **_):
        self.submit_calls.append({"prompt": prompt, "duration": duration, "image_urls": image_urls})
        return self._submit_result

    async def poll(self, task_id, **_):
        return self._poll_result


def _setup(monkeypatch, *, ws: FakeWS, user_id="u1"):
    # capture pushes via the live registry (background tools push without fallback_ws)
    notify.register(user_id, ws)

    async def _no_cost(**_):
        return None

    async def _no_emit(*a, **k):
        return None

    monkeypatch.setattr(cascade_tools, "cost_guard", _no_cost)
    monkeypatch.setattr(cascade_tools, "emit", _no_emit)
    set_run_ctx({"user_id": user_id, "thread_id": "t1", "ws": ws, "run_id": "run1"})


def _teardown(ws: FakeWS, user_id="u1"):
    notify.unregister(user_id, ws)


# ---------- cascade_generate_shot_video (sync paths) ----------


def test_no_shot_image_returns_friendly_and_pushes_error(monkeypatch):
    ws = FakeWS()
    _setup(monkeypatch, ws=ws)
    monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", _aret(_rewrite_json()))
    monkeypatch.setattr(cascade_tools, "load_shot_assets", _aret([]))
    monkeypatch.setattr(cascade_tools, "load_shot_image", _aret(None))

    result = asyncio.run(cascade_generate_shot_video.ainvoke({"rewrite_id": "rw_vid", "shot_index": 1}))
    _teardown(ws)

    assert result["error"] == "NO_SHOT_IMAGE"
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "shot_video_returned"
    assert ws.sent[0]["error"]


def test_cached_video_returns_without_submit(monkeypatch):
    ws = FakeWS()
    _setup(monkeypatch, ws=ws)
    monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", _aret(_rewrite_json()))
    monkeypatch.setattr(
        cascade_tools, "load_shot_assets",
        _aret([{"shot_index": 1, "image_url": "/media/rw_vid/shot_1.jpg", "video_url": "/media/rw_vid/shot_1.mp4"}]),
    )
    # 若误调 SeedanceProvider 会炸(没 mock submit)→ 验证不走提交
    result = asyncio.run(cascade_generate_shot_video.ainvoke({"rewrite_id": "rw_vid", "shot_index": 1}))
    _teardown(ws)

    assert result["cached"] is True
    assert result["video_url"] == "/media/rw_vid/shot_1.mp4"
    assert ws.sent[0]["video_url"] == "/media/rw_vid/shot_1.mp4"


def test_cost_cap_pushes_per_shot_error_no_submit(monkeypatch):
    ws = FakeWS()
    _setup(monkeypatch, ws=ws)
    monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", _aret(_rewrite_json()))
    monkeypatch.setattr(cascade_tools, "load_shot_assets", _aret([{"shot_index": 1, "image_url": "/media/rw_vid/shot_1.jpg", "video_url": None}]))
    monkeypatch.setattr(cascade_tools, "load_shot_image", _aret("/media/rw_vid/shot_1.jpg"))

    async def _cap(**_):
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "over cap")

    monkeypatch.setattr(cascade_tools, "cost_guard", _cap)

    result = asyncio.run(cascade_generate_shot_video.ainvoke({"rewrite_id": "rw_vid", "shot_index": 1}))
    _teardown(ws)

    assert result["error"] == "S8_UPSTREAM_REFUSED"
    assert ws.sent[0]["type"] == "shot_video_returned"
    assert ws.sent[0]["error"]


def test_submit_success_returns_submitted_and_spawns_bg(monkeypatch):
    ws = FakeWS()
    _setup(monkeypatch, ws=ws)
    monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", _aret(_rewrite_json()))
    monkeypatch.setattr(cascade_tools, "load_shot_assets", _aret([{"shot_index": 1, "image_url": "/media/rw_vid/shot_1.jpg", "video_url": None}]))
    monkeypatch.setattr(cascade_tools, "load_shot_image", _aret("/media/rw_vid/shot_1.jpg"))
    fake = _FakeSeedance(submit_result={"task_id": "task_123"}, poll_result={"video_url": "https://ark/v.mp4"})
    monkeypatch.setattr(cascade_tools, "SeedanceProvider", lambda: fake)

    # 把后台 poll 换成 noop(别动全局 asyncio.create_task —— langchain 内部也用它;
    # 真 poll 会跑 _download 卡住)。后台路径由 _poll_shot_video 直测覆盖。
    async def _noop_poll(*a, **k):
        return None

    monkeypatch.setattr(cascade_tools, "_poll_shot_video", _noop_poll)

    result = asyncio.run(cascade_generate_shot_video.ainvoke({"rewrite_id": "rw_vid", "shot_index": 1}))
    _teardown(ws)

    assert result["status"] == "submitted"
    assert result["task_id"] == "task_123"
    assert fake.submit_calls and fake.submit_calls[0]["image_urls"] == ["/media/rw_vid/shot_1.jpg"]


# ---------- _poll_shot_video (background) ----------


def test_poll_success_downloads_persists_and_pushes(monkeypatch, tmp_path):
    ws = FakeWS()
    notify.register("u1", ws)
    fake = _FakeSeedance(submit_result={}, poll_result={"video_url": "https://ark/v.mp4"})

    async def _fake_download(url, dest):
        with open(dest, "wb") as f:
            f.write(b"video-bytes")

    recorded = {}

    async def _fake_record(rid, idx, url):
        recorded["url"] = url

    monkeypatch.setattr(cascade_tools, "_download", _fake_download)
    monkeypatch.setattr(cascade_tools, "media_root", lambda: tmp_path)
    monkeypatch.setattr(cascade_tools, "record_shot_video", _fake_record)

    async def _no_emit(*a, **k):
        return None

    monkeypatch.setattr(cascade_tools, "emit", _no_emit)

    asyncio.run(_poll_shot_video(fake, "task_123", "u1", "t1", "rw_vid", 2))
    notify.unregister("u1", ws)

    assert recorded["url"] == "/media/rw_vid/shot_2.mp4"
    assert (tmp_path / "rw_vid" / "shot_2.mp4").exists()
    assert ws.sent[0]["type"] == "shot_video_returned"
    assert ws.sent[0]["video_url"] == "/media/rw_vid/shot_2.mp4"
    assert ws.sent[0]["error"] is None


def test_poll_failure_pushes_error(monkeypatch, tmp_path):
    ws = FakeWS()
    notify.register("u1", ws)
    fake = _FakeSeedance(submit_result={}, poll_result={"error": "timeout"})
    monkeypatch.setattr(cascade_tools, "media_root", lambda: tmp_path)

    asyncio.run(_poll_shot_video(fake, "task_123", "u1", "t1", "rw_vid", 2))
    notify.unregister("u1", ws)

    assert ws.sent[0]["type"] == "shot_video_returned"
    assert ws.sent[0]["error"]
    assert ws.sent[0]["video_url"] == ""


# ---------- cascade_compose_film ----------


def test_compose_no_videos_returns_error(monkeypatch):
    ws = FakeWS()
    _setup(monkeypatch, ws=ws)
    monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", _aret(_rewrite_json()))
    monkeypatch.setattr(cascade_tools, "load_film", _aret(None))
    monkeypatch.setattr(cascade_tools, "load_shot_assets", _aret([{"shot_index": 1, "image_url": "x", "video_url": None}]))

    result = asyncio.run(cascade_compose_film.ainvoke({"rewrite_id": "rw_vid"}))
    _teardown(ws)
    assert result["error"] == "NO_SHOT_VIDEOS"


def test_compose_cached_film(monkeypatch):
    ws = FakeWS()
    _setup(monkeypatch, ws=ws)
    monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", _aret(_rewrite_json()))
    monkeypatch.setattr(cascade_tools, "load_film", _aret("/media/rw_vid/film.mp4"))

    result = asyncio.run(cascade_compose_film.ainvoke({"rewrite_id": "rw_vid"}))
    _teardown(ws)
    assert result["cached"] is True
    assert ws.sent[0]["type"] == "film_returned"
    assert ws.sent[0]["film_url"] == "/media/rw_vid/film.mp4"


def test_compose_composing_spawns_bg(monkeypatch):
    ws = FakeWS()
    _setup(monkeypatch, ws=ws)
    monkeypatch.setattr(cascade_tools, "load_rewrite_by_id", _aret(_rewrite_json()))
    monkeypatch.setattr(cascade_tools, "load_film", _aret(None))
    monkeypatch.setattr(
        cascade_tools, "load_shot_assets",
        _aret([
            {"shot_index": 1, "image_url": "x", "video_url": "/media/rw_vid/shot_1.mp4"},
            {"shot_index": 2, "image_url": "x", "video_url": "/media/rw_vid/shot_2.mp4"},
        ]),
    )

    async def _noop_bg(*a, **k):
        return None

    monkeypatch.setattr(cascade_tools, "_compose_film_bg", _noop_bg)

    result = asyncio.run(cascade_compose_film.ainvoke({"rewrite_id": "rw_vid"}))
    _teardown(ws)
    assert result["status"] == "composing"
    assert result["shots"] == 2


def test_compose_film_bg_persists_and_pushes(monkeypatch, tmp_path):
    ws = FakeWS()
    notify.register("u1", ws)

    async def _fake_compose(paths):
        return b"film-bytes"

    recorded = {}

    async def _fake_record_film(rid, url):
        recorded["url"] = url

    async def _no_emit(*a, **k):
        return None

    monkeypatch.setattr(cascade_tools, "compose_local_files", _fake_compose)
    monkeypatch.setattr(cascade_tools, "media_root", lambda: tmp_path)
    monkeypatch.setattr(cascade_tools, "record_film", _fake_record_film)
    monkeypatch.setattr(cascade_tools, "emit", _no_emit)

    asyncio.run(_compose_film_bg("u1", "t1", "rw_vid", [str(tmp_path / "a.mp4")]))
    notify.unregister("u1", ws)

    assert recorded["url"] == "/media/rw_vid/film.mp4"
    assert (tmp_path / "rw_vid" / "film.mp4").read_bytes() == b"film-bytes"
    assert ws.sent[0]["type"] == "film_returned"
    assert ws.sent[0]["film_url"] == "/media/rw_vid/film.mp4"


def _aret(value):
    """Helper: async function returning `value` (for monkeypatching async repo fns)."""

    async def _f(*a, **k):
        return value

    return _f
