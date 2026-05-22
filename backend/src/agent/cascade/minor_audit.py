"""Keyword-based minor-subject audit for Phase 1 compliance telemetry.

The detector is intentionally conservative but non-blocking: W14 is INFO-only
and exists so Phase 1 can measure how often creator inputs involve minors
before Phase 2 decides whether to add a hard policy gate.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


CHINESE_MINOR_KEYWORDS = frozenset({
    "宝宝",
    "小孩",
    "婴儿",
    "幼儿",
    "小朋友",
    "儿童",
    "小宝",
})
ENGLISH_MINOR_KEYWORDS = frozenset({
    "baby",
    "kid",
    "child",
    "children",
    "infant",
    "toddler",
})
MINOR_KEYWORDS = CHINESE_MINOR_KEYWORDS | ENGLISH_MINOR_KEYWORDS
_ENGLISH_RE = re.compile(
    r"\b("
    + "|".join(re.escape(keyword) for keyword in sorted(ENGLISH_MINOR_KEYWORDS))
    + r")\b",
    re.IGNORECASE,
)


def detect_minor_subjects(scenes: Sequence[Any]) -> list[str]:
    """Return 1-based scene indices whose text suggests minor subjects."""
    hits: list[str] = []
    for position, scene in enumerate(scenes, start=1):
        text = _scene_text(scene)
        if _has_minor_keyword(text):
            hits.append(str(_scene_index(scene) or position))
    return hits


def _scene_text(scene: Any) -> str:
    parts: list[str] = []
    for field in ("dialogue_and_narration", "dialogue", "visual_content", "subject"):
        value = scene.get(field) if isinstance(scene, Mapping) else getattr(scene, field, None)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def _scene_index(scene: Any) -> int | None:
    value = scene.get("scene_index") if isinstance(scene, Mapping) else getattr(scene, "scene_index", None)
    return value if isinstance(value, int) else None


def _has_minor_keyword(text: str) -> bool:
    if not text:
        return False
    if any(keyword in text for keyword in CHINESE_MINOR_KEYWORDS):
        return True
    return _ENGLISH_RE.search(text) is not None
