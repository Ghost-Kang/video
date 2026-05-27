"""图片生成 task pipeline。

输入:queued node dict (canvas_tools.claim_pending_tasks 返回)
输出:更新 canvas 节点 generation_status + result;notify_user 推送 canvas_updated。
"""

from __future__ import annotations

import time

from agent.config import IMAGE_GEN_PROVIDER
from agent.tools import canvas as canvas_tools
from agent.transport.notify import notify_user
from agent.workers.s3 import download_and_upload, upload_bytes_to_s3


def make_image_provider(name: str):
    """按 provider 名构造 image provider 实例。"""
    from agent.tools.generation import ApimartProvider, GoogleProvider

    if name == "google":
        return GoogleProvider()
    return ApimartProvider()


def get_ref_urls(node: dict) -> list[str]:
    """获取节点的上游参考图 URL 列表。显式 user/thread 走 explicit args。"""
    uid = node["user_id"]
    tid = node["thread_id"]
    all_edges = canvas_tools._load_all_edges(user_id=uid, thread_id=tid)
    parent_ids = [e["source"] for e in all_edges if e["target"] == node["id"]]
    refs: list[str] = []
    for pid in parent_ids:
        parent = canvas_tools._load_node(pid, user_id=uid, thread_id=tid)
        p_url = (parent.get("result") or {}).get("url") if parent else None
        if p_url:
            refs.append(str(p_url))
    return refs


async def process_image_task(node: dict) -> None:
    """处理单个图片生成任务。所有 canvas_tools 调用显式传 user_id/thread_id。"""
    nid = node["id"]
    uid = node["user_id"]
    tid = node["thread_id"]
    provider_name = node.get("image_gen_provider") or IMAGE_GEN_PROVIDER
    prompt = (node.get("result") or {}).get("prompt") or node.get("description", "")

    ref_urls = get_ref_urls(node)

    provider = make_image_provider(provider_name)
    print(f"[Worker] 图片生成 node={nid} provider={provider_name} prompt={prompt[:50]}... refs={len(ref_urls)}")

    t0 = time.time()
    submitted = await provider.submit(prompt, "16:9", "2k", ref_urls if ref_urls else None)
    elapsed = (time.time() - t0) * 1000
    if not submitted.get("task_id"):
        canvas_tools.update_generation_state(nid, "failed", error=submitted.get("error", "submit failed"), user_id=uid, thread_id=tid)
        print(f"[Worker] 提交失败 node={nid} 耗时={elapsed:.0f}ms")
        notify_user(uid, tid)
        return

    canvas_tools.update_generation_state(nid, "polling", task_id=submitted["task_id"], user_id=uid, thread_id=tid)
    print(f"[Worker] 已提交 node={nid} task_id={submitted['task_id']} 耗时={elapsed:.0f}ms")

    result = await provider.poll(submitted["task_id"])

    if result.get("url"):
        s3_url = await download_and_upload(result["url"], nid)
        final_url = s3_url or result["url"]
        canvas_tools.update_generation_state(nid, "done", user_id=uid, thread_id=tid)
        canvas_tools._update_node_result(nid, {"url": final_url, "actual_time": result.get("actual_time", 0)}, user_id=uid, thread_id=tid)
        print(f"[Worker] 生图完成 node={nid} url={final_url[:60]}...")
    elif result.get("image_data"):
        s3_url = upload_bytes_to_s3(result["image_data"], f"{nid}.png")
        if s3_url:
            canvas_tools.update_generation_state(nid, "done", user_id=uid, thread_id=tid)
            canvas_tools._update_node_result(nid, {"url": s3_url, "actual_time": result.get("actual_time", 0)}, user_id=uid, thread_id=tid)
            print(f"[Worker] 生图完成 node={nid} url={s3_url[:60]}...")
        else:
            canvas_tools.update_generation_state(nid, "failed", error="S3 上传失败", user_id=uid, thread_id=tid)
    else:
        is_timeout = result.get("error") == "timeout"
        err = result.get("error", "")
        if is_timeout:
            err = "timeout"
        canvas_tools.update_generation_state(nid, "failed", error=err, user_id=uid, thread_id=tid)
        print(f"[Worker] 生图{'超时' if is_timeout else '失败'} node={nid} {err}")

    notify_user(uid, tid)
