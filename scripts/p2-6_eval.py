"""P2-6 eval harness CLI.

Usage from repo root:
    cd backend && uv run python ../scripts/p2-6_eval.py [--niche all|baomam_fushi|...] [--mode fixture|llm] [--baseline last] [--skip-judge]

Outputs:
    docs/nexus/founder_log/p2-6_baseline_<UTC>.json
    docs/nexus/founder_log/p2-6_report_<UTC>.md
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from agent.cascade.eval.baselines import save_baseline  # noqa: E402
from agent.cascade.eval.report import render_markdown  # noqa: E402
from agent.cascade.eval.runner import NICHES, run_eval  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="P2-6 eval harness")
    parser.add_argument("--niche", default="all", choices=("all",) + NICHES)
    parser.add_argument("--mode", default=None, choices=(None, "fixture", "llm"), help="override CASCADE_REWRITE_UPSTREAM")
    parser.add_argument("--baseline", default="last", help="'last' loads latest baseline for diff; 'none' skips")
    parser.add_argument("--skip-judge", action="store_true", help="bypass LLM judge (no API key required)")
    args = parser.parse_args()

    niches = list(NICHES) if args.niche == "all" else [args.niche]

    report = asyncio.run(run_eval(
        niches,
        mode=args.mode,
        baseline_dir=None if args.baseline == "last" else None,
        skip_judge=args.skip_judge,
    ))

    baseline_path = save_baseline(report)
    report_md = render_markdown(report)
    ts_safe = report.timestamp.replace(":", "").replace("-", "")
    report_path = REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-6_report_{ts_safe}.md"
    report_path.write_text(report_md, encoding="utf-8")

    print(f"baseline saved: {baseline_path.relative_to(REPO_ROOT)}")
    print(f"report saved:   {report_path.relative_to(REPO_ROOT)}")
    print(f"overall mechanical pass rate: {report.overall_mechanical_pass_rate:.2%}")
    print(f"overall judge realism avg: {report.overall_judge_realism_avg:.2f}")
    print(f"overall judge ad-risk hits: {report.overall_judge_ad_risk_count}")
    if report.delta_from_baseline.get("baseline_status") == "first-ever":
        print("(first baseline — no delta)")
    else:
        print("delta vs baseline:")
        for k, v in report.delta_from_baseline.items():
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
