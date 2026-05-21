"""Tests for the anchor service (P1-6 backend).

Cases mirror docs/nexus/handoff/claude_backend_P1-6.md §5.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.cascade.anchors import (
    Anchor,
    AnchorKind,
    create_anchor,
    get_anchor,
    list_anchors,
    reuse_anchor,
)


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


def _events(db_path: Path, name: str) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute(
        "SELECT payload_json FROM events WHERE event_name = ? ORDER BY id",
        (name,),
    ).fetchall()
    db.close()
    return [json.loads(row[0]) for row in rows]


def _anchor_rows(db_path: Path) -> list[tuple]:
    if not db_path.exists():
        return []
    db = sqlite3.connect(str(db_path))
    try:
        rows = db.execute("SELECT id, user_id, kind, label, reuse_count FROM anchors").fetchall()
    except sqlite3.OperationalError:
        rows = []
    db.close()
    return rows


def _reuse_rows(db_path: Path, anchor_id: str) -> list[tuple]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute(
        "SELECT anchor_id, reused_in_run_id, reused_in_shot_index FROM anchor_reuses WHERE anchor_id = ?",
        (anchor_id,),
    ).fetchall()
    db.close()
    return rows


async def _seed(user_id: str = "u1", **overrides) -> Anchor:
    kwargs: dict = {
        "user_id": user_id,
        "kind": "character",
        "label": "小张妈妈",
        "image_url": "https://cdn.example.com/img.png",
        "source_run_id": "run_001",
        "source_shot_index": 2,
    }
    kwargs.update(overrides)
    return await create_anchor(**kwargs)


# 1. Create OK → row + event
def test_create_anchor_inserts_row_and_emits_event(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    anchor = asyncio.run(_seed())
    assert anchor.id.startswith("anc_")
    assert anchor.kind == AnchorKind.CHARACTER
    assert anchor.reuse_count == 0
    rows = _anchor_rows(db_path)
    assert len(rows) == 1
    assert rows[0][0] == anchor.id
    events = _events(db_path, "anchor_created")
    assert len(events) == 1
    assert events[0]["anchor_id"] == anchor.id
    assert events[0]["anchor_type"] == "character"
    assert events[0]["source_run_id"] == "run_001"


# 2. Label > 40 → ValidationError, no row, no event
def test_create_anchor_label_too_long(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    with pytest.raises(ValidationError):
        asyncio.run(_seed(label="x" * 41))
    assert _anchor_rows(db_path) == []
    db = sqlite3.connect(str(db_path))
    try:
        cnt = db.execute(
            "SELECT COUNT(*) FROM events WHERE event_name='anchor_created'"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        cnt = 0
    db.close()
    assert cnt == 0


# 3. Wrong kind value → ValueError
def test_create_anchor_wrong_kind(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(_seed(kind="bogus"))


# 4. Multi-user isolation
def test_list_anchors_isolates_users(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_seed(user_id="u1", label="a"))
    asyncio.run(_seed(user_id="u2", label="b"))
    u1 = asyncio.run(list_anchors(user_id="u1"))
    u2 = asyncio.run(list_anchors(user_id="u2"))
    assert {a.label for a in u1} == {"a"}
    assert {a.label for a in u2} == {"b"}


# 5. List sort: reuse_count DESC then created_at DESC
def test_list_anchors_sort_order(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    older = asyncio.run(_seed(label="older"))
    newer = asyncio.run(_seed(label="newer"))
    most_used = asyncio.run(_seed(label="mostused"))
    # Bump most_used.reuse_count via reuse
    asyncio.run(
        reuse_anchor(
            anchor_id=most_used.id,
            user_id="u1",
            reused_in_run_id="run_002",
        )
    )
    listed = asyncio.run(list_anchors(user_id="u1"))
    labels = [a.label for a in listed]
    # most_used (reuse_count=1) first; among reuse_count=0, newer before older
    assert labels[0] == "mostused"
    assert labels.index("newer") < labels.index("older")


# 6. Reuse twice → count=2, two reuse rows, two events
def test_reuse_anchor_increments_and_logs(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    anchor = asyncio.run(_seed())
    asyncio.run(
        reuse_anchor(
            anchor_id=anchor.id,
            user_id="u1",
            reused_in_run_id="run_007",
            reused_in_shot_index=3,
        )
    )
    second = asyncio.run(
        reuse_anchor(
            anchor_id=anchor.id,
            user_id="u1",
            reused_in_run_id="run_008",
        )
    )
    assert second.reuse_count == 2
    assert len(_reuse_rows(db_path, anchor.id)) == 2
    events = _events(db_path, "anchor_reused")
    assert len(events) == 2


# 7. is_first_reuse_for_user true once, then false
def test_is_first_reuse_for_user_flag(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    a1 = asyncio.run(_seed(label="a"))
    a2 = asyncio.run(_seed(label="b"))
    asyncio.run(reuse_anchor(anchor_id=a1.id, user_id="u1", reused_in_run_id="run_002"))
    asyncio.run(reuse_anchor(anchor_id=a2.id, user_id="u1", reused_in_run_id="run_003"))
    events = _events(db_path, "anchor_reused")
    assert events[0]["is_first_reuse_for_user"] is True
    assert events[1]["is_first_reuse_for_user"] is False


# 8. days_since_created computed correctly
def test_days_since_created(monkeypatch, tmp_path):
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    anchor = asyncio.run(_seed())
    # Backdate the anchor 3 days
    past = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    db = sqlite3.connect(str(db_path))
    db.execute("UPDATE anchors SET created_at = ? WHERE id = ?", (past, anchor.id))
    db.commit()
    db.close()
    asyncio.run(reuse_anchor(anchor_id=anchor.id, user_id="u1", reused_in_run_id="run_009"))
    events = _events(db_path, "anchor_reused")
    assert events[0]["days_since_created"] >= 3


# 9. Nonexistent anchor → LookupError → 404 at HTTP layer
def test_reuse_nonexistent_anchor(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    with pytest.raises(LookupError):
        asyncio.run(
            reuse_anchor(
                anchor_id="anc_missing",
                user_id="u1",
                reused_in_run_id="run_001",
            )
        )


# 10. Cross-user reuse → PermissionError → 403 at HTTP layer
def test_reuse_cross_user_forbidden(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    anchor = asyncio.run(_seed(user_id="u1"))
    with pytest.raises(PermissionError):
        asyncio.run(
            reuse_anchor(
                anchor_id=anchor.id,
                user_id="u2",
                reused_in_run_id="run_010",
            )
        )


# Extra: get_anchor sanity
def test_get_anchor_roundtrip(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    anchor = asyncio.run(_seed())
    fetched = asyncio.run(get_anchor(anchor.id))
    assert fetched is not None
    assert fetched.id == anchor.id
    assert fetched.label == anchor.label
