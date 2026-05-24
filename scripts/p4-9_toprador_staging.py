"""P4-9/P5-3 real end-to-end staging runner.

Usage:
    cd backend && uv run python ../scripts/p4-9_toprador_staging.py \
      --url https://www.douyin.com/video/... \
      --url https://www.douyin.com/video/...

Default upstream:
    mediakit, using the configured Doubao/ARK model path. The legacy Toprador
    HTTP endpoint can still be exercised with --upstream toprador.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "backend" / ".env")

from agent.cascade.analysis_service import request_shallow_analysis  # noqa: E402
from agent.cascade.failures import HardFailure  # noqa: E402
from agent.cascade.storage import list_events  # noqa: E402


URL_SOURCE = REPO_ROOT / "docs" / "nexus" / "founder_log" / "real_urls_for_p2-4.md"
REPORT_DIR = REPO_ROOT / "docs" / "nexus" / "founder_log"
URL_RE = re.compile(r"https?://[^\s)>\"]+")


@dataclass(frozen=True)
class StagingResult:
    index: int
    url: str
    ok: bool
    latency_ms: int
    upstream_latency_ms: int | None
    upstream_attempts: int | None
    warnings: list[str]
    failure_code: str | None = None
    detail: str | None = None


def _load_default_urls() -> list[str]:
    if not URL_SOURCE.exists():
        return []
    text = URL_SOURCE.read_text(encoding="utf-8")
    urls: list[str] = []
    for url in URL_RE.findall(text):
        if url not in urls:
            urls.append(url)
    return urls[:3]


def _toprador_configured() -> bool:
    endpoint = os.getenv("TOPRADOR_ENDPOINT", "").strip()
    return bool(endpoint)


async def _run_one(index: int, url: str) -> StagingResult:
    start = time.monotonic()
    try:
        contract = await request_shallow_analysis(
            url,
            user_id="staging",
            run_id=f"p4-9-{index}",
        )
    except HardFailure as exc:
        return StagingResult(
            index=index,
            url=url,
            ok=False,
            latency_ms=int((time.monotonic() - start) * 1000),
            upstream_latency_ms=None,
            upstream_attempts=None,
            warnings=[],
            failure_code=exc.code.value,
            detail=exc.debug_detail,
        )
    return StagingResult(
        index=index,
        url=url,
        ok=True,
        latency_ms=int((time.monotonic() - start) * 1000),
        upstream_latency_ms=None,
        upstream_attempts=None,
        warnings=[warning.code.value for warning in contract.warnings],
    )


async def _exercise_cache(url: str) -> None:
    # Different user_id avoids analysis idempotency and reaches the Toprador cache layer.
    await request_shallow_analysis(url, user_id="staging-cache", run_id="p4-9-cache")


async def _recent_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for user_id in ("staging", "staging-cache"):
        page = await list_events(limit=1000, user_id=user_id)
        events.extend(page["events"])
    return sorted(events, key=lambda event: (event["ts"], event["id"]))


def _event_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event["event_name"]] = counts.get(event["event_name"], 0) + 1
    return counts


def _render_report(results: list[StagingResult], events: list[dict[str, Any]], generated_at: datetime) -> str:
    issue_count = sum(1 for result in results if not result.ok)
    counts = _event_counts(events)
    title_status = "READY" if issue_count == 0 else f"{issue_count} issues"
    lines = [
        f"# P4-9 Toprador staging report - {generated_at.isoformat()}",
        "",
        f"status: {title_status}",
        f"samples_count: {len(results)}",
        "",
        "| # | ok | latency_ms | upstream_attempts | warnings | failure | url |",
        "|---:|---|---:|---:|---|---|---|",
    ]
    for result in results:
        lines.append(
            "| {index} | {ok} | {latency} | {attempts} | {warnings} | {failure} | {url} |".format(
                index=result.index,
                ok="yes" if result.ok else "no",
                latency=result.latency_ms,
                attempts="see analysis_returned event",
                warnings=", ".join(result.warnings) if result.warnings else "-",
                failure=result.failure_code or "-",
                url=result.url,
            )
        )
    lines.extend([
        "",
        "## Event Counts",
        "",
    ])
    for name in sorted(counts):
        lines.append(f"- {name}: {counts[name]}")
    lines.extend([
        "",
        "## Recent Cascade Events",
        "",
    ])
    for event in events[-20:]:
        if not event["event_name"].startswith("cascade_") and event["event_name"] != "analysis_returned":
            continue
        lines.append(f"- {event['ts']} `{event['event_name']}` {event['payload']}")
    lines.extend([
        "",
        "## Manual Follow-up",
        "",
        "- Open `/admin/events` and attach the staging screenshot if this report is used for Phase 1 readiness signoff.",
    ])
    return "\n".join(lines) + "\n"


async def _run(urls: list[str], *, upstream: str) -> Path:
    os.environ["CASCADE_UPSTREAM"] = upstream
    results: list[StagingResult] = []
    for index, url in enumerate(urls, start=1):
        results.append(await _run_one(index, url))
    if results and results[0].ok:
        await _exercise_cache(results[0].url)

    generated_at = datetime.now(timezone.utc)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"p4-9_{upstream}_staging_{generated_at.strftime('%Y%m%dT%H%M%SZ')}.md"
    report_path.write_text(_render_report(results, await _recent_events(), generated_at), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P4-9/P5-3 staging against real URLs.")
    parser.add_argument("--url", action="append", default=[], help="extra founder-provided staging URL; pass twice to reach 5 URLs")
    parser.add_argument("--allow-partial-url-set", action="store_true", help="run with fewer than 5 URLs for connectivity debugging")
    parser.add_argument(
        "--upstream",
        choices=["mediakit", "toprador", "fixture"],
        default=os.getenv("CASCADE_UPSTREAM", "mediakit").strip().lower() or "mediakit",
        help="analysis upstream to stage; default follows CASCADE_UPSTREAM or mediakit",
    )
    args = parser.parse_args()

    if args.upstream == "toprador" and not _toprador_configured():
        print("blocked: --upstream toprador requires TOPRADOR_ENDPOINT", file=sys.stderr)
        return 2

    urls = _load_default_urls()
    for url in args.url:
        if url not in urls:
            urls.append(url)
    if len(urls) < 5 and not args.allow_partial_url_set:
        print("blocked: P4-9 requires 5 URLs; add two founder URLs via --url or pass --allow-partial-url-set", file=sys.stderr)
        return 2

    report_path = asyncio.run(_run(urls[:5], upstream=args.upstream))
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
