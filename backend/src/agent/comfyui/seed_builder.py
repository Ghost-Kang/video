"""分析/主题 → 种子可执行图(Pro 模式核心入口,plan §6 + 创作流愿景)。

把「爆点分析」或「用户输入的主题」deterministic 编译成一张开箱可跑的创作计算图:
    [脚本卡] +  每个分镜: [提示词(画面)] → [生成图(首帧)] → [生成视频(i2v)] → [预览]
character/scene 锚点节点跨镜共享(锚点级联图形化)。已生成(shot_assets 有 url)的镜标 cached
(命中已生成产物,避免重复花钱)。

执行默认走境内:Generate→Seedream、Video→Seedance(per-node 执行器,见 workers/pro_run_pipeline)。
图里**不放 Model/checkpoint 节点**(境内 Seedream 自带模型);Generate.model 可选,故 validate 通过。

字段订正(实读代码):shot 文案 = RewriteShot.visual(不是 plan 的 rewriteText);firstFrame/video 在
shot_assets(image_url/video_url 按 rewrite_id+shot_index)。build_seed_graph 用 thread_id 走
session_results.load_pointers 定位改写,缺则 load_recent_rewrite(generic),再缺降级 analysis.scenes。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agent.comfyui.compiler import CompileError, validate_graph


class SeedBuildError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _x(col: int) -> float:
    return float(80 + col * 300)


def _y(row: int) -> float:
    return float(80 + row * 210)


# ── 核心:一组分镜 → 创作计算图 ───────────────────────────────────────────────────


def _build_graph_from_shots(
    shots: list[dict],
    *,
    script_markdown: str,
    char_anchors: list,
    scene_anchors: list,
    assets_by_shot: dict[int, dict],
    meta: dict[str, Any],
    theme: str = "",
) -> dict[str, Any]:
    """shots = [{shot_index, text}]。返回境内创作图(Script + 每镜 Prompt→Generate→Video→Preview)。"""
    nodes: list[dict] = []
    edges: list[dict] = []
    eid = 0

    def add_edge(src: str, src_h: str, dst: str, dst_h: str) -> None:
        nonlocal eid
        eid += 1
        edges.append({"id": f"e{eid}", "source": src, "sourceHandle": src_h, "target": dst, "targetHandle": dst_h})

    # 脚本卡(信息/可编辑,不执行)。theme 留底支持「改主题→重生整篇」。
    nodes.append(
        {"id": "script_main", "type": "Script", "label": "脚本",
         "params": {"theme": theme or "", "script_markdown": script_markdown or ""}, "x": _x(0), "y": _y(0)}
    )

    # 共享锚点(跨镜复用一份;MVP 取首个 character 锚点作 img2img 参考)
    anchor_nodes: list[str] = []
    ref_anchor_id: str | None = None
    row = 1
    for kind, anchors in (("character", char_anchors), ("scene", scene_anchors)):
        for a in anchors[:3]:
            aid = f"anchor_{kind}_{len(anchor_nodes)}"
            nodes.append(
                {"id": aid, "type": "Anchor", "label": a.label or kind,
                 "params": {"anchor_id": a.id, "image_url": str(a.image_url), "label": a.label, "kind": kind},
                 "x": _x(0), "y": _y(row)}
            )
            anchor_nodes.append(aid)
            if ref_anchor_id is None and kind == "character":
                ref_anchor_id = aid
            row += 1

    video_ids: list[str] = []
    for i, shot in enumerate(shots):
        si = int(shot["shot_index"])
        idx = i + 1  # 节点 id 用连续序号,不用 shot_index(LLM 可能重复)
        text = (shot.get("text") or "").strip()
        asset = assets_by_shot.get(si) or {}
        img_cached = asset.get("image_url")
        vid_cached = asset.get("video_url")
        prompt_id, gen_id, vid_id = f"prompt_{idx}", f"gen_{idx}", f"vid_{idx}"
        mark = f"镜{idx}"

        nodes.append(
            {"id": prompt_id, "type": "Prompt", "label": f"{mark}·画面",
             "params": {"text": text, "role": "positive"}, "x": _x(1), "y": _y(i)}
        )
        nodes.append(
            {"id": gen_id, "type": "Generate", "label": mark, "params": {},
             "cached": bool(img_cached), "cached_url": img_cached, "x": _x(2), "y": _y(i)}
        )
        nodes.append(
            {"id": vid_id, "type": "Video", "label": mark, "params": {},
             "cached": bool(vid_cached), "cached_url": vid_cached, "x": _x(3), "y": _y(i)}
        )

        add_edge(prompt_id, "text", gen_id, "positive")
        if ref_anchor_id is not None:
            add_edge(ref_anchor_id, "image", gen_id, "image")
        add_edge(gen_id, "image", vid_id, "image")
        video_ids.append(vid_id)

    # 末端:合成成片 + 成片预览(所有分镜视频 → Compose → Preview)
    mid_y = _y(max(0, (len(shots) - 1) // 2))
    nodes.append({"id": "compose_main", "type": "Compose", "label": "成片", "params": {}, "x": _x(4), "y": mid_y})
    nodes.append({"id": "prev_final", "type": "Preview", "label": "成片", "params": {}, "x": _x(5), "y": mid_y})
    for vid_id in video_ids:
        add_edge(vid_id, "video", "compose_main", "videos")
    add_edge("compose_main", "video", "prev_final", "image")

    graph: dict[str, Any] = {
        "version": 1,
        "nodes": nodes,
        "edges": edges,
        "meta": {**meta, "shot_count": len(shots), "anchor_count": len(anchor_nodes),
                 "cached_shots": sum(1 for s in shots if assets_by_shot.get(int(s["shot_index"]), {}).get("image_url"))},
    }
    try:
        validate_graph(graph)  # 「不改直接 Run」硬保证
    except CompileError as e:  # pragma: no cover
        raise SeedBuildError("seed_invalid", f"种子图非法({e.code}): {e.message}") from e
    return graph


async def _load_anchors(user_id: str):
    try:
        from agent.cascade.anchors import list_anchors

        return (
            await list_anchors(user_id=user_id, kind="character"),
            await list_anchors(user_id=user_id, kind="scene"),
        )
    except Exception:  # noqa: BLE001
        return [], []


# ── 主题路径(空白入口) ──────────────────────────────────────────────────────────


async def build_seed_graph_from_theme(theme: str, user_id: str) -> dict[str, Any]:
    """主题 → Doubao 生成脚本+分镜 → 创作图。"""
    from agent.comfyui.script_gen import generate_script_from_theme

    result = await generate_script_from_theme(theme)  # 抛 ScriptGenError(路由映射)
    shots = [{"shot_index": s["shot_index"], "text": s["visual"]} for s in result["shots"]]
    char_anchors, scene_anchors = await _load_anchors(user_id)
    return _build_graph_from_shots(
        shots,
        script_markdown=result.get("script_markdown", ""),
        char_anchors=char_anchors,
        scene_anchors=scene_anchors,
        assets_by_shot={},
        meta={"source": "theme", "theme": theme[:200]},
        theme=theme[:500],
    )


async def build_seed_graph_from_script(script_markdown: str, user_id: str) -> dict[str, Any]:
    """脚本卡重生:用户编辑后的脚本 → Doubao 重拆分镜 → 创作图(保留脚本文本)。"""
    from agent.comfyui.script_gen import generate_shots_from_script

    result = await generate_shots_from_script(script_markdown)  # 抛 ScriptGenError
    shots = [{"shot_index": s["shot_index"], "text": s["visual"]} for s in result["shots"]]
    char_anchors, scene_anchors = await _load_anchors(user_id)
    return _build_graph_from_shots(
        shots,
        script_markdown=result.get("script_markdown", ""),
        char_anchors=char_anchors,
        scene_anchors=scene_anchors,
        assets_by_shot={},
        meta={"source": "script_regen"},
    )


# ── 分析路径 ─────────────────────────────────────────────────────────────────────


async def _resolve_rewrite(analysis_id: str, user_id: str, thread_id: str | None):
    from agent.cascade.persistence.rewrites_repo import load_recent_rewrite, load_rewrite_by_id
    from agent.cascade.persistence.session_results_repo import load_pointers
    from agent.cascade.rewrite_service import RewriteResult

    rewrite_id: str | None = None
    raw: str | None = None
    if thread_id:
        try:
            _a, rewrite_id = await load_pointers(user_id, thread_id)
        except Exception:  # noqa: BLE001
            rewrite_id = None
        if rewrite_id:
            try:
                raw = await load_rewrite_by_id(rewrite_id)
            except Exception:  # noqa: BLE001
                raw = None
    if not raw:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        try:
            raw = await load_recent_rewrite(analysis_id=analysis_id, niche="generic", user_id=user_id, since=since)
        except Exception:  # noqa: BLE001
            raw = None
    if not raw:
        return None, rewrite_id
    try:
        rw = RewriteResult.model_validate_json(raw)
        return rw, rw.rewrite_id
    except Exception:  # noqa: BLE001
        return None, rewrite_id


async def build_seed_graph(analysis_id: str, user_id: str, *, thread_id: str | None = None) -> dict[str, Any]:
    """分析 → 创作图。Raises SeedBuildError。"""
    from agent.cascade.persistence.analyses_repo import load_analysis

    if not analysis_id:
        raise SeedBuildError("missing_analysis_id", "缺少 analysis_id")
    contract = await load_analysis(analysis_id)
    if contract is None:
        raise SeedBuildError("analysis_not_found", f"找不到分析:{analysis_id}")

    rewrite, rewrite_id = await _resolve_rewrite(analysis_id, user_id, thread_id)

    assets_by_shot: dict[int, dict] = {}
    if rewrite_id:
        try:
            from agent.cascade.persistence.shot_assets_repo import load_shot_assets

            for a in await load_shot_assets(rewrite_id):
                assets_by_shot[int(a["shot_index"])] = a
        except Exception:  # noqa: BLE001
            assets_by_shot = {}

    if rewrite and rewrite.shots:
        shots = [{"shot_index": s.shot_index, "text": (s.visual or s.dialogue or "").strip()} for s in rewrite.shots]
        script_md = rewrite.script_markdown or ""
        source = "rewrite"
    else:
        shots = [{"shot_index": sc.scene_index, "text": (sc.visual_content or sc.visual_summary or "").strip()} for sc in contract.scenes]
        script_md = ""
        source = "analysis"
    if not shots:
        raise SeedBuildError("no_shots", "分析既无改写镜也无场景,无法生成种子图")

    char_anchors, scene_anchors = await _load_anchors(user_id)
    return _build_graph_from_shots(
        shots,
        script_markdown=script_md,
        char_anchors=char_anchors,
        scene_anchors=scene_anchors,
        assets_by_shot=assets_by_shot,
        meta={"analysis_id": analysis_id, "rewrite_id": rewrite_id, "source": source},
    )
