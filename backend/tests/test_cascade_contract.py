"""Cascade contract tests (P0-5).

These tests are the operational definition of Phase 0 Gate (PHASED_PLAN §3.2):
- 深分析成功率 ≥ 80%   →   `test_phase0_gate_success_rate`
- 核心字段完整率 ≥ 90% →   `test_phase0_gate_field_completeness`
- 静默失败 = 0         →   `test_phase0_gate_no_silent_failures`
- 每类失败有恢复路径    →   `test_phase0_gate_every_failure_has_recovery_path`
- 单条成本 < ¥5        →   `test_phase0_gate_cost_under_5`

Plus unit tests for each fallback rule in the adapter.

Replace `fixtures/real_v1/*.json` with hand-labeled samples before declaring
Phase 0 Gate passed. The synthetic_v1 corpus exercises the contract; only real
samples close the Gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.cascade.adapter import normalize_analysis_result
from agent.cascade.contract import (
    CascadeAnalysisContract,
    Platform,
    SCHEMA_VERSION,
    ShotType,
)
from agent.cascade.failures import (
    RECOVERY_ACTIONS,
    RECOVERY_HINTS,
    FailureCode,
    HardFailure,
    WarningCode,
)


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "src" / "agent" / "cascade" / "fixtures"
SYNTH = FIXTURES_ROOT / "synthetic_v1"

HAPPY_FIXTURES = [
    SYNTH / "baomam_fushi" / "001.json",
    SYNTH / "yuer_richang" / "001.json",
    SYNTH / "jiating_chufang" / "001.json",
]

EDGE_HARD_FAIL = {
    "edge_no_formula.json": FailureCode.S3_NO_FORMULA,
    "edge_scenes_too_short.json": FailureCode.S4_SCENES_LEN_OUT_OF_RANGE,
}

EDGE_RECOVERABLE = [
    "edge_scenes_too_long.json",
    "edge_non_monotonic.json",
    "edge_low_confidence.json",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- happy-path fixtures ----------


@pytest.mark.parametrize("fixture_path", HAPPY_FIXTURES, ids=[f.parent.name for f in HAPPY_FIXTURES])
def test_happy_fixture_validates(fixture_path: Path) -> None:
    raw = _load(fixture_path)
    contract = normalize_analysis_result(raw)
    assert isinstance(contract, CascadeAnalysisContract)
    assert contract.schema_version == SCHEMA_VERSION
    assert 3 <= len(contract.scenes) <= 12
    assert contract.viral_analysis.replicable_formula
    # Happy paths should have NO viral_analysis fallbacks
    for w in contract.warnings:
        assert w.code != WarningCode.W2_FALLBACK_USED.value, (
            f"happy fixture {fixture_path.name} unexpectedly used a fallback for {w.field}"
        )


def test_happy_fixture_scene_index_is_1_based_contiguous() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    contract = normalize_analysis_result(raw)
    assert [s.scene_index for s in contract.scenes] == list(range(1, len(contract.scenes) + 1))


def test_happy_fixture_timestamps_monotonic() -> None:
    raw = _load(SYNTH / "jiating_chufang" / "001.json")
    contract = normalize_analysis_result(raw)
    for i in range(1, len(contract.scenes)):
        assert contract.scenes[i].timestamp_start >= contract.scenes[i - 1].timestamp_end


def test_happy_fixture_silent_scene_is_allowed() -> None:
    """jiating_chufang scene 5 has empty dialogue — that's fine (silent scenes are normal)."""
    raw = _load(SYNTH / "jiating_chufang" / "001.json")
    contract = normalize_analysis_result(raw)
    silent = [s for s in contract.scenes if s.dialogue_and_narration == ""]
    assert len(silent) >= 1
    # No warning should fire for the silent scene
    silent_warnings = [w for w in contract.warnings if "dialogue" in w.field]
    assert silent_warnings == []


def test_yuer_fixture_subject_can_be_none() -> None:
    """yuer_richang has 2 scenes with subject=None — the contract must accept null."""
    raw = _load(SYNTH / "yuer_richang" / "001.json")
    contract = normalize_analysis_result(raw)
    nones = [s for s in contract.scenes if s.subject is None]
    assert len(nones) == 2


# ---------- hard-fail edge fixtures ----------


@pytest.mark.parametrize(
    ("filename", "expected_code"),
    EDGE_HARD_FAIL.items(),
)
def test_hard_fail_edge_fixture(filename: str, expected_code: FailureCode) -> None:
    raw = _load(SYNTH / filename)
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == expected_code
    payload = exc.value.to_payload()
    assert payload["code"] == expected_code.value
    assert payload["hint"]  # non-empty 人话
    assert payload["actions"]  # at least one recovery option
    assert "REPORT" in payload["actions"]  # report is always available


# ---------- recoverable edge fixtures ----------


def test_recoverable_truncates_too_many_scenes() -> None:
    raw = _load(SYNTH / "edge_scenes_too_long.json")
    contract = normalize_analysis_result(raw)
    assert len(contract.scenes) == 12
    assert any(w.code == WarningCode.W3_SCENES_TRUNCATED.value for w in contract.warnings)


def test_recoverable_sorts_unsorted_scenes() -> None:
    raw = _load(SYNTH / "edge_non_monotonic.json")
    contract = normalize_analysis_result(raw)
    # After sort, scene_index is re-derived 1..N matching position
    assert [s.scene_index for s in contract.scenes] == [1, 2, 3]
    # Timestamps are now monotonic
    for i in range(1, len(contract.scenes)):
        assert contract.scenes[i].timestamp_start >= contract.scenes[i - 1].timestamp_end
    assert any(w.code == WarningCode.W5_TIMESTAMPS_SORTED.value for w in contract.warnings)


def test_recoverable_low_confidence_fills_fallbacks() -> None:
    raw = _load(SYNTH / "edge_low_confidence.json")
    contract = normalize_analysis_result(raw)
    assert contract.confidence == pytest.approx(0.32, abs=1e-6)
    fallback_warnings = [w for w in contract.warnings if w.code == WarningCode.W2_FALLBACK_USED.value]
    # At least 6 of 7 optional viral_analysis fields fell back
    assert len(fallback_warnings) >= 6


# ---------- adapter behavior unit tests ----------


def test_adapter_rejects_non_dict() -> None:
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(["not", "a", "dict"])
    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD


def test_adapter_rejects_missing_source_url() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw.pop("source_url")
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == FailureCode.S1_NO_SOURCE_URL


def test_adapter_rejects_bad_schema_version() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["schema_version"] = "2.0"
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == FailureCode.S2_VERSION_MISMATCH


def test_adapter_rejects_missing_schema_version() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw.pop("schema_version")
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == FailureCode.S2_VERSION_MISMATCH


def test_adapter_rejects_empty_schema_version() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["schema_version"] = ""
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == FailureCode.S2_VERSION_MISMATCH


def test_adapter_warns_when_clamping_confidence() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["confidence"] = 1.5
    contract = normalize_analysis_result(raw)
    assert contract.confidence == 1.0
    assert any(w.code == WarningCode.W11_CONFIDENCE_CLAMPED.value for w in contract.warnings)


def test_adapter_warns_when_clamping_timestamp_out_of_duration() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    # duration_s=38; push last scene's end to 9999.0
    raw["scenes"][-1]["timestamp_end"] = 9999.0
    contract = normalize_analysis_result(raw)
    assert contract.scenes[-1].timestamp_end <= 38.0
    assert any(w.code == WarningCode.W12_TIMESTAMP_CLAMPED.value for w in contract.warnings)


def test_adapter_warns_on_wrong_type_subject() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["scenes"][0]["subject"] = 12345
    contract = normalize_analysis_result(raw)
    assert contract.scenes[0].subject is None
    assert any(
        w.code == WarningCode.W2_FALLBACK_USED.value and "subject" in w.field
        for w in contract.warnings
    )


def test_adapter_warns_on_wrong_type_enum() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["scenes"][0]["shot_type"] = 42
    raw["scenes"][0]["camera_movement"] = []
    contract = normalize_analysis_result(raw)
    field_warnings = [
        w for w in contract.warnings
        if w.code == WarningCode.W2_FALLBACK_USED.value
        and ("shot_type" in w.field or "camera_movement" in w.field)
    ]
    assert len(field_warnings) == 2


def test_adapter_generates_id_when_missing() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw.pop("analysis_id")
    contract = normalize_analysis_result(raw)
    assert contract.analysis_id.startswith("ana_auto_")
    assert any(w.code == WarningCode.W1_AUTO_ID.value for w in contract.warnings)


def test_adapter_warns_on_missing_cost() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw.pop("cost_cny")
    contract = normalize_analysis_result(raw)
    assert contract.cost_cny == 0.0
    assert any(w.code == WarningCode.W8_COST_UNKNOWN.value for w in contract.warnings)


def test_adapter_rejects_negative_cost() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["cost_cny"] = -1.0
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == FailureCode.S6_NEGATIVE_COST


def test_adapter_strips_pii_silently() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["author_uid"] = "user_12345"
    raw["author_handle"] = "@some_creator"
    contract = normalize_analysis_result(raw)
    # PII keys must not surface on the contract object (extra=forbid would fail validation otherwise)
    serialized = contract.model_dump()
    assert "author_uid" not in serialized
    assert "author_handle" not in serialized
    # Audit warning recorded
    assert any(w.code == WarningCode.W10_AUTHOR_PII_STRIPPED.value for w in contract.warnings)


def test_adapter_flags_cross_border_source() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["source_url"] = "https://www.youtube.com/watch?v=abc"
    contract = normalize_analysis_result(raw)
    assert any(w.code == WarningCode.W9_CROSS_BORDER_SOURCE.value for w in contract.warnings)


def test_adapter_coerces_unknown_enum_values() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["scenes"][0]["shot_type"] = "bonkers"
    raw["scenes"][0]["camera_movement"] = "yeet"
    contract = normalize_analysis_result(raw)
    assert contract.scenes[0].shot_type == ShotType.MEDIUM
    # Unknown enums are coerced silently (per schema §5: "too noisy" if we warn)


def test_adapter_computes_confidence_when_missing() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw.pop("confidence")
    contract = normalize_analysis_result(raw)
    assert 0.0 <= contract.confidence <= 1.0
    assert any(w.code == WarningCode.W7_CONFIDENCE_COMPUTED.value for w in contract.warnings)


def test_adapter_replaces_generic_scene_label() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["scenes"][0]["scene"] = ""
    contract = normalize_analysis_result(raw)
    assert contract.scenes[0].scene.startswith("镜头")
    assert any(w.code == WarningCode.W4_GENERIC_SCENE_LABEL.value for w in contract.warnings)


def test_adapter_clamps_confidence_out_of_range() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["confidence"] = 1.5
    contract = normalize_analysis_result(raw)
    assert contract.confidence == 1.0


# ---------- Phase 0 Gate (PHASED_PLAN §3.2) ----------


def test_phase0_gate_success_rate() -> None:
    """≥ 80% of fixtures with intended-success expectation must validate."""
    succeeded = 0
    intended_success_total = 0
    # Happy paths are intended-success
    for fp in HAPPY_FIXTURES:
        intended_success_total += 1
        try:
            normalize_analysis_result(_load(fp))
            succeeded += 1
        except HardFailure:
            pass
    # Recoverable edges are intended-success (different from hard-fail edges)
    for name in EDGE_RECOVERABLE:
        intended_success_total += 1
        try:
            normalize_analysis_result(_load(SYNTH / name))
            succeeded += 1
        except HardFailure:
            pass
    rate = succeeded / intended_success_total
    assert rate >= 0.80, f"Phase 0 success rate {rate:.0%} < 80%"


def test_happy_fixtures_have_zero_viral_fallbacks() -> None:
    """Sanity check: HAPPY_FIXTURES are by construction fully populated.

    NOTE: This is NOT the Phase 0 Gate G2 measurement. Gate G2 ("核心字段完整率 ≥ 90%")
    is meaningful only over the ≥20 real hand-labeled samples (per TOPRADOR_SCHEMA.md §8 +
    §11). The synthetic_v1 corpus has the answer baked in, so measuring against it is
    tautological. The real-fixture test below is skipped until those samples exist.
    """
    for fp in HAPPY_FIXTURES:
        contract = normalize_analysis_result(_load(fp))
        viral_fallbacks = [
            w for w in contract.warnings
            if w.code == WarningCode.W2_FALLBACK_USED.value
            and w.field.startswith("viral_analysis.")
        ]
        assert viral_fallbacks == [], f"{fp.name} unexpectedly used a viral_analysis fallback"


@pytest.mark.skipif(
    not (FIXTURES_ROOT / "real_v1").exists(),
    reason="real_v1 corpus not yet hand-labeled; see TOPRADOR_SCHEMA.md §8",
)
def test_phase0_gate_field_completeness_real() -> None:
    """Phase 0 Gate G2: ≥ 90% core-field completeness over real samples (≥20)."""
    required_fields = [
        "hook", "pacing", "climax", "visual_style",
        "emotional_arc", "target_audience", "engagement_levers", "replicable_formula",
    ]
    real_dir = FIXTURES_ROOT / "real_v1"
    samples = sorted(real_dir.rglob("*.json"))
    assert len(samples) >= 20, f"need ≥20 real samples; found {len(samples)}"
    total = 0
    fallback_count = 0
    for fp in samples:
        contract = normalize_analysis_result(_load(fp))
        total += len(required_fields)
        for w in contract.warnings:
            if w.code == WarningCode.W2_FALLBACK_USED.value and w.field.startswith("viral_analysis."):
                fallback_count += 1
    completeness = 1.0 - fallback_count / total
    assert completeness >= 0.90, f"Phase 0 Gate G2 field completeness {completeness:.0%} < 90%"


_SENTINEL_DELETE = object()


def _apply_corruption(payload: dict, path: str, value) -> dict:
    """Apply a dotted-path corruption to a deep copy of `payload`. `value=_SENTINEL_DELETE` deletes the key."""
    corrupted = json.loads(json.dumps(payload))
    keys = path.split(".")
    cursor = corrupted
    for k in keys[:-1]:
        cursor = cursor[int(k)] if k.isdigit() else cursor[k]
    last = keys[-1]
    if value is _SENTINEL_DELETE:
        if last.isdigit():
            del cursor[int(last)]
        else:
            cursor.pop(last, None)
    else:
        if last.isdigit():
            cursor[int(last)] = value
        else:
            cursor[last] = value
    return corrupted


def test_phase0_gate_no_silent_failures() -> None:
    """For each corruption, the adapter must EITHER raise HardFailure OR emit at least one warning.

    The Evidence Collector audit (2026-05-19) found 5 silent paths that this test now
    explicitly probes. Adding a new silent path without a warning will break this test.
    """
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    # (path, corrupted_value) — _SENTINEL_DELETE removes the key entirely.
    corruptions = [
        # Originally-tested loud paths
        ("source_url", ""),
        ("viral_analysis.replicable_formula", ""),
        ("viral_analysis.hook", ""),  # falls back, must warn
        ("scenes.0.scene", ""),
        ("cost_cny", -5.0),
        # New probes covering Evidence Collector findings
        ("schema_version", _SENTINEL_DELETE),       # was: silent fill → now: HARD FAIL S2
        ("schema_version", ""),                     # was: silent fill → now: HARD FAIL S2
        ("confidence", 1.7),                        # was: silent clamp → now: warn
        ("confidence", -0.3),                       # was: silent clamp → now: warn
        ("scenes.0.subject", 12345),                # was: silent → now: warn (wrong type)
        ("scenes.0.shot_type", 42),                 # was: silent → now: warn (wrong type)
        ("scenes.0.camera_movement", []),           # was: silent → now: warn (wrong type)
        ("scenes.4.timestamp_end", 9999.0),         # was: silent → now: clamp + warn (out of duration)
        ("scenes.0.timestamp_start", -3.0),         # was: silent clamp → now: warn
    ]
    for path, value in corruptions:
        corrupted = _apply_corruption(raw, path, value)
        raised = False
        warned = False
        try:
            contract = normalize_analysis_result(corrupted)
            warned = len(contract.warnings) > 0
        except HardFailure:
            raised = True
        assert raised or warned, (
            f"silent failure on corruption {path}={value!r}: adapter accepted with zero warnings"
        )


def test_phase0_gate_every_failure_has_recovery_path() -> None:
    """Karpathy rule: every FailureCode has a UI banner hint AND >= 1 recovery action."""
    for code in FailureCode:
        assert code.value in RECOVERY_HINTS, f"{code.value} missing recovery hint"
        assert RECOVERY_HINTS[code.value].strip(), f"{code.value} hint is blank"
        assert code.value in RECOVERY_ACTIONS, f"{code.value} missing recovery actions"
        assert len(RECOVERY_ACTIONS[code.value]) >= 1, f"{code.value} has no actions"


def test_phase0_gate_cost_under_5() -> None:
    """All happy fixtures must report cost < ¥5 per run."""
    for fp in HAPPY_FIXTURES:
        contract = normalize_analysis_result(_load(fp))
        assert contract.cost_cny < 5.0, (
            f"{fp.name} cost_cny={contract.cost_cny} ≥ ¥5; Phase 0 gate fails"
        )


def test_phase0_gate_warning_codes_have_hints() -> None:
    """Every WarningCode in the catalog has a hint string (may be empty for silent codes)."""
    for code in WarningCode:
        assert code.value in RECOVERY_HINTS, f"WarningCode {code.value} missing in RECOVERY_HINTS"
