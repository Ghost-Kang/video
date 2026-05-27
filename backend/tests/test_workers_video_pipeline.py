"""workers/video_pipeline.py 集成测试 — mock get_video_provider + S3 + canvas_tools。

video_pipeline 与 image_pipeline 形似但有关键不同:
- 用 `get_video_provider()`(singleton)而非 `make_image_provider(name)`
- provider.submit 签名带 duration/resolution/ratio/generate_audio/image_urls
- poll 结果用 `video_url` 字段(不是 `url`),且**没有 image_data 备用通道**
- S3 download 走 ext="mp4"
- S3 失败 → 标 failed(无 fallback 到原 url,因为视频文件大不适合直接给前端)
"""

from __future__ import annotations

import asyncio

import pytest

from agent.workers import video_pipeline
from agent.workers.video_pipeline import process_video_task


class _FakeVideoProvider:
    """模拟 video provider:submit + poll 返预设值。"""

    def __init__(self, *, submit_result: dict, poll_result: dict) -> None:
        self._submit = submit_result
        self._poll = poll_result
        self.submit_calls: list[dict] = []
        self.poll_calls: list[str] = []

    async def submit(self, prompt, *, duration, resolution, ratio, generate_audio, image_urls=None):
        self.submit_calls.append({
            "prompt": prompt, "duration": duration, "resolution": resolution,
            "ratio": ratio, "generate_audio": generate_audio, "image_urls": image_urls,
        })
        return self._submit

    async def poll(self, task_id):
        self.poll_calls.append(task_id)
        return self._poll


@pytest.fixture
def captured_canvas(monkeypatch):
    """stub canvas_tools.update_generation_state / _update_node_result / notify_user / get_ref_urls。"""
    calls: dict[str, list] = {"state": [], "result": [], "notify": []}

    def _state(nid, status, task_id=None, error=None, *, user_id=None, thread_id=None):
        calls["state"].append({
            "nid": nid, "status": status, "task_id": task_id, "error": error,
            "user_id": user_id, "thread_id": thread_id,
        })

    def _result(nid, updates, *, user_id=None, thread_id=None):
        calls["result"].append({"nid": nid, "updates": updates, "user_id": user_id, "thread_id": thread_id})

    def _notify(uid, tid):
        calls["notify"].append((uid, tid))

    monkeypatch.setattr(video_pipeline.canvas_tools, "update_generation_state", _state)
    monkeypatch.setattr(video_pipeline.canvas_tools, "_update_node_result", _result)
    monkeypatch.setattr(video_pipeline, "notify_user", _notify)
    monkeypatch.setattr(video_pipeline, "get_ref_urls", lambda _node: [])
    return calls


def _node(**overrides) -> dict:
    base = {
        "id": "v1",
        "user_id": "u1",
        "thread_id": "t1",
        "description": "boil potato",
        "result": {
            "prompt": "boil potato in steel pot",
            "duration": 8,
            "resolution": "1080p",
            "generate_audio": True,
        },
    }
    base.update(overrides)
    return base


def _set_provider(monkeypatch, provider: _FakeVideoProvider) -> None:
    monkeypatch.setattr(video_pipeline, "get_video_provider", lambda: provider)


# ---------- 参数传递 ----------


class TestSubmitParams:
    def test_passes_result_params_to_submit(self, captured_canvas, monkeypatch):
        provider = _FakeVideoProvider(submit_result={"task_id": None, "error": "x"}, poll_result={})
        _set_provider(monkeypatch, provider)

        asyncio.run(process_video_task(_node()))

        call = provider.submit_calls[0]
        assert call["prompt"] == "boil potato in steel pot"
        assert call["duration"] == 8
        assert call["resolution"] == "1080p"
        assert call["generate_audio"] is True
        assert call["ratio"] == "16:9"
        assert call["image_urls"] is None  # captured_canvas 默认 get_ref_urls = []

    def test_defaults_when_result_missing(self, captured_canvas, monkeypatch):
        """node.result = None 时,duration/resolution/generate_audio 应用 default。"""
        provider = _FakeVideoProvider(submit_result={"task_id": None, "error": "x"}, poll_result={})
        _set_provider(monkeypatch, provider)

        node = _node()
        node["result"] = None
        node["description"] = "fallback prompt"

        asyncio.run(process_video_task(node))

        call = provider.submit_calls[0]
        assert call["prompt"] == "fallback prompt"
        assert call["duration"] == 5
        assert call["resolution"] == "720p"
        assert call["generate_audio"] is True

    def test_ref_urls_passed_when_non_empty(self, captured_canvas, monkeypatch):
        provider = _FakeVideoProvider(submit_result={"task_id": None, "error": "x"}, poll_result={})
        _set_provider(monkeypatch, provider)
        monkeypatch.setattr(video_pipeline, "get_ref_urls", lambda _node: ["https://ref"])

        asyncio.run(process_video_task(_node()))

        assert provider.submit_calls[0]["image_urls"] == ["https://ref"]


# ---------- 状态机 ----------


class TestProcessVideoTask:
    def test_submit_failure_marks_failed(self, captured_canvas, monkeypatch):
        provider = _FakeVideoProvider(
            submit_result={"task_id": None, "error": "rate_limited"},
            poll_result={},  # not reached
        )
        _set_provider(monkeypatch, provider)

        asyncio.run(process_video_task(_node()))

        assert len(captured_canvas["state"]) == 1
        assert captured_canvas["state"][0]["status"] == "failed"
        assert captured_canvas["state"][0]["error"] == "rate_limited"
        assert provider.poll_calls == []
        # 失败仍 notify(UI 要刷新 failed 状态)
        assert captured_canvas["notify"] == [("u1", "t1")]

    def test_video_url_uploads_mp4_marks_done(self, captured_canvas, monkeypatch):
        provider = _FakeVideoProvider(
            submit_result={"task_id": "VT1"},
            poll_result={"video_url": "https://provider/raw.mp4", "actual_time": 30},
        )
        _set_provider(monkeypatch, provider)

        captured_dl: dict = {}

        async def fake_dl(url, nid, ext="png"):
            captured_dl["url"] = url
            captured_dl["nid"] = nid
            captured_dl["ext"] = ext
            return "https://s3/v1.mp4"

        monkeypatch.setattr(video_pipeline, "download_and_upload", fake_dl)

        asyncio.run(process_video_task(_node()))

        # state: polling → done
        statuses = [s["status"] for s in captured_canvas["state"]]
        assert statuses == ["polling", "done"]
        assert captured_canvas["state"][0]["task_id"] == "VT1"
        # download_and_upload 必须用 ext="mp4"
        assert captured_dl["ext"] == "mp4"
        assert captured_dl["url"] == "https://provider/raw.mp4"
        assert captured_dl["nid"] == "v1"
        # result 写入 S3 url + actual_time
        assert captured_canvas["result"] == [{
            "nid": "v1",
            "updates": {"url": "https://s3/v1.mp4", "actual_time": 30},
            "user_id": "u1", "thread_id": "t1",
        }]

    def test_video_url_s3_failure_marks_failed_no_fallback(self, captured_canvas, monkeypatch):
        """与 image 不同:video S3 失败**不**回退到 provider 原 url(文件大,前端无法直接消费)。"""
        provider = _FakeVideoProvider(
            submit_result={"task_id": "VT1"},
            poll_result={"video_url": "https://provider/raw.mp4"},
        )
        _set_provider(monkeypatch, provider)

        async def fake_dl(url, nid, ext="png"):
            return None  # S3 失败

        monkeypatch.setattr(video_pipeline, "download_and_upload", fake_dl)

        asyncio.run(process_video_task(_node()))

        statuses = [s["status"] for s in captured_canvas["state"]]
        assert statuses == ["polling", "failed"]
        assert captured_canvas["state"][-1]["error"] == "S3 上传失败"
        # 没 _update_node_result 写入(失败路径)
        assert captured_canvas["result"] == []

    def test_poll_timeout_marks_failed(self, captured_canvas, monkeypatch):
        provider = _FakeVideoProvider(
            submit_result={"task_id": "VT1"},
            poll_result={"error": "timeout"},
        )
        _set_provider(monkeypatch, provider)

        asyncio.run(process_video_task(_node()))

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == "timeout"

    def test_poll_empty_marks_failed_with_passthrough_error(self, captured_canvas, monkeypatch):
        provider = _FakeVideoProvider(
            submit_result={"task_id": "VT1"},
            poll_result={"error": "provider_5xx"},
        )
        _set_provider(monkeypatch, provider)

        asyncio.run(process_video_task(_node()))

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == "provider_5xx"

    def test_explicit_user_thread_propagated(self, captured_canvas, monkeypatch):
        """A2 contract:worker 必须显式传 user_id/thread_id 给所有 canvas_tools 调用。"""
        provider = _FakeVideoProvider(
            submit_result={"task_id": "VT1"},
            poll_result={"video_url": "https://x.mp4"},
        )
        _set_provider(monkeypatch, provider)

        async def fake_dl(url, nid, ext="png"):
            return "https://s3/v.mp4"

        monkeypatch.setattr(video_pipeline, "download_and_upload", fake_dl)

        asyncio.run(process_video_task(_node(user_id="u_target", thread_id="t_target")))

        for s in captured_canvas["state"]:
            assert s["user_id"] == "u_target"
            assert s["thread_id"] == "t_target"
        for r in captured_canvas["result"]:
            assert r["user_id"] == "u_target"
            assert r["thread_id"] == "t_target"
        assert captured_canvas["notify"] == [("u_target", "t_target")]
