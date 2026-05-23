from __future__ import annotations

import asyncio
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.cascade.storage import save_event


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "cost_calibration.py"
SPEC = importlib.util.spec_from_file_location("cost_calibration", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
cost_calibration = importlib.util.module_from_spec(SPEC)
sys.modules["cost_calibration"] = cost_calibration
SPEC.loader.exec_module(cost_calibration)


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    return db_path


async def _seed_generation_cost(call_kind: str, cost_fen: int) -> None:
    await save_event(
        "generation_cost",
        user_id="user_1",
        run_id="run_1",
        payload={
            "run_id": "run_1",
            "call_kind": call_kind,
            "provider": "test",
            "model": "fixture",
            "cost_fen": cost_fen,
            "latency_ms": 1,
            "tokens_in": 0,
            "tokens_out": 0,
            "outcome": "ok",
        },
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def test_report_markdown_file_is_written(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    out_dir = tmp_path / "reports"

    path = asyncio.run(cost_calibration.write_report(out_dir))

    assert path.exists()
    assert path.parent == out_dir
    assert path.name.startswith("cost_calibration_")
    assert path.read_text(encoding="utf-8").startswith("# cost_guard calibration report")


def test_report_includes_known_and_observed_call_kinds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _use_tmp_db(monkeypatch, tmp_path)

    async def go() -> str:
        await _seed_generation_cost("analysis", 20)
        await _seed_generation_cost("rewrite", 120)
        await _seed_generation_cost("shot", 150)
        await _seed_generation_cost("other", 5)
        path = await cost_calibration.write_report(tmp_path / "reports")
        return path.read_text(encoding="utf-8")

    report = asyncio.run(go())

    assert "| analysis |" in report
    assert "| rewrite |" in report
    assert "| shot |" in report
    assert "| other |" in report


def test_drift_marks_warning_ok_and_no_sample(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _use_tmp_db(monkeypatch, tmp_path)

    async def go() -> str:
        for _ in range(10):
            await _seed_generation_cost("analysis", 40)
        await _seed_generation_cost("rewrite", 120)
        path = await cost_calibration.write_report(tmp_path / "reports")
        return path.read_text(encoding="utf-8")

    report = asyncio.run(go())

    # PREDICT_ANALYSIS_CNY raised 2026-05-23 to 1.200 (MediaKit storyline
    # ¥1.00/min + ARK overlay ~¥0.10). 0.400 p95 < 1.200 PREDICT → still OK.
    assert "| analysis | 0.400 | 0.400 | 0.400 | 0.400 | 10 | 1.200 | OK |" in report
    assert "| rewrite | 1.200 | 1.200 | 1.200 | 1.200 | 1 | 1.000 | WARN p95>PREDICT |" in report
    assert "| shot | - | - | - | - | 0 | 1.500 | - |" in report


def test_samples_count_matches_generation_cost_events(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _use_tmp_db(monkeypatch, tmp_path)

    async def go() -> str:
        for idx in range(7):
            await _seed_generation_cost("analysis", 10 + idx)
        path = await cost_calibration.write_report(tmp_path / "reports")
        return path.read_text(encoding="utf-8")

    report = asyncio.run(go())

    assert "samples_count: 7" in report
