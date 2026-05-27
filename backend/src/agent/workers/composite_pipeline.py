"""视频合成 task pipeline:收集上游 video → ffmpeg 拼接 → S3。"""

from __future__ import annotations

from agent.tools import canvas as canvas_tools
from agent.tools.compose import compose_videos
from agent.tools.s3_upload import upload_bytes
from agent.transport.notify import notify_user


async def process_composite_task(node: dict) -> None:
    """合成 task。所有 canvas_tools 调用显式传 user_id/thread_id。"""
    nid = node["id"]
    uid = node["user_id"]
    tid = node["thread_id"]

    edges = canvas_tools._load_all_edges(user_id=uid, thread_id=tid)
    parent_ids = [e["source"] for e in edges if e["target"] == nid]
    urls: list[str] = []
    for pid in parent_ids:
        parent = canvas_tools._load_node(pid, user_id=uid, thread_id=tid)
        if parent and parent["type"] == "video":
            p_url = (parent.get("result") or {}).get("url")
            if p_url:
                urls.append(str(p_url))

    if len(urls) < 1:
        canvas_tools.update_generation_state(nid, "failed", error="没有可拼接的视频", user_id=uid, thread_id=tid)
        print(f"[Worker] 合成失败 node={nid} 没有视频")
        notify_user(uid, tid)
        return

    print(f"[Worker] 合成 node={nid} 合并 {len(urls)} 个视频...")
    result_bytes = await compose_videos(urls)
    if not result_bytes:
        canvas_tools.update_generation_state(nid, "failed", error="ffmpeg 合成失败", user_id=uid, thread_id=tid)
        print(f"[Worker] 合成失败 node={nid} ffmpeg 失败")
        notify_user(uid, tid)
        return

    s3_url = upload_bytes(result_bytes, "composite.mp4")
    if not s3_url:
        canvas_tools.update_generation_state(nid, "failed", error="S3 上传失败", user_id=uid, thread_id=tid)
        print(f"[Worker] 合成失败 node={nid} S3 失败")
        notify_user(uid, tid)
        return

    canvas_tools.update_generation_state(nid, "done", user_id=uid, thread_id=tid)
    canvas_tools._update_node_result(nid, {"url": s3_url, "clips": len(urls)}, user_id=uid, thread_id=tid)
    print(f"[Worker] 合成完成 node={nid} url={s3_url[:60]}...")
    notify_user(uid, tid)
