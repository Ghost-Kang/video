"""One-shot fixture migration: add toprador 爆点/视频分析 dimensions.

Adds the new ViralAnalysis (summary/theme/material_benefit/main_elements/
micro_innovation/pain_points/emotion_trigger/bgm_style) + per-scene descriptive
fields (theme/segment_*/emotion/visual_summary/audio_*/cinematography/
camera_position/actors/on_screen_text/visual_presentation_style/scene/
props_list/costume/lighting_and_color) + top-level video_summary.

Only ADDS missing keys (never overwrites). Derives sensible content from the
existing old-schema fields so happy fixtures don't trigger W2 fallbacks.
Idempotent. Run from backend/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src" / "agent" / "cascade" / "fixtures"

_SHOT_CN = {
    "close_up": "特写", "medium": "中景", "wide": "全景",
    "aerial": "俯拍", "pov": "第一视角", "unknown": "中景",
}
_MOVE_CN = {
    "static": "固定机位", "push": "推镜", "pull": "拉镜", "pan": "横移",
    "tilt": "俯仰", "tracking": "跟拍", "handheld": "手持", "unknown": "固定机位",
}


def _first_clause(s: str, n: int = 30) -> str:
    s = (s or "").strip()
    for sep in ("，", ",", "。", "!", "?", "！", "？", "\n"):
        i = s.find(sep)
        if i > 0:
            s = s[:i]
            break
    return s[:n]


def migrate_viral(va: dict) -> None:
    hook = va.get("hook", "")
    climax = va.get("climax", "")
    arc = va.get("emotional_arc", "")
    audio = va.get("audio") or {}
    va.setdefault("summary", _first_clause(hook, 60) + "；" + _first_clause(climax, 60) if (hook or climax) else "组合钩子+情绪共鸣,具备传播潜力")
    va.setdefault("theme", "生活分享")
    va.setdefault("material_benefit", "为观众提供可照着做的方法 + 情绪价值")
    va.setdefault("main_elements", va.get("visual_style") or "实拍画面、口播、字幕")
    va.setdefault("micro_innovation", "可加入封面优化、话题引导、片尾互动提升完播与转发")
    va.setdefault("pain_points", _first_clause(hook, 60) or "戳中观众的具体需求")
    va.setdefault("emotion_trigger", _first_clause(arc, 60) or "共鸣感、满足感")
    va.setdefault("bgm_style", audio.get("bgm") or "情绪向背景音乐")


def migrate_scene(sc: dict) -> None:
    scene_desc = sc.get("scene", "")
    vc = sc.get("visual_content", "")
    sc.setdefault("theme", _first_clause(scene_desc, 16) or f"镜头 {sc.get('scene_index', '')}")
    sc.setdefault("segment_note", "")
    sc.setdefault("segment_description", scene_desc)
    sc.setdefault("emotion", "")
    sc.setdefault("visual_summary", _first_clause(vc, 30))
    sc.setdefault("audio_summary", "")
    sc.setdefault("audio_content", sc.get("dialogue_and_narration") or "无")
    sc.setdefault("cinematography", _MOVE_CN.get(sc.get("camera_movement", "static"), ""))
    sc.setdefault("camera_position", _SHOT_CN.get(sc.get("shot_type", "medium"), ""))
    sc.setdefault("actors", sc.get("subject") or "无")
    sc.setdefault("on_screen_text", "无")
    sc.setdefault("visual_presentation_style", "真人实拍")
    # keep `scene` as 场景/环境 (already present); ensure string
    if not isinstance(sc.get("scene"), str):
        sc["scene"] = ""
    sc.setdefault("props_list", "无")
    sc.setdefault("costume", "无")
    sc.setdefault("lighting_and_color", "自然光为主")


def migrate_file(fp: Path) -> bool:
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    changed_before = json.dumps(data, ensure_ascii=False, sort_keys=True)
    data.setdefault("video_summary", "")
    va = data.get("viral_analysis")
    if isinstance(va, dict):
        migrate_viral(va)
    scenes = data.get("scenes")
    if isinstance(scenes, list):
        for sc in scenes:
            if isinstance(sc, dict):
                migrate_scene(sc)
    if json.dumps(data, ensure_ascii=False, sort_keys=True) == changed_before:
        return False
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    n = 0
    for fp in sorted(ROOT.rglob("*.json")):
        # edge_* fixtures intentionally leave viral fields blank to exercise the
        # adapter's fallback path — never migrate them.
        if fp.name.startswith("edge_"):
            continue
        if migrate_file(fp):
            n += 1
            print(f"migrated {fp.relative_to(ROOT)}")
    print(f"\n{n} fixtures migrated")


if __name__ == "__main__":
    sys.exit(main())
