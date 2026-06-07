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
