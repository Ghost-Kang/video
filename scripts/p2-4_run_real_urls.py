"""P2-4 LLM-mode rewrite runner for founder-curated real URLs.

Reads `docs/nexus/founder_log/real_urls_for_p2-4.md`, parses 5 URLs per niche,
fetches a shallow analysis (via the configured CASCADE_UPSTREAM), runs the
LLM-mode rewrite for that niche, and drops the per-URL output for founder
qualitative review.

Usage from repo root:
    cd backend && uv run python ../scripts/p2-4_run_real_urls.py [--niche all|baomam_fushi|...] [--dry-run]

Outputs:
    docs/nexus/founder_log/p2-4_llm_outputs_<UTC YYYY-MM-DD>/<niche>/url<N>_output.json
    docs/nexus/founder_log/p2-4_llm_outputs_<UTC YYYY-MM-DD>/<niche>/url<N>_output.md
    docs/nexus/founder_log/p2-4_mechanical_<UTC YYYY-MM-DD>.md
    docs/nexus/founder_log/p2-4_qualitative_signoff_<UTC YYYY-MM-DD>.md (template)

Acceptance bar (per claude_llm_P2-4.md §4):
- 4/5 mechanical pass per niche
- 4/5 founder qualitative pass per niche (manual review of the .md outputs)
- cumulative cost ≤ ¥3/run

Notes:
- Requires CASCADE_REWRITE_UPSTREAM=llm AND a working analysis upstream (P2-2 done for real URLs).
- If P2-2 isn't ready yet, run with --use-synthetic-analysis to substitute the synthetic_v1
  fixture matching each niche (useful for dry-running the rewrite path before Toprador wiring).
- Idempotent: re-running on the same date will overwrite the day's output dir.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from agent.cascade.contract import CascadeAnalysisContract  # noqa: E402
from agent.cascade.rewrite import FORBIDDEN_TERMS, rewrite_for_niche  # noqa: E402


NICHES = ("baomam_fushi", "yuer_richang", "jiating_chufang")
URL_FILE = REPO_ROOT / "docs" / "nexus" / "founder_log" / "real_urls_for_p2-4.md"
SYNTHETIC_DIR = REPO_ROOT / "backend" / "src" / "agent" / "cascade" / "fixtures" / "synthetic_v1"


def parse_urls(path: Path) -> dict[str, list[str]]:
    """Parse `real_urls_for_p2-4.md` — accepts numbered lines like `1. https://...`.

    Section markers: `## 1. 宝妈辅食 (baomam_fushi) — 5 条` etc.
    """
    if not path.exists():
        return {n: [] for n in NICHES}

    text = path.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {n: [] for n in NICHES}
    current: str | None = None

    section_pat = re.compile(r"^##\s+\d+\.\s+\S+\s+\((baomam_fushi|yuer_richang|jiating_chufang)\)")
    url_pat = re.compile(r"^\s*\d+\.\s+(https?://\S+)\s*$")

    for line in text.splitlines():
        m_section = section_pat.match(line)
        if m_section:
            current = m_section.group(1)
            continue
        if current is None:
            continue
        m_url = url_pat.match(line)
        if m_url:
            sections[current].append(m_url.group(1))

    return sections


def load_synthetic_analysis(niche: str) -> CascadeAnalysisContract | None:
    """Fallback contract while P2-2 (Toprador wiring) is not yet implemented."""
    path = SYNTHETIC_DIR / niche / "001.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    cleaned = {k: v for k, v in raw.items() if not k.startswith("_")}
    return CascadeAnalysisContract.model_validate(cleaned)


async def fetch_real_analysis(url: str, niche: str) -> CascadeAnalysisContract:
    """Live analysis call. Routes through the configured upstream."""
    from agent.cascade.analysis_service import request_shallow_analysis  # local import to allow dry runs without analysis deps

    user_id = f"p2-4_runner_{niche}"
    run_id = f"p2-4_{niche}_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    return await request_shallow_analysis(url, user_id=user_id, run_id=run_id)


def mechanical_checks(result: dict) -> list[tuple[str, bool, str]]:
    """Return list of (check_name, passed, detail). Mirrors test_rewrite.py + adds 3 from P2-6 brief."""
    checks: list[tuple[str, bool, str]] = []
    script = result.get("script_markdown", "")
    shots = result.get("shots", [])

    checks.append(("script_length_80_600", 80 <= len(script) <= 600, f"len={len(script)}"))
    checks.append(("shot_count_3_5", 3 <= len(shots) <= 5, f"count={len(shots)}"))

    leaked = [t for t in FORBIDDEN_TERMS if t in script or any(t in s.get("dialogue", "") + s.get("visual", "") for s in shots)]
    checks.append(("no_forbidden_terms", not leaked, f"leaked={leaked}"))

    confidence = float(result.get("confidence", 0.0))
    checks.append(("confidence_ge_0_5", confidence >= 0.5, f"conf={confidence:.2f}"))

    checks.append(("rationale_marker_present", "保留" in script and "改" in script, "checked '保留' + '改' in script"))

    # P2-6 brief additions
    dialogues = [s.get("dialogue", "") for s in shots]
    checks.append(("dialogue_diversity", len(set(dialogues)) == len(dialogues), f"unique={len(set(dialogues))}/{len(dialogues)}"))

    avg_len = (sum(len(d) for d in dialogues) / len(dialogues)) if dialogues else 0
    checks.append(("avg_dialogue_ge_10", avg_len >= 10, f"avg={avg_len:.1f}"))

    family_keywords = ("暖色", "厨房", "客厅", "卧室", "餐桌", "家")
    has_anchor = any(any(kw in s.get("visual", "") for kw in family_keywords) for s in shots)
    checks.append(("family_scene_anchor", has_anchor, "checked family keywords in visuals"))

    return checks


def render_output_md(url: str, niche: str, result: dict, checks: list[tuple[str, bool, str]]) -> str:
    pass_count = sum(1 for _, p, _ in checks if p)
    lines = [
        f"# P2-4 改写输出 · {niche}",
        "",
        f"**源 URL**: {url}",
        f"**rewrite_id**: `{result.get('rewrite_id', '?')}`",
        f"**model**: `{result.get('model', '?')}`",
        f"**confidence**: {result.get('confidence', 0):.2f}",
        f"**cost_cny**: ¥{result.get('cost_cny', 0):.4f}",
        f"**机械检查**: {pass_count}/{len(checks)} 通过",
        "",
        "## script_markdown",
        "",
        "```",
        result.get("script_markdown", "(empty)"),
        "```",
        "",
        "## shots",
        "",
    ]
    for shot in result.get("shots", []):
        lines.append(f"- shot {shot.get('shot_index', '?')}:")
        lines.append(f"  - dialogue: {shot.get('dialogue', '')}")
        lines.append(f"  - visual: {shot.get('visual', '')}")
    lines.append("")
    lines.append("## parser_warnings")
    lines.append("")
    warns = result.get("parser_warnings") or []
    if warns:
        for w in warns:
            lines.append(f"- {w}")
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("## 机械检查详情")
    lines.append("")
    for name, passed, detail in checks:
        mark = "✅" if passed else "❌"
        lines.append(f"- {mark} {name} — {detail}")
    lines.append("")
    return "\n".join(lines)


def render_qualitative_template(date_str: str, results_by_niche: dict[str, list[dict]]) -> str:
    """Founder signoff template — same structure as P1-3."""
    lines = [
        f"# P2-4 LLM 改写真实模式 · Founder qualitative signoff",
        "",
        f"**Date**: {date_str}",
        f"**Acceptance bar**: 4/5 per niche \"我会把这个版本发出去\"",
        "",
        "Read each output file and tick the checkbox. If you want changes, write them under 调整诉求.",
        "",
    ]
    for niche, items in results_by_niche.items():
        lines.append(f"## {niche}")
        lines.append("")
        for item in items:
            url = item["url"]
            output_path = item["output_md_relpath"]
            lines.append(f"### {url}")
            lines.append("")
            lines.append(f"Output: [{output_path}]({output_path})")
            lines.append("")
            lines.append("- [ ] 我会把这个版本发出去 — 通过")
            lines.append("- [ ] 还需要调整")
            lines.append("")
            lines.append("调整诉求(若有):")
            lines.append("")
            lines.append("> (空)")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 跨 niche 共性观察")
    lines.append("")
    lines.append("> (空 — founder 填)")
    lines.append("")
    lines.append("## 下一步")
    lines.append("")
    lines.append("- 若每个 niche ≥ 4/5 打勾 → P2-4 done,触发 P2-6 eval harness 建立 baseline")
    lines.append("- 若任一 niche 不达标 → 列出共性问题 → 启动 prompt iteration (改 `backend/src/agent/prompts/rewrite_<niche>.md`),复跑 `scripts/p2-4_run_real_urls.py`,再 review")
    return "\n".join(lines)


def render_mechanical_summary(date_str: str, results_by_niche: dict[str, list[dict]]) -> str:
    lines = [f"# P2-4 LLM 改写真实模式 · 机械检查汇总", "", f"**Date**: {date_str}", ""]
    for niche, items in results_by_niche.items():
        if not items:
            lines.append(f"## {niche} — (no URLs)")
            lines.append("")
            continue
        passes = sum(1 for it in items if it["mechanical_pass"])
        lines.append(f"## {niche} — {passes}/{len(items)} 全过")
        lines.append("")
        for it in items:
            mark = "✅" if it["mechanical_pass"] else "❌"
            fails = [name for name, passed, _ in it["checks"] if not passed]
            extra = f" (fail: {', '.join(fails)})" if fails else ""
            lines.append(f"- {mark} {it['url']}{extra}")
        lines.append("")
    return "\n".join(lines)


async def run(niches: list[str], dry_run: bool, use_synthetic: bool) -> dict:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-4_llm_outputs_{date_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    urls_by_niche = parse_urls(URL_FILE)
    results_by_niche: dict[str, list[dict]] = {}
    total_cost = 0.0
    total_runs = 0
    total_failed = 0

    for niche in niches:
        urls = urls_by_niche.get(niche, [])
        results_by_niche[niche] = []

        if not urls:
            print(f"[{niche}] no URLs found in {URL_FILE.relative_to(REPO_ROOT)} — skipping")
            continue

        niche_dir = out_dir / niche
        niche_dir.mkdir(parents=True, exist_ok=True)

        for n, url in enumerate(urls, start=1):
            print(f"[{niche}] url {n}/{len(urls)}: {url}")
            if dry_run:
                continue

            try:
                if use_synthetic:
                    contract = load_synthetic_analysis(niche)
                    if contract is None:
                        raise RuntimeError(f"synthetic fallback fixture missing for {niche}")
                else:
                    contract = await fetch_real_analysis(url, niche)

                result = await rewrite_for_niche(contract, niche)
                checks = mechanical_checks(result)
                pass_count = sum(1 for _, p, _ in checks if p)
                mechanical_pass = pass_count == len(checks)
                cost = float(result.get("cost_cny") or 0)
                total_cost += cost
                total_runs += 1

                (niche_dir / f"url{n}_output.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                md = render_output_md(url, niche, result, checks)
                (niche_dir / f"url{n}_output.md").write_text(md, encoding="utf-8")

                results_by_niche[niche].append({
                    "url": url,
                    "output_md_relpath": f"p2-4_llm_outputs_{date_str}/{niche}/url{n}_output.md",
                    "mechanical_pass": mechanical_pass,
                    "checks": checks,
                    "cost_cny": cost,
                })

                mark = "✅" if mechanical_pass else "❌"
                print(f"  {mark} {pass_count}/{len(checks)} checks · ¥{cost:.4f}")
            except Exception as exc:
                total_failed += 1
                print(f"  ❌ ERROR: {exc.__class__.__name__}: {exc}")
                results_by_niche[niche].append({
                    "url": url,
                    "output_md_relpath": "(error — no output)",
                    "mechanical_pass": False,
                    "checks": [("execution", False, str(exc))],
                    "cost_cny": 0.0,
                })

    # Summaries
    if not dry_run:
        mech_summary = render_mechanical_summary(date_str, results_by_niche)
        (REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-4_mechanical_{date_str}.md").write_text(
            mech_summary, encoding="utf-8"
        )
        qual_template = render_qualitative_template(date_str, results_by_niche)
        (REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-4_qualitative_signoff_{date_str}.md").write_text(
            qual_template, encoding="utf-8"
        )

    return {
        "date": date_str,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "total_runs": total_runs,
        "total_failed": total_failed,
        "total_cost_cny": round(total_cost, 4),
        "results_by_niche": {n: len(items) for n, items in results_by_niche.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P2-4 LLM-mode runner")
    parser.add_argument("--niche", default="all", choices=("all",) + NICHES)
    parser.add_argument("--dry-run", action="store_true", help="parse URLs and print plan; no LLM calls")
    parser.add_argument(
        "--use-synthetic-analysis",
        action="store_true",
        help="substitute synthetic_v1 fixture for the analysis stage (P2-2 not yet wired)",
    )
    args = parser.parse_args()

    niches = list(NICHES) if args.niche == "all" else [args.niche]

    # Force LLM mode unless caller already set CASCADE_REWRITE_UPSTREAM=fixture explicitly
    if os.environ.get("CASCADE_REWRITE_UPSTREAM") not in {"fixture", "llm"}:
        os.environ["CASCADE_REWRITE_UPSTREAM"] = "llm"

    if not URL_FILE.exists():
        print(f"FATAL: {URL_FILE.relative_to(REPO_ROOT)} does not exist. Have founder paste URLs first.")
        return 2

    summary = asyncio.run(run(niches, args.dry_run, args.use_synthetic_analysis))
    print("---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"qualitative template: docs/nexus/founder_log/p2-4_qualitative_signoff_{summary['date']}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
