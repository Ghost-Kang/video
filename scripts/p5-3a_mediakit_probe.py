"""P5-3a 火山 MediaKit 端到端 schema probe。

目的:在 Codex sub-phase A 真起跑前,先用真实 API 探测 3 个 endpoint
(extract-audio / extract-frames / transcribe)的 request + response schema,
落 founder_log/p5-3a_mediakit_schemas_<UTC>.md 作为后续 sub-phase B/C 真理源。

公开 docs 缺(2026-05-23 W3D3 WebFetch + WebSearch 均未找到 MediaKit
官方文档);只有 founder 提供的 curl + 3 endpoint 名称推测。

用法:
    cd backend  # 必须从 backend/ 跑以加载 ../.env
    export VOLC_MEDIAKIT_AK=<your-AK>  # 或写入 .env
    uv run python ../scripts/p5-3a_mediakit_probe.py \
        --video-url "https://example.com/sample.mp4" \
        --output ../docs/nexus/founder_log/p5-3a_mediakit_schemas_<UTC>.md

输出:
    一份 markdown 报告,3 个 endpoint 各列:
    - 请求体 JSON 完整 echo
    - HTTP status code
    - 响应 JSON 完整 dump
    - 字段语义观察(PM 注释)

注意:
- 单 endpoint 调用 < ¥0.05 估计;3 个 endpoint 整体 < ¥0.20
- 失败 endpoint(404 / 405)会照样落报告 + 标 "endpoint path 推测错"
- 不操作 backend 库代码 — 这是独立 probe,不入产品流
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "backend" / ".env")

MEDIAKIT_BASE = "https://mediakit.cn-beijing.volces.com/api/v1/tools"
MEDIAKIT_ROOT = "https://mediakit.cn-beijing.volces.com/api/v1"
# Confirmed working (returns 200 + task_id): extract-audio
# Confirmed 404 (tool not found): extract-frames, transcribe
CONFIRMED_PROBE_TOOLS = (
    "extract-audio",
    "extract-frames",
    "transcribe",
)
# Candidates to try for frame extraction:
FRAME_CANDIDATES = (
    "keyframes",
    "snapshot",
    "screenshot",
    "extract-keyframes",
    "video-frames",
    "extract-image",
    "extract-snapshot",
)
# Candidates to try for transcription:
TRANSCRIBE_CANDIDATES = (
    "asr",
    "speech-to-text",
    "stt",
    "extract-text",
    "audio-to-text",
    "voice-recognition",
    "video-transcribe",
)
DEFAULT_TIMEOUT_S = 120.0


def main() -> int:
    parser = argparse.ArgumentParser(description="P5-3a MediaKit schema probe")
    parser.add_argument(
        "--video-url",
        required=True,
        help="Publicly accessible video URL (douyin / xiaohongshu / arbitrary CDN)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output markdown report path; default = docs/nexus/founder_log/p5-3a_mediakit_schemas_<UTC>.md",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help=f"Per-endpoint timeout (default {DEFAULT_TIMEOUT_S})",
    )
    parser.add_argument(
        "--include-candidates",
        action="store_true",
        help="Also probe slug candidates that previously failed; default probes only the 3 canonical P5-3a tools.",
    )
    args = parser.parse_args()

    ak = os.getenv("VOLC_MEDIAKIT_AK", "").strip()
    if not ak:
        print(
            "ERROR: VOLC_MEDIAKIT_AK not set. Add it to backend/.env or export.",
            file=sys.stderr,
        )
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = args.output or (
        REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p5-3a_mediakit_schemas_{ts}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sections: list[str] = [
        f"# P5-3a 火山 MediaKit endpoint schema probe — {ts}",
        "",
        f"**Date**: {datetime.now(timezone.utc).isoformat()}",
        f"**video_url**: `{args.video_url}`",
        f"**Endpoint base**: `{MEDIAKIT_BASE}`",
        f"**Timeout per endpoint**: {args.timeout_s}s",
        "",
        "**Purpose**: ground-truth schema discovery for P5-3 sub-phase A. Public "
        "Volcengine docs do not list MediaKit as of 2026-05-23 W3D3. This report "
        "is consumed by sub-phase B/C/D as the authoritative request/response "
        "contract.",
        "",
        "---",
        "",
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ak}",
    }
    payload = {"video_url": args.video_url}
    tools = list(CONFIRMED_PROBE_TOOLS)
    if args.include_candidates:
        tools.extend(FRAME_CANDIDATES)
        tools.extend(TRANSCRIBE_CANDIDATES)
    tools = list(dict.fromkeys(tools))

    with httpx.Client(timeout=args.timeout_s) as client:
        for tool in tools:
            url = f"{MEDIAKIT_BASE}/{tool}"
            sections.append(f"## /{tool}")
            sections.append("")
            sections.append("### Request")
            sections.append("")
            sections.append(f"`POST {url}`")
            sections.append("")
            sections.append("```http")
            sections.append("Content-Type: application/json")
            sections.append("Authorization: Bearer <VOLC_MEDIAKIT_AK>")
            sections.append("")
            sections.append(json.dumps(payload, ensure_ascii=False, indent=2))
            sections.append("```")
            sections.append("")
            sections.append("### Response")
            sections.append("")
            try:
                resp = client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                sections.append(f"⛔ **Timeout** after {args.timeout_s}s: {exc!r}")
                sections.append("")
                sections.append("**PM note**: increase timeout or this endpoint is async (job_id pattern).")
                sections.append("")
                continue
            except httpx.TransportError as exc:
                sections.append(f"⛔ **Transport error**: {exc!r}")
                sections.append("")
                sections.append("**PM note**: endpoint may not exist (typo or wrong path). Check with founder.")
                sections.append("")
                continue

            sections.append(f"**HTTP status**: `{resp.status_code} {resp.reason_phrase}`")
            sections.append("")
            try:
                body = resp.json()
                sections.append("```json")
                sections.append(json.dumps(body, ensure_ascii=False, indent=2))
                sections.append("```")
            except ValueError:
                sections.append("```text")
                sections.append(resp.text[:4000])  # cap for safety
                if len(resp.text) > 4000:
                    sections.append("... (truncated)")
                sections.append("```")
            sections.append("")

            if resp.status_code == 200:
                note = "✅ endpoint exists + returns 200. Use this schema as contract."
            elif resp.status_code == 401:
                note = "🔒 401 unauthorized — verify VOLC_MEDIAKIT_AK is correct + has tool scope."
            elif resp.status_code == 404:
                note = "❓ 404 — endpoint path may be wrong. Try alternative path candidates."
            elif resp.status_code == 405:
                note = "❓ 405 — method probably wrong (try GET or query param)."
            elif 500 <= resp.status_code < 600:
                note = "⚠️ 5xx — server-side error; retry or contact 火山 support."
            else:
                note = f"❓ status {resp.status_code} — investigate."

            sections.append(f"**PM note**: {note}")
            sections.append("")
            sections.append("---")
            sections.append("")

    sections.append("## Summary for Codex sub-phase A")
    sections.append("")
    sections.append(
        "Use the response shapes above to design `mediakit_client.py`. Field "
        "names + nesting structure dictate `scenes[].dialogue_and_narration` + "
        "`scenes[].timestamps` projection in `_call_doubao_lite()`."
    )
    sections.append("")

    output_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"probe report written: {output_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
