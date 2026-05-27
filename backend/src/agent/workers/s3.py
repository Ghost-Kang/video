"""S3 上传 helper(worker 用)。

`agent.tools.s3_upload.upload_bytes` 的薄包装,增加下载 URL → upload 的 round-trip。
异常一律 swallow + log,返 None 让 caller 决定后续。
"""

from __future__ import annotations

import time

import httpx

from agent.tools.s3_upload import upload_bytes


def upload_bytes_to_s3(data: bytes, filename: str) -> str | None:
    """直接上传 bytes。"""
    try:
        return upload_bytes(data, filename)
    except Exception as e:
        print(f"[S3] 上传异常 {filename}: {e}")
        return None


async def download_and_upload(image_url: str, node_id: str, ext: str = "png") -> str | None:
    """先 http 下载,再传 S3。失败返 None。"""
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
        dl_ms = (time.time() - t0) * 1000
        print(f"[S3] 下载完成 node={node_id} size={len(resp.content)} 耗时={dl_ms:.0f}ms")

        s3_url = upload_bytes(resp.content, f"{node_id}.{ext}")
        total_ms = (time.time() - t0) * 1000
        if s3_url:
            print(f"[S3] 上传完成 node={node_id} 总耗时={total_ms:.0f}ms")
        return s3_url
    except Exception as e:
        print(f"[S3] 上传异常 node={node_id}: {e}")
        return None
