"""Tests for storage.list_events() — P4-2 backend (admin events firehose)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agent.cascade.events import emit
from agent.cascade.storage import list_events


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


async def _emit_run_started(user_id: str, run_id: str) -> None:
    await emit(
        "run_started",
        user_id=user_id,
        run_id=run_id,
        payload={"entry_kind": "test", "niche_text_len": 0, "niche_text_hash": "h"},
    )


async def _emit_interview(user_id: str) -> None:
    await emit(
        "interview_logged",
        user_id=user_id,
        run_id=None,
        payload={
            "value_statement_match": True,
            "would_pay_39": True,
            "notes_url": "https://example.com/n",
            "niche": "baomam_fushi",
        },
    )


def test_list_events_returns_reverse_time(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_run_started("u1", "r1")
        await _emit_run_started("u2", "r2")
        await _emit_interview("u1")
        return await list_events(limit=10)

    payload = asyncio.run(go())
    assert payload["has_more"] is False
    assert payload["next_offset"] is None
    names = [e["event_name"] for e in payload["events"]]
    assert names[0] == "interview_logged"
    assert names[-1] == "run_started"
    assert len(payload["events"]) == 3


def test_list_events_filter_by_type(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_run_started("u1", "r1")
        await _emit_run_started("u2", "r2")
        await _emit_interview("u1")
        return await list_events(limit=10, event_name="interview_logged")

    payload = asyncio.run(go())
    assert len(payload["events"]) == 1
    assert payload["events"][0]["event_name"] == "interview_logged"
    assert payload["events"][0]["user_id"] == "u1"


def test_list_events_filter_by_user_id(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_run_started("u1", "r1")
        await _emit_run_started("u2", "r2")
        await _emit_interview("u1")
        return await list_events(limit=10, user_id="u1")

    payload = asyncio.run(go())
    assert len(payload["events"]) == 2
    assert {e["user_id"] for e in payload["events"]} == {"u1"}


def test_list_events_pagination(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        for i in range(5):
            await _emit_run_started("u1", f"r{i}")
        page1 = await list_events(limit=2, offset=0)
        page2 = await list_events(limit=2, offset=2)
        page3 = await list_events(limit=2, offset=4)
        return page1, page2, page3

    page1, page2, page3 = asyncio.run(go())
    assert page1["has_more"] is True
    assert page1["next_offset"] == 2
    assert len(page1["events"]) == 2
    assert page2["has_more"] is True
    assert page2["next_offset"] == 4
    assert page3["has_more"] is False
    assert page3["next_offset"] is None
    assert len(page3["events"]) == 1

    ids_all = (
        [e["id"] for e in page1["events"]]
        + [e["id"] for e in page2["events"]]
        + [e["id"] for e in page3["events"]]
    )
    assert len(set(ids_all)) == 5  # no duplicates across pages


def test_list_events_since_ts(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_run_started("u1", "r1")
        first = await list_events(limit=10)
        cutoff = first["events"][0]["ts"]
        await _emit_run_started("u2", "r2")
        return cutoff, await list_events(limit=10, since_ts=cutoff)

    cutoff, payload = asyncio.run(go())
    assert len(payload["events"]) == 1
    assert payload["events"][0]["user_id"] == "u2"
    assert payload["events"][0]["ts"] > cutoff


def test_list_events_payload_round_trip(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        await _emit_run_started("u1", "r1")
        return await list_events(limit=1)

    payload = asyncio.run(go())
    e = payload["events"][0]
    assert e["payload"]["entry_kind"] == "test"
    assert e["payload"]["niche_text_hash"] == "h"


def test_list_events_validates_limit(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    async def go():
        with pytest.raises(ValueError):
            await list_events(limit=0)
        with pytest.raises(ValueError):
            await list_events(limit=10, offset=-1)

    asyncio.run(go())
