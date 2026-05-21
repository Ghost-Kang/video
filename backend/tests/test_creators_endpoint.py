"""Tests for storage.list_creators() — P3-3 backend (admin creator view)."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.cascade.anchors import create_anchor
from agent.cascade.events import emit
from agent.cascade.storage import list_creators


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


async def _emit_event(event_name: str, *, user_id: str, run_id: str | None = None, payload: dict | None = None):
    """Helper — fills in required event payload fields with placeholders."""
    base: dict = {
        "run_started": {"entry_kind": "test", "niche_text_len": 0, "niche_text_hash": "x"},
        "script_rewritten": {"shot_count": 4, "script_char_len": 200, "parser_warnings": 0},
        "publish_pack_copied": {
            "shot_count_in_pack": 4,
            "has_title": True,
            "has_tags": True,
            "script_char_len": 100,
        },
        "interview_logged": {
            "value_statement_match": True,
            "would_pay_39": True,
            "notes_url": "https://example.com/n",
            "niche": "baomam_fushi",
        },
    }.get(event_name, {})
    merged = dict(base)
    if payload:
        merged.update(payload)
    await emit(event_name, user_id=user_id, run_id=run_id, payload=merged)


def test_empty_db_returns_empty_list(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    creators = asyncio.run(list_creators())
    assert creators == []


def test_single_user_three_runs(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        for i in range(3):
            await _emit_event("run_started", user_id="u_alpha", run_id=f"r{i}")
        return await list_creators()

    creators = asyncio.run(go())
    assert len(creators) == 1
    c = creators[0]
    assert c["user_id"] == "u_alpha"
    assert c["runs_started"] == 3
    assert c["rewrites_completed"] == 0
    assert c["publish_packs_copied"] == 0
    assert c["anchors_count"] == 0


def test_multi_user_isolation(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_event("run_started", user_id="u_alpha", run_id="r1")
        await _emit_event("run_started", user_id="u_alpha", run_id="r2")
        await _emit_event("run_started", user_id="u_beta", run_id="r3")
        await _emit_event("script_rewritten", user_id="u_beta", run_id="r3")
        return await list_creators()

    creators = asyncio.run(go())
    by_id = {c["user_id"]: c for c in creators}
    assert by_id["u_alpha"]["runs_started"] == 2
    assert by_id["u_alpha"]["rewrites_completed"] == 0
    assert by_id["u_beta"]["runs_started"] == 1
    assert by_id["u_beta"]["rewrites_completed"] == 1


def test_anchor_aggregates_show_up(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        # Anchor creation also emits anchor_created so user_id surfaces
        await create_anchor(
            user_id="u_anchor",
            kind="character",
            label="妈妈",
            image_url="https://cdn.example.com/m.png",
            source_run_id="r1",
            source_shot_index=1,
        )
        # Backdoor: bump reuse_count manually to simulate a reuse
        from agent.cascade.storage import db_path
        con = sqlite3.connect(str(db_path()))
        con.execute("UPDATE anchors SET reuse_count = 3 WHERE user_id = 'u_anchor'")
        con.commit()
        con.close()
        return await list_creators()

    creators = asyncio.run(go())
    by_id = {c["user_id"]: c for c in creators}
    assert by_id["u_anchor"]["anchors_count"] == 1
    assert by_id["u_anchor"]["anchors_total_reuse_count"] == 3


def test_interview_logged_flips_boolean(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_event("run_started", user_id="u_int", run_id="r1")
        await _emit_event("interview_logged", user_id="u_int")
        return await list_creators()

    creators = asyncio.run(go())
    by_id = {c["user_id"]: c for c in creators}
    assert by_id["u_int"]["interview_logged"] is True


def test_sort_order_most_recent_first(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_event("run_started", user_id="u_old", run_id="r1")
        await _emit_event("run_started", user_id="u_new", run_id="r2")
        return await list_creators()

    # Backdate u_old's events so it appears last
    creators_first = asyncio.run(go())
    con = sqlite3.connect(str(db_path))
    backdated = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    con.execute("UPDATE events SET created_at = ? WHERE user_id = 'u_old'", (backdated,))
    con.commit()
    con.close()

    creators = asyncio.run(list_creators())
    assert creators[0]["user_id"] == "u_new"
    assert creators[-1]["user_id"] == "u_old"


def test_full_funnel_per_user(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_event("run_started", user_id="u_full", run_id="r1")
        await _emit_event("script_rewritten", user_id="u_full", run_id="r1")
        await _emit_event("publish_pack_copied", user_id="u_full", run_id="r1")
        await create_anchor(
            user_id="u_full",
            kind="scene",
            label="厨房",
            image_url="https://cdn.example.com/k.png",
        )
        return await list_creators()

    creators = asyncio.run(go())
    c = creators[0]
    assert c["user_id"] == "u_full"
    assert c["runs_started"] == 1
    assert c["rewrites_completed"] == 1
    assert c["publish_packs_copied"] == 1
    assert c["anchors_count"] == 1
