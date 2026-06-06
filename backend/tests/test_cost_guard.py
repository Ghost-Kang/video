from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.cascade.cost_guard import (
    PREDICT_SHOT_IMAGE_CNY,
    PREDICT_VIDEO_SECOND_CNY,
    cost_guard,
    cost_status,
    predict_generation_cost,
)
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.storage import save_event, utc_now_rfc3339


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    monkeypatch.delenv("CASCADE_RUN_CAP_CNY", raising=False)
    monkeypatch.delenv("CASCADE_USER_DAY_CAP_CNY", raising=False)
    return db_path


async def _cost(user_id: str, run_id: str, fen: int, created_at: str | None = None) -> None:
    await save_event(
        "generation_cost",
        user_id,
        run_id,
        {
            "run_id": run_id,
            "call_kind": "rewrite",
            "provider": "test",
            "model": "test",
            "cost_fen": fen,
            "latency_ms": 1,
            "tokens_in": 0,
            "tokens_out": 0,
            "outcome": "done",
        },
        created_at or utc_now_rfc3339(),
    )


def test_below_80_percent_has_no_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "3.0")  # default raised to ¥25 — pin for the threshold
    asyncio.run(_cost("u1", "r1", 100))
    asyncio.run(cost_guard("u1", "r1", 0.5))
    assert asyncio.run(cost_status("u1", "r1"))["warn"] is False


def test_at_80_percent_warns_without_block(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "3.0")  # default raised to ¥25 — pin for the 80% threshold
    asyncio.run(_cost("u1", "r1", 240))
    asyncio.run(cost_guard("u1", "r1", 0.0))
    assert asyncio.run(cost_status("u1", "r1"))["warn"] is True


def test_run_cap_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "3.0")  # default raised to ¥25 — pin to test the cap mechanism
    asyncio.run(_cost("u1", "r1", 260))
    with pytest.raises(HardFailure) as exc:
        asyncio.run(cost_guard("u1", "r1", 0.5))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED


def test_user_day_cap_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 2_980))
    with pytest.raises(HardFailure):
        asyncio.run(cost_guard("u1", "r2", 0.5))


def test_emit_generation_cost_feeds_day_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """审计 #1-7 修复:cascade._emit_generation_cost 让生成成本进 GENERATION_COST 事件,
    ¥30/天 user 级闸才读得到(此前生成只 emit SHOT_*_RETURNED → cap 读 0 → 失效)。
    且 run_id=None 安全:拦截来自日级闸,run 级因 run_id 错配保持 no-op(不全局卡死)。"""
    _use_tmp_db(monkeypatch, tmp_path)
    from agent.tools.cascade import _emit_generation_cost

    asyncio.run(
        _emit_generation_cost(
            user_id="u1", run_id=None, call_kind="shot_image", cost_cny=29.8, provider="image"
        )
    )
    st = asyncio.run(cost_status("u1", "r1"))
    assert st["user_today_cost_cny"] == 29.8  # 日级成本真读到了
    # 再生成 ¥1.5 → 累计 > ¥30 → 日级闸拦(而非 run 级)
    with pytest.raises(HardFailure):
        asyncio.run(cost_guard("u1", "r2", PREDICT_SHOT_IMAGE_CNY))


def test_costs_are_isolated_by_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 2_980))
    asyncio.run(cost_guard("u2", "r2", 0.5))


def test_utc_day_boundary_excludes_yesterday(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    asyncio.run(_cost("u1", "old", 2_980, yesterday))
    asyncio.run(cost_guard("u1", "new", 0.5))
    assert asyncio.run(cost_status("u1", "new"))["user_today_cost_cny"] == 0


# --- B3: generation-leg cost prediction + enqueue guard ---------------------


def test_predict_generation_cost_image_and_video():
    assert predict_generation_cost("image", n_images=1) == PREDICT_SHOT_IMAGE_CNY
    assert predict_generation_cost("image", n_images=3) == 3 * PREDICT_SHOT_IMAGE_CNY
    assert predict_generation_cost("video", video_seconds=10) == 10 * PREDICT_VIDEO_SECOND_CNY
    # composite/script cost nothing at enqueue (no external paid provider call)
    assert predict_generation_cost("composite") == 0.0
    assert predict_generation_cost("script") == 0.0
    # defensive: negatives clamp to 0
    assert predict_generation_cost("image", n_images=-5) == 0
    assert predict_generation_cost("video", video_seconds=-3) == 0.0


def test_generation_enqueue_blocked_over_run_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An image gen (¥1.5) on top of a run already near the ¥3.0 cap is refused
    BEFORE enqueue → worker never spends. This is the裸奔 hole B3 closes."""
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "3.0")  # default raised to ¥25 — pin for the ¥3 enqueue guard
    asyncio.run(_cost("u1", "r1", 200))  # ¥2.00 already this run
    predicted = predict_generation_cost("image", n_images=1)  # ¥1.50 → 3.50 > 3.0
    with pytest.raises(HardFailure) as exc:
        asyncio.run(cost_guard("u1", "r1", predicted))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED


def test_generation_enqueue_allowed_within_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "3.0")  # default raised to ¥25 — pin for the ¥3 within-cap case
    asyncio.run(_cost("u1", "r1", 100))  # ¥1.00 this run
    predicted = predict_generation_cost("image", n_images=1)  # ¥1.50 → 2.50 ≤ 3.0
    asyncio.run(cost_guard("u1", "r1", predicted))  # must not raise


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "1.0")
    asyncio.run(_cost("u1", "r1", 80))
    with pytest.raises(HardFailure):
        asyncio.run(cost_guard("u1", "r1", 0.3))


def test_generation_cost_sums_match_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    asyncio.run(_cost("u1", "r1", 42))
    asyncio.run(_cost("u1", "r1", 58))
    assert asyncio.run(cost_status("u1", "r1"))["run_cost_cny"] == 1.0
    db = sqlite3.connect(str(db_path))
    total = sum(json.loads(row[0])["cost_fen"] for row in db.execute("SELECT payload_json FROM events"))
    db.close()
    assert total == 100


# --- 2026-06-06: per-run cap revived (audit #1-7 根因 A/C) -------------------
# Until now run_id was hardcoded None in the run ctx → _run_cost(None)≈0 → the
# ¥/run cap was a silent no-op. agent_runner now mints f"{thread_id}#{run_seq}"
# and the generation tools emit GENERATION_COST under that SAME id, so the
# per-run sum finally bites. These guard both the fix and the "改错全挂" risk.


def test_per_run_cap_bites_with_matching_run_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """emit 与 cost_guard 共用同一真 run_id → per-run 累积上限真正生效,且 run 间隔离。"""
    _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "3.0")
    run = "t1#1"
    asyncio.run(_cost("u1", run, 150))  # ¥1.5 this run
    asyncio.run(_cost("u1", run, 150))  # ¥3.0 this run
    # 同 run 再来一笔 → 超 ¥3 → 拦(此前 run_id=None 永远拦不住)
    with pytest.raises(HardFailure) as exc:
        asyncio.run(cost_guard("u1", run, 0.5))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    # 不同 run(同用户)→ per-run 归零 → 放行(证明按 run 隔离,不是全局累加)
    asyncio.run(cost_guard("u1", "t1#2", 0.5))


def test_full_film_turn_not_killed_at_default_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """改错全挂守卫:run_id 生效后,默认 ¥25 cap 必须容纳一次合法满片 turn(~¥18-20),
    否则 normal 多镜生成会被误杀。同样负载压到 ¥3 cap 下必须被拦(证明 cap 仍在工作)。"""
    _use_tmp_db(monkeypatch, tmp_path)  # 默认 cap = 25
    run = "t1#1"
    asyncio.run(_cost("u1", run, 1800))  # ¥18 已花(满片)
    asyncio.run(cost_guard("u1", run, 1.5))  # +¥1.5 = ¥19.5 < 25 → 不抛
    monkeypatch.setenv("CASCADE_RUN_CAP_CNY", "3.0")  # 压低 → 同负载必拦
    with pytest.raises(HardFailure):
        asyncio.run(cost_guard("u1", run, 1.5))


def test_emit_generation_cost_real_run_id_feeds_run_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """cascade._emit_generation_cost 带真 run_id → sum_generation_cost(run_id=...) 命中 →
    cost_status 的 run_cost 与 user_today_cost 同时反映该笔(根因 A/C 闭环验证)。"""
    _use_tmp_db(monkeypatch, tmp_path)
    from agent.tools.cascade import _emit_generation_cost

    run = "t1#9"
    asyncio.run(
        _emit_generation_cost(
            user_id="u1", run_id=run, call_kind="shot_image", cost_cny=1.5, provider="image"
        )
    )
    st = asyncio.run(cost_status("u1", run))
    assert st["run_cost_cny"] == 1.5  # per-run 读到了(此前恒 0)
    assert st["user_today_cost_cny"] == 1.5  # 日级也读到了
