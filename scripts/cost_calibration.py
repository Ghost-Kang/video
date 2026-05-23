"""Generate a P4-8 cost_guard calibration report.

Usage:
    cd backend && uv run python ../scripts/cost_calibration.py
"""

from __future__ import annotations

import asyncio
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.cascade.cost_guard import (
    PREDICT_ANALYSIS_CNY,
    PREDICT_REWRITE_CNY,
    PREDICT_SHOT_IMAGE_CNY,
)
from agent.cascade.storage import list_events


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_DIR = REPO_ROOT / "docs" / "nexus" / "founder_log"
KNOWN_CALL_KINDS = ("analysis", "rewrite", "shot")
PREDICT_CNY = {
    "analysis": PREDICT_ANALYSIS_CNY,
    "rewrite": PREDICT_REWRITE_CNY,
    "shot": PREDICT_SHOT_IMAGE_CNY,
}


@dataclass(frozen=True)
class CostRow:
    call_kind: str
    values_cny: tuple[float, ...]
    predict_cny: float | None
    total_samples: int

    @property
    def n(self) -> int:
        return len(self.values_cny)

    @property
    def p50(self) -> float | None:
        return percentile(self.values_cny, 0.50)

    @property
    def p95(self) -> float | None:
        return percentile(self.values_cny, 0.95)

    @property
    def max(self) -> float | None:
        return max(self.values_cny) if self.values_cny else None

    @property
    def mean(self) -> float | None:
        return sum(self.values_cny) / self.n if self.values_cny else None

    @property
    def drift(self) -> str:
        if self.n == 0:
            return "-"
        if self.total_samples < 10:
            return "insufficient"
        if self.predict_cny is None:
            return "no_predict"
        assert self.p95 is not None
        return "WARN p95>PREDICT" if self.p95 > self.predict_cny else "OK"


def percentile(values: tuple[float, ...], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil(q * len(ordered)) - 1
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


async def load_generation_costs() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = await list_events(event_name="generation_cost", limit=1000, offset=offset)
        events.extend(page["events"])
        next_offset = page.get("next_offset")
        if next_offset is None:
            break
        offset = int(next_offset)
    return events


def build_rows(events: list[dict[str, Any]]) -> list[CostRow]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for event in events:
        payload = event.get("payload") or {}
        call_kind = str(payload.get("call_kind") or "unknown")
        try:
            grouped[call_kind].append(int(payload.get("cost_fen")) / 100.0)
        except (TypeError, ValueError):
            continue

    ordered_kinds = list(KNOWN_CALL_KINDS)
    ordered_kinds.extend(sorted(k for k in grouped if k not in ordered_kinds))
    total_samples = sum(len(values) for values in grouped.values())
    return [
        CostRow(
            call_kind=kind,
            values_cny=tuple(sorted(grouped.get(kind, []))),
            predict_cny=PREDICT_CNY.get(kind),
            total_samples=total_samples,
        )
        for kind in ordered_kinds
    ]


def render_report(rows: list[CostRow], generated_at: datetime) -> str:
    samples_count = sum(row.n for row in rows)
    lines = [
        f"# cost_guard calibration report - {generated_at.isoformat()}",
        "",
        f"samples_count: {samples_count}",
        "",
    ]
    if samples_count < 10:
        lines.extend([
            "> Sample count is below 10; treat drift as directional only.",
            "",
        ])
    lines.extend([
        "| call_kind | p50 (CNY) | p95 (CNY) | max (CNY) | mean (CNY) | n | PREDICT (CNY) | drift |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ])
    for row in rows:
        lines.append(
            "| {call_kind} | {p50} | {p95} | {max_cost} | {mean} | {n} | {predict} | {drift} |".format(
                call_kind=row.call_kind,
                p50=_fmt_money(row.p50),
                p95=_fmt_money(row.p95),
                max_cost=_fmt_money(row.max),
                mean=_fmt_money(row.mean),
                n=row.n,
                predict=_fmt_money(row.predict_cny),
                drift=row.drift,
            )
        )
    lines.extend(["", "## Recommendations", *recommendations(rows)])
    return "\n".join(lines) + "\n"


def recommendations(rows: list[CostRow]) -> list[str]:
    items: list[str] = []
    for row in rows:
        if row.n == 0:
            items.append(f"- {row.call_kind}: no samples yet; keep current prediction.")
            continue
        if row.predict_cny is None:
            items.append(f"- {row.call_kind}: observed p95 {_fmt_money(row.p95)} CNY; add a prediction if this call kind becomes guarded.")
            continue
        if row.total_samples < 10:
            items.append(f"- {row.call_kind}: only {row.n} samples; wait for at least 10 generation_cost events before changing PREDICT.")
            continue
        if row.p95 is not None and row.p95 > row.predict_cny:
            suggested = math.ceil(row.p95 * 100) / 100
            items.append(f"- {row.call_kind}: p95 {_fmt_money(row.p95)} CNY exceeds PREDICT {_fmt_money(row.predict_cny)} CNY; consider raising to {_fmt_money(suggested)} CNY.")
        else:
            items.append(f"- {row.call_kind}: p95 is within PREDICT; no change recommended.")
    return items


async def write_report(output_dir: Path = DEFAULT_REPORT_DIR) -> Path:
    generated_at = datetime.now(timezone.utc)
    rows = build_rows(await load_generation_costs())
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"cost_calibration_{generated_at.strftime('%Y%m%dT%H%M%SZ')}.md"
    path.write_text(render_report(rows, generated_at), encoding="utf-8")
    return path


def _fmt_money(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


async def _main() -> None:
    print(await write_report())


if __name__ == "__main__":
    asyncio.run(_main())
