"""「我的成片」库:repo 单测 + HTTP route 接缝。"""

from __future__ import annotations

import asyncio

from agent import config
from agent.tools.canvas_persistence import pro_films_repo as repo
from agent.transport import http_router


def _tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr("agent.tools.canvas_persistence.db.canvas_db_path", lambda: tmp_path / "canvas.db")


def test_film_crud_roundtrip(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    assert repo.list_films(user_id="u1") == []
    f = repo.save_film(user_id="u1", video_url="/media/x/out.mp4", title="片1", thread_id="t1")
    assert f["film_id"].startswith("film_") and f["video_url"] == "/media/x/out.mp4"
    films = repo.list_films(user_id="u1")
    assert len(films) == 1 and films[0]["title"] == "片1"
    repo.delete_film(user_id="u1", film_id=f["film_id"])
    assert repo.list_films(user_id="u1") == []


def test_films_scoped_by_user(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    repo.save_film(user_id="u1", video_url="/media/a.mp4")
    assert repo.list_films(user_id="u2") == []
    assert len(repo.list_films(user_id="u1")) == 1


def test_film_routes(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    # save
    status, body, _ = asyncio.run(http_router.handle_pro_film_post({}, {"video_url": "/media/v.mp4", "user_id": "u1"}))
    assert status == 200 and body["film_id"]
    # list
    status, body, _ = asyncio.run(http_router.handle_pro_films_get({}, {"user_id": "u1"}))
    assert status == 200 and len(body["films"]) == 1
    fid = body["films"][0]["film_id"]
    # delete
    status, body, _ = asyncio.run(http_router.handle_pro_film_delete({}, {"film_id": fid, "user_id": "u1"}))
    assert status == 200 and body["deleted"] is True
    status, body, _ = asyncio.run(http_router.handle_pro_films_get({}, {"user_id": "u1"}))
    assert body["films"] == []


def test_film_save_requires_url(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", True)
    status, body, _ = asyncio.run(http_router.handle_pro_film_post({}, {"user_id": "u1"}))
    assert status == 400 and body["error"] == "video_url_required"


def test_film_routes_flag_off(monkeypatch, tmp_path):
    _tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PRO_CANVAS_ENABLED", False)
    status, body, _ = asyncio.run(http_router.handle_pro_films_get({}, {"user_id": "u1"}))
    assert status == 403
