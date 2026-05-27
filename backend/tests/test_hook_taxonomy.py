"""Unit tests for `infer_niche_from_hooks` — the Director's niche auto-pilot.

The Director calls `cascade_analyze` first; the tool runs `detect_hooks_in_text`
on the viral_analysis text and feeds the result into `infer_niche_from_hooks` to
decide whether to auto-call `cascade_rewrite` or fall back to asking the user.

These tests pin down the contract:
- clean P0 match per niche → that niche, with non-empty reason.
- negative hook present → niche is disqualified entirely (score=-inf),
  even if its P0 hook also fires.
- empty input or no P0 overlap → (None, "no_match").
- tie between equally-scored niches → (None, "tie:<sorted-list>").
"""

from __future__ import annotations

from agent.cascade.hook_taxonomy import infer_niche_from_hooks


class TestInferNicheFromHooks:
    def test_baomam_clean_match(self):
        # H1 + H2 are the P0 hooks for baomam_fushi. No negative (H4) → wins.
        niche, reason = infer_niche_from_hooks(["H1", "H2"])
        assert niche == "baomam_fushi"
        assert "score=2" in reason
        assert "H1" in reason and "H2" in reason

    def test_yuer_clean_match(self):
        # H8 is P0 for yuer_richang. No H2 → no negative.
        niche, reason = infer_niche_from_hooks(["H8"])
        assert niche == "yuer_richang"
        assert "score=1" in reason
        assert "H8" in reason

    def test_jiating_clean_match(self):
        # H4 + H9 are P0 for jiating_chufang. No H8 → no negative.
        niche, reason = infer_niche_from_hooks(["H4", "H9"])
        assert niche == "jiating_chufang"
        assert "score=2" in reason

    def test_h1_plus_h4_disqualifies_baomam_picks_jiating(self):
        # Tie-breaking honesty case from spec:
        # baomam_fushi: H1 hit BUT H4 ∈ negatives → score=-inf
        # jiating_chufang: H4 hit (+1), no H8 in input → score=1 → wins.
        niche, reason = infer_niche_from_hooks(["H1", "H4"])
        assert niche == "jiating_chufang"
        assert "H4" in reason

    def test_negative_hook_alone_disqualifies_and_no_other_match(self):
        # Only H4 detected → baomam disqualified, jiating wins (H4 ∈ P0).
        niche, _ = infer_niche_from_hooks(["H4"])
        assert niche == "jiating_chufang"

    def test_negative_disqualifies_even_when_p0_also_hit(self):
        # H8 ∈ jiating_chufang.negatives → jiating disqualified.
        # H2 ∈ baomam.P0 but H2 doesn't disqualify baomam (only H4 does) → baomam wins.
        # Note: H8 is also yuer's P0 hit (+1). So this is actually yuer vs baomam.
        # yuer: H8 hit, no H2 detected? Wait — H2 IS detected → H2 ∈ yuer.negatives.
        # → yuer also disqualified by H2. Only baomam remains: H2 ∈ P0 → score=1.
        niche, reason = infer_niche_from_hooks(["H2", "H8"])
        assert niche == "baomam_fushi"
        assert "score=1" in reason

    def test_empty_input_returns_no_match(self):
        niche, reason = infer_niche_from_hooks([])
        assert niche is None
        assert reason == "no_match"

    def test_only_irrelevant_hooks_returns_no_match(self):
        # H3, H5, H6, H7 are P0 for no niche → no_match.
        niche, reason = infer_niche_from_hooks(["H3", "H5", "H6", "H7"])
        assert niche is None
        assert reason == "no_match"

    def test_tie_returns_none_and_lists_candidates(self):
        # H1 → baomam (+1, no H4). H9 → jiating (+1, no H8). Tie.
        niche, reason = infer_niche_from_hooks(["H1", "H9"])
        assert niche is None
        assert reason.startswith("tie:")
        assert "baomam_fushi" in reason
        assert "jiating_chufang" in reason

    def test_iterable_input_set_works(self):
        # The signature says Iterable[str] — must accept set, generator, list.
        niche_from_set, _ = infer_niche_from_hooks({"H1", "H2"})
        assert niche_from_set == "baomam_fushi"
        niche_from_gen, _ = infer_niche_from_hooks(h for h in ("H8",))
        assert niche_from_gen == "yuer_richang"
