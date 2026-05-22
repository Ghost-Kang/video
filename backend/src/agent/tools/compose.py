"""视频合成 — ffmpeg 拼接，自动处理混合分辨率"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile

import httpx


async def _download(url: str, dest: str):
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)


async def _probe(path: str) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return json.loads(stdout) if stdout else {}


def _get_resolution(info: dict) -> tuple[int, int]:
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            return (s["width"], s["height"])
    return (1920, 1080)


async def compose_videos(video_urls: list[str]) -> bytes | None:
    """下载视频 → ffmpeg 拼接 → 返回合成视频 bytes。"""
    if not video_urls:
        return None
    if len(video_urls) == 1:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(video_urls[0])
            resp.raise_for_status()
            return resp.content

    tmp_dir = tempfile.mkdtemp(prefix="rhtv_compose_")
    try:
        # 1. 下载 + 探测分辨率
        paths: list[str] = []
        resolutions: list[tuple[int, int]] = []
        for i, url in enumerate(video_urls):
            path = os.path.join(tmp_dir, f"clip_{i}.mp4")
            print(f"[合成] 下载 clip {i} ...")
            await _download(url, path)
            paths.append(path)
            info = await _probe(path)
            w, h = _get_resolution(info)
            resolutions.append((w, h))
            print(f"[合成] clip {i} size={os.path.getsize(path)/1024:.0f}KB {w}x{h}")

        output = os.path.join(tmp_dir, "output.mp4")

        # 2. 判断分辨率是否一致
        unique_res = set(resolutions)
        if len(unique_res) == 1:
            # 所有视频分辨率相同 → concat demuxer（无损，快）
            concat_list = os.path.join(tmp_dir, "list.txt")
            with open(concat_list, "w") as f:
                for p in paths:
                    f.write(f"file '{p}'\n")
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", output]
            print(f"[合成] concat demuxer（分辨率一致 {resolutions[0][0]}x{resolutions[0][1]}）")
        else:
            # 混合分辨率 → concat filter（统一缩放到最常见的分辨率，需重编码）
            target = max(resolutions, key=lambda r: r[0] * r[1])  # 取最高分辨率
            tw, th = target
            print(f"[合成] concat filter（混合分辨率 → {tw}x{th}）")

            # 构建 filter_complex: scale each → concat
            filter_parts = []
            concat_inputs = []
            for i in range(len(paths)):
                filter_parts.append(f"[{i}:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2[v{i}]")
                concat_inputs.append(f"[v{i}]")
                if any(s.get("codec_type") == "audio" for s in (await _probe(paths[i])).get("streams", [])):
                    concat_inputs.append(f"[{i}:a]")

            n = len(paths)
            filter_str = ";".join(filter_parts)
            filter_str += f";{''.join(concat_inputs)}concat=n={n}:v=1:a=1[v][a]"

            cmd = ["ffmpeg", "-y"]
            for p in paths:
                cmd.extend(["-i", p])
            cmd.extend([
                "-filter_complex", filter_str,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac",
                output,
            ])

        print(f"[合成] ffmpeg: {' '.join(cmd[:6])}...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")[-500:] if stderr else "unknown"
            print(f"[合成] ffmpeg 失败: {err}")
            return None

        if os.path.exists(output) and os.path.getsize(output) > 0:
            with open(output, "rb") as f:
                data = f.read()
            print(f"[合成] 完成 size={len(data)/1024/1024:.1f}MB")
            return data

        print("[合成] 输出文件为空")
        return None
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
