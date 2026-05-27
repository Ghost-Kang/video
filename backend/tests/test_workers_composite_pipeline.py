"""workers/composite_pipeline.py 集成测试 — mock parents + compose_videos + upload。

composite 与 image/video 不同点:
- 不调外部 provider — 用本地 ffmpeg(compose_videos)
- 输入是上游 video 节点的 result.url 列表(只挑 type=="video" 的父)
- 输出 bytes 走 `agent.tools.s3_upload.upload_bytes`(不是 workers/s3 包装)
- 失败模式 3 种:无视频 / ffmpeg fail / S3 fail
"""

from __future__ import annotations

import asyncio

import pytest

from agent.workers import composite_pipeline
from agent.workers.composite_pipeline import process_composite_task


@pytest.fixture
def captured_canvas(monkeypatch):
    """stub canvas_tools.update_generation_state / _update_node_result / notify_user。

    parents 由各 test 用 _seed_parents helper 注入 _load_all_edges + _load_node。
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

    monkeypatch.setattr(composite_pipeline.canvas_tools, "update_generation_state", _state)
    monkeypatch.setattr(composite_pipeline.canvas_tools, "_update_node_result", _result)
    monkeypatch.setattr(composite_pipeline, "notify_user", _notify)
    return calls


def _seed_parents(monkeypatch, *, edges: list[dict], nodes: dict[str, dict]) -> None:
    """注入 mock _load_all_edges + _load_node 返回预设的边和父节点 dict。"""

    def _load_all_edges(*, user_id=None, thread_id=None):
        return edges

    def _load_node(node_id, *, user_id=None, thread_id=None):
        return nodes.get(node_id)

    monkeypatch.setattr(composite_pipeline.canvas_tools, "_load_all_edges", _load_all_edges)
    monkeypatch.setattr(composite_pipeline.canvas_tools, "_load_node", _load_node)


def _composite_node(**overrides) -> dict:
    base = {"id": "c1", "user_id": "u1", "thread_id": "t1"}
    base.update(overrides)
    return base


# ---------- parent 收集逻辑 ----------


class TestParentCollection:
    def test_no_edges_marks_failed_no_videos(self, captured_canvas, monkeypatch):
        _seed_parents(monkeypatch, edges=[], nodes={})
        # compose / upload 不应被调
        monkeypatch.setattr(composite_pipeline, "compose_videos", _unreachable_compose)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", _unreachable_upload)

        asyncio.run(process_composite_task(_composite_node()))

        assert captured_canvas["state"] == [{
            "nid": "c1", "status": "failed", "task_id": None,
            "error": "没有可拼接的视频", "user_id": "u1", "thread_id": "t1",
        }]
        assert captured_canvas["notify"] == [("u1", "t1")]
        assert captured_canvas["result"] == []

    def test_non_video_parents_skipped(self, captured_canvas, monkeypatch):
        """type != video 的父被过滤掉(image 父不参与合成)。"""
        _seed_parents(
            monkeypatch,
            edges=[
                {"id": "e1", "source": "img1", "target": "c1", "position": 1},
                {"id": "e2", "source": "scr1", "target": "c1", "position": 2},
            ],
            nodes={
                "img1": {"id": "img1", "type": "image", "result": {"url": "https://img.png"}},
                "scr1": {"id": "scr1", "type": "script", "result": {"url": "https://x"}},
            },
        )
        monkeypatch.setattr(composite_pipeline, "compose_videos", _unreachable_compose)

        asyncio.run(process_composite_task(_composite_node()))

        # 没视频父 → 失败,error 与 no-edges case 相同
        assert captured_canvas["state"][-1]["error"] == "没有可拼接的视频"

    def test_video_parent_without_url_skipped(self, captured_canvas, monkeypatch):
        _seed_parents(
            monkeypatch,
            edges=[
                {"id": "e1", "source": "v_no_url", "target": "c1", "position": 1},
            ],
            nodes={
                "v_no_url": {"id": "v_no_url", "type": "video", "result": None},
            },
        )
        monkeypatch.setattr(composite_pipeline, "compose_videos", _unreachable_compose)

        asyncio.run(process_composite_task(_composite_node()))

        assert captured_canvas["state"][-1]["error"] == "没有可拼接的视频"

    def test_edges_to_other_targets_filtered_out(self, captured_canvas, monkeypatch):
        """只挑 target == nid 的边,其他边的视频父不应被认领。"""
        _seed_parents(
            monkeypatch,
            edges=[
                {"id": "e1", "source": "v_other", "target": "c_other", "position": 1},
            ],
            nodes={
                "v_other": {"id": "v_other", "type": "video", "result": {"url": "https://v.mp4"}},
            },
        )
        monkeypatch.setattr(composite_pipeline, "compose_videos", _unreachable_compose)

        asyncio.run(process_composite_task(_composite_node()))
        # composite c1 没有指向自己的边 → 失败
        assert captured_canvas["state"][-1]["error"] == "没有可拼接的视频"


# ---------- 失败路径 ----------


class TestFailurePaths:
    def test_ffmpeg_returns_none_marks_failed(self, captured_canvas, monkeypatch):
        _seed_parents(
            monkeypatch,
            edges=[{"id": "e1", "source": "v1", "target": "c1", "position": 1}],
            nodes={"v1": {"id": "v1", "type": "video", "result": {"url": "https://v.mp4"}}},
        )

        async def _compose_none(_urls):
            return None

        monkeypatch.setattr(composite_pipeline, "compose_videos", _compose_none)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", _unreachable_upload)

        asyncio.run(process_composite_task(_composite_node()))

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == "ffmpeg 合成失败"

    def test_ffmpeg_empty_bytes_marks_failed(self, captured_canvas, monkeypatch):
        """compose_videos 返 b'' 也算失败(falsy 检查)。"""
        _seed_parents(
            monkeypatch,
            edges=[{"id": "e1", "source": "v1", "target": "c1", "position": 1}],
            nodes={"v1": {"id": "v1", "type": "video", "result": {"url": "https://v.mp4"}}},
        )

        async def _compose_empty(_urls):
            return b""

        monkeypatch.setattr(composite_pipeline, "compose_videos", _compose_empty)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", _unreachable_upload)

        asyncio.run(process_composite_task(_composite_node()))
        assert captured_canvas["state"][-1]["error"] == "ffmpeg 合成失败"

    def test_s3_upload_returns_none_marks_failed(self, captured_canvas, monkeypatch):
        _seed_parents(
            monkeypatch,
            edges=[{"id": "e1", "source": "v1", "target": "c1", "position": 1}],
            nodes={"v1": {"id": "v1", "type": "video", "result": {"url": "https://v.mp4"}}},
        )

        async def _compose_ok(_urls):
            return b"MP4_BYTES"

        monkeypatch.setattr(composite_pipeline, "compose_videos", _compose_ok)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", lambda data, name: None)

        asyncio.run(process_composite_task(_composite_node()))

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == "S3 上传失败"
        # 没 _update_node_result(失败路径)
        assert captured_canvas["result"] == []


# ---------- happy path ----------


class TestHappyPath:
    def test_single_video_parent(self, captured_canvas, monkeypatch):
        _seed_parents(
            monkeypatch,
            edges=[{"id": "e1", "source": "v1", "target": "c1", "position": 1}],
            nodes={"v1": {"id": "v1", "type": "video", "result": {"url": "https://v1.mp4"}}},
        )

        compose_calls: list[list] = []

        async def _compose(urls):
            compose_calls.append(list(urls))
            return b"COMPOSED_BYTES"

        upload_calls: list[tuple] = []

        def _upload(data, filename):
            upload_calls.append((data, filename))
            return "https://s3/composite.mp4"

        monkeypatch.setattr(composite_pipeline, "compose_videos", _compose)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", _upload)

        asyncio.run(process_composite_task(_composite_node()))

        # state: done(无 polling 中间态,因为 composite 是同步流)
        assert captured_canvas["state"] == [{
            "nid": "c1", "status": "done", "task_id": None, "error": None,
            "user_id": "u1", "thread_id": "t1",
        }]
        # compose 接收的是 video URL list
        assert compose_calls == [["https://v1.mp4"]]
        # upload 接收的 filename 是 "composite.mp4"(固定)
        assert upload_calls == [(b"COMPOSED_BYTES", "composite.mp4")]
        # result 写入 url + clips count
        assert captured_canvas["result"] == [{
            "nid": "c1",
            "updates": {"url": "https://s3/composite.mp4", "clips": 1},
            "user_id": "u1", "thread_id": "t1",
        }]
        assert captured_canvas["notify"] == [("u1", "t1")]

    def test_multiple_video_parents_in_order(self, captured_canvas, monkeypatch):
        """多个视频父按 _load_all_edges 返回顺序拼接(position 已被 DAO 排序)。"""
        _seed_parents(
            monkeypatch,
            edges=[
                {"id": "e1", "source": "v1", "target": "c1", "position": 1},
                {"id": "e2", "source": "v2", "target": "c1", "position": 2},
                {"id": "e3", "source": "v3", "target": "c1", "position": 3},
            ],
            nodes={
                "v1": {"id": "v1", "type": "video", "result": {"url": "https://v1.mp4"}},
                "v2": {"id": "v2", "type": "video", "result": {"url": "https://v2.mp4"}},
                "v3": {"id": "v3", "type": "video", "result": {"url": "https://v3.mp4"}},
            },
        )

        compose_calls: list[list] = []

        async def _compose(urls):
            compose_calls.append(list(urls))
            return b"OK"

        monkeypatch.setattr(composite_pipeline, "compose_videos", _compose)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", lambda data, name: "https://s3/c.mp4")

        asyncio.run(process_composite_task(_composite_node()))

        assert compose_calls == [["https://v1.mp4", "https://v2.mp4", "https://v3.mp4"]]
        assert captured_canvas["result"][0]["updates"]["clips"] == 3

    def test_mixed_parents_filters_to_video_only(self, captured_canvas, monkeypatch):
        """混合 image + video 父时,只 video 进 compose。"""
        _seed_parents(
            monkeypatch,
            edges=[
                {"id": "e1", "source": "v1", "target": "c1", "position": 1},
                {"id": "e2", "source": "img1", "target": "c1", "position": 2},
                {"id": "e3", "source": "v2", "target": "c1", "position": 3},
            ],
            nodes={
                "v1": {"id": "v1", "type": "video", "result": {"url": "https://v1.mp4"}},
                "img1": {"id": "img1", "type": "image", "result": {"url": "https://img.png"}},
                "v2": {"id": "v2", "type": "video", "result": {"url": "https://v2.mp4"}},
            },
        )

        compose_calls: list[list] = []

        async def _compose(urls):
            compose_calls.append(list(urls))
            return b"OK"

        monkeypatch.setattr(composite_pipeline, "compose_videos", _compose)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", lambda data, name: "https://s3/c.mp4")

        asyncio.run(process_composite_task(_composite_node()))

        # image 被过滤
        assert compose_calls == [["https://v1.mp4", "https://v2.mp4"]]
        assert captured_canvas["result"][0]["updates"]["clips"] == 2

    def test_explicit_user_thread_propagated(self, captured_canvas, monkeypatch):
        """A2 contract:worker 必须显式传 user_id/thread_id 给所有 canvas_tools 调用。"""
        edge_calls: list[tuple] = []
        node_calls: list[tuple] = []

        def _load_all_edges(*, user_id=None, thread_id=None):
            edge_calls.append((user_id, thread_id))
            return [{"id": "e1", "source": "v1", "target": "c1", "position": 1}]

        def _load_node(node_id, *, user_id=None, thread_id=None):
            node_calls.append((node_id, user_id, thread_id))
            return {"id": "v1", "type": "video", "result": {"url": "https://v1.mp4"}}

        monkeypatch.setattr(composite_pipeline.canvas_tools, "_load_all_edges", _load_all_edges)
        monkeypatch.setattr(composite_pipeline.canvas_tools, "_load_node", _load_node)

        async def _compose(_urls):
            return b"OK"

        monkeypatch.setattr(composite_pipeline, "compose_videos", _compose)
        monkeypatch.setattr(composite_pipeline, "upload_bytes", lambda data, name: "https://s3/c.mp4")

        asyncio.run(process_composite_task(_composite_node(user_id="u_target", thread_id="t_target")))

        assert edge_calls == [("u_target", "t_target")]
        assert node_calls == [("v1", "u_target", "t_target")]
        for s in captured_canvas["state"]:
            assert s["user_id"] == "u_target"
            assert s["thread_id"] == "t_target"
        for r in captured_canvas["result"]:
            assert r["user_id"] == "u_target"
            assert r["thread_id"] == "t_target"
        assert captured_canvas["notify"] == [("u_target", "t_target")]


# ---------- helpers ----------


async def _unreachable_compose(_urls):
    raise AssertionError("compose_videos should not be called")


def _unreachable_upload(_data, _name):
    raise AssertionError("upload_bytes should not be called")
