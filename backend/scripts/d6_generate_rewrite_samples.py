#!/usr/bin/env python
"""D6 — 改写质量人工锚点样例生成器(founder 标「这就是我会发的口吻」)。

founder D6 决策(phase2_kickoff_synthesis_2026-05-31 §3):改写「质量达标」=
Founder 人工锚点 + rubric 辅助。本脚本生成一份 **可勾选的 markdown 工作表**:
对 N 条源(沿用 real_urls_for_p2-4.md 的源 + 一组通用主题)跑 generic 通用代笔
改写,逐条列出改写稿,founder 勾「✅ 我会发」/ 写调整诉求。被标 ✅ 的样例就是
judge 校准锚点 + 解封质量门的人类基线。

用法:
    # 免费、确定性(fixture 路径,验证工作表结构 / 占位)
    uv run python scripts/d6_generate_rewrite_samples.py

    # 真模型(doubao 境内,**会产生 API 成本**,需 ARK_API_KEY)
    uv run python scripts/d6_generate_rewrite_samples.py --mode llm

输出:docs/nexus/founder_log/d6_rewrite_anchors_<date>.md
注意:本脚本**不解封**任何东西 —— 只跑改写生成样例,不动 REWRITE_ENABLED /
CASCADE_REWRITE_UPSTREAM 的部署默认 / REWRITE_PIPELINE_REVISION。
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

# scripts/ 不是包,确保能 import agent.*
import sys

_BACKEND_ROOT = Path(__file__).resolve().parent.parent  # .../backend
_REPO_ROOT = _BACKEND_ROOT.parent  # repo root (where docs/ lives)
sys.path.insert(0, str(_BACKEND_ROOT / "src"))

from agent.cascade.eval.runner import _URL_FILE, _load_p24_helpers  # noqa: E402
from agent.cascade.rewrite import rewrite_for_niche  # noqa: E402

# 通用主题集 —— 跨题材(非宝妈/育儿/厨房),验证去 niche 后通用代笔的口吻覆盖面。
# founder 可在 worksheet 里替换/增删主题。
DEFAULT_TOPICS = [
    "三分钟搞定的减脂早餐",
    "通勤包里我每天必带的 5 样东西",
    "第一次养猫踩过的坑",
    "周末在家把阳台改造成小花园",
    "月薪普通人怎么记账才存得下钱",
]


async def _gen_one(helpers, entry, topic: str) -> dict:
    contract = helpers.synthesize_contract_from_entry(entry)
    extras = {
        "hook_pattern_id": entry.hook_pattern_id,
        "source_classification": entry.classification,
        "source_title": entry.title,
        "source_author": entry.author,
        "topic": topic,
    }
    return await rewrite_for_niche(contract, "generic", extras=extras)


async def _build(mode: str, topics: list[str]) -> str:
    helpers = _load_p24_helpers()
    entries_by_niche = helpers.parse_url_entries(_URL_FILE)
    # 用各旧 niche 的第 1 条源做素材底(只取 viral 结构,改写走 generic+topic)
    sources = [
        entries_by_niche[n][0]
        for n in ("baomam_fushi", "yuer_richang", "jiating_chufang")
        if entries_by_niche.get(n)
    ]

    if mode == "llm":
        os.environ["CASCADE_REWRITE_UPSTREAM"] = "llm"
    else:
        os.environ["CASCADE_REWRITE_UPSTREAM"] = "fixture"

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# D6 改写质量人工锚点 worksheet — {date_str}",
        "",
        f"**模式**: `{mode}`（fixture=确定性占位，免费；llm=真 doubao 境内，有 API 成本）",
        "**怎么用**: 逐条读改写稿，勾「✅ 我会发」= 这就是我会发的口吻（judge 校准锚点）；",
        "否则在「调整诉求」写清哪里不对。被标 ✅ 的样例 = 解封质量门的人类基线。",
        "",
        "> 本 worksheet 不解封任何东西。解封 checklist 见 rewrite_quality_standard_2026-05-31.md。",
        "",
        "---",
        "",
    ]

    idx = 0
    for topic in topics:
        # 每个主题用一条源(轮转),避免同源重复
        entry = sources[idx % len(sources)]
        idx += 1
        result = await _gen_one(helpers, entry, topic)
        script = result["script_markdown"]
        conf = result.get("confidence")
        lines += [
            f"## 主题 #{idx}: {topic}",
            "",
            f"- 源参考: {getattr(entry, 'title', '(n/a)')}",
            f"- confidence: {conf}",
            "",
            "```",
            script,
            "```",
            "",
            "- [ ] ✅ 我会把这个版本发出去（口吻锚点）",
            "- [ ] 还需要调整",
            "",
            "调整诉求（若有）:",
            "",
            "> （空）",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="D6 改写质量人工锚点样例生成器")
    ap.add_argument("--mode", choices=["fixture", "llm"], default="fixture",
                    help="fixture=免费确定性；llm=真 doubao（有成本）")
    ap.add_argument("--topics", nargs="*", default=None, help="覆盖默认主题集")
    args = ap.parse_args()

    topics = args.topics or DEFAULT_TOPICS
    md = asyncio.run(_build(args.mode, topics))

    out_dir = _REPO_ROOT / "docs" / "nexus" / "founder_log"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / f"d6_rewrite_anchors_{date_str}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"[D6] worksheet written → {out_path}  (mode={args.mode}, topics={len(topics)})")


if __name__ == "__main__":
    main()
