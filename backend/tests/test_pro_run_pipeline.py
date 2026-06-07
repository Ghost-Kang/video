"""Pro 计算图 worker pipeline 单测(fixture provider 端到端 + 失败重试 + 成本记账 + 恢复)。"""

from __future__ import annotations

import asyncio
import json

from agent import config
from agent.cascade.failures import FailureCode, HardFailure
from agent.tools.canvas_persistence import pro_runs_repo as repo
from agent.workers import pro_run_pipeline as pipe


VALID_GRAPH = {
    "version": 1,
    "nodes": [
        {"id": "m", "type": "Model"},
        {"id": "p", "type": "Prompt", "params": {"text": "猫"}},
        {"id": "g", "type": "Generate"},
        {"id": "v", "type": "Preview"},
    ],
    "edges": [
        {"id": "1", "source": "m", "sourceHandle": "model", "target": "g", "targetHandle": "model"},
        {"id": "2", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
        {"id": "3", "source": "g", "sourceHandle": "image", "target": "v", "targetHandle": "image"},
    ],
}


def _setup(monkeypatch, tmp_path):
    db_file = tmp_path / "canvas.db"
    monkeypatch.setattr("agent.tools.canvas_persistence.db.canvas_db_path", lambda: db_file)
    # 隔离 events DB(worker 现在会调真 cost_guard.cost_guard → 读 cascade.db 记账总额)。
    # 空库 → recorded=0 → 正常预算下放行,测试确定性。
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    frames: list[dict] = []
    costs: list[dict] = []

    async def fake_send(user_id, payload, **kw):
        frames.append({"user_id": user_id, **payload})

    async def fake_download(url, key):
        return None  # 保留原 URL(fixture data: URL)

    async def fake_record(**kw):
        costs.append(kw)

    monkeypatch.setattr("agent.workers.pro_run_pipeline.send_to_user", fake_send)
    monkeypatch.setattr("agent.workers.pro_run_pipeline.download_and_upload", fake_download)
    monkeypatch.setattr("agent.cascade.cost_guard.record_generation_cost", fake_record)
    return frames, costs


def _enqueue(graph=VALID_GRAPH, provider="fixture", run_id="r1", cost=3.0):
    repo.create_pro_run(
        run_id, user_id="u1", thread_id="t1", graph_json=json.dumps(graph), provider=provider, cost_est=cost
    )
    claimed = repo.claim_pending_pro_runs()
    return claimed[0]


def test_pipeline_happy_path_fixture(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    run = _enqueue()
    asyncio.run(pipe.process_pro_run_task(run))

    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "done"
    assert after["result"] and after["result"][0].startswith("data:image/png")
    # frames: progress(submitting) + progress(running) + node_done + done
    types = [f["type"] for f in frames]
    assert "pro_run_progress" in types
    assert "pro_run_node_done" in types
    assert types[-1] == "pro_run_done"
    assert frames[-1]["outputs"]


def test_pipeline_records_cost_with_run_id(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    run = _enqueue(cost=4.5)
    asyncio.run(pipe.process_pro_run_task(run))
    assert len(costs) == 1
    c = costs[0]
    assert c["run_id"] == "r1"  # MUST match the enqueue-time guard bucket
    assert c["user_id"] == "u1"
    assert c["call_kind"] == "canvas_comfyui"
    assert c["cost_cny"] == 4.5


class _FakeProvider:
    def __init__(self, submit_result, poll_result):
        self._submit = submit_result
        self._poll = poll_result

    async def submit(self, graph, *, user_id, run_id):
        return self._submit

    async def poll(self, task_id):
        return self._poll


def test_pipeline_submit_error_schedules_retry(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "agent.workers.pro_run_pipeline.get_comfyui_provider",
        lambda name=None: _FakeProvider({"error": "boom"}, None),
    )
    run = _enqueue()
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    # attempt 1 < max -> retried -> back to pending, no cost recorded (submit failed)
    assert after["status"] == "pending"
    assert after["next_retry_at"] is not None
    assert costs == []


def test_pipeline_poll_failed_schedules_retry(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "agent.workers.pro_run_pipeline.get_comfyui_provider",
        lambda name=None: _FakeProvider({"task_id": "x"}, {"status": "failed", "error": "gpu oom"}),
    )
    run = _enqueue()
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "pending"  # retried
    # cost WAS recorded (submit succeeded = billable)
    assert len(costs) == 1


def test_recover_repolls_completed(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "agent.workers.pro_run_pipeline.get_comfyui_provider",
        lambda name=None: _FakeProvider(None, {"status": "completed", "outputs": ["http://x/a.png"]}),
    )
    run = _enqueue()
    repo.update_pro_run_state("r1", "polling", user_id="u1", thread_id="t1", comfy_prompt_id="pid")
    recovered = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    asyncio.run(pipe.recover_pro_run_task(recovered))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "done"
    assert after["result"] == ["http://x/a.png"]


DOMESTIC_GRAPH = {
    "version": 1,
    "nodes": [
        {"id": "p", "type": "Prompt", "params": {"text": "一只猫"}},
        {"id": "g", "type": "Generate", "params": {}},
        {"id": "vid", "type": "Video", "params": {"duration": 4}},
        {"id": "prev", "type": "Preview", "params": {}},
    ],
    "edges": [
        {"id": "1", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
        {"id": "2", "source": "g", "sourceHandle": "image", "target": "vid", "targetHandle": "image"},
        {"id": "3", "source": "vid", "sourceHandle": "video", "target": "prev", "targetHandle": "image"},
    ],
}


class _FakeSeed:
    async def generate(self, prompt, image_urls=None):
        return {"url": "https://img/a.png"}


class _FakeVid:
    async def generate(self, prompt, duration=5, image_urls=None):
        return {"video_url": "https://vid/a.mp4"}


def _patch_domestic(monkeypatch):
    monkeypatch.setattr("agent.tools.generation.SeedreamProvider", lambda: _FakeSeed())
    monkeypatch.setattr("agent.tools.video_generation.get_video_provider", lambda: _FakeVid())


def test_domestic_pipeline_image_and_video(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    _patch_domestic(monkeypatch)
    run = _enqueue(graph=DOMESTIC_GRAPH, provider="domestic", cost=5.0)
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "done"
    assert after["result"] == ["https://vid/a.mp4"]  # Preview 收的是 Video 产物
    kinds = [c["call_kind"] for c in costs]
    assert "canvas_image" in kinds and "canvas_video" in kinds  # 逐节点记账
    assert frames[-1]["type"] == "pro_run_done"


def test_domestic_cached_generate_skips_seedream(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    called = {"seed": False}

    class _Seed:
        async def generate(self, prompt, image_urls=None):
            called["seed"] = True
            return {"url": "https://img/new.png"}

    monkeypatch.setattr("agent.tools.generation.SeedreamProvider", lambda: _Seed())
    monkeypatch.setattr("agent.tools.video_generation.get_video_provider", lambda: _FakeVid())
    g = json.loads(json.dumps(DOMESTIC_GRAPH))
    for n in g["nodes"]:
        if n["id"] == "g":
            n["cached"] = True
            n["cached_url"] = "https://img/cached.png"
    run = _enqueue(graph=g, provider="domestic", cost=1.5)
    asyncio.run(pipe.process_pro_run_task(run))
    assert called["seed"] is False  # 缓存命中 → 不调 Seedream
    # 只记了视频成本(图缓存)
    assert [c["call_kind"] for c in costs] == ["canvas_video"]


def test_domestic_node_backend_comfyui(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)

    class _FakeCU:
        async def submit(self, graph, *, user_id, run_id):
            return {"task_id": "cu1"}

        async def poll(self, task_id):
            return {"status": "completed", "outputs": ["https://cu/img.png"]}

    monkeypatch.setattr("agent.workers.pro_run_pipeline.get_comfyui_provider", lambda name: _FakeCU())
    monkeypatch.setattr(pipe.config, "COMFYUI_PROVIDER", "fixture")

    def _seed_should_not_be_called():
        raise AssertionError("ComfyUI 后端节点不应调 Seedream")

    monkeypatch.setattr("agent.tools.generation.SeedreamProvider", _seed_should_not_be_called)

    g = {
        "version": 1,
        "nodes": [
            {"id": "p", "type": "Prompt", "params": {"text": "猫"}},
            {"id": "g", "type": "Generate", "params": {"backend": "ComfyUI"}},
            {"id": "pv", "type": "Preview", "params": {}},
        ],
        "edges": [
            {"id": "1", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
            {"id": "2", "source": "g", "sourceHandle": "image", "target": "pv", "targetHandle": "image"},
        ],
    }
    run = _enqueue(graph=g, provider="domestic", cost=1.5)
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "done"
    assert after["result"] == ["https://cu/img.png"]  # 走了 ComfyUI provider
    assert "canvas_comfyui" in [c["call_kind"] for c in costs]  # 记 comfyui 账(非 seedream)


def test_domestic_compose_concats_videos(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    _patch_domestic(monkeypatch)
    composed = {"urls": None}

    async def fake_compose(urls):
        composed["urls"] = list(urls)
        return b"FAKE-MP4-BYTES"

    monkeypatch.setattr("agent.tools.compose.compose_videos", fake_compose)
    # media_root writes under CASCADE_DB_PATH parent (tmp) — real write, fine.
    g = {
        "version": 1,
        "nodes": [
            {"id": "p", "type": "Prompt", "params": {"text": "猫"}},
            {"id": "g", "type": "Generate", "params": {}},
            {"id": "v", "type": "Video", "params": {"duration": 4}},
            {"id": "c", "type": "Compose", "params": {}},
            {"id": "pv", "type": "Preview", "params": {}},
        ],
        "edges": [
            {"id": "1", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
            {"id": "2", "source": "g", "sourceHandle": "image", "target": "v", "targetHandle": "image"},
            {"id": "3", "source": "v", "sourceHandle": "video", "target": "c", "targetHandle": "videos"},
            {"id": "4", "source": "c", "sourceHandle": "video", "target": "pv", "targetHandle": "image"},
        ],
    }
    run = _enqueue(graph=g, provider="domestic", cost=5.0)
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "done"
    assert composed["urls"] == ["https://vid/a.mp4"]  # 合成收到了分镜视频
    assert after["result"] and after["result"][0].startswith("/media/")  # 成片落 /media


def test_domestic_partial_failure_still_outputs(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)

    class _SeedFail:
        async def generate(self, prompt, image_urls=None):
            return {"error": "seedream down"}

    monkeypatch.setattr("agent.tools.generation.SeedreamProvider", lambda: _SeedFail())
    monkeypatch.setattr("agent.tools.video_generation.get_video_provider", lambda: _FakeVid())
    run = _enqueue(graph=DOMESTIC_GRAPH, provider="domestic", cost=5.0)
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    # 图失败 → 视频缺输入跳过 → 零产物 → failed(不自动重试,避免重跑扣费)
    assert after["status"] == "failed"
    # 图失败不记账(没成);视频没调(缺输入)
    assert costs == []


def test_recover_no_prompt_id_requeues(monkeypatch, tmp_path):
    frames, costs = _setup(monkeypatch, tmp_path)
    run = _enqueue()
    # submitted but never got prompt_id (crash between submit and polling write)
    recovered = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    recovered["comfy_prompt_id"] = None
    asyncio.run(pipe.recover_pro_run_task(recovered))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "pending"


def test_worker_blocks_cross_border_provider(monkeypatch, tmp_path):
    """review 修复:worker 使用点(真出境点)再拦跨境 provider。runninghub 行重放 → failed,不 submit。"""
    frames, costs = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "STRICT_CROSS_BORDER_REJECT", True)

    submitted = {"called": False}

    class _NeverSubmit:
        async def submit(self, *a, **k):
            submitted["called"] = True
            return {"task_id": "x"}

        async def poll(self, *a, **k):
            return {"status": "completed", "outputs": ["x"]}

    monkeypatch.setattr("agent.workers.pro_run_pipeline.get_comfyui_provider", lambda name=None: _NeverSubmit())
    run = _enqueue(provider="runninghub")
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "failed"
    assert submitted["called"] is False  # never reached the provider (no egress)
    assert costs == []
    assert frames[-1]["type"] == "pro_run_failed"


def test_worker_cost_guard_refuses_before_submit(monkeypatch, tmp_path):
    """review 修复:worker 在每次 submit 前再核成本闸;超额 → failed,不 submit、不记账。"""
    frames, costs = _setup(monkeypatch, tmp_path)

    async def _raise(user_id, run_id, predicted, **_kw):
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "over cap")

    monkeypatch.setattr("agent.cascade.cost_guard.cost_guard", _raise)
    submitted = {"called": False}

    class _NeverSubmit:
        async def submit(self, *a, **k):
            submitted["called"] = True
            return {"task_id": "x"}

        async def poll(self, *a, **k):
            return {"status": "completed", "outputs": ["x"]}

    monkeypatch.setattr("agent.workers.pro_run_pipeline.get_comfyui_provider", lambda name=None: _NeverSubmit())
    run = _enqueue()
    asyncio.run(pipe.process_pro_run_task(run))
    after = repo.get_pro_run("r1", user_id="u1", thread_id="t1")
    assert after["status"] == "failed"
    assert submitted["called"] is False
    assert costs == []
    assert frames[-1]["type"] == "pro_run_failed"
