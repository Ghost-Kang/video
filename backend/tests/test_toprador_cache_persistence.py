from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from agent.cascade.storage import (
    cleanup_expired_toprador_cache,
    load_toprador_cache,
    save_toprador_cache,
)


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


def test_save_then_load_returns_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    payload = {"platform": "douyin", "nested": {"score": 1}}

    asyncio.run(save_toprador_cache("hash_a", payload, ttl_s=60))

    assert asyncio.run(load_toprador_cache("hash_a")) == payload


def test_expired_entry_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)

    asyncio.run(save_toprador_cache("hash_expired", {"ok": True}, ttl_s=-1))

    assert asyncio.run(load_toprador_cache("hash_expired")) is None


def test_cache_survives_new_connections(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    payload = {"schema_version": "1.0", "analysis": {"hook": "cold start safe"}}

    asyncio.run(save_toprador_cache("hash_restart", payload, ttl_s=60))

    # save/load use fresh SQLite connections, matching a process restart boundary.
    assert asyncio.run(load_toprador_cache("hash_restart")) == payload


def test_cleanup_expired_entry_preserves_fresh_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)

    asyncio.run(save_toprador_cache("hash_old", {"old": True}, ttl_s=-1))
    asyncio.run(save_toprador_cache("hash_new", {"new": True}, ttl_s=60))

    assert asyncio.run(cleanup_expired_toprador_cache()) == 1
    db = sqlite3.connect(str(db_path))
    rows = db.execute("SELECT source_url_hash, payload_json FROM toprador_cache").fetchall()
    db.close()
    # 存储键含 pipeline revision(#10),故只断言 payload + 数量,键以 hash_new 开头。
    assert len(rows) == 1
    assert json.loads(rows[0][1]) == {"new": True}
    assert rows[0][0].startswith("hash_new")


def test_revision_bump_invalidates_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """#10(bug 审计 2026-06-04):bump ANALYSIS_PIPELINE_REVISION 后旧 toprador 缓存项
    不再命中(键含 revision),避免 schema 变更后喂旧数据。"""
    _use_tmp_db(monkeypatch, tmp_path)
    from agent.cascade.persistence import toprador_cache_repo as repo

    asyncio.run(save_toprador_cache("hash_rev", {"v": 1}, ttl_s=60))
    assert asyncio.run(load_toprador_cache("hash_rev")) == {"v": 1}  # 同 revision 命中
    monkeypatch.setattr(repo, "ANALYSIS_PIPELINE_REVISION", repo.ANALYSIS_PIPELINE_REVISION + 1)
    assert asyncio.run(load_toprador_cache("hash_rev")) is None  # bump 后 miss


def test_distinct_hashes_are_isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)

    asyncio.run(save_toprador_cache("hash_one", {"value": 1}, ttl_s=60))
    asyncio.run(save_toprador_cache("hash_two", {"value": 2}, ttl_s=60))

    assert asyncio.run(load_toprador_cache("hash_one")) == {"value": 1}
    assert asyncio.run(load_toprador_cache("hash_two")) == {"value": 2}
