"""图片生成 — Provider 抽象层

统一异步接口：submit() 返回 task_id，poll() 返回结果。
"""

from __future__ import annotations

import asyncio
import io
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import httpx
import requests
from PIL import Image as PILImage

from agent.config import (
    ARK_API_KEY,
    ARK_BASE_URL,
    IMAGE_GEN_API_KEY,
    IMAGE_GEN_BASE_URL,
    IMAGE_GEN_MODEL,
    IMAGE_GEN_GOOGLE_MODEL,
    IMAGE_GEN_PROVIDER,
    GOOGLE_API_KEY,
    SEEDREAM_MODEL,
)


# ─── ApimartProvider ────────────────────────────────────────────────────────────


class ApimartProvider:
    """Apimart (OpenAI 兼容) 图片生成，异步提交 + 轮询。"""

    def __init__(self):
        self._generate_url = f"{IMAGE_GEN_BASE_URL}/v1/images/generations"
        self._task_url = f"{IMAGE_GEN_BASE_URL}/v1/tasks"
        self._auth = {"Authorization": f"Bearer {IMAGE_GEN_API_KEY}"}
        self._json_headers = {**self._auth, "Content-Type": "application/json"}

    async def submit(
        self,
        prompt: str,
        size: str = "16:9",
        resolution: str = "2k",
        image_urls: list[str] | None = None,
    ) -> dict:
        """提交生图，返回 {task_id} 或 {error}。"""
        payload = {"model": IMAGE_GEN_MODEL, "prompt": prompt, "n": 1, "size": size, "resolution": resolution}
        if image_urls:
            payload["image_urls"] = image_urls

        loop = asyncio.get_running_loop()
        try:
            resp = await loop.run_in_executor(
                None, lambda: requests.post(self._generate_url, json=payload, headers=self._json_headers, timeout=30),
            )
            data = resp.json()
        except Exception as e:
            return {"error": f"提交失败: {e}"}

        if data.get("code") != 200:
            return {"error": f"生图提交失败: {data}"}
        return {"task_id": data["data"][0]["task_id"]}

    async def poll(self, task_id: str) -> dict:
        """异步轮询（120s 超时，每 20s 一次），返回 {url, actual_time} 或 {error}。"""
        POLL_MAX = 6  # 120s / 20s
        async with httpx.AsyncClient(timeout=15) as client:
            for i in range(POLL_MAX):
                await asyncio.sleep(20)
                try:
                    resp = await client.get(
                        f"{self._task_url}/{task_id}",
                        headers=self._json_headers,
                        params={"language": "zh"},
                    )
                    task = resp.json()
                except Exception as e:
                    print(f"[Apimart轮询] task={task_id} 第{i+1}次异常: {e}")
                    return {"error": f"轮询异常: {e}"}

                print(f"[Apimart轮询] task={task_id} 第{i+1}/{POLL_MAX}次 code={task.get('code')}")
                if task.get("code") != 200:
                    continue
                status = task["data"].get("status")
                if status == "completed":
                    images = task["data"]["result"]["images"]
                    url = images[0]["url"] if isinstance(images[0]["url"], str) else images[0]["url"][0]
                    print(f"[Apimart轮询] task={task_id} 完成 第{i+1}次")
                    return {"url": url, "actual_time": task["data"].get("actual_time", 0)}
                if status == "failed":
                    return {"error": f"生图任务失败: {task_id}"}

        print(f"[Apimart轮询] task={task_id} 超时（{POLL_MAX}次/120s）")
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
        size: str = "16:9",
        resolution: str = "2k",
        image_urls: list[str] | None = None,
    ) -> dict:
        """便捷方法：submit + poll。"""
        submitted = await self.submit(prompt, size, resolution, image_urls)
        if "error" in submitted:
            return submitted
        return await self.poll(submitted["task_id"])


# ─── SeedreamProvider ───────────────────────────────────────────────────────────


class SeedreamProvider:
    """火山豆包 Seedream 图像生成(方舟 ARK)。**复用 ARK_API_KEY**(同分析/改写/视频
    Seedance,境内官方、合规一致、无需独立密钥)。同步 images API:单次 POST 直接返回
    图片 URL(不像 apimart 的 submit+poll)。接口对齐 ApimartProvider.generate 以便
    `_make_image_provider` 透明替换。"""

    # (ratio, resolution) → Seedream 像素 size。doubao-seedream-4.0 范围 [1280x720, 4096x4096]。
    _SIZE_MAP = {
        ("16:9", "2k"): "2560x1440", ("16:9", "4k"): "3840x2160",
        ("9:16", "2k"): "1440x2560", ("9:16", "4k"): "2160x3840",
        ("1:1", "2k"): "2048x2048", ("1:1", "4k"): "4096x4096",
    }

    def __init__(self):
        self._url = ARK_BASE_URL.rstrip("/") + "/images/generations"
        self._key = ARK_API_KEY
        self._model = SEEDREAM_MODEL

    def _size(self, size: str, resolution: str) -> str:
        return self._SIZE_MAP.get((size, (resolution or "").lower()), "2048x2048")

    async def generate(
        self,
        prompt: str,
        size: str = "16:9",
        resolution: str = "2k",
        image_urls: list[str] | None = None,
    ) -> dict:
        """文生图 / 图生图(传 image_urls 即图生图)→ {url} 或 {error}。"""
        body: dict = {
            "model": self._model,
            "prompt": prompt,
            "size": self._size(size, resolution),
            "response_format": "url",
            "watermark": False,
        }
        if image_urls:
            body["image"] = image_urls if len(image_urls) > 1 else image_urls[0]
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    self._url,
                    headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
                    json=body,
                )
                data = resp.json()
        except Exception as e:
            return {"error": f"seedream 调用出错: {e}"}
        if resp.status_code != 200:
            return {"error": f"seedream 提交失败 {resp.status_code}: {data}"}
        try:
            return {"url": data["data"][0]["url"]}
        except Exception:
            return {"error": f"seedream 未返回 url: {data}"}

    # ── worker pipeline 协议适配(submit/poll)──────────────────────────────────
    # 画布 worker(image_pipeline)按 apimart/google 的「submit → 拿 task_id → poll」
    # 异步任务模式调用,但 seedream 是同步单次 generate。这里把 generate 包成
    # submit/poll:submit 内部同步出图后用伪 task_id 缓存,poll 取走。
    # (修 Phase 1 遗留断点:worker 默认 provider=seedream 却无 submit/poll → 画布生图从未跑通)
    _pending: dict[str, dict] = {}
    _seq: int = 0

    async def submit(
        self,
        prompt: str,
        size: str = "16:9",
        resolution: str = "2k",
        image_urls: list[str] | None = None,
    ) -> dict:
        result = await self.generate(prompt, size, resolution, image_urls)
        if result.get("error"):
            return {"error": result["error"]}
        SeedreamProvider._seq += 1
        task_id = f"seedream-{SeedreamProvider._seq}"
        SeedreamProvider._pending[task_id] = result
        return {"task_id": task_id}

    async def poll(self, task_id: str) -> dict:
        return SeedreamProvider._pending.pop(task_id, {"error": "seedream: no pending result"})


# ─── GoogleProvider ─────────────────────────────────────────────────────────────


class GoogleProvider:
    """Google Gemini 图片生成，使用官方原生异步接口 client.aio.models.generate_content。"""

    _tasks: dict[str, asyncio.Task] = {}

    def __init__(self):
        from google import genai
        self._client = genai.Client(api_key=GOOGLE_API_KEY)

    async def submit(
        self,
        prompt: str,
        size: str = "16:9",
        resolution: str = "2k",
        image_urls: list[str] | None = None,
    ) -> dict:
        """提交生图（原生异步），返回 {task_id} 或 {error}。"""
        task_id = uuid.uuid4().hex
        refs = await self._download_refs(image_urls)

        coro = self._generate_async(prompt, refs, aspect_ratio=size)
        self._tasks[task_id] = asyncio.create_task(coro)

        return {"task_id": task_id}

    async def _generate_async(
        self,
        prompt: str,
        refs: list[PILImage.Image] | None,
        aspect_ratio: str | None = None,
    ) -> bytes:
        """原生异步 genai 调用 → 返回 image_bytes。失败抛异常。"""
        from google.genai import types

        contents = [prompt] + (refs or [])

        config_kwargs: dict = {"response_modalities": ["TEXT", "IMAGE"]}
        if aspect_ratio and ":" in aspect_ratio:
            config_kwargs["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

        response = await self._client.aio.models.generate_content(
            model=IMAGE_GEN_GOOGLE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        for part in response.parts:
            if (img := part.as_image()) and img.image_bytes:
                return img.image_bytes

        raise RuntimeError("Google 未返回图片")

    async def poll(self, task_id: str) -> dict:
        """等待 task 完成（120s 超时），返回 {image_data, actual_time} 或 {error}。"""
        task = self._tasks.pop(task_id, None)
        if task is None:
            return {"error": f"Google 任务不存在或已过期: {task_id}"}

        t0 = time.time()
        try:
            image_bytes = await asyncio.wait_for(task, timeout=120)
            actual_time = time.time() - t0
            print(f"[Google轮询] task={task_id} 完成 耗时={actual_time:.1f}s")
            return {"image_data": image_bytes, "actual_time": actual_time}
        except asyncio.TimeoutError:
            print(f"[Google轮询] task={task_id} 超时（120s）")
            return {"error": "timeout", "task_id": task_id}
        except Exception as e:
            print(f"[Google轮询] task={task_id} 异常: {e}")
            return {"error": f"Google 生图失败: {e}"}

    async def poll_all(self, tasks: dict[str, str]) -> dict[str, dict]:
        """并行等待多个任务。"""
        results = {}

        async def _poll_one(nid: str, tid: str):
            results[nid] = await self.poll(tid)

        await asyncio.gather(*(_poll_one(nid, tid) for nid, tid in tasks.items()))
        return results

    async def generate(
        self,
        prompt: str,
        size: str = "16:9",
        resolution: str = "2k",
        image_urls: list[str] | None = None,
    ) -> dict:
        """便捷方法：submit + poll。"""
        submitted = await self.submit(prompt, size, resolution, image_urls)
        if "error" in submitted:
            return submitted
        return await self.poll(submitted["task_id"])

    async def _download_refs(self, urls: list[str] | None) -> list[PILImage.Image] | None:
        """下载参考图 URL → PIL Image 列表。"""
        if not urls:
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            results = []
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    results.append(PILImage.open(io.BytesIO(resp.content)))
                except Exception as e:
                    print(f"[Google] 参考图下载失败 {url[:60]}...: {e}")
            return results or None


# ─── 工厂 ──────────────────────────────────────────────────────────────────────


def get_provider() -> ApimartProvider | GoogleProvider | SeedreamProvider:
    """根据 IMAGE_GEN_PROVIDER 返回 provider 实例(动态读 config,resp env/测试)。"""
    from agent import config

    p = (config.IMAGE_GEN_PROVIDER or "apimart").lower()
    if p == "seedream":
        return SeedreamProvider()
    if p == "google":
        return GoogleProvider()
    return ApimartProvider()


def image_gen_ready() -> bool:
    """当前生图 provider 的密钥是否就绪(决定 cascade_generate_first_frame 是否 fail-fast)。
    seedream → ARK_API_KEY;google → GOOGLE_API_KEY;apimart → IMAGE_GEN_API_KEY。
    动态读 config(而非模块级 from-import 绑定),好让 env 变更/测试 monkeypatch 生效。"""
    from agent import config

    p = (config.IMAGE_GEN_PROVIDER or "apimart").lower()
    if p == "seedream":
        return bool(str(config.ARK_API_KEY or "").strip())
    if p == "google":
        return bool(str(config.GOOGLE_API_KEY or "").strip())
    return bool(str(config.IMAGE_GEN_API_KEY or "").strip())
