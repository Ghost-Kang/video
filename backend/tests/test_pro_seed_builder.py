"""seed_builder 单测(monkeypatch 异步加载器/LLM,不依赖 DB)。

新形态(境内创作流):Script 卡 + 每分镜 Prompt→Generate→Video→Preview,无 Model/neg。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from agent.comfyui.compiler import estimate_graph_cost, validate_graph
from agent.comfyui.seed_builder import (
    SeedBuildError,
    build_seed_graph,
    build_seed_graph_from_script,
    build_seed_graph_from_theme,
)
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
        rewrite_id="rw_x", analysis_id="ana_x", niche="generic", script_markdown="# 脚本正文",
        shots=[
            RewriteShot(shot_index=1, dialogue="口播1", visual="画面1"),
            RewriteShot(shot_index=2, dialogue="口播2", visual="画面2"),
            RewriteShot(shot_index=3, dialogue="口播3", visual="画面3"),
        ],
        parser_warnings=[], confidence=0.8, cost_cny=1.0, model="doubao",
    )


def _types(graph):
    out = {}
    for n in graph["nodes"]:
        out[n["type"]] = out.get(n["type"], 0) + 1
    return out


def _patch(monkeypatch, *, contract=None, pointers=("ana_x", "rw_x"), rewrite_raw=None,
           recent_raw=None, shot_assets=None, char_anchors=None, scene_anchors=None):
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
        return (char_anchors or []) if kind == "character" else (scene_anchors or [])

    monkeypatch.setattr("agent.cascade.persistence.analyses_repo.load_analysis", load_analysis)
    monkeypatch.setattr("agent.cascade.persistence.session_results_repo.load_pointers", load_pointers)
    monkeypatch.setattr("agent.cascade.persistence.rewrites_repo.load_rewrite_by_id", load_rewrite_by_id)
    monkeypatch.setattr("agent.cascade.persistence.rewrites_repo.load_recent_rewrite", load_recent_rewrite)
    monkeypatch.setattr("agent.cascade.persistence.shot_assets_repo.load_shot_assets", load_shot_assets)
    monkeypatch.setattr("agent.cascade.anchors.list_anchors", list_anchors)


def test_seed_from_rewrite_creation_flow(monkeypatch):
    _patch(monkeypatch, contract=_contract(), rewrite_raw=_rewrite().model_dump_json())
    g = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(g)
    assert g["meta"]["source"] == "rewrite"
    t = _types(g)
    assert t["Script"] == 1 and t.get("Model", 0) == 0  # 脚本卡有、无 Model 节点
    assert t["Prompt"] == 3 and t["Generate"] == 3 and t["Video"] == 3
    assert t["Compose"] == 1 and t["Preview"] == 1  # 末端合成成片 + 一个成片预览
    # 脚本卡承载整篇脚本
    script = next(n for n in g["nodes"] if n["id"] == "script_main")
    assert script["params"]["script_markdown"] == "# 脚本正文"
    # 分镜带镜号 label + 画面文案
    p1 = next(n for n in g["nodes"] if n["id"] == "prompt_1")
    assert p1["params"]["text"] == "画面1" and "镜1" in p1["label"]
    # 链路:prompt→gen→vid→compose→prev
    handles = {(e["source"].split("_")[0], e["target"].split("_")[0]) for e in g["edges"]}
    assert ("prompt", "gen") in handles and ("gen", "vid") in handles
    assert ("vid", "compose") in handles and ("compose", "prev") in handles
    # 所有分镜视频都连到 Compose
    compose_in = [e for e in g["edges"] if e["target"] == "compose_main" and e["targetHandle"] == "videos"]
    assert len(compose_in) == 3


def test_seed_marks_cached(monkeypatch):
    _patch(monkeypatch, contract=_contract(), rewrite_raw=_rewrite().model_dump_json(),
           shot_assets=[{"shot_index": 1, "image_url": "https://x/1.png", "video_url": None}])
    g = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    g1 = next(n for n in g["nodes"] if n["id"] == "gen_1")
    assert g1["cached"] is True and g1["cached_url"] == "https://x/1.png"
    assert g["meta"]["cached_shots"] == 1
    est = estimate_graph_cost(g)
    # gen_1 cached → skip;gen_2/3 billable(2)+ vid_1/2/3 billable(3)= 5
    assert est["billable_node_count"] == 5 and est["cached_skipped"] == 1


def test_seed_anchor_wired_to_generate(monkeypatch):
    anchors = [SimpleNamespace(id="anc_1", image_url="https://x/c.png", label="主角", kind="character")]
    _patch(monkeypatch, contract=_contract(), rewrite_raw=_rewrite().model_dump_json(), char_anchors=anchors)
    g = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(g)
    img_edges = [e for e in g["edges"] if e["targetHandle"] == "image" and e["target"].startswith("gen_")]
    assert len(img_edges) == 3 and all(e["source"].startswith("anchor_character") for e in img_edges)


def test_seed_fallback_to_scenes(monkeypatch):
    _patch(monkeypatch, contract=_contract(scenes=4), pointers=(None, None), rewrite_raw=None, recent_raw=None)
    g = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(g)
    assert g["meta"]["source"] == "analysis" and g["meta"]["shot_count"] == 4
    assert next(n for n in g["nodes"] if n["id"] == "prompt_1")["params"]["text"] == "场景1画面"


def test_seed_analysis_not_found(monkeypatch):
    _patch(monkeypatch, contract=None)
    with pytest.raises(SeedBuildError) as ei:
        asyncio.run(build_seed_graph("ana_missing", "u1", thread_id="t1"))
    assert ei.value.code == "analysis_not_found"


def test_seed_duplicate_shot_index_unique_ids(monkeypatch):
    rw = RewriteResult(
        rewrite_id="rw_d", analysis_id="ana_x", niche="generic", script_markdown="x",
        shots=[
            RewriteShot(shot_index=1, dialogue="d1", visual="画面1"),
            RewriteShot(shot_index=1, dialogue="d2", visual="画面2"),
            RewriteShot(shot_index=2, dialogue="d3", visual="画面3"),
        ],
        parser_warnings=[], confidence=0.8, cost_cny=1.0, model="doubao",
    )
    _patch(monkeypatch, contract=_contract(), rewrite_raw=rw.model_dump_json())
    g = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(g)
    gen_ids = [n["id"] for n in g["nodes"] if n["type"] == "Generate"]
    assert len(gen_ids) == len(set(gen_ids)) == 3


def test_seed_resilient_when_rewrite_load_raises(monkeypatch):
    async def boom(rid):
        raise RuntimeError("db down")

    _patch(monkeypatch, contract=_contract(), recent_raw=None)
    monkeypatch.setattr("agent.cascade.persistence.rewrites_repo.load_rewrite_by_id", boom)
    g = asyncio.run(build_seed_graph("ana_x", "u1", thread_id="t1"))
    validate_graph(g)
    assert g["meta"]["source"] == "analysis"


# ── 主题路径 ─────────────────────────────────────────────────────────────────────


def test_seed_from_theme(monkeypatch):
    async def fake_gen(theme):
        return {
            "script_markdown": "# 关于" + theme,
            "shots": [
                {"shot_index": 1, "visual": "开场画面", "dialogue": "钩子"},
                {"shot_index": 2, "visual": "正文画面", "dialogue": "讲解"},
            ],
            "model": "doubao",
        }

    monkeypatch.setattr("agent.comfyui.script_gen.generate_script_from_theme", fake_gen)
    monkeypatch.setattr("agent.cascade.anchors.list_anchors", lambda **k: _empty())
    g = asyncio.run(build_seed_graph_from_theme("宝宝辅食", "u1"))
    validate_graph(g)
    assert g["meta"]["source"] == "theme" and g["meta"]["shot_count"] == 2
    t = _types(g)
    assert t["Script"] == 1 and t["Generate"] == 2 and t["Video"] == 2 and t["Compose"] == 1 and t["Preview"] == 1
    assert next(n for n in g["nodes"] if n["id"] == "prompt_1")["params"]["text"] == "开场画面"


def test_seed_from_script_regen(monkeypatch):
    async def fake_shots(script):
        return {
            "script_markdown": script,
            "shots": [
                {"shot_index": 1, "visual": "改后画面1", "dialogue": ""},
                {"shot_index": 2, "visual": "改后画面2", "dialogue": ""},
            ],
            "model": "doubao",
        }

    monkeypatch.setattr("agent.comfyui.script_gen.generate_shots_from_script", fake_shots)
    monkeypatch.setattr("agent.cascade.anchors.list_anchors", lambda **k: _empty())
    g = asyncio.run(build_seed_graph_from_script("# 用户编辑后的脚本", "u1"))
    validate_graph(g)
    assert g["meta"]["source"] == "script_regen"
    # 保留用户编辑的脚本文本
    assert next(n for n in g["nodes"] if n["id"] == "script_main")["params"]["script_markdown"] == "# 用户编辑后的脚本"
    t = _types(g)
    assert t["Generate"] == 2 and t["Video"] == 2 and t["Compose"] == 1 and t["Preview"] == 1
    assert next(n for n in g["nodes"] if n["id"] == "prompt_1")["params"]["text"] == "改后画面1"


async def _empty():
    return []
