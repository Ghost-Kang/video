"""workers/generation_worker.py 集成测试。

覆盖:
- `start_workers()` idempotent + 创建 3 个 task
- `_worker_loop` 的 claim → gather → recover → sleep tick 序列
- `_worker_loop` 异常隔离(claim/recover 抛异常不应让 worker 停)
- `_run_with_sem` 异常路径写 failed + notify
- `_recover_one` 4 个分支(google image / missing task_id / video poll / 异常)
- `_apply_poll_result` 4 个 result 分支(url / video_url / image_data / 空)

无限循环用 monkeypatch asyncio.sleep 在 N 次后抛 BaseException 强制退出。
"""

from __future__ import annotations

import asyncio

import pytest

from agent.workers import generation_worker


# ---------- helpers ----------


class _StopLoop(BaseException):
    """BaseException — `except Exception` 不会捕获,可以穿透 worker loop 强制退出。"""

    pass


# 在 monkeypatch 替换之前,先抓一个真 asyncio.sleep 的引用,
# 避免 fake_sleep 内部 yield 控制权时递归调到自己。
_REAL_ASYNCIO_SLEEP = asyncio.sleep


def _make_stop_after(n_sleeps: int):
    """返回一个 sleep stub:被调用 n 次后抛 _StopLoop。每次让出控制权(让 gather 子任务跑)。"""
    state = {"count": 0}

    async def fake_sleep(seconds):
        state["count"] += 1
        if state["count"] > n_sleeps:
            raise _StopLoop
        await _REAL_ASYNCIO_SLEEP(0)

    return fake_sleep, state


@pytest.fixture
def captured_canvas(monkeypatch):
    """stub canvas_tools state writes + notify_user。"""
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

    monkeypatch.setattr(generation_worker.canvas_tools, "update_generation_state", _state)
    monkeypatch.setattr(generation_worker.canvas_tools, "_update_node_result", _result)
    monkeypatch.setattr(generation_worker, "notify_user", _notify)
    return calls


def _task(nid: str = "n1", *, task_type: str = "image", task_id: str | None = None, provider: str = "apimart") -> dict:
    return {
        "id": nid,
        "user_id": "u1",
        "thread_id": "t1",
        "type": task_type,
        "image_gen_provider": provider,
        "generation_task_id": task_id,
        "description": "x",
        "result": {"prompt": "x"},
    }


# ---------- start_workers idempotent ----------


class TestStartWorkers:
    def test_first_call_creates_three_tasks(self, monkeypatch):
        """start_workers 应通过 asyncio.create_task 启动 3 个 worker(image/video/composite)。"""
        created: list = []
        # _started 是 module-level,前一个 test 可能跑过,reset
        monkeypatch.setattr(generation_worker, "_started", False)
        monkeypatch.setattr(generation_worker.asyncio, "create_task", lambda coro: created.append(coro) or coro)
        # 关掉真实 coroutine 避免 warning(我们只 capture)
        # coro 不会被 await,Python 会 warn — 用 close() 主动消毒。
        try:
            generation_worker.start_workers()
            assert len(created) == 3
        finally:
            for coro in created:
                coro.close()

    def test_second_call_is_idempotent(self, monkeypatch):
        created: list = []
        monkeypatch.setattr(generation_worker, "_started", False)
        monkeypatch.setattr(generation_worker.asyncio, "create_task", lambda coro: created.append(coro) or coro)
        try:
            generation_worker.start_workers()
            generation_worker.start_workers()
            assert len(created) == 3, "第二次 start_workers 应是 no-op(idempotent)"
        finally:
            for coro in created:
                coro.close()


# ---------- _worker_loop tick sequence ----------


class TestWorkerLoop:
    def test_no_tasks_just_sleeps(self, captured_canvas, monkeypatch):
        """claim/recover 都返空时,loop 只 sleep 不 process。"""
        monkeypatch.setattr(generation_worker.canvas_tools, "claim_pending_tasks", lambda task_type: [])
        monkeypatch.setattr(generation_worker.canvas_tools, "recover_generation_tasks", lambda task_type: [])

        fake_sleep, state = _make_stop_after(3)
        monkeypatch.setattr(generation_worker.asyncio, "sleep", fake_sleep)

        process_calls: list = []

        async def _process(task):
            process_calls.append(task)

        async def driver():
            try:
                await generation_worker._worker_loop("test", "image", asyncio.Semaphore(5), _process)
            except _StopLoop:
                pass

        asyncio.run(driver())

        assert process_calls == []
        # 跑了 3 个 tick(然后第 4 次 sleep 抛了 _StopLoop)
        assert state["count"] == 4

    def test_claim_returns_tasks_processed_with_semaphore(self, captured_canvas, monkeypatch):
        """claim 返 task 列表 → process 被 gather 调用。"""
        tasks_to_claim = [_task("a"), _task("b"), _task("c")]
        calls = {"count": 0}

        def _claim(task_type):
            calls["count"] += 1
            if calls["count"] == 1:
                return tasks_to_claim
            return []  # 后续 tick 空

        monkeypatch.setattr(generation_worker.canvas_tools, "claim_pending_tasks", _claim)
        monkeypatch.setattr(generation_worker.canvas_tools, "recover_generation_tasks", lambda task_type: [])

        fake_sleep, _state = _make_stop_after(2)
        monkeypatch.setattr(generation_worker.asyncio, "sleep", fake_sleep)

        process_calls: list = []

        async def _process(task):
            process_calls.append(task["id"])

        async def driver():
            try:
                await generation_worker._worker_loop("test", "image", asyncio.Semaphore(5), _process)
            except _StopLoop:
                pass

        asyncio.run(driver())

        assert set(process_calls) == {"a", "b", "c"}
        assert len(process_calls) == 3

    def test_claim_exception_swallowed_loop_continues(self, captured_canvas, monkeypatch):
        """claim_pending_tasks 抛异常 → loop catch + 继续下个 tick(不应停)。"""
        call_log = {"claim": 0, "recover": 0}

        def _claim(task_type):
            call_log["claim"] += 1
            if call_log["claim"] == 1:
                raise RuntimeError("DB locked")
            return []

        def _recover(task_type):
            call_log["recover"] += 1
            return []

        monkeypatch.setattr(generation_worker.canvas_tools, "claim_pending_tasks", _claim)
        monkeypatch.setattr(generation_worker.canvas_tools, "recover_generation_tasks", _recover)

        fake_sleep, _ = _make_stop_after(3)
        monkeypatch.setattr(generation_worker.asyncio, "sleep", fake_sleep)

        async def _process(_t):
            pass

        async def driver():
            try:
                await generation_worker._worker_loop("test", "image", asyncio.Semaphore(5), _process)
            except _StopLoop:
                pass

        asyncio.run(driver())

        # _make_stop_after(3) → sleep 第 4 次抛 → 跑了 4 个完整 tick
        # claim 每 tick 1 次 = 4;recover 跳过 tick 1(claim 抛在 recover 前)= 3
        assert call_log["claim"] == 4
        assert call_log["recover"] == 3

    def test_process_exception_does_not_break_gather(self, captured_canvas, monkeypatch):
        """单个 task 抛异常不影响 batch 的其他 task — gather(return_exceptions=True)。"""
        tasks_to_claim = [_task("ok1"), _task("bad"), _task("ok2")]
        calls = {"count": 0}

        def _claim(task_type):
            calls["count"] += 1
            return tasks_to_claim if calls["count"] == 1 else []

        monkeypatch.setattr(generation_worker.canvas_tools, "claim_pending_tasks", _claim)
        monkeypatch.setattr(generation_worker.canvas_tools, "recover_generation_tasks", lambda task_type: [])

        fake_sleep, _ = _make_stop_after(2)
        monkeypatch.setattr(generation_worker.asyncio, "sleep", fake_sleep)

        success: list = []

        async def _process(task):
            if task["id"] == "bad":
                raise RuntimeError("boom")
            success.append(task["id"])

        async def driver():
            try:
                await generation_worker._worker_loop("test", "image", asyncio.Semaphore(5), _process)
            except _StopLoop:
                pass

        asyncio.run(driver())

        # ok1 + ok2 都跑了
        assert set(success) == {"ok1", "ok2"}
        # bad 走 _run_with_sem 的 except → 写 failed
        assert any(s["nid"] == "bad" and s["status"] == "failed" for s in captured_canvas["state"])
        # 异常那条也 notify(让 UI 刷新 failed 状态)
        assert ("u1", "t1") in captured_canvas["notify"]


# ---------- _run_with_sem ----------


class TestRunWithSem:
    def test_happy_path_calls_process(self, captured_canvas):
        called: list = []

        async def _process(task):
            called.append(task["id"])

        sem = asyncio.Semaphore(2)
        asyncio.run(generation_worker._run_with_sem(sem, _process, _task("n42"), "test"))

        assert called == ["n42"]
        # 没异常 → 不应有 state 写入(那是 pipeline 内部的事)
        assert captured_canvas["state"] == []
        assert captured_canvas["notify"] == []

    def test_exception_writes_failed_and_notifies(self, captured_canvas):
        async def _process(_t):
            raise RuntimeError("processor down")

        sem = asyncio.Semaphore(2)
        asyncio.run(generation_worker._run_with_sem(sem, _process, _task("n7"), "test"))

        assert captured_canvas["state"] == [{
            "nid": "n7", "status": "failed", "task_id": None,
            "error": "processor down", "user_id": "u1", "thread_id": "t1",
        }]
        assert captured_canvas["notify"] == [("u1", "t1")]


# ---------- _recover_one ----------


class TestRecoverOne:
    def test_google_image_reenqueues_as_pending(self, captured_canvas, monkeypatch):
        """Google 用内存 task → 重启后丢失 → 重新标 pending 等下一 tick claim。"""
        # provider not called for Google image branch
        monkeypatch.setattr(
            generation_worker, "make_image_provider", lambda _n: pytest.fail("provider 不应被调"),
        )
        monkeypatch.setattr(
            generation_worker, "get_video_provider", lambda: pytest.fail("video provider 不应被调"),
        )

        task = _task("g1", task_type="image", provider="google", task_id="oldtid")
        asyncio.run(generation_worker._recover_one(task, "image"))

        assert captured_canvas["state"] == [{
            "nid": "g1", "status": "pending", "task_id": None,
            "error": "服务重启,重新提交", "user_id": "u1", "thread_id": "t1",
        }]
        # google 分支不调 notify(等下个 claim tick 再走完整流程)
        assert captured_canvas["notify"] == []

    def test_missing_task_id_marks_failed(self, captured_canvas, monkeypatch):
        """generation_task_id 缺失 → 标 failed,不再 poll。"""
        # 装个 provider 防止 fallthrough 出问题
        class _DummyProvider:
            async def poll(self, tid):
                pytest.fail("不应被调")

        monkeypatch.setattr(generation_worker, "make_image_provider", lambda _n: _DummyProvider())
        task = _task("v1", task_type="image", provider="apimart", task_id=None)

        asyncio.run(generation_worker._recover_one(task, "image"))

        assert captured_canvas["state"] == [{
            "nid": "v1", "status": "failed", "task_id": None,
            "error": "缺少 task_id", "user_id": "u1", "thread_id": "t1",
        }]

    def test_image_provider_poll_url_marks_done(self, captured_canvas, monkeypatch):
        class _Provider:
            async def poll(self, tid):
                assert tid == "TID42"
                return {"url": "https://done.png", "actual_time": 7}

        monkeypatch.setattr(generation_worker, "make_image_provider", lambda _n: _Provider())
        task = _task("i1", task_type="image", provider="apimart", task_id="TID42")

        asyncio.run(generation_worker._recover_one(task, "image"))

        # _apply_poll_result 走 url 分支
        assert captured_canvas["state"][-1]["status"] == "done"
        assert captured_canvas["result"][0]["updates"] == {"url": "https://done.png", "actual_time": 7}
        assert captured_canvas["notify"] == [("u1", "t1")]

    def test_video_uses_video_provider(self, captured_canvas, monkeypatch):
        class _Provider:
            async def poll(self, tid):
                return {"video_url": "https://v.mp4"}

        monkeypatch.setattr(generation_worker, "get_video_provider", lambda: _Provider())
        monkeypatch.setattr(
            generation_worker, "make_image_provider", lambda _n: pytest.fail("image provider 不应被调"),
        )
        task = _task("v1", task_type="video", task_id="VTID")

        asyncio.run(generation_worker._recover_one(task, "video"))

        assert captured_canvas["state"][-1]["status"] == "done"
        assert captured_canvas["result"][0]["updates"]["url"] == "https://v.mp4"

    def test_poll_exception_swallowed(self, captured_canvas, monkeypatch, capsys):
        """poll 抛异常 — _recover_one 应 catch + log,不 propagate。"""
        class _ExplodingProvider:
            async def poll(self, tid):
                raise RuntimeError("upstream gone")

        monkeypatch.setattr(generation_worker, "make_image_provider", lambda _n: _ExplodingProvider())
        task = _task("e1", task_type="image", provider="apimart", task_id="EXPLODE")

        # 不应 raise
        asyncio.run(generation_worker._recover_one(task, "image"))

        # 没 state 写入,因为 exception 在 poll 调用前发生 → 跳过 _apply_poll_result
        assert captured_canvas["state"] == []
        # log 应有异常字样
        captured = capsys.readouterr()
        assert "异常" in captured.out


# ---------- _apply_poll_result branches ----------


class TestApplyPollResult:
    def test_url_branch(self, captured_canvas):
        task = _task("n1")
        generation_worker._apply_poll_result(task, {"url": "https://x.png", "actual_time": 4})

        assert captured_canvas["state"][-1]["status"] == "done"
        assert captured_canvas["result"][0]["updates"] == {"url": "https://x.png", "actual_time": 4}
        assert captured_canvas["notify"] == [("u1", "t1")]

    def test_video_url_branch(self, captured_canvas):
        task = _task("n2")
        generation_worker._apply_poll_result(task, {"video_url": "https://x.mp4", "actual_time": 9})

        assert captured_canvas["state"][-1]["status"] == "done"
        assert captured_canvas["result"][0]["updates"]["url"] == "https://x.mp4"
        assert captured_canvas["result"][0]["updates"]["actual_time"] == 9

    def test_image_data_branch_uploads_to_s3(self, captured_canvas, monkeypatch):
        captured_upload: dict = {}

        def _upload(data, filename):
            captured_upload["data"] = data
            captured_upload["filename"] = filename
            return "https://s3/from_bytes.png"

        monkeypatch.setattr(generation_worker, "upload_bytes_to_s3", _upload)

        task = _task("n3")
        generation_worker._apply_poll_result(task, {"image_data": b"\x89PNG"})

        assert captured_upload == {"data": b"\x89PNG", "filename": "n3.png"}
        assert captured_canvas["state"][-1]["status"] == "done"
        assert captured_canvas["result"][0]["updates"] == {"url": "https://s3/from_bytes.png"}

    def test_image_data_branch_s3_failure_silent(self, captured_canvas, monkeypatch):
        """S3 fail 时 _apply_poll_result 既不标 done 也不标 failed — 静默(由下次 recover 处理)。

        这是当前实现的行为;若想改成 mark failed 需要修 worker 代码,本测试 lock 现状。
        """
        monkeypatch.setattr(generation_worker, "upload_bytes_to_s3", lambda d, n: None)
        task = _task("n4")
        generation_worker._apply_poll_result(task, {"image_data": b"X"})

        assert captured_canvas["state"] == []
        assert captured_canvas["result"] == []
        # notify 仍发(让 UI 知道 polling 推进)
        assert captured_canvas["notify"] == [("u1", "t1")]

    def test_empty_result_marks_failed(self, captured_canvas):
        task = _task("n5")
        generation_worker._apply_poll_result(task, {"error": "timeout"})

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == "timeout"

    def test_empty_result_passthrough_error(self, captured_canvas):
        task = _task("n6")
        generation_worker._apply_poll_result(task, {"error": "5xx_from_provider"})

        assert captured_canvas["state"][-1]["error"] == "5xx_from_provider"

    def test_empty_result_no_error_string(self, captured_canvas):
        """result 是空 dict — error 也缺失 → 写空 string。"""
        task = _task("n7")
        generation_worker._apply_poll_result(task, {})

        assert captured_canvas["state"][-1]["status"] == "failed"
        assert captured_canvas["state"][-1]["error"] == ""
