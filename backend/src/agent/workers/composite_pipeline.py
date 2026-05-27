"""视频合成 task pipeline:收集上游 video → ffmpeg 拼接 → S3。"""

from __future__ import annotations

from agent.tools import canvas as canvas_tools
from agent.tools.compose import compose_videos
from agent.tools.s3_upload import upload_bytes
from agent.transport.notify import notify_user
from agent.workers.canvas_context import setup_canvas_context


async def process_composite_task(node: dict) -> None:
    nid = node["id"]
    setup_canvas_context(node)

    edges = canvas_tools._load_all_edges()
    parent_ids = [e["source"] for e in edges if e["target"] == nid]
    urls: list[str] = []
    for pid in parent_ids:
        parent = canvas_tools._load_node(pid)
        if parent and parent["type"] == "video":
            p_url = (parent.get("result") or {}).get("url")
            if p_url:
                urls.append(str(p_url))

    if len(urls) < 1:
        canvas_tools.update_generation_state(nid, "failed", error="没有可拼接的视频")
        print(f"[Worker] 合成失败 node={nid} 没有视频")
        notify_user(node["user_id"], node["thread_id"])
        return

    print(f"[Worker] 合成 node={nid} 合并 {len(urls)} 个视频...")
    result_bytes = await compose_videos(urls)
    if not result_bytes:
        canvas_tools.update_generation_state(nid, "failed", error="ffmpeg 合成失败")
        print(f"[Worker] 合成失败 node={nid} ffmpeg 失败")
        notify_user(node["user_id"], node["thread_id"])
        return

    s3_url = upload_bytes(result_bytes, "composite.mp4")
    if not s3_url:
        canvas_tools.update_generation_state(nid, "failed", error="S3 上传失败")
        print(f"[Worker] 合成失败 node={nid} S3 失败")
        notify_user(node["user_id"], node["thread_id"])
        return

    canvas_tools.update_generation_state(nid, "done")
    canvas_tools._update_node_result(nid, {"url": s3_url, "clips": len(urls)})
    print(f"[Worker] 合成完成 node={nid} url={s3_url[:60]}...")
    notify_user(node["user_id"], node["thread_id"])
