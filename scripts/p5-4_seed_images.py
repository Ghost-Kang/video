"""P5-4 seed post image generation runner.

Usage:
    cd backend && uv run python ../scripts/p5-4_seed_images.py --dry-run
    cd backend && uv run python ../scripts/p5-4_seed_images.py
    cd backend && uv run python ../scripts/p5-4_seed_images.py --only cover
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "backend" / ".env")

from agent import config  # noqa: E402
from agent.tools.generation import get_provider  # noqa: E402


PROMPTS_JSON = REPO_ROOT / "scripts" / "p5-4_prompts.json"
OUT_DIR = REPO_ROOT / "docs" / "nexus" / "founder_log" / "xhs_post_2026-05-23_images"
EXPECTED_NAMES = ["cover", *[f"img_{idx}" for idx in range(2, 10)]]
ESTIMATED_COST_CNY_PER_IMAGE = 0.5


async def _generate_one(provider: Any, item: dict[str, str], *, retries: int) -> dict[str, Any]:
    name = item["name"]
    prompt = item["prompt"]
    for attempt in range(1, retries + 2):
        started = time.time()
        result = await provider.generate(prompt=prompt, size="3:4", resolution="2k")
        elapsed_s = round(time.time() - started, 1)
        if "url" in result or "image_data" in result:
            return {**result, "attempt": attempt, "elapsed_s": elapsed_s}
        if attempt > retries:
            return {**result, "attempt": attempt, "elapsed_s": elapsed_s}
        print(f"[{name}] generation failed, retrying {attempt}/{retries}: {result.get('error', 'unknown')}")
        await asyncio.sleep(5)
    return {"error": "unreachable", "attempt": retries + 1}


async def _download(url: str, path: Path) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url)
        response.raise_for_status()
        path.write_bytes(response.content)


def _load_prompts() -> list[dict[str, str]]:
    prompts = json.loads(PROMPTS_JSON.read_text(encoding="utf-8"))
    if not isinstance(prompts, list):
        raise ValueError("p5-4_prompts.json must contain a list")
    names = [item.get("name") for item in prompts if isinstance(item, dict)]
    if names != EXPECTED_NAMES:
        raise ValueError(f"prompt names must be {EXPECTED_NAMES}; got {names}")
    for item in prompts:
        prompt = item.get("prompt")
        if not isinstance(prompt, str) or len(prompt.strip()) < 200:
            raise ValueError(f"{item.get('name')} prompt is missing or too short")
    return prompts


def _filter_prompts(prompts: list[dict[str, str]], only: list[str]) -> list[dict[str, str]]:
    if not only:
        return prompts
    allowed = set(only)
    unknown = sorted(allowed - set(EXPECTED_NAMES))
    if unknown:
        raise ValueError(f"unknown --only names: {', '.join(unknown)}")
    return [item for item in prompts if item["name"] in allowed]


def _validate_config() -> list[str]:
    issues: list[str] = []
    provider = config.IMAGE_GEN_PROVIDER
    if provider == "google":
        if not config.GOOGLE_API_KEY:
            issues.append("GOOGLE_API_KEY missing for IMAGE_GEN_PROVIDER=google")
    else:
        if not config.IMAGE_GEN_API_KEY:
            issues.append("IMAGE_GEN_API_KEY missing for Apimart image generation")
        if not config.IMAGE_GEN_BASE_URL:
            issues.append("IMAGE_GEN_BASE_URL missing for Apimart image generation")
    return issues


async def _run(prompts: list[dict[str, str]], *, retries: int, dry_run: bool) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_lines = [
        "# P5-4 image gen log",
        f"started: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"provider: {config.IMAGE_GEN_PROVIDER}",
        f"model: {config.IMAGE_GEN_GOOGLE_MODEL if config.IMAGE_GEN_PROVIDER == 'google' else config.IMAGE_GEN_MODEL}",
        f"dry_run: {str(dry_run).lower()}",
        "",
    ]

    if dry_run:
        for index, item in enumerate(prompts, start=1):
            log_lines.append(f"- {item['name']}: dry-run ok prompt_index={index} chars={len(item['prompt'])}")
        log_lines.append("")
        log_lines.append(f"estimated_cost_cny: {len(prompts) * ESTIMATED_COST_CNY_PER_IMAGE:.2f}")
        (OUT_DIR / "_gen_log.md").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        print(f"dry-run ok: {len(prompts)} prompt(s), log={OUT_DIR / '_gen_log.md'}")
        return 0

    config_issues = _validate_config()
    if config_issues:
        for issue in config_issues:
            print(f"blocked: {issue}", file=sys.stderr)
        return 2

    provider = get_provider()
    failures = 0
    for index, item in enumerate(prompts, start=1):
        name = item["name"]
        local_path = OUT_DIR / f"{name}.png"
        submit_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"[{index}/{len(prompts)}] generating {name}...")
        result = await _generate_one(provider, item, retries=retries)
        if "url" in result:
            try:
                await _download(result["url"], local_path)
                log_lines.append(
                    f"- {name}: ok prompt_index={index} submit_ts={submit_ts} "
                    f"url={result['url']} actual_time={result.get('actual_time', 0)}s "
                    f"elapsed={result.get('elapsed_s', 0)}s attempt={result['attempt']} local={local_path.name}"
                )
            except Exception as exc:
                failures += 1
                log_lines.append(f"- {name}: download_failed prompt_index={index} error={exc}")
                print(f"[{name}] download failed: {exc}", file=sys.stderr)
        elif "image_data" in result:
            local_path.write_bytes(result["image_data"])
            log_lines.append(
                f"- {name}: ok prompt_index={index} submit_ts={submit_ts} url=<inline-google-image> "
                f"actual_time={result.get('actual_time', 0)}s elapsed={result.get('elapsed_s', 0)}s "
                f"attempt={result['attempt']} local={local_path.name}"
            )
        else:
            failures += 1
            log_lines.append(
                f"- {name}: failed prompt_index={index} submit_ts={submit_ts} "
                f"attempt={result.get('attempt')} error={result.get('error', 'unknown')}"
            )
            print(f"[{name}] failed: {result.get('error', 'unknown')}", file=sys.stderr)

    log_lines.extend([
        "",
        f"finished: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"estimated_cost_cny: {len(prompts) * ESTIMATED_COST_CNY_PER_IMAGE:.2f}",
        f"failures: {failures}",
    ])
    (OUT_DIR / "_gen_log.md").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"done: failures={failures}, log={OUT_DIR / '_gen_log.md'}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate P5-4 Xiaohongshu seed post images.")
    parser.add_argument("--dry-run", action="store_true", help="validate prompts/config and write a dry-run log only")
    parser.add_argument("--only", action="append", default=[], help="generate only one image name; repeatable")
    parser.add_argument("--retries", type=int, default=2, help="generation retries per image")
    args = parser.parse_args()

    prompts = _filter_prompts(_load_prompts(), args.only)
    return asyncio.run(_run(prompts, retries=max(0, args.retries), dry_run=args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
