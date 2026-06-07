"""生成任务调度 — 按 task type 拆 3 个 worker(Founder Decision-2 2026-05-26)。

之前的 `_generation_worker` 单 loop 串行处理 image/video/composite,导致一个 60s
视频轮询会卡所有图片提交。本版拆为:

    image_worker     — claim type='image' 的 pending,Semaphore(5) 并发处理
    video_worker     — claim type='video',Semaphore(2)
    composite_worker — claim type='composite',串行(ffmpeg 本地 CPU 密集)

`start_workers()` 启动 3 个 asyncio.Task,启动一次后由 module-level _started 标志 idempotent。

重启恢复(`recover_generation_tasks`)也按 type 分配到对应 worker。
"""

from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

from agent.config import IMAGE_GEN_PROVIDER
from agent.tools import canvas as canvas_tools
from agent.tools.canvas_persistence import pro_runs_repo
from agent.tools.video_generation import get_video_provider
from agent.transport.notify import notify_user
from agent.workers.composite_pipeline import process_composite_task
from agent.workers.image_pipeline import make_image_provider, process_image_task
from agent.workers.pro_run_pipeline import process_pro_run_task, recover_pro_run_task
from agent.workers.s3 import upload_bytes_to_s3
from agent.workers.video_pipeline import process_video_task


IMAGE_CONCURRENCY = 5
VIDEO_CONCURRENCY = 2
COMPOSITE_CONCURRENCY = 1
PRO_RUN_CONCURRENCY = 2  # ComfyUI 整图;self-host 单卡时 ComfyUI 自身队列再串行化
TICK_INTERVAL_SEC = 2

_started = False


def start_workers() -> None:
    """启动 image / video / composite / pro_run 四个独立 worker task。Idempotent。"""
    global _started
    if _started:
        return
    _started = True
    asyncio.create_task(_image_worker())
    asyncio.create_task(_video_worker())
    asyncio.create_task(_composite_worker())
    asyncio.create_task(_pro_run_worker())


# 兼容旧名:server.py + tests monkeypatch 用的是 _start_worker
def start_worker() -> None:  # pragma: no cover - thin alias
    start_workers()


# ---------- per-type worker loops ----------


async def _image_worker() -> None:
    sem = asyncio.Semaphore(IMAGE_CONCURRENCY)
    await _worker_loop("image", "image", sem, process_image_task)


async def _video_worker() -> None:
    sem = asyncio.Semaphore(VIDEO_CONCURRENCY)
    await _worker_loop("video", "video", sem, process_video_task)


async def _composite_worker() -> None:
    sem = asyncio.Semaphore(COMPOSITE_CONCURRENCY)
    await _worker_loop("composite", "composite", sem, process_composite_task)


# ---------- Pro 计算图 worker(pro_runs 表,独立于 canvas_nodes) ----------
# 注:不能复用 _worker_loop —— 它硬编码 canvas_tools.claim_pending_tasks(canvas_nodes)。
# pro_runs 是另一张表、另一套 id(run_id),故单独成 loop。


async def _pro_run_worker() -> None:
    sem = asyncio.Semaphore(PRO_RUN_CONCURRENCY)
    print(f"[Worker:pro_run] 启动 (concurrency={PRO_RUN_CONCURRENCY})")
    tick = 0
    while True:
        tick += 1
        try:
            runs = pro_runs_repo.claim_pending_pro_runs()
            if runs:
                print(f"[Worker:pro_run] tick={tick} 认领 {len(runs)}: {[r['run_id'][:12] for r in runs]}")
                await asyncio.gather(
                    *(_run_pro_with_sem(sem, r) for r in runs), return_exceptions=True
                )
            recovered = pro_runs_repo.recover_pro_runs()
            if recovered:
                print(f"[Worker:pro_run] tick={tick} 恢复 {len(recovered)} 个中断计算图")
                for r in recovered:
                    try:
                        await recover_pro_run_task(r)
                    except Exception as e:  # noqa: BLE001
                        print(f"[Worker:pro_run] 恢复异常 run={r['run_id'][:16]}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"[Worker:pro_run] 调度异常: {e}")
        await asyncio.sleep(TICK_INTERVAL_SEC)


async def _run_pro_with_sem(sem: asyncio.Semaphore, run: dict) -> None:
    """semaphore-bounded 单 run 执行。pipeline 自处理预期错误;这里兜底未预期异常 → 重试/失败。"""
    async with sem:
        rid = run.get("run_id", "?")
        uid = run.get("user_id", "")
        tid = run.get("thread_id", "")
        try:
            await process_pro_run_task(run)
        except Exception as e:  # noqa: BLE001
            print(f"[Worker:pro_run] 任务异常 run={rid[:16]} error={e}")
            retried = pro_runs_repo.schedule_pro_run_retry(rid, str(e), user_id=uid, thread_id=tid)
            if not retried:
                pro_runs_repo.update_pro_run_state(rid, "failed", user_id=uid, thread_id=tid, error=str(e))


# ---------- shared loop body ----------


async def _worker_loop(
    label: str,
    task_type: str,
    semaphore: asyncio.Semaphore,
    process: Callable[[dict], Awaitable[None]],
) -> None:
    """单 type 的 tick loop:claim → gather(with sem) → recover → sleep。

    异常隔离:单 task 失败不阻塞整个 worker。
    """
    print(f"[Worker:{label}] 启动 (concurrency={semaphore._value})")
    tick = 0
    while True:
        tick += 1
        t_tick = time.time()
        try:
            tasks = canvas_tools.claim_pending_tasks(task_type)
            if tasks:
                print(f"[Worker:{label}] tick={tick} 认领 {len(tasks)}: {[t['id'][:12] for t in tasks]}")
                await asyncio.gather(
                    *(_run_with_sem(semaphore, process, t, label) for t in tasks),
                    return_exceptions=True,
                )

            recovered = canvas_tools.recover_generation_tasks(task_type)
            if recovered:
                print(f"[Worker:{label}] tick={tick} 恢复 {len(recovered)} 个中断任务")
                for task in recovered:
                    await _recover_one(task, task_type)

            dt = (time.time() - t_tick) * 1000
            if tasks or recovered:
                print(f"[Worker:{label}] tick={tick} 完成 耗时={dt:.0f}ms")

        except Exception as e:
            print(f"[Worker:{label}] 调度异常: {e}")

        await asyncio.sleep(TICK_INTERVAL_SEC)


async def _run_with_sem(
    sem: asyncio.Semaphore,
    process: Callable[[dict], Awaitable[None]],
    task: dict,
    label: str,
) -> None:
    """semaphore-bounded 单任务执行。异常写回 canvas + notify。

    pipeline 自己显式传 user/thread,这里只兜底异常 → update_generation_state 也显式传。
    """
    async with sem:
        t0 = time.time()
        nid = task.get("id", "?")
        uid = task.get("user_id", "")
        tid = task.get("thread_id", "")
        try:
            await process(task)
            dt = (time.time() - t0) * 1000
            print(f"[Worker:{label}] 完成 node={nid[:16]} 耗时={dt:.0f}ms")
        except Exception as e:
            dt = (time.time() - t0) * 1000
            print(f"[Worker:{label}] 任务异常 node={nid[:16]} 耗时={dt:.0f}ms error={e}")
            retried = canvas_tools.schedule_generation_retry(task["id"], str(e), user_id=uid, thread_id=tid)
            if not retried:
                canvas_tools.update_generation_state(task["id"], "failed", error=str(e), user_id=uid, thread_id=tid)
            notify_user(uid, tid)


# ---------- recovery ----------


async def _recover_one(task: dict, task_type: str) -> None:
    """处理一个 submitted/polling 状态的中断任务。所有 canvas_tools 调用显式传 user/thread。"""
    nid = task["id"]
    uid = task["user_id"]
    tid = task["thread_id"]
    provider_name = task.get("image_gen_provider") or IMAGE_GEN_PROVIDER
    if task_type == "image" and provider_name == "google":
        # Google 用内存 task,重启后丢失 → 重新入队
        print(f"[Worker:recover] Google 任务重入队 node={nid[:16]}")
        canvas_tools.update_generation_state(nid, "pending", error="服务重启,重新提交", user_id=uid, thread_id=tid)
        return

    print(f"[Worker:recover] 续轮询 node={nid[:16]} type={task_type} provider={provider_name}")
    try:
        provider = get_video_provider() if task_type == "video" else make_image_provider(provider_name)
        generation_tid = task.get("generation_task_id")
        if not generation_tid:
            canvas_tools.update_generation_state(nid, "failed", error="缺少 task_id", user_id=uid, thread_id=tid)
            return
        result = await provider.poll(generation_tid)
        _apply_poll_result(task, result)
    except Exception as e:
        print(f"[Worker:recover] 异常 node={nid[:16]}: {e}")
        retried = canvas_tools.schedule_generation_retry(nid, str(e), user_id=uid, thread_id=tid)
        if retried:
            notify_user(uid, tid)


def _apply_poll_result(task: dict, result: dict) -> None:
    """将续轮询结果写入节点。"""
    nid = task["id"]
    uid = task["user_id"]
    tid = task["thread_id"]
    if result.get("url"):
        canvas_tools.update_generation_state(nid, "done", user_id=uid, thread_id=tid)
        canvas_tools._update_node_result(nid, {"url": result["url"], "actual_time": result.get("actual_time", 0)}, user_id=uid, thread_id=tid)
        print(f"[Worker:recover] 完成 node={nid} url={result['url'][:60]}...")
    elif result.get("video_url"):
        canvas_tools.update_generation_state(nid, "done", user_id=uid, thread_id=tid)
        canvas_tools._update_node_result(
            nid, {"url": result["video_url"], "actual_time": result.get("actual_time", 0)}, user_id=uid, thread_id=tid,
        )
        print(f"[Worker:recover] 完成 node={nid}")
    elif result.get("image_data"):
        s3_url = upload_bytes_to_s3(result["image_data"], f"{nid}.png")
        if s3_url:
            canvas_tools.update_generation_state(nid, "done", user_id=uid, thread_id=tid)
            canvas_tools._update_node_result(nid, {"url": s3_url}, user_id=uid, thread_id=tid)
    else:
        is_timeout = result.get("error") == "timeout"
        canvas_tools.update_generation_state(nid, "failed", error=result.get("error", ""), user_id=uid, thread_id=tid)
        print(f"[Worker:recover] {'超时' if is_timeout else '失败'} node={nid}")
    notify_user(uid, tid)
