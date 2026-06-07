"""分析 → 种子可执行图(Pro 模式核心入口,plan §6)。

把「爆点拆解分析 + niche 改写 + 锚点」deterministic 地编译成一张**开箱可跑**的计算图:
用户进 Pro 画布看到的是已连好、不改即可 Run 的图,而非空白画布。

每个 rewrite shot → 一条子管线(Prompt → Generate → Preview);character/scene 锚点节点跨镜
共享一份(锚点级联的图形化);已生成(shot_assets 有 image_url)的镜对应 Generate 标 cached
(命中已生成产物,避免重复花钱)。

> 与 plan §6.2/6.3 的字段订正(实读代码):shot 文案 = RewriteShot.visual(不是 rewriteText);
> firstFrame/video 在 shot_assets 表(image_url/video_url),不在 shot 上;build_seed_graph 仅有
> analysis_id+user_id 定位不到改写,故加 thread_id 走 session_results.load_pointers,缺则回落
> load_recent_rewrite(niche='generic'),再缺则降级用 analysis.scenes 直接打底(仍可 Run)。

deterministic、不用 LLM、可复现、便宜、快。产出图保证 validate_graph 通过(「不改直接 Run」硬保证)。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agent.comfyui.compiler import CompileError, validate_graph
from agent.comfyui.node_registry import (
    DEFAULT_CKPT,
    DEFAULT_DENOISE,
)

# 锚点作 img2img 参考时降低 denoise,让参考图真正生效(否则 denoise=1 等于忽略)。
_ANCHOR_DENOISE = 0.6
_NEG_DEFAULT = "低质量, 模糊, 畸形, 多余的手指, 水印"


class SeedBuildError(Exception):
    """种子图构建失败。code 面向前端,message 中文人话。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _x(col: int) -> float:
    return float(80 + col * 320)


def _y(row: int) -> float:
    return float(80 + row * 200)


async def _resolve_rewrite(analysis_id: str, user_id: str, thread_id: str | None):
    """定位本分析对应的改写。返回 (RewriteResult|None, rewrite_id|None)。"""
    from agent.cascade.persistence.rewrites_repo import (
        load_recent_rewrite,
        load_rewrite_by_id,
    )
    from agent.cascade.persistence.session_results_repo import load_pointers
    from agent.cascade.rewrite_service import RewriteResult

    rewrite_id: str | None = None
    raw: str | None = None

    # 主路径:thread 指针 → rewrite_id → by_id(无 niche/时间/版本过滤,最稳)
    if thread_id:
        try:
            _a, rewrite_id = await load_pointers(user_id, thread_id)
        except Exception:  # noqa: BLE001 — best-effort,失败回落
            rewrite_id = None
        if rewrite_id:
            try:
                raw = await load_rewrite_by_id(rewrite_id)
            except Exception:  # noqa: BLE001 — DB 抖动不该 500;落到下方 recent 回落
                raw = None

    # 回落:近 24h 的 generic 改写(lossy,但聊胜于无)
    if not raw:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        try:
            raw = await load_recent_rewrite(
                analysis_id=analysis_id, niche="generic", user_id=user_id, since=since
            )
        except Exception:  # noqa: BLE001
            raw = None

    if not raw:
        return None, rewrite_id
    try:
        rw = RewriteResult.model_validate_json(raw)
        return rw, rw.rewrite_id
    except Exception:  # noqa: BLE001 — 损坏的改写不应拖垮 seeding
        return None, rewrite_id


def _shot_prompts(rewrite, contract) -> list[dict[str, Any]]:
    """统一出一组 {shot_index, text} —— 优先改写 shots,缺则降级用 analysis scenes。"""
    if rewrite and rewrite.shots:
        out = []
        for s in rewrite.shots:
            text = (s.visual or s.dialogue or "").strip()
            out.append({"shot_index": s.shot_index, "text": text})
        return out
    # 降级:用 analysis 场景的画面内容打底
    out = []
    for sc in contract.scenes:
        text = (sc.visual_content or sc.visual_summary or "").strip()
        out.append({"shot_index": sc.scene_index, "text": text})
    return out


async def build_seed_graph(
    analysis_id: str,
    user_id: str,
    *,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """读 analyses/rewrites/anchors/shot_assets → 返回 tldraw 兼容 graph JSON。

    Raises SeedBuildError(找不到分析等)。返回图保证 validate_graph 通过。
    """
    from agent.cascade.persistence.analyses_repo import load_analysis

    if not analysis_id:
        raise SeedBuildError("missing_analysis_id", "缺少 analysis_id")
    contract = await load_analysis(analysis_id)
    if contract is None:
        raise SeedBuildError("analysis_not_found", f"找不到分析:{analysis_id}")

    rewrite, rewrite_id = await _resolve_rewrite(analysis_id, user_id, thread_id)

    # 已生成产物(命中缓存避免重复花钱)
    assets_by_shot: dict[int, dict] = {}
    if rewrite_id:
        try:
            from agent.cascade.persistence.shot_assets_repo import load_shot_assets

            for a in await load_shot_assets(rewrite_id):
                assets_by_shot[int(a["shot_index"])] = a
        except Exception:  # noqa: BLE001 — best-effort
            assets_by_shot = {}

    # 锚点(character/scene,user 维度,跨镜共享)
    char_anchors: list = []
    scene_anchors: list = []
    try:
        from agent.cascade.anchors import list_anchors

        char_anchors = await list_anchors(user_id=user_id, kind="character")
        scene_anchors = await list_anchors(user_id=user_id, kind="scene")
    except Exception:  # noqa: BLE001
        char_anchors, scene_anchors = [], []

    nodes: list[dict] = []
    edges: list[dict] = []
    eid = 0

    def add_edge(src: str, src_h: str, dst: str, dst_h: str) -> None:
        nonlocal eid
        eid += 1
        edges.append(
            {"id": f"e{eid}", "source": src, "sourceHandle": src_h, "target": dst, "targetHandle": dst_h}
        )

    # 共享 Model + 共享 negative Prompt
    nodes.append(
        {"id": "model_main", "type": "Model", "params": {"ckpt_name": DEFAULT_CKPT},
         "x": _x(0), "y": _y(0)}
    )
    nodes.append(
        {"id": "neg_main", "type": "Prompt", "params": {"text": _NEG_DEFAULT, "role": "negative"},
         "x": _x(0), "y": _y(1)}
    )

    # 共享 Anchor 节点(跨镜复用一份)。MVP:取首个 character 锚点作 img2img 参考。
    anchor_nodes: list[str] = []
    ref_anchor_id: str | None = None
    row = 2
    for kind, anchors in (("character", char_anchors), ("scene", scene_anchors)):
        for a in anchors[:3]:  # 防止锚点过多撑爆种子图
            aid = f"anchor_{kind}_{len(anchor_nodes)}"
            nodes.append(
                {
                    "id": aid,
                    "type": "Anchor",
                    "params": {
                        "anchor_id": a.id,
                        "image_url": str(a.image_url),
                        "label": a.label,
                        "kind": kind,
                    },
                    "x": _x(0),
                    "y": _y(row),
                }
            )
            anchor_nodes.append(aid)
            if ref_anchor_id is None and kind == "character":
                ref_anchor_id = aid
            row += 1

    shots = _shot_prompts(rewrite, contract)
    if not shots:
        raise SeedBuildError("no_shots", "分析既无改写镜也无场景,无法生成种子图")

    for i, shot in enumerate(shots):
        si = shot["shot_index"]
        # 节点 id 用连续的循环序号(idx),不用 shot_index —— LLM 改写可能出重复 shot_index
        # (RewriteResult 不约束唯一),直接拿它当 id 会撞 → duplicate_node_id 让整张种子图 500,
        # 破坏「不改直接 Run」保证。shot_index 仅用于资产查找(命中缓存)。
        idx = i + 1
        prompt_id = f"prompt_{idx}"
        gen_id = f"gen_{idx}"
        prev_id = f"prev_{idx}"
        asset = assets_by_shot.get(si) or {}
        cached_url = asset.get("image_url")
        is_cached = bool(cached_url)

        nodes.append(
            {"id": prompt_id, "type": "Prompt",
             "params": {"text": shot["text"], "role": "positive"},
             "x": _x(1), "y": _y(i)}
        )
        gen_params: dict[str, Any] = {}
        if ref_anchor_id is not None:
            gen_params["denoise"] = _ANCHOR_DENOISE
        else:
            gen_params["denoise"] = DEFAULT_DENOISE
        gen_node = {
            "id": gen_id, "type": "Generate", "params": gen_params,
            "cached": is_cached, "cached_url": cached_url,
            "x": _x(2), "y": _y(i),
        }
        nodes.append(gen_node)
        nodes.append(
            {"id": prev_id, "type": "Preview", "params": {}, "x": _x(3), "y": _y(i)}
        )

        add_edge("model_main", "model", gen_id, "model")
        add_edge(prompt_id, "text", gen_id, "positive")
        add_edge("neg_main", "text", gen_id, "negative")
        if ref_anchor_id is not None:
            add_edge(ref_anchor_id, "image", gen_id, "image")
        add_edge(gen_id, "image", prev_id, "image")

    graph: dict[str, Any] = {
        "version": 1,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "analysis_id": analysis_id,
            "rewrite_id": rewrite_id,
            "source": "rewrite" if (rewrite and rewrite.shots) else "analysis",
            "shot_count": len(shots),
            "anchor_count": len(anchor_nodes),
            "cached_shots": sum(1 for s in shots if assets_by_shot.get(s["shot_index"], {}).get("image_url")),
        },
    }

    # 「不改直接 Run」硬保证:产出图必须编译通过。
    try:
        validate_graph(graph)
    except CompileError as e:  # pragma: no cover — builder 自身 bug 才会触发
        raise SeedBuildError("seed_invalid", f"种子图非法({e.code}): {e.message}") from e

    return graph
