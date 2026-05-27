"""P2-4 LLM-mode rewrite runner for founder-curated real URLs (v2.0).

Reads `docs/nexus/founder_log/real_urls_for_p2-4.md` v2.0, including the
per-URL HTML-comment metadata (author / date / title / hook_pattern_id /
classification). Synthesizes a `CascadeAnalysisContract` per URL from the
founder's annotations, runs the niche rewrite (LLM or fixture mode), and
drops per-URL output for founder qualitative review.

Why per-URL contract synthesis:
- Real upstream (Toprador) is wired in code but requires TOPRADOR_ENDPOINT
  + API key that isn't configured locally yet.
- Synthesizing a contract from the founder's *manual* analysis (which is
  what the URL-file annotations are) gives URL-specific inputs without
  depending on the live upstream.

Usage from repo root:
    cd backend && uv run python ../scripts/p2-4_run_real_urls.py [--niche all|...] [--dry-run]

Outputs:
    docs/nexus/founder_log/p2-4_llm_outputs_<UTC YYYY-MM-DD>/<niche>/url<N>_output.json
    docs/nexus/founder_log/p2-4_llm_outputs_<UTC YYYY-MM-DD>/<niche>/url<N>_output.md
    docs/nexus/founder_log/p2-4_mechanical_<UTC YYYY-MM-DD>.md
    docs/nexus/founder_log/p2-4_qualitative_signoff_<UTC YYYY-MM-DD>.md (template)
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from agent.cascade.contract import CascadeAnalysisContract, Platform  # noqa: E402
from agent.cascade.rewrite import FORBIDDEN_TERMS, rewrite_for_niche  # noqa: E402
from agent.cascade import hook_taxonomy  # noqa: E402


NICHES = ("baomam_fushi", "yuer_richang", "jiating_chufang")
URL_FILE = REPO_ROOT / "docs" / "nexus" / "founder_log" / "real_urls_for_p2-4.md"


@dataclasses.dataclass
class URLEntry:
    url: str
    niche: str
    index: int  # 1..5 within the niche
    author: str = ""
    date: str = ""
    title: str = ""
    hook_pattern_id: str = ""  # e.g. "H1+H2+H3"
    classification: str = "positive"  # positive | negative_ref | edge_case
    raw_metadata: str = ""


# --- Parser ----------------------------------------------------------------

_SECTION_PAT = re.compile(r"^##\s+\d+\.\s+\S+\s+\((baomam_fushi|yuer_richang|jiating_chufang)\)")
_URL_PAT = re.compile(r"^\s*(\d+)\.\s+(https?://\S+)\s*$")
_COMMENT_OPEN = "<!--"
_COMMENT_CLOSE = "-->"
_HOOK_PAT = re.compile(r"钩子模式[::]\s*([H0-9+\(\)\s一-鿿/]+)")
_TITLE_PAT = re.compile(r"标题[::]\s*[\"']?([^\"'\n]+?)[\"']?\s*$", re.MULTILINE)
_DATE_PAT = re.compile(r"(\d{4}-\d{2}-\d{2})")
_AUTHOR_PAT = re.compile(r"@([^\s|()（]+)")
_H_CODE = re.compile(r"H\d+")
_NEG_PAT = re.compile(r"NEGATIVE\s*REF|❌-?IP")
_EDGE_PAT = re.compile(r"EDGE\s*CASE")


def _extract_hook_pattern_id(comment: str) -> str:
    """Compact `H1(月龄) + H2(一周不重样)` → `H1+H2`."""
    m = _HOOK_PAT.search(comment)
    if not m:
        return ""
    codes = _H_CODE.findall(m.group(1))
    return "+".join(codes) if codes else ""


def _extract_classification(comment: str) -> str:
    if _NEG_PAT.search(comment):
        return "negative_ref"
    if _EDGE_PAT.search(comment):
        return "edge_case"
    return "positive"


def _extract_title(comment: str) -> str:
    m = _TITLE_PAT.search(comment)
    return m.group(1).strip() if m else ""


def _extract_author(comment: str) -> str:
    m = _AUTHOR_PAT.search(comment)
    return m.group(1).strip() if m else ""


def _extract_date(comment: str) -> str:
    m = _DATE_PAT.search(comment)
    return m.group(1) if m else ""


def parse_url_entries(path: Path) -> dict[str, list[URLEntry]]:
    """Walk the URL file and pair each URL with the following HTML comment block."""
    if not path.exists():
        return {n: [] for n in NICHES}

    text = path.read_text(encoding="utf-8")
    sections: dict[str, list[URLEntry]] = {n: [] for n in NICHES}
    current_niche: str | None = None

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        m_section = _SECTION_PAT.match(line)
        if m_section:
            current_niche = m_section.group(1)
            i += 1
            continue

        if current_niche is None:
            i += 1
            continue

        m_url = _URL_PAT.match(line)
        if m_url:
            idx = int(m_url.group(1))
            url = m_url.group(2)
            # Look ahead for an HTML comment block on subsequent lines.
            comment_lines: list[str] = []
            j = i + 1
            in_comment = False
            while j < len(lines):
                ln = lines[j]
                stripped = ln.strip()
                if not in_comment and stripped.startswith(_COMMENT_OPEN):
                    in_comment = True
                    comment_lines.append(stripped)
                    if _COMMENT_CLOSE in stripped:
                        break
                    j += 1
                    continue
                if in_comment:
                    comment_lines.append(ln)
                    if _COMMENT_CLOSE in ln:
                        break
                    j += 1
                    continue
                # No comment immediately follows — stop look-ahead.
                break

            comment = "\n".join(comment_lines)
            entry = URLEntry(
                url=url,
                niche=current_niche,
                index=idx,
                author=_extract_author(comment),
                date=_extract_date(comment),
                title=_extract_title(comment),
                hook_pattern_id=_extract_hook_pattern_id(comment),
                classification=_extract_classification(comment),
                raw_metadata=comment,
            )
            sections[current_niche].append(entry)
            i = j + 1
            continue

        i += 1
    return sections


# --- Contract synthesis -----------------------------------------------------

# Niche-specific scene templates for the synthesized contract. Each provides
# 4 scenes shaped to the niche's typical pacing. The rewriter operates over
# this contract; the founder's title/hook get injected into the viral_analysis
# so the rewriter has URL-specific anchors.
_SCENE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "baomam_fushi": [
        {"scene": "宝宝在餐椅上拒食", "dialogue": "你家宝宝是不是也这样,怎么喂都不吃", "visual": "暖色俯拍,餐椅特写,食材碗"},
        {"scene": "妈妈换一种做法", "dialogue": "试试换一种食材或工具", "visual": "砧板/料理台特写"},
        {"scene": "蒸/煮关键步骤", "dialogue": "几分钟搞定的小技巧", "visual": "侧拍灶台,食物变化特写"},
        {"scene": "宝宝主动接受", "dialogue": "你家几个月开始吃这个,评论区告诉我", "visual": "宝宝面部特写"},
    ],
    "yuer_richang": [
        {"scene": "深夜场景,娃醒了", "dialogue": "他又醒了,我快撑不住", "visual": "夜灯昏黄,卧室广角"},
        {"scene": "妈妈视角自述", "dialogue": "当妈以后才发现,真累的是没人理解", "visual": "妈妈侧脸,自拍角度"},
        {"scene": "孩子说了一句话", "dialogue": "他突然说了句让我破防的话", "visual": "孩子局部特写,小手小脚"},
        {"scene": "妈妈和娃和解", "dialogue": "你被娃哪句话戳过,评论区聊聊", "visual": "妈妈和娃靠在一起"},
    ],
    "jiating_chufang": [
        {"scene": "对比餐厅菜单/价格", "dialogue": "餐厅 88,在家成本不到 15", "visual": "自家厨房台面,手机/菜单照"},
        {"scene": "关键操作步骤", "dialogue": "切片调味,关键就这两步", "visual": "俯拍砧板,食材特写"},
        {"scene": "火候/手法", "dialogue": "热锅冷油,30 秒变色", "visual": "侧拍炒锅,火光特写"},
        {"scene": "成品反差", "dialogue": "这一道你家做不做,留言告诉我", "visual": "成品装盘俯拍,拉丝/出汁"},
    ],
}


def _platform_from_url(url: str) -> Platform:
    if "douyin.com" in url:
        return Platform.DOUYIN
    if "xiaohongshu.com" in url or "xhslink" in url:
        return Platform.XIAOHONGSHU
    return Platform.OTHER


def synthesize_contract_from_entry(entry: URLEntry) -> CascadeAnalysisContract:
    """Build a contract from founder annotations.

    Identity: analysis_id derived from URL + niche. viral_analysis fields
    seed from title/hook so the rewriter's downstream output anchors on the
    founder's chosen pattern, not on a generic synthetic template.
    """
    digest = hashlib.sha256(f"{entry.niche}\0{entry.url}".encode("utf-8")).hexdigest()[:16]
    analysis_id = f"ana_p24_{digest}"
    title = entry.title or f"{entry.niche} 改写源 #{entry.index}"
    hook_id = entry.hook_pattern_id or "(unset)"

    templates = _SCENE_TEMPLATES[entry.niche]
    scenes: list[dict[str, Any]] = []
    for i, tpl in enumerate(templates, start=1):
        scenes.append({
            "scene_index": i,
            "timestamp_start": float((i - 1) * 6),
            "timestamp_end": float(i * 6),
            "scene": tpl["scene"],
            "dialogue_and_narration": tpl["dialogue"],
            "visual_content": tpl["visual"],
            "subject": None,
            "shot_type": "medium",
            "camera_movement": "static",
            "first_frame_url": None,
            "warnings": [],
        })

    contract = {
        "schema_version": "1.0",
        "analysis_id": analysis_id,
        "source_url": entry.url,
        "platform": _platform_from_url(entry.url).value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "p2-4-synth-v1",
        "cost_cny": 0.0,
        "duration_s": len(scenes) * 6,
        "confidence": 0.8,
        "viral_analysis": {
            "hook": f"{hook_id}: {title}"[:80],
            "pacing": "founder-annotated; LLM/fixture renders accordingly",
            "climax": "依赖 hook_pattern 钩子组合,改写时由 prompt 路径处理",
            "visual_style": "暖色调,家庭场景,自然光",
            "emotional_arc": "见 hook_pattern 描述",
            "target_audience": f"{entry.niche} 受众",
            "engagement_levers": "结尾抛问题/抛对比/抛承诺",
            "replicable_formula": f"{hook_id} · {title[:60]}",
            # W4D5: audio + production are required on the contract. p2-4 is
            # founder-annotated synth — we seed with safe defaults; the
            # adapter would fall back the same way if these were absent.
            "audio": {
                "bgm": "n/a — founder-annotated synth",
                "voice_pace": "n/a — founder-annotated synth",
                "sound_effects": "n/a — founder-annotated synth",
            },
            "production": {
                "cost_tier": "solo_phone",
                "estimated_hours": 1.0,
                "replaceable_anchors": [],
            },
        },
        "scenes": scenes,
        "warnings": [],
    }
    return CascadeAnalysisContract.model_validate(contract)


# --- Mechanical checks ------------------------------------------------------


MANDATORY_CHECKS: frozenset[str] = frozenset({
    # Per p2-4_hooks_taxonomy.md §4: #7 and #8 are P0 mandatory.
    "nutrient_category_consistency",
    "hook_p0_compliance",
})


def mechanical_checks(result: dict, niche: str, source_title: str = "") -> list[tuple[str, bool, str]]:
    """Return list of (check_name, passed, detail).

    Threshold: ≥ 8/10 pass + all MANDATORY_CHECKS pass.
    """
    checks: list[tuple[str, bool, str]] = []
    script = result.get("script_markdown", "")
    shots = result.get("shots", [])

    # Original 5 (P1-3 brief §3)
    checks.append(("script_length_80_600", 80 <= len(script) <= 600, f"len={len(script)}"))
    checks.append(("shot_count_3_5", 3 <= len(shots) <= 5, f"count={len(shots)}"))

    leaked = [t for t in FORBIDDEN_TERMS if t in script or any(t in s.get("dialogue", "") + s.get("visual", "") for s in shots)]
    checks.append(("no_forbidden_terms", not leaked, f"leaked={leaked}"))

    confidence = float(result.get("confidence", 0.0))
    classification = str(result.get("source_classification") or "positive")
    if classification == "negative_ref":
        checks.append(("confidence_in_range", 0.4 <= confidence <= 0.6, f"conf={confidence:.2f} (capped for negative_ref)"))
    else:
        checks.append(("confidence_ge_0_5", confidence >= 0.5, f"conf={confidence:.2f}"))

    checks.append(("rationale_marker_present", "保留" in script and "改" in script, "checked '保留' + '改' in script"))

    # New 5 (p2-4_hooks_taxonomy.md §4)
    passed, detail = hook_taxonomy.visual_diversity(result)
    checks.append(("visual_diversity_score", passed, detail))

    passed, detail = hook_taxonomy.nutrient_category_consistency(result, niche, source_title)
    checks.append(("nutrient_category_consistency", passed, detail))

    passed, detail = hook_taxonomy.hook_p0_compliance(result, niche)
    checks.append(("hook_p0_compliance", passed, detail))

    passed, detail = hook_taxonomy.hook_diversity(result)
    checks.append(("hook_diversity", passed, detail))

    passed, detail = hook_taxonomy.negative_hook_absence(result, niche)
    checks.append(("negative_hook_absence", passed, detail))

    # 菜名 anchor (F-3-a) — jiating-specific addendum on top of the 10 standard
    passed, detail = hook_taxonomy.dish_anchor_present(result, niche)
    checks.append(("dish_anchor_present", passed, detail))

    return checks


def mechanical_pass(checks: list[tuple[str, bool, str]]) -> bool:
    """Pass threshold: ≥ 8/10 standard checks + all MANDATORY_CHECKS pass."""
    standard = [c for c in checks if c[0] != "dish_anchor_present"]
    standard_pass = sum(1 for _, p, _ in standard if p)
    mandatory_ok = all(p for name, p, _ in checks if name in MANDATORY_CHECKS)
    # If niche has a 菜名 hard rule (jiating), it must also pass.
    dish_check = next((c for c in checks if c[0] == "dish_anchor_present"), None)
    dish_ok = dish_check is None or dish_check[1]
    return standard_pass >= 8 and mandatory_ok and dish_ok


# --- Renderers --------------------------------------------------------------


def render_output_md(entry: URLEntry, result: dict, checks: list[tuple[str, bool, str]]) -> str:
    pass_count = sum(1 for _, p, _ in checks if p)
    lines = [
        f"# P2-4 改写输出 · {entry.niche} #{entry.index}",
        "",
        f"**源 URL**: {entry.url}",
        f"**源 @作者**: {entry.author or '(unknown)'}",
        f"**源日期**: {entry.date or '(unknown)'}",
        f"**源标题**: {entry.title or '(unknown)'}",
        f"**hook_pattern_id**: `{entry.hook_pattern_id or '(unset)'}`",
        f"**source_classification**: `{entry.classification}`",
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


def render_qualitative_template(date_str: str, mode_note: str, results_by_niche: dict[str, list[dict]]) -> str:
    lines = [
        f"# P2-4 LLM 改写真实模式 · Founder qualitative signoff",
        "",
        f"**Date**: {date_str}",
        f"**Mode**: {mode_note}",
        f"**Acceptance bar**: 4/5 per niche \"我会把这个版本发出去\"",
        "",
        "Read each output file and tick the checkbox. If you want changes, write them under 调整诉求.",
        "Note: rows tagged `negative_ref` are intentional anti-patterns; accept the rewrite if it injects an H1-H8 hook and avoids the bare-title leak. `edge_case` rows test brand/efficacy boundary — accept if no brand name / no functional claim.",
        "",
    ]
    for niche, items in results_by_niche.items():
        lines.append(f"## {niche}")
        lines.append("")
        for item in items:
            entry: URLEntry = item["entry"]
            output_path = item["output_md_relpath"]
            cls_tag = f" `[{entry.classification}]`" if entry.classification != "positive" else ""
            lines.append(f"### #{entry.index} {entry.title or entry.url}{cls_tag}")
            lines.append("")
            lines.append(f"- 源: {entry.url}")
            lines.append(f"- hook_pattern_id: `{entry.hook_pattern_id or '(unset)'}`")
            lines.append(f"- output: [{output_path}]({output_path})")
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
    lines.append("- LLM 模式跑一次需 `CASCADE_REWRITE_UPSTREAM=llm GOOGLE_API_KEY=...`;fixture 模式作为离线回归基线")
    return "\n".join(lines)


def render_mechanical_summary(date_str: str, mode_note: str, results_by_niche: dict[str, list[dict]]) -> str:
    lines = [
        f"# P2-4 LLM 改写真实模式 · 机械检查汇总",
        "",
        f"**Date**: {date_str}",
        f"**Mode**: {mode_note}",
        "",
    ]
    for niche, items in results_by_niche.items():
        if not items:
            lines.append(f"## {niche} — (no URLs)")
            lines.append("")
            continue
        passes = sum(1 for it in items if it["mechanical_pass"])
        lines.append(f"## {niche} — {passes}/{len(items)} 全过")
        lines.append("")
        for it in items:
            entry: URLEntry = it["entry"]
            mark = "✅" if it["mechanical_pass"] else "❌"
            fails = [name for name, passed, _ in it["checks"] if not passed]
            extra = f" (fail: {', '.join(fails)})" if fails else ""
            cls_tag = f" `[{entry.classification}]`" if entry.classification != "positive" else ""
            lines.append(f"- {mark} #{entry.index} `{entry.hook_pattern_id or '?'}`{cls_tag} {entry.url}{extra}")
        lines.append("")
    return "\n".join(lines)


# --- Main loop --------------------------------------------------------------


async def run(niches: list[str], dry_run: bool) -> dict:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-4_llm_outputs_{date_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    entries_by_niche = parse_url_entries(URL_FILE)
    results_by_niche: dict[str, list[dict]] = {}
    total_cost = 0.0
    total_runs = 0
    total_failed = 0

    upstream = os.environ.get("CASCADE_REWRITE_UPSTREAM", "fixture")
    mode_note = f"CASCADE_REWRITE_UPSTREAM={upstream} (analysis source: synthesized from founder annotations in real_urls_for_p2-4.md)"

    for niche in niches:
        entries = entries_by_niche.get(niche, [])
        results_by_niche[niche] = []

        if not entries:
            print(f"[{niche}] no URL entries parsed — skipping")
            continue

        niche_dir = out_dir / niche
        niche_dir.mkdir(parents=True, exist_ok=True)

        for entry in entries:
            print(f"[{niche}] url #{entry.index}: {entry.url}")
            print(f"  hook={entry.hook_pattern_id or '?'} cls={entry.classification} title={entry.title[:60]!r}")
            if dry_run:
                continue

            try:
                contract = synthesize_contract_from_entry(entry)
                extras = {
                    "hook_pattern_id": entry.hook_pattern_id,
                    "source_classification": entry.classification,
                    "source_title": entry.title,
                    "source_author": entry.author,
                }
                result = await rewrite_for_niche(contract, niche, extras=extras)
                checks = mechanical_checks(result, niche, source_title=entry.title)
                pass_count = sum(1 for _, p, _ in checks if p)
                ok = mechanical_pass(checks)
                cost = float(result.get("cost_cny") or 0)
                total_cost += cost
                total_runs += 1

                (niche_dir / f"url{entry.index}_output.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                md = render_output_md(entry, result, checks)
                (niche_dir / f"url{entry.index}_output.md").write_text(md, encoding="utf-8")

                results_by_niche[niche].append({
                    "entry": entry,
                    "output_md_relpath": f"p2-4_llm_outputs_{date_str}/{niche}/url{entry.index}_output.md",
                    "mechanical_pass": ok,
                    "checks": checks,
                    "cost_cny": cost,
                })

                mark = "✅" if ok else "❌"
                print(f"  {mark} {pass_count}/{len(checks)} checks · ¥{cost:.4f}")
            except Exception as exc:
                total_failed += 1
                print(f"  ❌ ERROR: {exc.__class__.__name__}: {exc}")
                results_by_niche[niche].append({
                    "entry": entry,
                    "output_md_relpath": "(error — no output)",
                    "mechanical_pass": False,
                    "checks": [("execution", False, str(exc))],
                    "cost_cny": 0.0,
                })

    if not dry_run:
        mech_summary = render_mechanical_summary(date_str, mode_note, results_by_niche)
        (REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-4_mechanical_{date_str}.md").write_text(
            mech_summary, encoding="utf-8"
        )
        qual_template = render_qualitative_template(date_str, mode_note, results_by_niche)
        (REPO_ROOT / "docs" / "nexus" / "founder_log" / f"p2-4_qualitative_signoff_{date_str}.md").write_text(
            qual_template, encoding="utf-8"
        )

    return {
        "date": date_str,
        "mode": upstream,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "total_runs": total_runs,
        "total_failed": total_failed,
        "total_cost_cny": round(total_cost, 4),
        "results_by_niche": {n: len(items) for n, items in results_by_niche.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P2-4 LLM-mode runner (v2.0, founder-annotated)")
    parser.add_argument("--niche", default="all", choices=("all",) + NICHES)
    parser.add_argument("--dry-run", action="store_true", help="parse URLs and print plan; no LLM calls")
    args = parser.parse_args()

    niches = list(NICHES) if args.niche == "all" else [args.niche]

    # Default to fixture mode (no API key required). Caller can override:
    # `CASCADE_REWRITE_UPSTREAM=llm GOOGLE_API_KEY=...`
    if os.environ.get("CASCADE_REWRITE_UPSTREAM") not in {"fixture", "llm"}:
        os.environ["CASCADE_REWRITE_UPSTREAM"] = "fixture"

    if not URL_FILE.exists():
        print(f"FATAL: {URL_FILE.relative_to(REPO_ROOT)} does not exist. Have founder paste URLs first.")
        return 2

    summary = asyncio.run(run(niches, args.dry_run))
    print("---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"qualitative template: docs/nexus/founder_log/p2-4_qualitative_signoff_{summary['date']}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
