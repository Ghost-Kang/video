"""视频生成 — Seedance 2.0 (Volcengine Ark)"""

from __future__ import annotations

import asyncio
import time

from volcenginesdkarkruntime import Ark

from agent.config import ARK_API_KEY, ARK_BASE_URL, ARK_VIDEO_MODEL


class SeedanceProvider:
    """Seedance 2.0 视频生成，submit + poll 模式。"""

    def __init__(self):
        self._client = Ark(base_url=ARK_BASE_URL, api_key=ARK_API_KEY)

    async def submit(
        self,
        prompt: str,
        duration: int = 5,
        ratio: str = "16:9",
        resolution: str = "720p",
        generate_audio: bool = True,
        image_urls: list[str] | None = None,
        video_urls: list[str] | None = None,
    ) -> dict:
        """提交生视频任务，返回 {task_id} 或 {error}。"""
        content: list[dict] = [{"type": "text", "text": prompt}]
        if image_urls:
            for url in image_urls:
                content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
        if video_urls:
            for url in video_urls:
                content.append({"type": "video_url", "video_url": {"url": url}, "role": "reference_video"})

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._client.content_generation.tasks.create(
                    model=ARK_VIDEO_MODEL,
                    content=content,
                    generate_audio=generate_audio,
                    ratio=ratio,
                    resolution=resolution,
                    duration=duration,
                    watermark=False,
                ),
            )
            print(f"[Seedance提交] task_id={result.id} model={ARK_VIDEO_MODEL} duration={duration}s resolution={resolution} ratio={ratio} audio={generate_audio} images={len(image_urls or [])} videos={len(video_urls or [])}")
            return {"task_id": result.id}
        except Exception as e:
            return {"error": f"Seedance 提交失败: {e}"}

    async def poll(self, task_id: str, interval: int = 30, timeout: int = 900) -> dict:
        """轮询直到完成，返回 {video_url, actual_time} 或 {error}。"""
        t0 = time.time()
        deadline = t0 + timeout
        attempt = 0

        while time.time() < deadline:
            await asyncio.sleep(interval)
            attempt += 1
            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._client.content_generation.tasks.get(task_id=task_id),
                )
            except Exception as e:
                print(f"[Seedance轮询] task={task_id} 第{attempt}次异常: {e}")
                continue

            status = result.status
            print(f"[Seedance轮询] task={task_id} 第{attempt}次 status={status}")
            if status == "succeeded":
                video_url = result.content.video_url if result.content else None
                if video_url:
                    actual_time = time.time() - t0
                    return {"video_url": video_url, "actual_time": actual_time}
                return {"error": "Seedance 完成但无视频 URL"}
            elif status == "failed":
                error = str(result.error) if hasattr(result, "error") and result.error else "unknown"
                return {"error": f"Seedance 任务失败: {error}"}

        print(f"[Seedance轮询] task={task_id} 超时（{timeout}s）")
        return {"error": "timeout", "task_id": task_id}

    async def poll_all(self, tasks: dict[str, str]) -> dict[str, dict]:
        """并行轮询多个任务。"""
        results = {}

        async def _poll_one(nid: str, tid: str):
            results[nid] = await self.poll(tid)

        await asyncio.gather(*(_poll_one(nid, tid) for nid, tid in tasks.items()))
        return results

    async def generate(
        self,
        prompt: str,
        duration: int = 5,
        ratio: str = "16:9",
        image_urls: list[str] | None = None,
    ) -> dict:
        """便捷方法：submit + poll。"""
        submitted = await self.submit(prompt, duration=duration, ratio=ratio, image_urls=image_urls)
        if "error" in submitted:
            return submitted
        return await self.poll(submitted["task_id"])


def get_video_provider() -> SeedanceProvider:
    return SeedanceProvider()
