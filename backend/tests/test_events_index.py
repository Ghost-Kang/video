from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from agent.cascade.events import emit


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


def test_frontend_emitted_events_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Regression (2026-06-04 浏览器真机验证抓出):前端 emit 这 6 个遥测事件,但后端
    EventName allowlist 漏列 → /api/events 400 拒,等待漏斗丢数据。锁死它们是合法事件,
    防再被移出 allowlist。"""
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    names = [
        "analysis_wait_started",
        "analysis_wait_completed",
        "analysis_wait_timeout",
        "analysis_wait_abandoned",
        "pin_escape_shown",
        "pin_escape_action",
    ]
    for n in names:
        asyncio.run(emit(n, user_id="u1", run_id="r1", payload={}))  # 不抛 ValueError
    db = sqlite3.connect(str(db_path))
    got = {r[0] for r in db.execute("SELECT DISTINCT event_name FROM events").fetchall()}
    db.close()
    assert set(names) <= got, f"missing from events table: {set(names) - got}"


def test_funnel_endpoint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Beta 漏斗端点(item D):每阶段去重用户数 + 转化率。"""
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    for u in ("u1", "u2", "u3"):  # 3 发起(emit 宽松 → 建表)
        asyncio.run(emit("analysis_wait_started", user_id=u, run_id="r", payload={}))
    db = sqlite3.connect(str(db_path))
    db.executemany(
        "INSERT INTO events (event_name, user_id, run_id, payload_json, created_at) VALUES (?,?,?,?,?)",
        [
            ("analysis_returned", "u1", "r", "{}", "2026-06-04T00:00:03+00:00"),
            ("analysis_returned", "u2", "r", "{}", "2026-06-04T00:00:04+00:00"),
            ("script_rewritten", "u1", "r", "{}", "2026-06-04T00:00:05+00:00"),
            ("interview_logged", "u1", "r", '{"would_pay_39": true}', "2026-06-04T00:00:06+00:00"),
        ],
    )
    db.commit()
    db.close()
    from agent.transport.http_router import handle_funnel

    status, payload, _ = asyncio.run(handle_funnel({}, {}))
    assert status == 200
    users = {x["label"]: x["users"] for x in payload["stages"]}
    assert users["发起分析"] == 3
    assert users["分析完成"] == 2
    assert users["改写"] == 1
    assert users["草稿图"] == 0
    assert users["付费意向"] == 1
    conv = {x["label"]: x["step_conv"] for x in payload["stages"]}
    assert conv["分析完成"] == round(2 / 3, 3)


def _seed_events(db_path: Path, count: int = 1000) -> None:
    db = sqlite3.connect(str(db_path))
    rows = [
        (
            "failure_emitted" if i % 2 else "run_started",
            f"user_{i % 10}",
            f"run_{i % 25}",
            "{}",
            f"2026-05-22T12:{i // 60:02d}:{i % 60:02d}+00:00",
        )
        for i in range(count)
    ]
    db.executemany(
        """INSERT INTO events (event_name, user_id, run_id, payload_json, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    db.commit()
    db.close()


def _plan_for(db_path: Path, sql: str, params: tuple[str, ...]) -> str:
    db = sqlite3.connect(str(db_path))
    rows = db.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    db.close()
    return " | ".join(str(part) for row in rows for part in row)


def _index_names(db_path: Path) -> set[str]:
    db = sqlite3.connect(str(db_path))
    names = {str(row[1]) for row in db.execute("PRAGMA index_list(events)").fetchall()}
    db.close()
    return names


def test_events_run_id_created_at_query_uses_compound_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(
        emit(
            "failure_emitted",
            user_id="user_1",
            run_id="run_1",
            payload={
                "failure_code": "S3_NO_FORMULA",
                "stage": "analysis",
                "recovery_path_id": "RETRY_WITH_NEW_URL",
            },
        )
    )
    _seed_events(db_path)

    assert "idx_events_thread_ts" in _index_names(db_path)
    plan = _plan_for(
        db_path,
        "SELECT * FROM events WHERE run_id = ? ORDER BY created_at DESC LIMIT 200",
        ("run_7",),
    )

    assert "USING INDEX idx_events_thread_ts" in plan or "SEARCH events USING INDEX" in plan


def test_events_type_created_at_query_uses_compound_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(
        emit(
            "failure_emitted",
            user_id="user_1",
            run_id="run_1",
            payload={
                "failure_code": "S3_NO_FORMULA",
                "stage": "analysis",
                "recovery_path_id": "RETRY_WITH_NEW_URL",
            },
        )
    )
    _seed_events(db_path)

    assert "idx_events_type_ts" in _index_names(db_path)
    plan = _plan_for(
        db_path,
        "SELECT * FROM events WHERE event_name = ? ORDER BY created_at DESC LIMIT 200",
        ("failure_emitted",),
    )

    assert "USING INDEX idx_events_type_ts" in plan or "SEARCH events USING INDEX" in plan
