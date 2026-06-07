"""Pro 画布图持久化 + 模板:repo 单测 + HTTP route 接缝。"""

from __future__ import annotations

import asyncio

from agent import config
from agent.tools.canvas_persistence import pro_graphs_repo as repo
from agent.transport import http_router


def _tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr("agent.tools.canvas_persistence.db.canvas_db_path", lambda: tmp_path / "canvas.db")


GRAPH = {"version": 1, "nodes": [{"id": "m", "type": "Model"}], "edges": []}


# ── repo ────────────────────────────────────────────────────────────────────────


def test_save_load_graph_roundtrip(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    assert repo.load_graph(user_id="u1", thread_id="t1") is None
    repo.save_graph(user_id="u1", thread_id="t1", graph_json='{"a":1}')
    assert repo.load_graph(user_id="u1", thread_id="t1") == '{"a":1}'
    # upsert overwrites
    repo.save_graph(user_id="u1", thread_id="t1", graph_json='{"a":2}')
    assert repo.load_graph(user_id="u1", thread_id="t1") == '{"a":2}'


def test_graph_scoped_by_user_and_thread(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    repo.save_graph(user_id="u1", thread_id="t1", graph_json="A")
    assert repo.load_graph(user_id="u2", thread_id="t1") is None
    assert repo.load_graph(user_id="u1", thread_id="t2") is None


def test_template_crud(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    tid = repo.save_template(user_id="u1", name="我的模板", graph_json="G")
    assert tid.startswith("tpl_")
    lst = repo.list_templates(user_id="u1")
    assert len(lst) == 1 and lst[0]["name"] == "我的模板" and "graph_json" not in lst[0]
    assert repo.load_template(user_id="u1", template_id=tid) == "G"
    # user isolation
    assert repo.load_template(user_id="u2", template_id=tid) is None
    assert repo.delete_template(user_id="u1", template_id=tid) is True
    assert repo.load_template(user_id="u1", template_id=tid) is None
    assert repo.delete_template(user_id="u1", template_id=tid) is False


# ── routes ──────────────────────────────────────────────────────────────────────


def test_graph_routes_roundtrip(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    s, _, _ = asyncio.run(http_router.handle_pro_graph_post({}, {"thread_id": "t1", "graph": GRAPH, "user_id": "u1"}))
    assert s == 200
    s, body, _ = asyncio.run(http_router.handle_pro_graph_get({"thread_id": ["t1"], "user_id": ["u1"]}, {}))
    assert s == 200 and body["graph"]["nodes"][0]["id"] == "m"


def test_graph_get_empty_returns_null(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    s, body, _ = asyncio.run(http_router.handle_pro_graph_get({"thread_id": ["nope"]}, {}))
    assert s == 200 and body["graph"] is None


def test_graph_post_disabled_403(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", False)
    s, body, _ = asyncio.run(http_router.handle_pro_graph_post({}, {"thread_id": "t1", "graph": GRAPH}))
    assert s == 403


def test_graph_post_missing_args_400(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    s, _, _ = asyncio.run(http_router.handle_pro_graph_post({}, {"thread_id": "t1"}))  # no graph
    assert s == 400


def test_template_routes(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    s, body, _ = asyncio.run(http_router.handle_pro_template_post({}, {"name": "T1", "graph": GRAPH, "user_id": "u1"}))
    assert s == 200
    tid = body["template_id"]
    s, body, _ = asyncio.run(http_router.handle_pro_templates_get({"user_id": ["u1"]}, {}))
    assert s == 200 and any(t["template_id"] == tid for t in body["templates"])
    s, body, _ = asyncio.run(http_router.handle_pro_template_get({"id": [tid], "user_id": ["u1"]}, {}))
    assert s == 200 and body["graph"]["nodes"][0]["id"] == "m"
    s, body, _ = asyncio.run(http_router.handle_pro_template_get({"id": ["tpl_missing"], "user_id": ["u1"]}, {}))
    assert s == 404
    s, body, _ = asyncio.run(http_router.handle_pro_template_delete({}, {"template_id": tid, "user_id": "u1"}))
    assert s == 200 and body["deleted"] is True
