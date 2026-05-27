"""视频生成 task pipeline。"""

from __future__ import annotations

import time

from agent.tools import canvas as canvas_tools
from agent.tools.video_generation import get_video_provider
from agent.transport.notify import notify_user
from agent.workers.image_pipeline import get_ref_urls
from agent.workers.s3 import download_and_upload


async def process_video_task(node: dict) -> None:
    """处理单个视频生成任务。所有 canvas_tools 调用显式传 user_id/thread_id。"""
    nid = node["id"]
    uid = node["user_id"]
    tid = node["thread_id"]
    prompt = (node.get("result") or {}).get("prompt") or node.get("description", "")
    params = node.get("result") or {}
    duration = params.get("duration", 5)
    resolution = params.get("resolution", "720p")
    generate_audio = params.get("generate_audio", True)

    ref_urls = get_ref_urls(node)
    provider = get_video_provider()

    print(
        f"[Worker] 视频生成 node={nid} duration={duration}s res={resolution} "
        f"audio={generate_audio} refs={len(ref_urls)}"
    )

    t0 = time.time()
    submitted = await provider.submit(
        prompt,
        duration=duration,
        resolution=resolution,
        ratio="16:9",
        generate_audio=generate_audio,
        image_urls=ref_urls if ref_urls else None,
    )
    elapsed = (time.time() - t0) * 1000
    if not submitted.get("task_id"):
        canvas_tools.update_generation_state(nid, "failed", error=submitted.get("error", "submit failed"), user_id=uid, thread_id=tid)
        print(f"[Worker] 视频提交失败 node={nid} 耗时={elapsed:.0f}ms")
        notify_user(uid, tid)
        return

    canvas_tools.update_generation_state(nid, "polling", task_id=submitted["task_id"], user_id=uid, thread_id=tid)
    print(f"[Worker] 视频已提交 node={nid} task_id={submitted['task_id']} 耗时={elapsed:.0f}ms")

    result = await provider.poll(submitted["task_id"])

    if result.get("video_url"):
        s3_url = await download_and_upload(result["video_url"], nid, ext="mp4")
        if s3_url:
            canvas_tools.update_generation_state(nid, "done", user_id=uid, thread_id=tid)
            canvas_tools._update_node_result(nid, {"url": s3_url, "actual_time": result.get("actual_time", 0)}, user_id=uid, thread_id=tid)
            print(f"[Worker] 视频完成 node={nid} url={s3_url[:60]}...")
        else:
            canvas_tools.update_generation_state(nid, "failed", error="S3 上传失败", user_id=uid, thread_id=tid)
    else:
        is_timeout = result.get("error") == "timeout"
        canvas_tools.update_generation_state(nid, "failed", error=result.get("error", ""), user_id=uid, thread_id=tid)
        print(f"[Worker] 视频{'超时' if is_timeout else '失败'} node={nid} {result.get('error')}")

    notify_user(uid, tid)
