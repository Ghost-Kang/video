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

# 2026-05-30 toprador 对齐:replicable_formula 不再硬必填(改写专用,已暂挂),
# 故 edge_no_formula 从硬失败降级为可恢复(校验通过 + 走兜底)。
EDGE_HARD_FAIL: dict[str, FailureCode] = {}

EDGE_RECOVERABLE = [
    "edge_scenes_too_long.json",
    "edge_scenes_too_short.json",  # W5D2: padded via W18_SCENES_PADDED
    "edge_non_monotonic.json",
    "edge_low_confidence.json",
    "edge_no_formula.json",  # 改写暂挂后不再硬失败
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


def test_adapter_snaps_model_emitted_overlap_without_clamp() -> None:
    # 2026-06-01 prod diag #2 root cause: the model emits OVERLAPPING scenes that
    # each pass per-scene clamping (within duration, end>start) — i.e. start <
    # prev_end with no value needing a clamp. Before the fix the overlap-snap pass
    # was gated behind `any_clamped` and thus SKIPPED, so the overlap reached the
    # contract's _timestamps_monotonic validator → S5_INVALID_PAYLOAD. Now snapped
    # unconditionally.
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    # scene1 now ends at 19.0 while scene2 starts at 4.5 → overlap. 19.0 <=
    # duration_s(38) and > 0.0, and starts stay ascending (0,4.5,11,18,28) so NO
    # clamp fires and the initial sort is a no-op — exactly the prod #2 shape.
    raw["scenes"][0]["timestamp_end"] = 19.0
    contract = normalize_analysis_result(raw)  # must NOT raise S5
    # Output is strictly non-overlapping / monotonic
    for i in range(1, len(contract.scenes)):
        assert contract.scenes[i].timestamp_start >= contract.scenes[i - 1].timestamp_end
    # scene_index re-derived 1..N contiguous
    assert [s.scene_index for s in contract.scenes] == list(range(1, len(contract.scenes) + 1))


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


def test_strip_pii_ip_and_author_name() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["author_name"] = "张三"
    raw["ip_address"] = "203.0.113.7"
    raw["user_ip"] = "203.0.113.8"
    contract = normalize_analysis_result(raw)
    serialized = contract.model_dump()
    assert "author_name" not in serialized
    assert "ip_address" not in serialized
    assert "user_ip" not in serialized
    assert any(w.code == WarningCode.W10_AUTHOR_PII_STRIPPED.value for w in contract.warnings)


def test_cross_border_hard_block_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["source_url"] = "https://www.youtube.com/watch?v=abc"
    monkeypatch.setattr("agent.config.STRICT_CROSS_BORDER_REJECT", True)
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == FailureCode.S9_CROSS_BORDER_BLOCKED


def test_cross_border_warning_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["source_url"] = "https://www.youtube.com/watch?v=abc"
    monkeypatch.setattr("agent.config.STRICT_CROSS_BORDER_REJECT", False)
    contract = normalize_analysis_result(raw)
    assert any(w.code == WarningCode.W9_CROSS_BORDER_SOURCE.value for w in contract.warnings)


def test_adapter_flags_platform_source_url_mismatch() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["platform"] = "douyin"
    raw["source_url"] = "https://www.xiaohongshu.com/explore/abc"
    contract = normalize_analysis_result(raw)
    assert contract.platform == Platform.XIAOHONGSHU
    assert any(
        w.code == WarningCode.W13_PLATFORM_URL_MISMATCH.value and w.field == "platform"
        for w in contract.warnings
    )


def test_minor_audit_keyword_hit() -> None:
    raw = _load(SYNTH / "jiating_chufang" / "001.json")
    raw["scenes"][0]["dialogue_and_narration"] = "宝宝在镜头前开心挥手"
    contract = normalize_analysis_result(raw)
    assert any(
        w.code == WarningCode.W14_MINOR_SUBJECT_DETECTED.value and w.field == "scenes[1]"
        for w in contract.warnings
    )


def test_minor_audit_no_false_positive() -> None:
    raw = _load(SYNTH / "jiating_chufang" / "001.json")
    for scene in raw["scenes"]:
        scene["dialogue_and_narration"] = "今天发现一个宝藏厨房角落"
        scene["visual_content"] = "厨房台面和餐具，没有人物"
        scene["subject"] = "厨房"
    contract = normalize_analysis_result(raw)
    assert not any(w.code == WarningCode.W14_MINOR_SUBJECT_DETECTED.value for w in contract.warnings)


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
    # toprador 对齐:分镜标题字段从 `scene` 改为 `theme`;空标题走通用兜底。
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["scenes"][0]["theme"] = ""
    contract = normalize_analysis_result(raw)
    assert contract.scenes[0].theme.startswith("镜头")
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


def _real_corpus_ready() -> bool:
    """real_v1 is "ready" only when it has ≥ 20 fixtures AND none are still A-only stubs.

    Stubs carry `_stub_status: "A_only_pending_founder_label_*"` to mark them as
    work-in-progress (per `docs/nexus/founder_log/p0-c_founder_handoff.md`). While
    stubs exist (or count < 20), the Gate G2 test skips — same intent as the
    original existence-only skipif, but tolerates partial labeling progress
    without failing CI."""
    real_dir = FIXTURES_ROOT / "real_v1"
    if not real_dir.exists():
        return False
    samples = list(real_dir.rglob("*.json"))
    if len(samples) < 20:
        return False
    for fp in samples:
        try:
            payload = json.loads(fp.read_text())
        except Exception:
            return False
        status = str(payload.get("_stub_status") or "")
        if status.startswith("A_only_pending_founder_label"):
            return False
    return True


@pytest.mark.skipif(
    not _real_corpus_ready(),
    reason="real_v1 corpus not yet ≥20 hand-labeled samples (stubs may exist); see p0-c_founder_handoff.md",
)
def test_phase0_gate_field_completeness_real() -> None:
    """Phase 0 Gate G2: ≥ 90% core-field completeness over real samples (≥20)."""
    required_fields = [
        "summary", "theme", "target_audience", "material_benefit", "hook",
        "main_elements", "micro_innovation", "pain_points", "emotion_trigger", "bgm_style",
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
        ("viral_analysis.summary", ""),  # toprador 维度,空 → 兜底告警
        ("viral_analysis.hook", ""),  # falls back, must warn
        ("scenes.0.theme", ""),  # 分镜标题空 → W4 通用兜底告警
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


# ---------- W4D5: audio / production / full_transcript ----------


def test_happy_fixtures_carry_audio_and_production() -> None:
    """W4D5: happy fixtures backfilled with audio + production blocks must validate without W15/W16."""
    for fp in HAPPY_FIXTURES:
        contract = normalize_analysis_result(_load(fp))
        # audio populated → no W15
        assert contract.viral_analysis.audio.bgm
        assert contract.viral_analysis.audio.voice_pace
        assert contract.viral_analysis.audio.sound_effects
        # production populated → no W16
        assert contract.viral_analysis.production.cost_tier in {
            "solo_phone", "small_team", "post_heavy",
        }
        for w in contract.warnings:
            assert w.code != WarningCode.W15_AUDIO_FALLBACK.value, (
                f"happy fixture {fp.name} unexpectedly emitted W15"
            )
            assert w.code != WarningCode.W16_PRODUCTION_FALLBACK.value, (
                f"happy fixture {fp.name} unexpectedly emitted W16"
            )


def test_adapter_emits_w15_when_audio_block_missing() -> None:
    """Upstream forgets `audio` → adapter backfills + emits W15."""
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["viral_analysis"].pop("audio", None)
    contract = normalize_analysis_result(raw)
    assert contract.viral_analysis.audio.bgm == "n/a — storyline 未呈现"
    assert any(w.code == WarningCode.W15_AUDIO_FALLBACK.value for w in contract.warnings)


def test_adapter_emits_w16_when_production_block_missing() -> None:
    """Upstream forgets `production` → adapter backfills + emits W16. cost_tier defaults solo_phone."""
    raw = _load(SYNTH / "yuer_richang" / "001.json")
    raw["viral_analysis"].pop("production", None)
    contract = normalize_analysis_result(raw)
    assert contract.viral_analysis.production.cost_tier == "solo_phone"
    assert contract.viral_analysis.production.estimated_hours == 1.0
    assert contract.viral_analysis.production.replaceable_anchors == []
    assert any(w.code == WarningCode.W16_PRODUCTION_FALLBACK.value for w in contract.warnings)


def test_adapter_emits_w15_for_partial_audio_axes() -> None:
    """Single missing axis → adapter fills it + emits W15 once with axis list."""
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["viral_analysis"]["audio"] = {
        "bgm": "实际的 BGM 描述",
        # voice_pace + sound_effects missing
    }
    contract = normalize_analysis_result(raw)
    assert contract.viral_analysis.audio.bgm == "实际的 BGM 描述"
    assert contract.viral_analysis.audio.voice_pace == "n/a — storyline 未呈现"
    assert contract.viral_analysis.audio.sound_effects == "n/a — storyline 未呈现"
    w15 = [w for w in contract.warnings if w.code == WarningCode.W15_AUDIO_FALLBACK.value]
    assert len(w15) == 1
    assert "voice_pace" in w15[0].message and "sound_effects" in w15[0].message


def test_adapter_coerces_bad_cost_tier_to_solo_phone() -> None:
    """Junk cost_tier → default solo_phone (no enum-blow-up at the boundary)."""
    raw = _load(SYNTH / "jiating_chufang" / "001.json")
    raw["viral_analysis"]["production"]["cost_tier"] = "totally-bogus"
    contract = normalize_analysis_result(raw)
    assert contract.viral_analysis.production.cost_tier == "solo_phone"


def test_adapter_caps_replaceable_anchors_to_ten() -> None:
    """Upstream may flood the list; adapter caps at 10 + drops non-strings."""
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["viral_analysis"]["production"]["replaceable_anchors"] = (
        [f"原片场景{i} → 你的场景{i}" for i in range(15)] + [None, 42]
    )
    contract = normalize_analysis_result(raw)
    assert len(contract.viral_analysis.production.replaceable_anchors) == 10


def test_full_transcript_defaults_empty() -> None:
    """W4D5: contract.full_transcript defaults to "" when upstream omits it."""
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw.pop("full_transcript", None)
    contract = normalize_analysis_result(raw)
    assert contract.full_transcript == ""


def test_full_transcript_passes_through_when_present() -> None:
    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["full_transcript"] = "第一段：宝宝拒食\n第二段：妈妈换苹果\n第三段：宝宝抢勺子"
    contract = normalize_analysis_result(raw)
    assert "宝宝拒食" in contract.full_transcript
    assert contract.full_transcript.count("\n") == 2


def test_phase0_gate_warning_codes_have_hints() -> None:
    """Every WarningCode in the catalog has a hint string (may be empty for silent codes)."""
    for code in WarningCode:
        assert code.value in RECOVERY_HINTS, f"WarningCode {code.value} missing in RECOVERY_HINTS"


# ---------- W5D3 CR-P0 — adapter all-scenes-dropped degenerate ----------


def test_adapter_all_scenes_dropped_raises_explicit_hardfailure() -> None:
    """Doubao occasionally returns every scene with timestamp_start >= duration_s.
    The drop pass then empties `normalized`, and W18 pad's `and normalized` guard
    silently no-ops, letting the contract validator hard-fail. W5D3 CR-P0 fix:
    detect the degenerate case and raise S5_INVALID_PAYLOAD with a real hint
    instead of letting the user see a generic validation error."""
    from agent.cascade.failures import FailureCode, HardFailure

    raw = _load(SYNTH / "baomam_fushi" / "001.json")
    raw["duration_s"] = 30
    raw["scenes"] = [
        {"scene_index": 1, "timestamp_start": 60, "timestamp_end": 65,
         "shot_type": "wide", "camera_movement": "static", "description": "x"},
        {"scene_index": 2, "timestamp_start": 70, "timestamp_end": 75,
         "shot_type": "wide", "camera_movement": "static", "description": "y"},
        {"scene_index": 3, "timestamp_start": 80, "timestamp_end": 85,
         "shot_type": "wide", "camera_movement": "static", "description": "z"},
    ]
    with pytest.raises(HardFailure) as exc:
        normalize_analysis_result(raw)
    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD
    # The debug_detail should hint at the degenerate timestamps so /admin/events
    # tells operators what happened.
    assert "duration" in str(exc.value).lower() or "timestamp" in str(exc.value).lower()
