from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.rewrite_service import (
    RewriteResult,
    RewriteShot,
    error_payload,
    request_rewrite,
)


def _use_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "messages.db"
    monkeypatch.setenv("CASCADE_DB_PATH", str(db_path))
    monkeypatch.setenv("CASCADE_UPSTREAM", "fixture")
    return db_path


async def _analysis() -> str:
    contract = await request_shallow_analysis(
        "https://example.com/rewrite-source",
        user_id="u1",
        run_id="r1",
    )
    return contract.analysis_id


def _events(db_path: Path, name: str) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    rows = db.execute("SELECT payload_json FROM events WHERE event_name = ? ORDER BY id", (name,)).fetchall()
    db.close()
    return [json.loads(row[0]) for row in rows]


def test_happy_path_returns_rewrite_and_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    result = asyncio.run(
        request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1", run_id="r1")
    )
    assert isinstance(result, RewriteResult)
    assert result.rewrite_id.startswith("rw_")
    assert len(_events(db_path, "script_rewritten")) == 1


def test_generic_niche_with_topic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """D3 — request_rewrite accepts niche='generic' + a one-line topic, round-trips
    through the service (cache/event) without error."""
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    result = asyncio.run(
        request_rewrite(
            analysis_id=analysis_id,
            niche="generic",
            user_id="u1",
            run_id="r1",
            topic="周末露营装备清单",
        )
    )
    assert isinstance(result, RewriteResult)
    assert result.niche == "generic"
    assert "周末露营装备清单" in result.script_markdown
    assert len(_events(db_path, "script_rewritten")) == 1


def test_unknown_analysis_raises_lookup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    with pytest.raises(LookupError):
        asyncio.run(request_rewrite(analysis_id="missing", niche="baomam_fushi", user_id="u1"))


def test_unsupported_niche_raises_hard_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_rewrite(analysis_id=analysis_id, niche="bad", user_id="u1"))  # type: ignore[arg-type]
    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD


def test_cost_cap_exceeded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    monkeypatch.setattr("agent.cascade.rewrite_service.predict_rewrite_cost", lambda *_: 3.01)
    with pytest.raises(HardFailure) as exc:
        asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    assert exc.value.code == FailureCode.S8_UPSTREAM_REFUSED
    assert _events(db_path, "script_rewritten") == []


def test_idempotency_within_24h(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    first = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    second = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    assert second.rewrite_id == first.rewrite_id
    assert len(_events(db_path, "script_rewritten")) == 1


def test_revision_bump_invalidates_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """B2 — 改写解封 guard: bumping REWRITE_PIPELINE_REVISION must invalidate the
    24h cache so a stale (e.g. fixture-era) row is NOT served after the flip.

    Within the same revision the rewrite is cached (idempotent). Simulate the
    unseal by bumping the revision the repo writes/reads; the prior row now has
    an older pipeline_revision and must miss → a fresh rewrite is generated.
    """
    from agent.cascade.persistence import rewrites_repo

    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())

    first = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    # same revision → cache hit (idempotent)
    cached = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    assert cached.rewrite_id == first.rewrite_id
    assert len(_events(db_path, "script_rewritten")) == 1

    # 改写解封: bump the revision the repo stamps + filters on.
    monkeypatch.setattr(rewrites_repo, "REWRITE_PIPELINE_REVISION", rewrites_repo.REWRITE_PIPELINE_REVISION + 1)
    after_bump = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    # old row (lower revision) must NOT be served → regenerated → new event
    assert len(_events(db_path, "script_rewritten")) == 2
    # and the newly stored row is now readable at the bumped revision
    again = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    assert again.rewrite_id == after_bump.rewrite_id
    assert len(_events(db_path, "script_rewritten")) == 2  # second call cached again


def _stub_rewrite_with_confidence(confidence: float):
    """Replace _rewrite_for_niche with a stub returning a fixed confidence so the
    confidence 质量闸 (D6 二轮) can be exercised deterministically."""

    async def _fn(contract, niche, *, topic=None):  # noqa: ANN001
        return RewriteResult(
            rewrite_id="rw_stub",
            analysis_id=contract.analysis_id,
            niche=niche,
            script_markdown="### 改写脚本\n1. 测试台词\n   画面：测试画面",
            shots=[
                RewriteShot(shot_index=1, dialogue="a", visual="x"),
                RewriteShot(shot_index=2, dialogue="b", visual="y"),
                RewriteShot(shot_index=3, dialogue="c", visual="z"),
            ],
            parser_warnings=[],
            confidence=confidence,
            cost_cny=0.1,
            model="test",
        )

    return _fn


def test_confidence_gate_low_flags_and_skips_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """D6 二轮 confidence 质量闸:自评 < 0.5 → quality_gated=True 且**不入缓存**,
    使「重生」每次都是新尝试(否则 24h 缓存回灌同一条平稿)。"""
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("CASCADE_REWRITE_MIN_CONFIDENCE", "0.5")
    monkeypatch.setattr("agent.config.REWRITE_MIN_CONFIDENCE", 0.5)
    monkeypatch.setattr(
        "agent.cascade.rewrite_service._rewrite_for_niche",
        _stub_rewrite_with_confidence(0.4),
    )
    analysis_id = asyncio.run(_analysis())

    first = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="generic", user_id="u1"))
    assert first.quality_gated is True
    # 低分稿不缓存 → 第二次仍重新生成(非幂等),两次都发 script_rewritten。
    asyncio.run(request_rewrite(analysis_id=analysis_id, niche="generic", user_id="u1"))
    assert len(_events(db_path, "script_rewritten")) == 2


def test_confidence_gate_high_passes_and_caches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """达标稿(≥ 0.5)→ quality_gated=False 且正常入缓存(幂等,只发一次事件)。"""
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    monkeypatch.setattr("agent.config.REWRITE_MIN_CONFIDENCE", 0.5)
    monkeypatch.setattr(
        "agent.cascade.rewrite_service._rewrite_for_niche",
        _stub_rewrite_with_confidence(0.7),
    )
    analysis_id = asyncio.run(_analysis())

    first = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="generic", user_id="u1"))
    assert first.quality_gated is False
    second = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="generic", user_id="u1"))
    assert second.rewrite_id == first.rewrite_id  # cache hit
    assert len(_events(db_path, "script_rewritten")) == 1


def test_multi_user_isolation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    first = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    second = asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u2"))
    assert second.rewrite_id != first.rewrite_id


def test_event_payload_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _use_tmp_db(monkeypatch, tmp_path)
    analysis_id = asyncio.run(_analysis())
    asyncio.run(request_rewrite(analysis_id=analysis_id, niche="baomam_fushi", user_id="u1"))
    payload = _events(db_path, "script_rewritten")[0]
    assert {
        "analysis_id",
        "rewrite_id",
        "niche",
        "parser_warnings",
        "shots_count",
        "confidence",
        "cost_cny",
        "model",
        "had_anchor_reference",
    } <= set(payload)


def test_error_payload_has_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CASCADE_DEBUG_ERRORS", raising=False)
    payload = error_payload(HardFailure(FailureCode.S5_INVALID_PAYLOAD, "detail"))
    assert payload["request_id"]
    assert "debug_detail" not in payload


def test_debug_detail_only_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CASCADE_DEBUG_ERRORS", "1")
    payload = error_payload(HardFailure(FailureCode.S5_INVALID_PAYLOAD, "debug"))
    assert payload["debug_detail"] == "debug"
