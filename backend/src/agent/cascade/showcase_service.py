"""Auto-showcase: turn a completed analysis into a landing-page sample case.

founder decision: high-confidence analyses auto-publish to the landing carousel
(founder can hide later via admin). The landing page reads published cases from
`showcase_cases` via GET /api/showcase — no more hand-editing sampleCases.ts +
redeploy.

Pipeline (all best-effort, NEVER raises into the analysis path):
  gate(contract) → copy the analysis's per-scene clips into the PERMANENT
  /media/showcase/<case_id>/ dir (regular clips are swept after 30 days;
  showcase/ is exempt) → derive a ShowcaseSlide[] config → insert published row.

The gate is the privacy/quality/cost valve: env kill-switch, a confidence floor,
a min-clip floor (a card with no video is a poor carousel item), a per-source
dedupe (don't re-decide a URL we've published OR hidden), and a hard cap on the
number of auto-published cases (bounds showcase/ disk growth + carousel length).
"""

from __future__ import annotations

import re
import shutil

from agent import config
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.mediakit.clip_extractor import media_root
from agent.cascade.persistence import showcase_repo

# 暖色渐变池 —— 给自动案例的卡头一点视觉变化(手动案例可在 DB 里自定 gradient)。
_GRADIENTS = [
    "bg-[radial-gradient(120%_120%_at_30%_20%,#fff7ec_0%,#fbe0b0_45%,#e8a766_100%)]",
    "bg-[radial-gradient(120%_120%_at_30%_20%,#fdf2f8_0%,#fbcfe8_45%,#f0a4c8_100%)]",
    "bg-[radial-gradient(120%_120%_at_30%_20%,#eef6ff_0%,#cfe4fb_45%,#a4c4f0_100%)]",
    "bg-[radial-gradient(120%_120%_at_30%_20%,#f0fdf4_0%,#bbf7d0_45%,#86d8a4_100%)]",
]


def _short(s: str | None, n: int) -> str:
    return (s or "").strip()[:n]


def _case_id_for(contract: CascadeAnalysisContract) -> str:
    """Stable case_id derived from analysis_id (so a re-run replaces in place).
    Sanitized to filesystem/url-safe chars (it becomes a /media/showcase/<id>/ dir)."""
    raw = (contract.analysis_id or "").strip() or "case"
    safe = re.sub(r"[^A-Za-z0-9_-]", "", raw)[:40] or "case"
    return f"auto-{safe}"


def _gradient_for(case_id: str) -> str:
    return _GRADIENTS[hash(case_id) % len(_GRADIENTS)]


def _safe_rmtree(path) -> None:
    """Best-effort recursive delete of a displaced case's media dir. Never raises."""
    try:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def _copy_clips_to_showcase(contract: CascadeAnalysisContract, case_id: str) -> int:
    """Copy the analysis's already-extracted per-scene clips+posters from the
    (sweep-eligible) analysis dir into the PERMANENT showcase dir. Returns the
    number of scenes whose clip landed. Best-effort; missing files just skip."""
    root = media_root()
    src_dir = root / contract.analysis_id
    dst_dir = root / "showcase" / case_id
    copied = 0
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    for s in contract.scenes:
        idx = getattr(s, "scene_index", None)
        if not idx:
            continue
        for ext in ("mp4", "jpg"):
            src = src_dir / f"scene_{idx}.{ext}"
            if src.exists():
                try:
                    shutil.copy2(src, dst_dir / f"scene_{idx}.{ext}")
                    if ext == "mp4":
                        copied += 1
                except OSError:
                    pass
    return copied


def _build_slides(contract: CascadeAnalysisContract, case_id: str) -> list[dict]:
    base = f"/media/showcase/{case_id}"
    slides: list[dict] = []
    for s in sorted(contract.scenes, key=lambda x: getattr(x, "scene_index", 0) or 0):
        idx = getattr(s, "scene_index", None)
        if not idx:
            continue
        # only slides whose clip actually got copied (file presence is the truth)
        clip_path = media_root() / "showcase" / case_id / f"scene_{idx}.mp4"
        if not clip_path.exists():
            continue
        poster_path = media_root() / "showcase" / case_id / f"scene_{idx}.jpg"
        slides.append({
            "clip": f"{base}/scene_{idx}.mp4",
            "poster": f"{base}/scene_{idx}.jpg" if poster_path.exists() else "",
            "theme": _short(getattr(s, "theme", ""), 30) or f"第 {idx} 幕",
            "note": _short(
                getattr(s, "visual_summary", None) or getattr(s, "segment_description", None) or getattr(s, "theme", ""),
                40,
            ),
            "emotion": _short(getattr(s, "emotion", None), 12) or None,
        })
    return slides


async def maybe_publish_showcase(contract: CascadeAnalysisContract) -> str | None:
    """Auto-publish a completed analysis as a landing-page case if it passes the
    gate. Returns case_id on publish, else None. NEVER raises — callers invoke
    this in the analysis path and it must never block or fail an analysis."""
    try:
        if not config.AUTO_SHOWCASE_ENABLED:
            return None
        if (contract.confidence or 0) < config.AUTO_SHOWCASE_MIN_CONFIDENCE:
            return None
        source_url = str(contract.source_url or "")
        if not source_url:
            return None
        # dedupe: never re-decide a URL we've already published OR hidden
        # (a hidden case must stay hidden — don't resurrect founder's takedown).
        existing = await showcase_repo.get_by_source_url(source_url)
        if existing is not None:
            return None
        # At the cap, keep a *living top-N by confidence*: displace the weakest
        # auto case if the newcomer is strictly more confident (founder rule —
        # rank by confidence; a tie keeps the incumbent, so a new equal-confidence
        # case does NOT evict — that path is handled below via insert ordering).
        # Manual/curated cases are never auto-evicted.
        displaced_case_id: str | None = None
        if await showcase_repo.count_published() >= config.AUTO_SHOWCASE_MAX:
            weakest = await showcase_repo.lowest_confidence_auto()
            new_conf = contract.confidence or 0
            if weakest is None or new_conf <= weakest["confidence"]:
                return None  # full of stronger (or non-auto) cases → skip
            displaced_case_id = weakest["case_id"]

        case_id = _case_id_for(contract)
        copied = _copy_clips_to_showcase(contract, case_id)
        if copied < config.AUTO_SHOWCASE_MIN_CLIPS:
            return None  # too few clips → poor carousel card, skip

        slides = _build_slides(contract, case_id)
        if len(slides) < config.AUTO_SHOWCASE_MIN_CLIPS:
            return None

        va = contract.viral_analysis
        await showcase_repo.insert_case(
            case_id=case_id,
            source_url=source_url,
            category=_short(getattr(va, "theme", None), 20) or "精选案例",
            emoji="🎬",
            hook=_short(getattr(va, "hook", None), 90),
            emotion=_short(getattr(va, "emotion_trigger", None), 60) or None,
            gradient=_gradient_for(case_id),
            slides=slides,
            confidence=contract.confidence or 0,
            origin="auto",
            status="published",
        )
        # New case is in; now evict the weakest one it displaced (DB row + its
        # permanent media dir, so showcase/ doesn't accumulate orphans). Done
        # after the insert so a failed insert never loses an existing case.
        if displaced_case_id and displaced_case_id != case_id:
            await showcase_repo.delete_case(displaced_case_id)
            _safe_rmtree(media_root() / "showcase" / displaced_case_id)
        return case_id
    except Exception:
        # best-effort: a showcase failure must never surface to the analysis.
        return None
