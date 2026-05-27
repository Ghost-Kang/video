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
from agent.tools.video_generation import get_video_provider
from agent.transport.notify import notify_user
from agent.workers.canvas_context import setup_canvas_context
from agent.workers.composite_pipeline import process_composite_task
from agent.workers.image_pipeline import make_image_provider, process_image_task
from agent.workers.s3 import upload_bytes_to_s3
from agent.workers.video_pipeline import process_video_task


IMAGE_CONCURRENCY = 5
VIDEO_CONCURRENCY = 2
COMPOSITE_CONCURRENCY = 1
TICK_INTERVAL_SEC = 2

_started = False


def start_workers() -> None:
    """启动 image / video / composite 三个独立 worker task。Idempotent。"""
    global _started
    if _started:
        return
    _started = True
    asyncio.create_task(_image_worker())
    asyncio.create_task(_video_worker())
    asyncio.create_task(_composite_worker())


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
    """semaphore-bounded 单任务执行。异常写回 canvas + notify。"""
    async with sem:
        t0 = time.time()
        nid = task.get("id", "?")
        try:
            setup_canvas_context(task)
            await process(task)
            dt = (time.time() - t0) * 1000
            print(f"[Worker:{label}] 完成 node={nid[:16]} 耗时={dt:.0f}ms")
        except Exception as e:
            dt = (time.time() - t0) * 1000
            print(f"[Worker:{label}] 任务异常 node={nid[:16]} 耗时={dt:.0f}ms error={e}")
            canvas_tools.update_generation_state(task["id"], "failed", error=str(e))
            notify_user(task.get("user_id", ""), task.get("thread_id", ""))


# ---------- recovery ----------


async def _recover_one(task: dict, task_type: str) -> None:
    """处理一个 submitted/polling 状态的中断任务。"""
    nid = task["id"]
    provider_name = task.get("image_gen_provider") or IMAGE_GEN_PROVIDER
    if task_type == "image" and provider_name == "google":
        # Google 用内存 task,重启后丢失 → 重新入队
        print(f"[Worker:recover] Google 任务重入队 node={nid[:16]}")
        canvas_tools.update_generation_state(nid, "pending", error="服务重启,重新提交")
        return

    print(f"[Worker:recover] 续轮询 node={nid[:16]} type={task_type} provider={provider_name}")
    try:
        setup_canvas_context(task)
        provider = get_video_provider() if task_type == "video" else make_image_provider(provider_name)
        tid = task.get("generation_task_id")
        if not tid:
            canvas_tools.update_generation_state(nid, "failed", error="缺少 task_id")
            return
        result = await provider.poll(tid)
        setup_canvas_context(task)
        _apply_poll_result(task, result)
    except Exception as e:
        print(f"[Worker:recover] 异常 node={nid[:16]}: {e}")


def _apply_poll_result(task: dict, result: dict) -> None:
    """将续轮询结果写入节点。"""
    nid = task["id"]
    if result.get("url"):
        canvas_tools.update_generation_state(nid, "done")
        canvas_tools._update_node_result(nid, {"url": result["url"], "actual_time": result.get("actual_time", 0)})
        print(f"[Worker:recover] 完成 node={nid} url={result['url'][:60]}...")
    elif result.get("video_url"):
        canvas_tools.update_generation_state(nid, "done")
        canvas_tools._update_node_result(
            nid, {"url": result["video_url"], "actual_time": result.get("actual_time", 0)}
        )
        print(f"[Worker:recover] 完成 node={nid}")
    elif result.get("image_data"):
        s3_url = upload_bytes_to_s3(result["image_data"], f"{nid}.png")
        if s3_url:
            canvas_tools.update_generation_state(nid, "done")
            canvas_tools._update_node_result(nid, {"url": s3_url})
    else:
        is_timeout = result.get("error") == "timeout"
        canvas_tools.update_generation_state(nid, "failed", error=result.get("error", ""))
        print(f"[Worker:recover] {'超时' if is_timeout else '失败'} node={nid}")
    notify_user(task["user_id"], task["thread_id"])
