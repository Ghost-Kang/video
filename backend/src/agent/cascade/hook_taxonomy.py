"""H1-H9 hook taxonomy + per-niche priority maps (P2-4 founder-curated).

Source of truth: `docs/nexus/founder_log/p2-4_hooks_taxonomy.md` v1.0.
This module mechanizes the regex / keyword constraints documented there
so the fixture rewrite generator, the P2-4 runner, and `test_rewrite.py`
all share one implementation.

Functions return `(passed: bool, detail: str)` tuples for mechanical check
ergonomics. Keep them pure (no I/O) so they're trivially testable.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


# --- Hook patterns ---------------------------------------------------------

# Each regex matches a TYPICAL surface form of the hook in Chinese ad copy.
# The patterns are intentionally loose — false positives cost less than
# false negatives at this stage (P2-4 fixture baseline). Tighten later as
# false positives surface in eval.

HOOK_PATTERNS: Mapping[str, re.Pattern[str]] = {
    "H1": re.compile(
        r"(?:\d+\s*(?:月龄|个月|岁)|[零一二三四五六七八九十两](?:个?月龄?|岁))"
    ),
    "H2": re.compile(
        r"(?:一周|7\s*天|[3456789]\s*天|[0-9]+\s*款|[0-9]+\s*道|[0-9]+\s*大|[0-9]+\s*个|不重样|清单)"
    ),
    "H3": re.compile(
        r"(?:蹭蹭涨|蹭蹭长|搞定|学会|必收藏|先收藏|建议收藏|拿食谱|教你|告诉你|个子涨|长高)"
    ),
    "H4": re.compile(
        r"(?:千万别|绝对不能|复刻|竟然|原来|没想到|为什么|VS|对比|宽油|你以为|餐厅\s*\d+)"
    ),
    "H5": re.compile(
        r"(?:[爷叔伯][做盘炒煎|]|师傅|爸视角|爸日记|爸辅食|vlog\d|Vlog\d|第\s*\d+\s*[集期])"
    ),
    "H6": re.compile(
        r"(?:过年|中秋|端午|六一|新年|开学|放学后|睡前|晨间|晚餐后|周末厨房)"
    ),
    "H7": re.compile(
        r"(?:一家人|好好吃饭|再忙也|家的味道|妈妈的|温馨|烟火气|再累也|家里人|围着)"
    ),
    "H8": re.compile(
        # P5-1a expansion 2026-05-23 (per p2-6_baseline_20260523T054123Z.md
        # yuer_richang 20% pass): original 字面 emotional words + 场景化 patterns
        # surfaced by LLM rewrites ("凌晨三点,他又醒了 / 这是今晚第四次") that
        # scored hooks_used=H8 in self_check but failed the original strict regex.
        # New scene patterns are intentionally yuer-leaning so baomam/jiating
        # false-positive rate stays near zero.
        r"(?:"
        r"当妈以后|才发现|没人懂|没人理解|崩溃|委屈|心酸|都懂|都明白|心累|累了"
        r"|快崩溃|要疯了|睡不好"
        r"|凌晨[一二三四五六七八九十两\d]+|半夜[一二三四五六七八九十两\d]+"
        r"|又.{0,3}[醒哭闹]了|这是.{0,4}第.{0,3}次"
        r")"
    ),
    # H9 — content-buried twist: "why X, not Y" / "many people get it wrong"
    "H9": re.compile(
        r"(?:为什么|不是|偏要|其实).{0,15}?(?:不|要|得|必须|搞反|搞错)"
        r"|(?:很多人|大家|你以为|其实).{0,15}?(?:都错了|搞反了|不知道|错的|不对)"
    ),
}


# --- Per-niche priority + negative maps ------------------------------------

# P0 hooks: shot 1 MUST match at least one of these for the niche.
# Negative hooks: rewrite MUST NOT trigger any of these for the niche.

P0_HOOKS_BY_NICHE: Mapping[str, tuple[str, ...]] = {
    "baomam_fushi": ("H1", "H2"),
    "yuer_richang": ("H8",),
    "jiating_chufang": ("H4", "H9"),
}

NEGATIVE_HOOKS_BY_NICHE: Mapping[str, tuple[str, ...]] = {
    "baomam_fushi": ("H4",),   # 危机制造 in 辅食 = 焦虑触发,禁止
    "yuer_richang": ("H2",),   # 数字清单 与情感流冲突
    "jiating_chufang": ("H8",),  # 情绪宣泄 与美食教程定调冲突
}


# --- Domain vocab ----------------------------------------------------------

NUTRIENT_CATEGORIES: Mapping[str, tuple[str, ...]] = {
    "protein": ("蛋", "鸡蛋", "肉", "瘦肉", "鸡肉", "牛肉", "猪肉", "鱼", "虾", "豆腐", "牛奶", "酸奶", "肉泥", "鱼泥"),
    "vegetable": ("胡萝卜", "西兰花", "菠菜", "南瓜", "青菜", "土豆", "番茄", "番茄汁", "西红柿", "蔬菜", "菜泥"),
    "fruit": ("苹果", "香蕉", "蓝莓", "梨", "草莓", "桃", "猕猴桃", "水果", "果泥"),
    "staple": ("米饭", "米粉", "米糊", "面条", "饭团", "粥", "馒头", "面食", "主食"),
}

# Common Chinese dish names. Conservative list — runner falls back to regex
# pattern `做/复刻/教你做 X` when no exact match.
DISH_NAMES: tuple[str, ...] = (
    "红烧肉", "家常豆腐", "麻婆豆腐", "辣子鸡", "可乐鸡翅", "番茄炒蛋", "宫保鸡丁",
    "鱼香肉丝", "回锅肉", "糖醋里脊", "酸辣土豆丝", "蒜蓉蒸虾", "包肉", "排骨",
    "牛肉炒饭", "蛋炒饭", "牛肉面", "肉片", "蒸鱼", "焖肉", "蛋羹", "羹",
    "卤味", "卤肉", "豆腐", "豆花", "炒蛋", "炒饭", "炒面", "鸡腿", "鸭",
    "饺子", "包子", "馄饨", "拉面", "汤", "海鲜大餐",
)

_DISH_PATTERN = re.compile(
    r"(?:做|复刻|教你做|教你|尝尝|这道|学做|跟我做|来一道)\s*[一-龥]{2,8}"
    r"|[一-龥]{2,5}(?:饭|面|粥|汤|肉|菜|蛋|鱼|虾|豆腐|豆花|羹|卷|饼|串|汁)"
)


# --- Public detection helpers ----------------------------------------------


def detect_hooks_in_text(text: str) -> list[str]:
    """Return the H-ids that fire on the given text, in canonical order."""
    return [h for h in ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9") if HOOK_PATTERNS[h].search(text)]


def infer_niche_from_hooks(detected: Iterable[str]) -> tuple[str | None, str]:
    """Map detected H-ids → most-likely niche.

    Used by the Director's Cascade auto-pilot: when the user pastes a link
    without pre-selecting a niche, run hook detection on the analysis text and
    map those hooks to the niche whose `P0_HOOKS_BY_NICHE` they best match.

    Algorithm:
      - For each (niche, p0_hooks): score = |detected ∩ p0_hooks|.
      - If ANY hook in `NEGATIVE_HOOKS_BY_NICHE[niche]` is in `detected`,
        the niche is disqualified (score = -inf), regardless of P0 matches.
      - Pick the unique highest positive score. Ties → return (None, "tie:<...>").
      - No positive matches → return (None, "no_match").

    Tie-breaking honesty example: if (H1, H4) both detected,
      - baomam_fushi has H1 (+1) but H4 ∈ neg → score = -inf
      - jiating_chufang has H4 (+1), no neg fired → score = 1
      → returns ("jiating_chufang", "score=1 hits=['H4']").

    Returns:
        (niche_id, reason) where niche_id is None when ambiguous/no match.
        `reason` is a short telemetry/debug string — NOT for LLM consumption.
    """
    detected_set = set(detected)
    if not detected_set:
        return None, "no_match"

    scores: dict[str, tuple[int, list[str]]] = {}
    for niche, p0 in P0_HOOKS_BY_NICHE.items():
        negatives = NEGATIVE_HOOKS_BY_NICHE.get(niche, ())
        if any(h in detected_set for h in negatives):
            # Disqualified by a forbidden hook — skip entirely.
            continue
        hits = [h for h in p0 if h in detected_set]
        if hits:
            scores[niche] = (len(hits), hits)

    if not scores:
        return None, "no_match"

    best_score = max(score for score, _ in scores.values())
    winners = [n for n, (s, _) in scores.items() if s == best_score]
    if len(winners) > 1:
        return None, f"tie:{sorted(winners)}"

    winner = winners[0]
    hits = scores[winner][1]
    return winner, f"score={best_score} hits={hits}"


def _tokens(text: str) -> set[str]:
    """Cheap tokenizer for visual-diversity comparison: 1-char CJK + ASCII words."""
    return set(re.findall(r"[一-龥]|[a-zA-Z]+", text or ""))


def _max_pairwise_jaccard(texts: Iterable[str]) -> float:
    sets = [s for s in (_tokens(t) for t in texts) if s]
    if len(sets) < 2:
        return 0.0
    high = 0.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            inter = len(sets[i] & sets[j])
            union = len(sets[i] | sets[j])
            if union == 0:
                continue
            high = max(high, inter / union)
    return high


def _shot_dialogue_1(result: Mapping) -> str:
    shots = result.get("shots") or []
    if not shots:
        return ""
    return shots[0].get("dialogue") or ""


def _all_dialogue(result: Mapping) -> str:
    return "\n".join(s.get("dialogue", "") for s in (result.get("shots") or []))


def _full_text(result: Mapping) -> str:
    return (result.get("script_markdown") or "") + "\n" + _all_dialogue(result)


# --- Mechanical check #6..#10 ----------------------------------------------


def visual_diversity(result: Mapping, threshold: float = 0.5) -> tuple[bool, str]:
    """#6: pairwise token overlap between shot visuals ≤ threshold."""
    shots = result.get("shots") or []
    visuals = [s.get("visual", "") for s in shots]
    if len(visuals) < 2:
        return True, "single shot, n/a"
    high = _max_pairwise_jaccard(visuals)
    return high <= threshold, f"max overlap {high:.2f} (threshold {threshold})"


def nutrient_category_consistency(result: Mapping, niche: str, source_title: str = "") -> tuple[bool, str]:
    """#7 (baomam_fushi only): rewrite must not introduce a nutrient category
    that wasn't present in the source.

    If source title is empty, allow any single category but reject multi-category mixing
    (e.g. fruit + protein in the same script is the F-1-b "信任崩塌雷区" case).
    """
    if niche != "baomam_fushi":
        return True, "n/a (not baomam_fushi)"
    text = _full_text(result)
    rewrite_cats = {
        cat for cat, foods in NUTRIENT_CATEGORIES.items() if any(f in text for f in foods)
    }
    if len(rewrite_cats) <= 1:
        return True, f"single category: {sorted(rewrite_cats) or ['(none)']}"
    source_cats = {
        cat for cat, foods in NUTRIENT_CATEGORIES.items() if any(f in (source_title or "") for f in foods)
    }
    if not source_cats:
        # Source ambiguous; reject any multi-category rewrite (F-1-b strict mode)
        return False, f"rewrite mixes categories {sorted(rewrite_cats)} (source ambiguous)"
    extras = rewrite_cats - source_cats
    if extras:
        return False, f"rewrite adds categories {sorted(extras)} not in source {sorted(source_cats)}"
    return True, f"categories {sorted(rewrite_cats)} ⊆ source {sorted(source_cats)}"


def dish_anchor_present(result: Mapping, niche: str) -> tuple[bool, str]:
    """F-3-a (jiating_chufang only): shot 1 must contain a 菜名."""
    if niche != "jiating_chufang":
        return True, "n/a (not jiating_chufang)"
    text = _shot_dialogue_1(result)
    for d in DISH_NAMES:
        if d in text:
            return True, f"shot 1 has dish '{d}'"
    if _DISH_PATTERN.search(text):
        return True, "shot 1 has dish-anchor pattern"
    return False, "shot 1 missing dish name"


def hook_p0_compliance(result: Mapping, niche: str) -> tuple[bool, str]:
    """#8: shot 1 must hit at least one P0 hook for this niche."""
    text = _shot_dialogue_1(result)
    required = P0_HOOKS_BY_NICHE.get(niche, ())
    if not required:
        return True, "no P0 hook required"
    hit = [h for h in required if HOOK_PATTERNS[h].search(text)]
    return bool(hit), f"shot 1 hits {hit or '∅'} (required any of {list(required)})"


def hook_diversity(result: Mapping, minimum: int = 2) -> tuple[bool, str]:
    """#9: full script must hit ≥ minimum distinct H hooks."""
    fired = detect_hooks_in_text(_full_text(result))
    return len(fired) >= minimum, f"{len(fired)} distinct hooks: {fired}"


def negative_hook_absence(result: Mapping, niche: str) -> tuple[bool, str]:
    """#10: the niche's "反面" hooks must not fire on any shot dialogue."""
    forbidden = NEGATIVE_HOOKS_BY_NICHE.get(niche, ())
    if not forbidden:
        return True, "no negative hooks for this niche"
    fired = [h for h in forbidden if HOOK_PATTERNS[h].search(_full_text(result))]
    return not fired, f"forbidden hooks fired: {fired}" if fired else f"no forbidden hooks ({list(forbidden)})"


# --- Per-niche P0 hook injection (used by fixture rewrite) ------------------

# Stock dialogue snippets that DEFINITELY fire the niche's P0 hooks. Used by
# the fixture generator to guarantee shot 1 compliance without an LLM.

P0_SHOT_1_TEMPLATES: Mapping[str, tuple[str, ...]] = {
    "baomam_fushi": (
        "一岁宝宝一周辅食不重样,今天换这道试试",  # H1 + H2
        "六月龄宝宝辅食清单,一周不重样",         # H1 + H2
        "12 月龄宝宝七天辅食,顿顿不一样",        # H1 + H2
    ),
    "yuer_richang": (
        "当妈以后才发现,最累的不是熬夜,是没人懂",  # H8
        "崩溃的瞬间太多了,但他一句话又把我治愈",   # H8
    ),
    "jiating_chufang": (
        "餐厅 88 的{dish},为什么我在家做只要 12",   # H4 + 菜名
        "你以为{dish}很难做,其实关键就一步",      # H4 + 菜名
        "今天教你做{dish},宽油到底是什么油",      # H4 + 菜名 + H9
    ),
}


# Default dish name when none is parsed from source title (jiating only).
DEFAULT_DISH: Mapping[str, str] = {
    "jiating_chufang": "家常红烧肉",
}


def extract_dish_from_title(title: str) -> str | None:
    """Best-effort dish-name extraction from a source video title."""
    if not title:
        return None
    for d in DISH_NAMES:
        if d in title:
            return d
    m = _DISH_PATTERN.search(title)
    if m:
        # Strip leading 动词 like "做" so the substring is the noun
        text = m.group(0)
        text = re.sub(r"^(?:做|复刻|教你做|教你|尝尝|这道|学做|跟我做|来一道)\s*", "", text)
        return text[:8]
    return None


# H9 (评论区二次梗钩) — content-buried twist sentences to seed into a non-first shot.
H9_SEED_LINES: tuple[str, ...] = (
    "为什么牛肉要逆纹切,顺纹一刀就老",
    "宽油不是花生油,是指多放油",
    "蒸蛋羹要过筛两次,你知道吗",
    "辅食米粉要冲到能挂勺,稀了不行",
)
