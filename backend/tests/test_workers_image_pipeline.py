"""workers/image_pipeline.py 集成测试 — mock provider + S3 + canvas_tools。

image_pipeline 是 worker 处理一条图片任务的完整流:
    queue node → provider.submit → polling → provider.poll → S3 → notify

完整真实路径要外部 API + 真实 S3 + 真实 DB。这里 stub 所有外部依赖,只验证
worker 内部的状态机和分支(submit fail / url result / image_data result / empty result)。
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest

from agent.tools import canvas as canvas_tools
from agent.workers import image_pipeline
from agent.workers.image_pipeline import (
    get_ref_urls,
    make_image_provider,
    process_image_task,
)


def _unique_thread() -> str:
    return f"img-{uuid.uuid4().hex[:8]}"


# ---------- make_image_provider ----------


class TestMakeImageProvider:
    def test_google_provider(self):
        from agent.tools.generation import GoogleProvider

        provider = make_image_provider("google")
        assert isinstance(provider, GoogleProvider)

    def test_default_apimart_provider(self):
        from agent.tools.generation import ApimartProvider

        # 任意非 "google" 字符串都走默认
        provider = make_image_provider("apimart")
        assert isinstance(provider, ApimartProvider)

    def test_unknown_name_still_apimart(self):
        from agent.tools.generation import ApimartProvider

        provider = make_image_provider("random_string")
        assert isinstance(provider, ApimartProvider)


# ---------- get_ref_urls(用真实 DB) ----------


class TestGetRefUrls:
    def test_no_parents_returns_empty(self):
        tid = _unique_thread()
        canvas_tools.set_thread_id(tid)
        node = canvas_tools.create_canvas_node("script", "孤儿节点", "无父")
        refs = get_ref_urls({"id": node["id"], "user_id": "default", "thread_id": tid})
        assert refs == []

    def test_collects_parent_urls(self):
        """parent.result.url 都被收集。"""
        tid = _unique_thread()
        canvas_tools.set_thread_id(tid)
        # 创建 script + 标 confirmed 才能挂下游
        parent = canvas_tools.create_canvas_node("script", "父", "x")
        canvas_tools.approve_node(parent["id"])
        # 父节点 result 加 url
        canvas_tools._update_node_result(parent["id"], {"url": "https://parent.png"})
        # 创建 child + 挂边
        child = canvas_tools.create_canvas_node("image", "子", "y", parent_ids=[parent["id"]], subtype="character")

        refs = get_ref_urls({"id": child["id"], "user_id": "default", "thread_id": tid})
        assert refs == ["https://parent.png"]

    def test_parent_without_url_skipped(self):
        tid = _unique_thread()
        canvas_tools.set_thread_id(tid)
        parent = canvas_tools.create_canvas_node("script", "无 url 父", "x")
        canvas_tools.approve_node(parent["id"])
        # 不写 result.url
        child = canvas_tools.create_canvas_node("image", "子", "y", parent_ids=[parent["id"]], subtype="character")

        refs = get_ref_urls({"id": child["id"], "user_id": "default", "thread_id": tid})
        assert refs == []


# ---------- process_image_task ----------


class _FakeProvider:
    """支持预设 submit/poll 返回 — 不发起真实网络。"""

    def __init__(self, *, submit_result: dict, poll_result: dict) -> None:
        self._submit = submit_result
        self._poll = poll_result
        self.submit_calls: list[tuple] = []
        self.poll_calls: list[str] = []

    async def submit(self, prompt, ratio, resolution, ref_urls=None):
        self.submit_calls.append((prompt, ratio, resolution, ref_urls))
        return self._submit

    async def poll(self, task_id):
        self.poll_calls.append(task_id)
        return self._poll


@pytest.fixture
def captured_canvas(monkeypatch):
    """stub canvas_tools.update_generation_state + _update_node_result + notify_user。

    返回一个 dict 让 test 看到调用序列。get_ref_urls 也 stub 成 [](不依赖 DB)。
    """
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

    monkeypatch.setattr(image_pipeline.canvas_tools, "update_generation_state", _state)
    monkeypatch.setattr(image_pipeline.canvas_tools, "_update_node_result", _result)
    monkeypatch.setattr(image_pipeline, "notify_user", _notify)
    monkeypatch.setattr(image_pipeline, "get_ref_urls", lambda _node: [])

    return calls


def _node(nid: str = "n1") -> dict:
    return {
        "id": nid,
        "user_id": "u1",
        "thread_id": "t1",
        "image_gen_provider": "apimart",
        "description": "a cat",
        "result": {"prompt": "a cat", "resolution": "1080p", "subtype": "character"},
    }


class TestProcessImageTask:
    def test_submit_failure_marks_failed(self, captured_canvas, monkeypatch):
        provider = _FakeProvider(
            submit_result={"task_id": None, "error": "rate_limited"},
            poll_result={},  # 不会被调到
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)

        asyncio.run(process_image_task(_node()))

        # 应一次 state 写入 failed,带 error
        assert len(captured_canvas["state"]) == 1
        assert captured_canvas["state"][0]["status"] == "failed"
        assert captured_canvas["state"][0]["error"] == "rate_limited"
        # 不该 polling 调到
        assert provider.poll_calls == []
        # notify 仍发(让 UI 刷新 failed 状态)
        assert captured_canvas["notify"] == [("u1", "t1")]

    def test_url_result_uses_s3_download(self, captured_canvas, monkeypatch):
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"url": "https://provider/raw.png", "actual_time": 12},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)

        # download_and_upload 是 async — patch 为 async stub
        async def fake_dl(url, nid, ext="png"):
            return f"https://s3/{nid}.{ext}"

        monkeypatch.setattr(image_pipeline, "download_and_upload", fake_dl)

        asyncio.run(process_image_task(_node()))

        # state: polling → done
        statuses = [s["status"] for s in captured_canvas["state"]]
        assert statuses == ["polling", "done"]
        assert captured_canvas["state"][0]["task_id"] == "T1"
        # result 写入 S3 url
        assert captured_canvas["result"] == [{
            "nid": "n1",
            "updates": {"url": "https://s3/n1.png", "actual_time": 12},
            "user_id": "u1", "thread_id": "t1",
        }]

    def test_url_result_s3_failure_falls_back_to_provider_url(self, captured_canvas, monkeypatch):
        """S3 download fail (None) — 落回 provider 原 url,仍标 done。"""
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"url": "https://provider/raw.png", "actual_time": 5},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)

        async def fake_dl(url, nid, ext="png"):
            return None  # S3 fail

        monkeypatch.setattr(image_pipeline, "download_and_upload", fake_dl)

        asyncio.run(process_image_task(_node()))

        # 仍标 done
        assert captured_canvas["state"][-1]["status"] == "done"
        # url 用 provider 原值
        assert captured_canvas["result"][0]["updates"]["url"] == "https://provider/raw.png"

    def test_image_data_result_uploads_bytes(self, captured_canvas, monkeypatch):
        """Google provider 这类返回 bytes 不是 URL — 走 upload_bytes_to_s3。"""
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"image_data": b"\x89PNG_BYTES", "actual_time": 8},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)

        captured_upload: dict = {}

        def fake_upload(data, filename):
            captured_upload["data"] = data
            captured_upload["filename"] = filename
            return "https://s3/n1.png"

        monkeypatch.setattr(image_pipeline, "upload_bytes_to_s3", fake_upload)

        asyncio.run(process_image_task(_node()))

        assert captured_canvas["state"][-1]["status"] == "done"
        assert captured_canvas["result"][0]["updates"]["url"] == "https://s3/n1.png"
        assert captured_upload["filename"] == "n1.png"
        assert captured_upload["data"] == b"\x89PNG_BYTES"

    def test_image_data_s3_failure_marks_failed(self, captured_canvas, monkeypatch):
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"image_data": b"X"},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)
        monkeypatch.setattr(image_pipeline, "upload_bytes_to_s3", lambda d, n: None)

        asyncio.run(process_image_task(_node()))

        statuses = [s["status"] for s in captured_canvas["state"]]
        assert statuses == ["polling", "failed"]
        assert captured_canvas["state"][-1]["error"] == "S3 上传失败"
        # 没 _update_node_result 写入(失败路径)
        assert captured_canvas["result"] == []

    def test_poll_timeout_marks_failed_with_timeout(self, captured_canvas, monkeypatch):
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"error": "timeout"},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)

        asyncio.run(process_image_task(_node()))

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == "timeout"

    def test_poll_empty_result_marks_failed_with_error_string(self, captured_canvas, monkeypatch):
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"error": "unknown_failure"},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)

        asyncio.run(process_image_task(_node()))

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == "unknown_failure"

    def test_passes_ref_urls_into_submit(self, captured_canvas, monkeypatch):
        """get_ref_urls 返回非空时,submit 应收到 list;空时 submit 应收到 None。"""
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"error": "timeout"},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)
        monkeypatch.setattr(image_pipeline, "get_ref_urls", lambda _node: ["https://ref1", "https://ref2"])

        asyncio.run(process_image_task(_node()))

        assert provider.submit_calls[0][3] == ["https://ref1", "https://ref2"]

    def test_empty_ref_urls_sends_none(self, captured_canvas, monkeypatch):
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"error": "timeout"},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)
        # captured_canvas fixture 默认 get_ref_urls → []

        asyncio.run(process_image_task(_node()))

        # submit_calls[0][3] 应是 None,不是 []
        assert provider.submit_calls[0][3] is None

    def test_uses_node_description_when_result_prompt_missing(self, captured_canvas, monkeypatch):
        """result.prompt 缺失时 fallback 到 node.description。"""
        provider = _FakeProvider(
            submit_result={"task_id": "T1"},
            poll_result={"error": "timeout"},
        )
        monkeypatch.setattr(image_pipeline, "make_image_provider", lambda _name: provider)

        node = _node()
        node["result"] = None  # 没 prompt
        node["description"] = "fallback prompt"

        asyncio.run(process_image_task(node))

        assert provider.submit_calls[0][0] == "fallback prompt"
