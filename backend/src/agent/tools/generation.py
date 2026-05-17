"""图片生成工具 — Apimart API"""

import asyncio
from pathlib import Path

import requests

from agent.config import IMAGE_GEN_API_KEY, IMAGE_GEN_BASE_URL, IMAGE_GEN_MODEL

GENERATE_URL = f"{IMAGE_GEN_BASE_URL}/v1/images/generations"
UPLOAD_URL = f"{IMAGE_GEN_BASE_URL}/v1/uploads/images"
TASK_URL = f"{IMAGE_GEN_BASE_URL}/v1/tasks"

AUTH_HEADER = {"Authorization": f"Bearer {IMAGE_GEN_API_KEY}"}
JSON_HEADERS = {**AUTH_HEADER, "Content-Type": "application/json"}


def upload_image(file_path: str | Path) -> dict:
    """上传本地图片，返回 {url} 或 {error}。"""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}
    with open(path, "rb") as f:
        resp = requests.post(UPLOAD_URL, headers=AUTH_HEADER, files={"file": f}, timeout=30)
    data = resp.json()
    if data.get("url"):
        return {"url": data["url"]}
    return {"error": f"上传失败: {data}"}


def submit_image(
    prompt: str,
    size: str = "16:9",
    resolution: str = "2k",
    image_urls: list[str] | None = None,
) -> dict:
    """提交生图任务，返回 {task_id} 或 {error}。

    Args:
        image_urls: 参考图 URL 列表，用于图生图。
    """
    payload: dict = {"model": IMAGE_GEN_MODEL, "prompt": prompt, "n": 1, "size": size, "resolution": resolution}
    if image_urls:
        payload["image_urls"] = image_urls

    resp = requests.post(GENERATE_URL, json=payload, headers=JSON_HEADERS, timeout=30)
    data = resp.json()
    if data.get("code") != 200:
        return {"error": f"生图提交失败: {data}"}
    return {"task_id": data["data"][0]["task_id"]}


async def poll_image(task_id: str) -> dict:
    """轮询直到完成或超时，返回 {url, actual_time} 或 {error}。"""
    for _ in range(30):  # 最多等 150 秒
        await asyncio.sleep(5)
        try:
            resp = requests.get(
                f"{TASK_URL}/{task_id}",
                headers=JSON_HEADERS,
                params={"language": "zh"},
                timeout=15,
            )
            task = resp.json()
        except Exception as e:
            return {"error": f"轮询异常: {e}"}

        if task.get("code") != 200:
            continue
        status = task["data"].get("status")
        if status == "completed":
            images = task["data"]["result"]["images"]
            url = images[0]["url"] if isinstance(images[0]["url"], str) else images[0]["url"][0]
            return {
                "url": url,
                "actual_time": task["data"].get("actual_time", 0),
            }
        if status == "failed":
            return {"error": f"生图任务失败: {task_id}"}

    return {"error": f"生图超时: {task_id}"}
