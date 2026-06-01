#!/usr/bin/env python
"""改写解封质量门 · 真 URL eval(generic 通用代笔路径)。

D6 质量门(rewrite_quality_standard §4.1)的批量验证:对一组真实抖音 URL,跑
真实分析 → 真实 generic 改写(真 doubao)→ 机械硬检查 + LLM judge → 汇总报告。

与旧 eval/runner 的区别:旧 runner 从 founder 标注合成 contract(离线确定性)、绑死
3 个 niche;本脚本走**真实管线**(真分析 + 真改写),适配去 niche 后的 generic 路径。

用法(prod 容器或本地,需 ARK_API_KEY):
    CASCADE_REWRITE_UPSTREAM=llm CASCADE_UPSTREAM=doubao_direct TOPRADOR_RESOLVER_MODE=douyin_share \
      uv run python scripts/eval_generic_real_urls.py <urls.txt> [topic_per_line.txt]

urls.txt:一行一个抖音链接(完整 URL / 短链 / 分享文案均可)。可选第 2 文件:
每行对应主题(一句话),空行=不指定主题(沿用原片)。

输出:逐条 confidence + 机械门通过情况 + judge(realism/kept_formula),末尾汇总对照
§4.1 阈值(机械≥85% / realism≥3.8 / kept_formula yes≥70% / ad_risk=0)。不写 DB、不解封。
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent.cascade.analysis_service import request_shallow_analysis  # noqa: E402

# request_shallow_analysis 入口要求整串是 http(s) URL(不抽链接)。但用户常带序号
# 前缀(「1.  https://…」)或整段分享文案。这里先抽出第一个 http(s) 链接,去掉前后噪声。
_URL_RE = re.compile(r"https?://[^\s,)）】]+")


def _extract_url(line: str) -> str | None:
    m = _URL_RE.search(line)
    if not m:
        return None
    # 去掉链接末尾误粘的标点/空白(保留路径里的 /)
    return m.group(0).rstrip(" ,.，。)）】")
from agent.cascade.eval import checks as checks_mod  # noqa: E402
from agent.cascade.eval.judge import judge_one  # noqa: E402
from agent.cascade.rewrite import rewrite_for_niche  # noqa: E402

_NICHE = "generic"


async def _eval_one(url: str, topic: str) -> dict:
    out: dict = {"url": url, "topic": topic, "ok": False}
    try:
        contract = await request_shallow_analysis(url, user_id="eval-gen")
    except Exception as exc:
        out["error"] = f"analysis: {type(exc).__name__}: {str(exc)[:80]}"
        return out
    extras = {"topic": topic} if topic else None
    try:
        result = await rewrite_for_niche(contract, _NICHE, extras=extras)
    except Exception as exc:
        out["error"] = f"rewrite: {type(exc).__name__}: {str(exc)[:80]}"
        return out

    chks = checks_mod.run_checks(result, _NICHE, source_title=getattr(contract.viral_analysis, "theme", ""))
    # mechanical pass = all MANDATORY checks pass (the §3.2 一票否决子集)
    mandatory = [c for c in chks if getattr(c, "mandatory", False)]
    mech_pass = all(c.passed for c in mandatory) if mandatory else True
    # forbidden-term hard check (ad_risk)
    forbidden_ok = next((c.passed for c in chks if c.name == "no_forbidden_terms"), True)

    try:
        judged = judge_one(
            result, niche=_NICHE,
            source_title=getattr(contract.viral_analysis, "theme", ""),
            source_formula=getattr(contract.viral_analysis, "replicable_formula", ""),
        )
    except Exception as exc:
        judged = {"skipped": True, "reason": f"{type(exc).__name__}: {str(exc)[:60]}"}

    jd = judged if isinstance(judged, dict) else {}
    out.update({
        "ok": True,
        "confidence": result.get("confidence"),
        "mech_pass": mech_pass,
        "forbidden_ok": forbidden_ok,
        "mandatory_fails": [c.name for c in mandatory if not c.passed],
        # judge 返回 key 是 realism_1to5 / ad_risk(不是 realism);之前读错 key → 全 None。
        "judge_realism": jd.get("realism_1to5"),
        "judge_kept_formula": jd.get("kept_formula"),
        "judge_ad_risk": jd.get("ad_risk"),  # "yes"/"no" — 质量门要 =no
        "judge_skipped": jd.get("skipped", False),
        "judge_skip_reason": jd.get("reason") if jd.get("skipped") else None,
        "script_len": len(result.get("script_markdown", "") or ""),
    })
    return out


async def main(urls: list[str], topics: list[str]) -> None:
    results = []
    for i, url in enumerate(urls):
        topic = topics[i] if i < len(topics) else ""
        print(f"[{i+1}/{len(urls)}] {url[:60]} … topic={topic or '(none)'}")
        r = await _eval_one(url, topic)
        results.append(r)
        if r["ok"]:
            jskip = f" judge-skip({r.get('judge_skip_reason')})" if r.get("judge_skipped") else ""
            print(f"   conf={r['confidence']} mech={'✓' if r['mech_pass'] else '✗'} "
                  f"forbidden_ok={r['forbidden_ok']} realism={r['judge_realism']} "
                  f"kept={r['judge_kept_formula']} ad_risk={r.get('judge_ad_risk')} "
                  f"len={r['script_len']}{jskip}")
        else:
            print(f"   ✗ {r.get('error')}")

    ok = [r for r in results if r["ok"]]
    n = len(ok) or 1
    mech_rate = sum(1 for r in ok if r["mech_pass"]) / n
    forbidden_rate = sum(1 for r in ok if r["forbidden_ok"]) / n
    realisms = [r["judge_realism"] for r in ok if isinstance(r.get("judge_realism"), (int, float))]
    avg_realism = sum(realisms) / len(realisms) if realisms else None
    kept_yes = sum(1 for r in ok if r.get("judge_kept_formula") == "yes") / n
    ad_risk_n = sum(1 for r in ok if r.get("judge_ad_risk") == "yes")
    judged_n = sum(1 for r in ok if not r.get("judge_skipped"))

    print("\n========== 质量门汇总(对照 rewrite_quality_standard §4.1)==========")
    print(f"成功跑通:           {len(ok)}/{len(results)}  (judge 实评 {judged_n} 条)")
    print(f"机械门通过率:        {mech_rate*100:.0f}%   (门槛 ≥85%)  {'✓' if mech_rate>=0.85 else '✗'}")
    print(f"广告法/禁词 0 泄漏:   {forbidden_rate*100:.0f}%   (门槛 =100%) {'✓' if forbidden_rate>=1.0 else '✗'}")
    print(f"judge realism 均值:  {f'{avg_realism:.2f}' if avg_realism is not None else 'n/a'}   (门槛 ≥3.8)  {'✓' if (avg_realism or 0)>=3.8 else '✗'}")
    print(f"kept_formula=yes:    {kept_yes*100:.0f}%   (门槛 ≥70%)  {'✓' if kept_yes>=0.70 else '✗'}")
    print(f"ad_risk=yes 条数:    {ad_risk_n}    (门槛 =0)    {'✓' if ad_risk_n==0 else '✗'}")
    print("注:人工 signoff(≥70%)+ llm vs fixture 对照 需 founder 看输出 / 另跑 fixture 对照。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: uv run python scripts/eval_generic_real_urls.py <urls.txt> [topics.txt]")
        sys.exit(1)
    # skip blank lines AND # comment lines; extract the bare http(s) URL from each
    # line (tolerates 序号前缀「1.  https://…」/ 整段分享文案). Lines with no URL drop.
    urls = []
    for l in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        if not l.strip() or l.lstrip().startswith("#"):
            continue
        u = _extract_url(l)
        if u:
            urls.append(u)
        else:
            print(f"[skip] 无法从该行抽出链接: {l.strip()[:50]}")
    topics = []
    if len(sys.argv) > 2:
        # topics align by URL index; keep # lines out but preserve blank-line slots
        # is hard once comments are stripped — so topics file should be comment-free.
        topics = [
            l.rstrip("\n")
            for l in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
            if not l.lstrip().startswith("#")
        ]
    asyncio.run(main(urls, topics))
