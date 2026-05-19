"""Seedance 2.0 视频生成测试（Volcengine Ark）"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv
from volcenginesdkarkruntime import Ark

from agent.config import ARK_API_KEY, ARK_BASE_URL, ARK_VIDEO_MODEL

_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


def _client():
    return Ark(base_url=ARK_BASE_URL, api_key=ARK_API_KEY)


def _submit(prompt: str, *, image_urls: list[str] | None = None,
            ratio: str = "16:9", duration: int = 5) -> str:
    """提交生视频任务，返回 task_id。"""
    client = _client()
    content: list[dict] = [{"type": "text", "text": prompt}]
    if image_urls:
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})

    result = client.content_generation.tasks.create(
        model=ARK_VIDEO_MODEL,
        content=content,
        generate_audio=True,
        ratio=ratio,
        duration=duration,
        watermark=False,
    )
    print(f"[提交] task_id={result.id} model={ARK_VIDEO_MODEL}")
    return result.id


def _poll(task_id: str, interval: int = 15, timeout: int = 600) -> dict:
    """轮询直到完成或超时，返回 {url, ...} 或 {error}。"""
    client = _client()
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        result = client.content_generation.tasks.get(task_id=task_id)
        status = result.status
        attempt += 1
        print(f"[轮询] #{attempt} status={status} task_id={task_id}")
        if status == "succeeded":
            video_url = result.content.video_url if result.content else None
            print(f"  video_url: {str(video_url)[:80] if video_url else 'N/A'}...")
            return {"status": "succeeded", "video_url": video_url, "data": result}
        elif status == "failed":
            error = str(result.error) if hasattr(result, "error") else "unknown"
            print(f"  失败: {error}")
            return {"status": "failed", "error": error}
        time.sleep(interval)
    return {"status": "timeout", "task_id": task_id}


def test_text_to_video():
    """纯文本生视频"""
    task_id = _submit(
        "一只柴犬在草地上奔跑，阳光明媚，慢动作，4K画质",
        duration=5,
    )
    print(f"task_id: {task_id}")
    result = _poll(task_id)
    if result["status"] == "succeeded":
        print(f"[成功] video: {result.get('video_url', 'N/A')}")
        print(f"[成功] audio: {result.get('audio_url', 'N/A')}")
    else:
        print(f"[结果] {result['status']}: {result.get('error', result.get('task_id', ''))}")


def test_ref_video():
    """带参考图的生视频（用上次生成的帧做参考）"""
    prompts = [
        "一只橘猫坐在窗台上看夕阳，慵懒地打了个哈欠，暖色调",
        "赛博朋克城市夜景，霓虹灯闪烁，雨滴从天空落下",
    ]

    for i, prompt in enumerate(prompts):
        print(f"\n{'='*50}")
        print(f"测试 {i+1}: {prompt[:40]}...")
        task_id = _submit(prompt, duration=5)
        result = _poll(task_id)
        if result["status"] == "succeeded":
            print(f"  视频: {result.get('video_url', 'N/A')}")
        else:
            print(f"  失败: {result['status']}")


async def _test_async():
    """异步封装：submit + poll（为后续集成做准备）"""
    loop = asyncio.get_running_loop()

    task_id = await loop.run_in_executor(
        None, lambda: _submit("海浪拍打礁石，慢动作，电影质感", duration=5)
    )
    print(f"async task_id: {task_id}")

    result = await loop.run_in_executor(
        None, lambda: _poll(task_id, interval=15, timeout=600)
    )
    if result["status"] == "succeeded":
        print(f"async 成功 video_url: {result.get('video_url', 'N/A')}")
    else:
        print(f"async 失败: {result['status']}")


def test_async():
    """异步封装测试"""
    asyncio.run(_test_async())


if __name__ == "__main__":
    print("=" * 50)
    print("测试 1: 纯文本生视频")
    print("=" * 50)
    test_text_to_video()
