"""seed_builder.build_seed_graph 单测(monkeypatch 异步加载器,不依赖 DB)。

覆盖:改写路径 / 标缓存 / 锚点级联 / 降级用 scenes / 找不到分析。所有产出图必须 validate 通过。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from agent.comfyui.compiler import estimate_graph_cost, validate_graph
from agent.comfyui.seed_builder import SeedBuildError, build_seed_graph
from agent.cascade.rewrite_service import RewriteResult, RewriteShot


def _contract(scenes=3):
    return SimpleNamespace(
        scenes=[
            SimpleNamespace(scene_index=i, visual_content=f"场景{i}画面", visual_summary=f"摘要{i}")
            for i in range(1, scenes + 1)
        ]
    )


def _rewrite():
    return RewriteResult(
        rewrite_id="rw_x",
        analysis_id="ana_x",
        niche="generic",
        script_markdown="# 脚本",
        shots=[
            RewriteShot(shot_index=1, dialogue="口播1", visual="画面1"),
            RewriteShot(shot_index=2, dialogue="口播2", visual="画面2"),
            RewriteShot(shot_index=3, dialogue="口播3", visual="画面3"),
        ],
        parser_warnings=[],
        confidence=0.8,
        cost_cny=1.0,
        model="doubao",
    )


def _patch(
    monkeypatch,
    *,
    contract=None,
    pointers=("ana_x", "rw_x"),
    rewrite_raw=None,
    recent_raw=None,
    shot_assets=None,
    char_anchors=None,
    scene_anchors=None,
):
    async def load_analysis(aid):
        return contract

    async def load_pointers(uid, tid):
        return pointers

    async def load_rewrite_by_id(rid):
        return rewrite_raw

    async def load_recent_rewrite(*, analysis_id, niche, user_id, since):
        return recent_raw

    async def load_shot_assets(rid):
        return shot_assets or []

    async def list_anchors(*, user_id, kind=None):
        if kind == "character":
            return char_anchors or []
        if kind == "scene":
            return scene_anchors or []
        return []

    monkeypatch.setattr("agent.cascade.persistence.analyses_repo.load_analysis", load_analysis)
    monkeypatch.setattr("agent.cascade.persistence.session_results_repo.load_pointers", load_pointers)
    monkeypatch.setattr("agent.cascade.persistence.rewrites_repo.load_rewrite_by_id", load_rewrite_by_id)
    monkeypatch.setattr("agent.cascade.persistence.rewrites_repo.load_recent_rewrite", load_recent_rewrite)
    monkeypatch.setattr("agent.cascade.persistence.shot_assets_repo.load_shot_assets", load_shot_assets)
    monkeypatch.setattr("agent.cascade.anchors.list_anchors", list_anchors)


def test_seed_from_rewrite(monkeypatch):
    _patch(monkeypatch, contract=_contract(), rewrite_raw=_rewrite().model_dump_json())
    graph = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(graph)  # 不改直接 Run 硬保证
    assert graph["meta"]["source"] == "rewrite"
    assert graph["meta"]["shot_count"] == 3
    # 3 子管线 + 共享 model + 共享 negative
    types = [n["type"] for n in graph["nodes"]]
    assert types.count("Generate") == 3
    assert types.count("Prompt") == 4  # 3 positive + 1 shared negative
    assert any(n["id"] == "model_main" for n in graph["nodes"])
    # prompt text from shot.visual
    p1 = next(n for n in graph["nodes"] if n["id"] == "prompt_1")
    assert p1["params"]["text"] == "画面1"


def test_seed_marks_cached_shots(monkeypatch):
    _patch(
        monkeypatch,
        contract=_contract(),
        rewrite_raw=_rewrite().model_dump_json(),
        shot_assets=[{"shot_index": 1, "image_url": "https://x/1.png", "video_url": None}],
    )
    graph = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    g1 = next(n for n in graph["nodes"] if n["id"] == "gen_1")
    g2 = next(n for n in graph["nodes"] if n["id"] == "gen_2")
    assert g1["cached"] is True and g1["cached_url"] == "https://x/1.png"
    assert g2["cached"] is False
    assert graph["meta"]["cached_shots"] == 1
    # cached generate excluded from cost
    est = estimate_graph_cost(graph)
    assert est["billable_node_count"] == 2
    assert est["cached_skipped"] == 1


def test_seed_with_anchors_wires_img2img(monkeypatch):
    anchors = [SimpleNamespace(id="anc_1", image_url="https://x/char.png", label="主角", kind="character")]
    _patch(
        monkeypatch,
        contract=_contract(),
        rewrite_raw=_rewrite().model_dump_json(),
        char_anchors=anchors,
    )
    graph = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(graph)
    anchor_nodes = [n for n in graph["nodes"] if n["type"] == "Anchor"]
    assert len(anchor_nodes) == 1
    assert anchor_nodes[0]["params"]["anchor_id"] == "anc_1"
    # anchor wired into each generate's image input (img2img)
    img_edges = [e for e in graph["edges"] if e["targetHandle"] == "image" and e["target"].startswith("gen_")]
    assert len(img_edges) == 3
    assert all(e["source"] == anchor_nodes[0]["id"] for e in img_edges)
    # denoise lowered so the reference actually matters
    g1 = next(n for n in graph["nodes"] if n["id"] == "gen_1")
    assert g1["params"]["denoise"] == pytest.approx(0.6)


def test_seed_fallback_to_scenes(monkeypatch):
    _patch(monkeypatch, contract=_contract(scenes=4), pointers=(None, None), rewrite_raw=None, recent_raw=None)
    graph = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(graph)
    assert graph["meta"]["source"] == "analysis"
    assert graph["meta"]["shot_count"] == 4
    p1 = next(n for n in graph["nodes"] if n["id"] == "prompt_1")
    assert p1["params"]["text"] == "场景1画面"


def test_seed_analysis_not_found(monkeypatch):
    _patch(monkeypatch, contract=None)
    with pytest.raises(SeedBuildError) as ei:
        asyncio.run(build_seed_graph("ana_missing", "u1", thread_id="t1"))
    assert ei.value.code == "analysis_not_found"


def test_seed_missing_analysis_id(monkeypatch):
    _patch(monkeypatch, contract=_contract())
    with pytest.raises(SeedBuildError) as ei:
        asyncio.run(build_seed_graph("", "u1"))
    assert ei.value.code == "missing_analysis_id"


def test_seed_no_thread_id_uses_recent_fallback(monkeypatch):
    # no thread_id -> skip pointers, hit load_recent_rewrite
    _patch(monkeypatch, contract=_contract(), rewrite_raw=None, recent_raw=_rewrite().model_dump_json())
    graph = asyncio.run(build_seed_graph("ana_x", "u1"))
    assert graph["meta"]["source"] == "rewrite"
    assert graph["meta"]["rewrite_id"] == "rw_x"


def test_seed_duplicate_shot_index_does_not_crash(monkeypatch):
    """LLM 改写可能出重复 shot_index(RewriteResult 不约束唯一)。节点 id 用连续序号而非 shot_index,
    否则撞 id → duplicate_node_id 让整张种子图 500,破坏「不改直接 Run」。"""
    rw = RewriteResult(
        rewrite_id="rw_dup", analysis_id="ana_x", niche="generic", script_markdown="# x",
        shots=[
            RewriteShot(shot_index=1, dialogue="d1", visual="画面1"),
            RewriteShot(shot_index=1, dialogue="d2", visual="画面2"),  # 重复 index!
            RewriteShot(shot_index=2, dialogue="d3", visual="画面3"),
        ],
        parser_warnings=[], confidence=0.8, cost_cny=1.0, model="doubao",
    )
    _patch(monkeypatch, contract=_contract(), rewrite_raw=rw.model_dump_json())
    graph = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(graph)  # must still be a valid, runnable graph
    assert graph["meta"]["shot_count"] == 3
    gen_ids = [n["id"] for n in graph["nodes"] if n["type"] == "Generate"]
    assert len(gen_ids) == len(set(gen_ids)) == 3  # ids are unique despite dup shot_index


def test_seed_resilient_when_rewrite_load_raises(monkeypatch):
    """load_rewrite_by_id 抛(DB 抖动)不该 500;落到 recent 回落 / scenes 降级。"""
    async def boom(rid):
        raise RuntimeError("db down")

    _patch(monkeypatch, contract=_contract(), recent_raw=None)
    monkeypatch.setattr("agent.cascade.persistence.rewrites_repo.load_rewrite_by_id", boom)
    graph = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(graph)
    assert graph["meta"]["source"] == "analysis"  # fell through to scenes
