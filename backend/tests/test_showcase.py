"""Auto-showcase — repo + gate + endpoints.

Covers the privacy/quality/cost valve (showcase_service.maybe_publish_showcase)
and the data-driven landing source (showcase_repo + GET /api/showcase).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent import config
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.persistence import showcase_repo
from agent.cascade import showcase_service
from agent.cascade.mediakit.clip_extractor import media_root

_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "src" / "agent" / "cascade" / "fixtures" / "rewrite_smoke" / "baomam_fushi" / "ref_001.json"
)


def _contract(confidence: float = 0.9) -> CascadeAnalysisContract:
    raw = {k: v for k, v in json.loads(_FIXTURE.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    c = CascadeAnalysisContract.model_validate(raw)
    return c.model_copy(update={"confidence": confidence})


def _fake_clips(contract: CascadeAnalysisContract, n: int) -> None:
    """Pretend the analysis already extracted clips: drop real files into the
    analysis media dir for the first n scenes (mp4 + jpg)."""
    d = media_root() / contract.analysis_id
    d.mkdir(parents=True, exist_ok=True)
    for s in sorted(contract.scenes, key=lambda x: x.scene_index)[:n]:
        (d / f"scene_{s.scene_index}.mp4").write_bytes(b"\x00\x00\x00fake-mp4")
        (d / f"scene_{s.scene_index}.jpg").write_bytes(b"\xff\xd8fake-jpg")


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    # default gate config sane for tests
    monkeypatch.setattr(config, "AUTO_SHOWCASE_ENABLED", True)
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MIN_CONFIDENCE", 0.85)
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MAX", 24)
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MIN_CLIPS", 3)
    return tmp_path


# ---------- gate ----------


def test_publishes_high_confidence_with_clips(db):
    c = _contract(confidence=0.9)
    _fake_clips(c, n=4)
    case_id = asyncio.run(showcase_service.maybe_publish_showcase(c))
    assert case_id is not None
    cases = asyncio.run(showcase_repo.list_published())
    assert len(cases) == 1
    case = cases[0]
    assert case["source_url"] == str(c.source_url)
    assert len(case["slides"]) >= 3
    assert case["slides"][0]["clip"].startswith(f"/media/showcase/{case_id}/")
    # clips copied into the PERMANENT showcase dir
    assert (media_root() / "showcase" / case_id / f"scene_{c.scenes[0].scene_index}.mp4").exists()


def test_skips_low_confidence(db):
    c = _contract(confidence=0.5)
    _fake_clips(c, n=4)
    assert asyncio.run(showcase_service.maybe_publish_showcase(c)) is None
    assert asyncio.run(showcase_repo.count_published()) == 0


def test_skips_too_few_clips(db):
    c = _contract(confidence=0.9)
    _fake_clips(c, n=2)  # below AUTO_SHOWCASE_MIN_CLIPS=3
    assert asyncio.run(showcase_service.maybe_publish_showcase(c)) is None
    assert asyncio.run(showcase_repo.count_published()) == 0


def test_skips_when_disabled(db, monkeypatch):
    monkeypatch.setattr(config, "AUTO_SHOWCASE_ENABLED", False)
    c = _contract(confidence=0.95)
    _fake_clips(c, n=4)
    assert asyncio.run(showcase_service.maybe_publish_showcase(c)) is None


def test_dedupes_same_source_url(db):
    c = _contract(confidence=0.9)
    _fake_clips(c, n=4)
    first = asyncio.run(showcase_service.maybe_publish_showcase(c))
    assert first is not None
    # same URL again → no second publish
    second = asyncio.run(showcase_service.maybe_publish_showcase(c))
    assert second is None
    assert asyncio.run(showcase_repo.count_published()) == 1


def test_does_not_resurrect_hidden(db):
    c = _contract(confidence=0.9)
    _fake_clips(c, n=4)
    case_id = asyncio.run(showcase_service.maybe_publish_showcase(c))
    assert case_id is not None
    # founder hides it
    assert asyncio.run(showcase_repo.set_status(case_id, "hidden")) is True
    assert asyncio.run(showcase_repo.count_published()) == 0
    # re-analysis of the same URL must NOT republish (respect the takedown)
    assert asyncio.run(showcase_service.maybe_publish_showcase(c)) is None


def test_respects_max_cap(db, monkeypatch):
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MAX", 1)
    c1 = _contract(confidence=0.9)
    _fake_clips(c1, n=4)
    assert asyncio.run(showcase_service.maybe_publish_showcase(c1)) is not None
    # second distinct URL hits the cap
    c2 = c1.model_copy(update={
        "analysis_id": "ana_other",
        "source_url": "https://www.douyin.com/video/999",
    })
    _fake_clips(c2, n=4)
    assert asyncio.run(showcase_service.maybe_publish_showcase(c2)) is None


def test_never_raises_on_bad_input(db):
    # contract with no scenes / no clips → returns None, no exception
    c = _contract(confidence=0.95).model_copy(update={"scenes": []})
    assert asyncio.run(showcase_service.maybe_publish_showcase(c)) is None


# ---------- ranking + displacement (founder: ≤10, rank by confidence, tie→newest) ----------


def test_list_published_ranked_by_confidence_then_recency(db):
    async def seed():
        # insert out of order; expect confidence DESC, then created_at DESC on tie
        await showcase_repo.insert_case(case_id="lo", source_url="u/lo", category="c", emoji=None,
            hook="h", emotion=None, gradient=None, slides=[], confidence=0.70)
        await showcase_repo.insert_case(case_id="hi", source_url="u/hi", category="c", emoji=None,
            hook="h", emotion=None, gradient=None, slides=[], confidence=0.95)
        await showcase_repo.insert_case(case_id="tie_old", source_url="u/tie_old", category="c", emoji=None,
            hook="h", emotion=None, gradient=None, slides=[], confidence=0.90)
        await showcase_repo.insert_case(case_id="tie_new", source_url="u/tie_new", category="c", emoji=None,
            hook="h", emotion=None, gradient=None, slides=[], confidence=0.90)
    asyncio.run(seed())
    ids = [c["id"] for c in asyncio.run(showcase_repo.list_published())]
    # hi(0.95) > tie(0.90, newest first) > lo(0.70)
    assert ids[0] == "hi"
    assert ids.index("tie_new") < ids.index("tie_old")  # tie broken by recency
    assert ids[-1] == "lo"


def test_list_published_caps_at_limit(db):
    async def seed():
        for i in range(15):
            await showcase_repo.insert_case(case_id=f"c{i}", source_url=f"u/{i}", category="c",
                emoji=None, hook="h", emotion=None, gradient=None, slides=[], confidence=0.8 + i * 0.001)
    asyncio.run(seed())
    assert len(asyncio.run(showcase_repo.list_published(limit=10))) == 10


def test_higher_confidence_displaces_weakest_at_cap(db, monkeypatch):
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MAX", 2)
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MIN_CLIPS", 1)
    # fill 2 weak auto cases
    async def seed():
        await showcase_repo.insert_case(case_id="weak1", source_url="u/w1", category="c", emoji=None,
            hook="h", emotion=None, gradient=None, slides=[], confidence=0.86, origin="auto")
        await showcase_repo.insert_case(case_id="weak2", source_url="u/w2", category="c", emoji=None,
            hook="h", emotion=None, gradient=None, slides=[], confidence=0.88, origin="auto")
    asyncio.run(seed())
    # a strong newcomer should displace weak1 (lowest)
    c = _contract(confidence=0.95)
    _fake_clips(c, n=2)
    case_id = asyncio.run(showcase_service.maybe_publish_showcase(c))
    assert case_id is not None
    ids = [x["id"] for x in asyncio.run(showcase_repo.list_published())]
    assert "weak1" not in ids  # weakest evicted
    assert "weak2" in ids and case_id in ids
    assert len(ids) == 2  # still capped


def test_weak_newcomer_does_not_displace(db, monkeypatch):
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MAX", 1)
    monkeypatch.setattr(config, "AUTO_SHOWCASE_MIN_CLIPS", 1)
    asyncio.run(showcase_repo.insert_case(case_id="strong", source_url="u/s", category="c", emoji=None,
        hook="h", emotion=None, gradient=None, slides=[], confidence=0.95, origin="auto"))
    c = _contract(confidence=0.86)  # weaker than incumbent
    _fake_clips(c, n=2)
    assert asyncio.run(showcase_service.maybe_publish_showcase(c)) is None
    assert [x["id"] for x in asyncio.run(showcase_repo.list_published())] == ["strong"]


# ---------- repo status ----------


def test_set_status_unknown_case(db):
    assert asyncio.run(showcase_repo.set_status("nope", "hidden")) is False
