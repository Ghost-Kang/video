"""一条命令把「一个真实视频」做成落地页样例案例(逐幕视频轮播)。

在 **prod 后端容器** 里跑(它有 DB + 媒体卷 + 网络):

    sudo docker exec cascade-backend sh -lc \
      "cd /app && uv run python scripts/gen_showcase_case.py <抖音链接> <case_id> [品类]"

它会:
  1. 确保这条链接已分析(没有就现在分析一次);
  2. 把它的逐幕 clip + 封面抽到稳定目录 /media/showcase/<case_id>/(永不清理);
  3. 把该分析的 clip_url 重指到稳定路径(这样点进详情页 clip 不会坏);
  4. 打印一段可直接粘进 `frontend/src/lib/sampleCases.ts` 的 `SAMPLE_CASES` 配置
     (含 slides)。把它粘进去、提交、重新部署前端,新案例就上轮播了。

注意:链接必须是我们能解析的抖音视频(完整 URL / iesdouyin / v.douyin.com 短链 / 整段
分享文案均可)。品类不填则用 case_id。
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent.cascade.analysis_service import request_shallow_analysis  # noqa: E402
from agent.cascade.contract import CascadeAnalysisContract  # noqa: E402
from agent.cascade.mediakit.clip_extractor import extract_scene_clips  # noqa: E402
from agent.cascade.mediakit.url_resolver import resolve_to_direct_media  # noqa: E402
from agent.cascade.persistence.db import db_path  # noqa: E402


def _load_contract(con: sqlite3.Connection, source_url: str) -> CascadeAnalysisContract | None:
    row = con.execute(
        "SELECT contract_json FROM analyses WHERE source_url=? ORDER BY created_at DESC LIMIT 1",
        (source_url,),
    ).fetchone()
    return CascadeAnalysisContract.model_validate_json(row[0]) if row else None


def _short(s: str | None, n: int = 44) -> str:
    return (s or "").strip()[:n]


async def main(source_url: str, case_id: str, category: str) -> None:
    con = sqlite3.connect(str(db_path()))

    # 1) 确保已分析
    contract = _load_contract(con, source_url)
    if contract is None:
        print(f"[1/4] 未找到分析,现在分析 {source_url} …(真模型,约 60–120s)")
        contract = await request_shallow_analysis(source_url, user_id="showcase-gen")
    else:
        print(f"[1/4] 命中已有分析 {contract.analysis_id}({len(contract.scenes)} 幕)")

    # 2) 抽取逐幕 clip → 稳定 showcase 目录
    print(f"[2/4] 抽取逐幕 clip → /media/showcase/{case_id}/ …")
    direct_url, _meta = await resolve_to_direct_media(str(contract.source_url))
    clips = await extract_scene_clips(
        direct_url, contract.scenes, f"showcase/{case_id}", duration_s=contract.duration_s
    )
    print(f"      生成 {len(clips)}/{len(contract.scenes)} 幕 clip+poster")
    if not clips:
        print("      ⚠️ 一帧都没抽到(直链失效/ffmpeg?)。终止,不改 DB。")
        return

    # 3) 把该 URL 的所有分析行 clip_url 重指到稳定路径
    print("[3/4] 把该分析的 clip_url 重指到稳定路径 …")
    base = f"/media/showcase/{case_id}"
    n = 0
    for aid, cj in con.execute(
        "SELECT analysis_id, contract_json FROM analyses WHERE source_url=?", (source_url,)
    ).fetchall():
        pj = json.loads(cj)
        for s in pj.get("scenes", []):
            i = s.get("scene_index")
            s["clip_url"] = f"{base}/scene_{i}.mp4"
            s["clip_poster_url"] = f"{base}/scene_{i}.jpg"
        con.execute(
            "UPDATE analyses SET contract_json=? WHERE analysis_id=?",
            (json.dumps(pj, ensure_ascii=False), aid),
        )
        n += 1
    con.commit()
    print(f"      重指 {n} 行")

    # 4) 打印配置
    va = contract.viral_analysis
    cfg = {
        "id": case_id,
        "source_url": source_url,
        "category": category,
        "emoji": "🎬",
        "hook": _short(va.hook, 90),
        "emotion": _short(va.emotion_trigger, 60),
        "slides": [
            {
                "clip": f"{base}/scene_{s.scene_index}.mp4",
                "poster": f"{base}/scene_{s.scene_index}.jpg",
                "theme": s.theme,
                "note": _short(s.visual_summary or s.segment_description or s.theme, 40),
                "emotion": s.emotion,
            }
            for s in sorted(contract.scenes, key=lambda x: x.scene_index)
        ],
    }
    print("[4/4] ✅ 完成。把下面这条对象加进 frontend/src/lib/sampleCases.ts 的 SAMPLE_CASES:\n")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: uv run python scripts/gen_showcase_case.py <source_url> <case_id> [品类]")
        sys.exit(1)
    _src, _cid = sys.argv[1], sys.argv[2]
    _cat = sys.argv[3] if len(sys.argv) > 3 else _cid
    asyncio.run(main(_src, _cid, _cat))
