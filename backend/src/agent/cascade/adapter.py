"""Cascade analysis adapter (P0-4).

normalize_analysis_result(raw) takes a best-effort JSON-like payload from any
upstream analyzer and returns a fully-validated CascadeAnalysisContract,
applying every fallback rule from docs/TOPRADOR_SCHEMA.md §5.

Karpathy review rule: never fail silently. Every fallback emits a Warning_.
Every unrecoverable issue raises HardFailure with a stable FailureCode.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from agent import config
from agent.cascade.contract import (
    CameraMovement,
    CascadeAnalysisContract,
    Platform,
    Scene,
    SCHEMA_VERSION,
    Severity,
    ShotType,
    ViralAnalysis,
    Warning_,
)
from agent.cascade.failures import FailureCode, HardFailure, WarningCode
from agent.cascade.minor_audit import detect_minor_subjects


_VIRAL_FALLBACKS: dict[str, str] = {
    "hook": "未识别开场钩子",
    "pacing": "未识别节奏特征",
    "climax": "未识别爆点",
    "visual_style": "自然风格",
    "emotional_arc": "未识别情绪轨迹",
    "target_audience": "未识别目标人群",
    "engagement_levers": "未识别互动钩子",
    # NOTE: replicable_formula has no fallback — it is HARD-required (S3).
}

_KNOWN_PII_KEYS = frozenset({
    "author_uid", "author_handle", "author_avatar_url", "uid",
    # Added per Stage 4 compliance audit (PIPL minimization)
    "author_id", "author_nickname", "author_name",
    "ip_address", "user_ip", "user_phone",
})

_CROSS_BORDER_HOSTS = frozenset({"youtube.com", "youtu.be", "tiktok.com", "instagram.com"})

# Generated ULID-ish IDs use this prefix to make their provenance obvious in logs.
_AUTO_ID_PREFIX = "ana_auto_"


def normalize_analysis_result(raw: Any) -> CascadeAnalysisContract:
    """Normalize an upstream payload into the Cascade contract.

    Raises HardFailure for unrecoverable conditions; emits Warning_ entries
    on the returned contract for every silent substitution.
    """
    if not isinstance(raw, dict):
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"expected dict, got {type(raw).__name__}")

    warnings: list[Warning_] = []
    # Defensive copy — never mutate the caller's payload.
    data: dict[str, Any] = dict(raw)

    _strip_metadata(data)
    _strip_pii(data, warnings)

    _ensure_schema_version(data)
    _ensure_analysis_id(data, warnings)
    _ensure_source_url(data, warnings)
    _ensure_platform(data, warnings)
    _ensure_created_at(data)
    _ensure_model(data)
    _ensure_cost(data, warnings)
    _ensure_duration(data)

    _normalize_viral_analysis(data, warnings)
    _normalize_scenes(data, warnings)
    _audit_minor_subjects(data, warnings)
    _ensure_confidence(data, warnings)

    # Merge any pre-existing top-level warnings the upstream may have included.
    upstream_warnings = data.get("warnings") or []
    if isinstance(upstream_warnings, list):
        for w in upstream_warnings:
            if isinstance(w, dict) and "code" in w and "field" in w and "message" in w:
                w.setdefault("severity", Severity.WARN.value)
                warnings.append(Warning_(**w))
    data["warnings"] = [w.model_dump(mode="json") for w in warnings]

    try:
        return CascadeAnalysisContract(**data)
    except ValidationError as e:
        # Last-mile: anything still invalid is a payload problem we couldn't salvage.
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, str(e)) from e


# ---------- field-level normalizers ----------


def _strip_metadata(data: dict[str, Any]) -> None:
    """Silently remove leading-underscore keys.

    Convention: any top-level key starting with `_` is fixture / debug metadata
    that is not part of the contract. Stripping is silent — no warning.
    """
    for key in [k for k in data.keys() if isinstance(k, str) and k.startswith("_")]:
        del data[key]


def _strip_pii(data: dict[str, Any], warnings: list[Warning_]) -> None:
    """Silently remove known PII keys (per contract §7). One audit-warning emitted if anything was stripped."""
    stripped = False
    for key in list(data.keys()):
        if key in _KNOWN_PII_KEYS:
            del data[key]
            stripped = True
    if stripped:
        warnings.append(
            Warning_(
                code=WarningCode.W10_AUTHOR_PII_STRIPPED.value,
                field="<root>",
                message="upstream PII keys stripped",
                severity=Severity.INFO,
            )
        )


def _ensure_schema_version(data: dict[str, Any]) -> None:
    # Karpathy rule: schema_version is mandatory. Missing OR explicit-empty is a HARD failure —
    # an upstream that omits or blanks this field is signalling active corruption.
    if "schema_version" not in data:
        raise HardFailure(FailureCode.S2_VERSION_MISMATCH, "schema_version field missing")
    raw_version = data["schema_version"]
    if not isinstance(raw_version, str) or not raw_version.strip():
        raise HardFailure(FailureCode.S2_VERSION_MISMATCH, f"schema_version is blank: {raw_version!r}")
    if not raw_version.startswith("1."):
        raise HardFailure(
            FailureCode.S2_VERSION_MISMATCH,
            f"schema_version={raw_version!r}; only 1.x is accepted in Phase 1",
        )


def _ensure_analysis_id(data: dict[str, Any], warnings: list[Warning_]) -> None:
    aid = data.get("analysis_id")
    if not isinstance(aid, str) or not aid.strip():
        data["analysis_id"] = f"{_AUTO_ID_PREFIX}{uuid.uuid4().hex[:16]}"
        warnings.append(
            Warning_(
                code=WarningCode.W1_AUTO_ID.value,
                field="analysis_id",
                message="upstream did not provide analysis_id; generated locally",
                severity=Severity.INFO,
            )
        )


def _ensure_source_url(data: dict[str, Any], warnings: list[Warning_]) -> None:
    url = data.get("source_url")
    if not isinstance(url, str) or not url.strip():
        raise HardFailure(FailureCode.S1_NO_SOURCE_URL, "source_url missing or blank")
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise HardFailure(FailureCode.S1_NO_SOURCE_URL, f"source_url unparseable: {e}") from e
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HardFailure(
            FailureCode.S1_NO_SOURCE_URL,
            f"source_url must be http(s) with a host; got {url!r}",
        )
    host = parsed.netloc.lower()
    # Match either exact host or "www.X" style suffix.
    if any(host == h or host.endswith("." + h) for h in _CROSS_BORDER_HOSTS):
        if config.STRICT_CROSS_BORDER_REJECT:
            raise HardFailure(
                FailureCode.S9_CROSS_BORDER_BLOCKED,
                f"cross-border platform blocked: {host}",
            )
        warnings.append(
            Warning_(
                code=WarningCode.W9_CROSS_BORDER_SOURCE.value,
                field="source_url",
                message=f"cross-border platform: {host}",
                severity=Severity.INFO,
            )
        )


def _ensure_platform(data: dict[str, Any], warnings: list[Warning_]) -> None:
    p = data.get("platform")
    if not isinstance(p, str):
        data["platform"] = Platform.OTHER.value
    elif p not in {member.value for member in Platform}:
        data["platform"] = Platform.OTHER.value
    else:
        data["platform"] = p

    sniffed = _platform_from_url(str(data.get("source_url") or ""))
    if sniffed and data["platform"] != sniffed:
        original = data["platform"]
        data["platform"] = sniffed
        warnings.append(
            Warning_(
                code=WarningCode.W13_PLATFORM_URL_MISMATCH.value,
                field="platform",
                message=f"platform {original!r} disagrees with source_url host; using {sniffed!r}",
                severity=Severity.WARN,
            )
        )


def _platform_from_url(source_url: str) -> str | None:
    try:
        host = urlparse(source_url).netloc.lower()
    except ValueError:
        return None
    if (
        host == "xiaohongshu.com"
        or host.endswith(".xiaohongshu.com")
        or host == "xhslink.com"
        or host.endswith(".xhslink.com")
    ):
        return Platform.XIAOHONGSHU.value
    if host == "douyin.com" or host.endswith(".douyin.com"):
        return Platform.DOUYIN.value
    return None


def _ensure_created_at(data: dict[str, Any]) -> None:
    if "created_at" not in data or not data["created_at"]:
        data["created_at"] = datetime.now(timezone.utc).isoformat()


def _ensure_model(data: dict[str, Any]) -> None:
    if not isinstance(data.get("model"), str) or not data["model"].strip():
        data["model"] = "unknown"


def _ensure_cost(data: dict[str, Any], warnings: list[Warning_]) -> None:
    cost = data.get("cost_cny")
    if cost is None:
        data["cost_cny"] = 0.0
        warnings.append(
            Warning_(
                code=WarningCode.W8_COST_UNKNOWN.value,
                field="cost_cny",
                message="upstream did not report cost; G6 Phase 1 Gate measurement may be incomplete",
                severity=Severity.WARN,
            )
        )
        return
    try:
        cost_f = float(cost)
    except (TypeError, ValueError) as e:
        raise HardFailure(FailureCode.S6_NEGATIVE_COST, f"cost_cny not numeric: {cost!r}") from e
    if cost_f < 0:
        raise HardFailure(FailureCode.S6_NEGATIVE_COST, f"cost_cny={cost_f}")
    data["cost_cny"] = cost_f


def _ensure_duration(data: dict[str, Any]) -> None:
    d = data.get("duration_s")
    if d is None:
        # Derive from the last scene's timestamp_end if we can; otherwise mark 1 (Pydantic min)
        scenes = data.get("scenes")
        if isinstance(scenes, list) and scenes:
            last = scenes[-1]
            if isinstance(last, dict) and "timestamp_end" in last:
                try:
                    data["duration_s"] = max(1, int(round(float(last["timestamp_end"]))))
                    return
                except (TypeError, ValueError):
                    pass
        data["duration_s"] = 1


def _normalize_viral_analysis(data: dict[str, Any], warnings: list[Warning_]) -> None:
    va = data.get("viral_analysis")
    if not isinstance(va, dict):
        # If the whole block is missing, we can salvage only if replicable_formula
        # surfaces elsewhere — which it doesn't. HARD fail.
        raise HardFailure(
            FailureCode.S3_NO_FORMULA,
            "viral_analysis missing entirely; cannot extract replicable_formula",
        )

    formula = va.get("replicable_formula")
    if not isinstance(formula, str) or not formula.strip():
        raise HardFailure(FailureCode.S3_NO_FORMULA, "viral_analysis.replicable_formula blank")
    # Trim to contract max
    va["replicable_formula"] = formula.strip()[:120]

    for key, fallback in _VIRAL_FALLBACKS.items():
        val = va.get(key)
        if not isinstance(val, str) or not val.strip():
            va[key] = fallback
            warnings.append(
                Warning_(
                    code=WarningCode.W2_FALLBACK_USED.value,
                    field=f"viral_analysis.{key}",
                    message=f"absent or blank; used fallback {fallback!r}",
                    severity=Severity.WARN,
                )
            )
        else:
            va[key] = val.strip()[:80]

    data["viral_analysis"] = va
    # validate now so we get a focused error rather than a top-level one
    try:
        ViralAnalysis(**va)
    except ValidationError as e:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"viral_analysis: {e}") from e


def _normalize_scenes(data: dict[str, Any], warnings: list[Warning_]) -> None:
    scenes_raw = data.get("scenes")
    if not isinstance(scenes_raw, list):
        raise HardFailure(FailureCode.S4_SCENES_LEN_OUT_OF_RANGE, "scenes not a list")

    if len(scenes_raw) < 3:
        raise HardFailure(
            FailureCode.S4_SCENES_LEN_OUT_OF_RANGE,
            f"scenes length {len(scenes_raw)} < 3",
        )

    if len(scenes_raw) > 12:
        kept = scenes_raw[:12]
        warnings.append(
            Warning_(
                code=WarningCode.W3_SCENES_TRUNCATED.value,
                field="scenes",
                message=f"truncated from {len(scenes_raw)} to 12",
                severity=Severity.WARN,
            )
        )
        scenes_raw = kept

    # First, sort by timestamp_start if necessary.
    def _ts(s: dict) -> float:
        try:
            return float(s.get("timestamp_start", 0.0))
        except (TypeError, ValueError):
            return 0.0

    needs_sort = False
    for i in range(1, len(scenes_raw)):
        if _ts(scenes_raw[i]) < _ts(scenes_raw[i - 1]):
            needs_sort = True
            break
    if needs_sort:
        scenes_raw = sorted(scenes_raw, key=_ts)
        warnings.append(
            Warning_(
                code=WarningCode.W5_TIMESTAMPS_SORTED.value,
                field="scenes",
                message="timestamps were not monotonic; reordered",
                severity=Severity.INFO,
            )
        )

    normalized: list[dict] = []
    for i, s in enumerate(scenes_raw, start=1):
        if not isinstance(s, dict):
            raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"scenes[{i - 1}] not a dict")
        ns = dict(s)
        ns["scene_index"] = i

        # scene label
        label = ns.get("scene")
        if not isinstance(label, str) or not label.strip():
            ns["scene"] = f"镜头 {i}"
            warnings.append(
                Warning_(
                    code=WarningCode.W4_GENERIC_SCENE_LABEL.value,
                    field=f"scenes[{i - 1}].scene",
                    message="scene label absent; used generic",
                    severity=Severity.WARN,
                )
            )
        else:
            ns["scene"] = label.strip()[:120]

        # dialogue may be empty — that's OK (silent scene)
        d = ns.get("dialogue_and_narration")
        ns["dialogue_and_narration"] = d.strip()[:2000] if isinstance(d, str) else ""

        # visual_content is required non-empty
        vc = ns.get("visual_content")
        if not isinstance(vc, str) or not vc.strip():
            # Salvage: derive from scene label
            ns["visual_content"] = ns["scene"][:200]
            warnings.append(
                Warning_(
                    code=WarningCode.W2_FALLBACK_USED.value,
                    field=f"scenes[{i - 1}].visual_content",
                    message="visual_content absent; derived from scene label",
                    severity=Severity.WARN,
                )
            )
        else:
            ns["visual_content"] = vc.strip()[:200]

        # subject — optional. Distinguish three cases:
        #   - absent: leave None silently (true optional)
        #   - present-but-wrong-type: drop + warn (schema §5)
        #   - present-as-string: normalize
        if "subject" in ns:
            subj = ns["subject"]
            if subj is None:
                ns["subject"] = None
            elif isinstance(subj, str):
                ns["subject"] = subj.strip()[:80] if subj.strip() else None
            else:
                ns["subject"] = None
                warnings.append(
                    Warning_(
                        code=WarningCode.W2_FALLBACK_USED.value,
                        field=f"scenes[{i - 1}].subject",
                        message=f"subject was {type(subj).__name__}; expected string. dropped.",
                        severity=Severity.WARN,
                    )
                )
        else:
            ns["subject"] = None

        # enums — schema §5 distinguishes:
        #   - missing/unknown-enum-string: silent default (would be "too noisy")
        #   - present but wrong type: drop + warning
        for enum_key, enum_cls, default in (
            ("shot_type", ShotType, ShotType.MEDIUM.value),
            ("camera_movement", CameraMovement, CameraMovement.STATIC.value),
        ):
            valid_values = {m.value for m in enum_cls}
            if enum_key not in ns:
                ns[enum_key] = default
                continue
            val = ns[enum_key]
            if isinstance(val, str):
                ns[enum_key] = val if val in valid_values else default
            else:
                # wrong type — emit a warning per schema §5
                ns[enum_key] = default
                warnings.append(
                    Warning_(
                        code=WarningCode.W2_FALLBACK_USED.value,
                        field=f"scenes[{i - 1}].{enum_key}",
                        message=f"{enum_key} was {type(val).__name__}; expected string. used {default!r}.",
                        severity=Severity.WARN,
                    )
                )

        # first_frame_url — keep if it's a string; HEAD-check is a future enhancement
        # (Phase 0 keeps this synchronous and dependency-free)
        ff = ns.get("first_frame_url")
        ns["first_frame_url"] = ff if isinstance(ff, str) and ff.startswith(("http://", "https://")) else None

        ns.setdefault("warnings", [])
        normalized.append(ns)

    # Re-sort + index-rewrite done. Now:
    #  1. clamp negative starts to 0 (with warning if changed)
    #  2. clamp end > duration_s back to duration_s (with warning)
    #  3. ensure end > start; on inversion, bump end and emit warning
    #  4. if any bump pushes a scene's end past the next scene's start, re-sort + warn
    duration_s = float(data.get("duration_s") or 0)
    any_clamped = False
    for i, s in enumerate(normalized):
        try:
            start = float(s.get("timestamp_start", 0.0))
            end = float(s.get("timestamp_end", start + 0.1))
        except (TypeError, ValueError) as e:
            raise HardFailure(
                FailureCode.S5_INVALID_PAYLOAD,
                f"scenes[{i}] timestamps not numeric: {e}",
            ) from e

        new_start = max(0.0, start)
        if new_start != start:
            warnings.append(
                Warning_(
                    code=WarningCode.W12_TIMESTAMP_CLAMPED.value,
                    field=f"scenes[{i}].timestamp_start",
                    message=f"start {start} < 0; clamped to 0",
                    severity=Severity.WARN,
                )
            )
            any_clamped = True

        new_end = end
        if duration_s > 0 and new_end > duration_s:
            warnings.append(
                Warning_(
                    code=WarningCode.W12_TIMESTAMP_CLAMPED.value,
                    field=f"scenes[{i}].timestamp_end",
                    message=f"end {end} > duration_s {duration_s}; clamped",
                    severity=Severity.WARN,
                )
            )
            new_end = duration_s
            any_clamped = True

        if new_end <= new_start:
            # Zero or inverted duration — bump and warn. Cap at duration_s if known.
            bumped = new_start + 0.1
            if duration_s > 0:
                bumped = min(bumped, duration_s)
            if bumped <= new_start:
                # Even the bump cannot produce a valid interval (start is at/beyond duration_s).
                raise HardFailure(
                    FailureCode.S4_SCENES_LEN_OUT_OF_RANGE,
                    f"scenes[{i}] cannot produce non-zero duration within video length {duration_s}",
                )
            warnings.append(
                Warning_(
                    code=WarningCode.W12_TIMESTAMP_CLAMPED.value,
                    field=f"scenes[{i}].timestamp_end",
                    message=f"end {end} <= start {new_start}; bumped to {bumped}",
                    severity=Severity.WARN,
                )
            )
            new_end = bumped
            any_clamped = True

        s["timestamp_start"] = new_start
        s["timestamp_end"] = new_end

    # If the bumps disturbed monotonicity (e.g., scene i's bumped end > scene i+1's start),
    # re-sort and re-index. Emit W5_TIMESTAMPS_SORTED if order actually changes.
    if any_clamped and len(normalized) > 1:
        before = [s["timestamp_start"] for s in normalized]
        normalized = sorted(normalized, key=lambda s: s["timestamp_start"])
        after = [s["timestamp_start"] for s in normalized]
        if before != after:
            warnings.append(
                Warning_(
                    code=WarningCode.W5_TIMESTAMPS_SORTED.value,
                    field="scenes",
                    message="post-clamp re-sort changed scene order",
                    severity=Severity.INFO,
                )
            )
        # If the clamped/bumped scenes still overlap, signal explicitly rather than letting
        # Pydantic catch this as S5_INVALID_PAYLOAD.
        for i in range(1, len(normalized)):
            if normalized[i]["timestamp_start"] < normalized[i - 1]["timestamp_end"]:
                raise HardFailure(
                    FailureCode.S4_SCENES_LEN_OUT_OF_RANGE,
                    f"scenes[{i}] still overlaps after clamp; upstream timestamps inconsistent",
                )
        # Re-index 1..N after sort
        for idx, s in enumerate(normalized, start=1):
            s["scene_index"] = idx

    data["scenes"] = normalized


def _audit_minor_subjects(data: dict[str, Any], warnings: list[Warning_]) -> None:
    scene_indices = detect_minor_subjects(data.get("scenes") or [])
    for scene_index in scene_indices:
        warnings.append(
            Warning_(
                code=WarningCode.W14_MINOR_SUBJECT_DETECTED.value,
                field=f"scenes[{scene_index}]",
                message="minor subject keyword detected",
                severity=Severity.INFO,
            )
        )


def _ensure_confidence(data: dict[str, Any], warnings: list[Warning_]) -> None:
    c = data.get("confidence")
    if c is None:
        # Heuristic: start at 1.0 and subtract 0.1 per warning, clamped.
        computed = max(0.0, min(1.0, 1.0 - 0.1 * len(warnings)))
        data["confidence"] = computed
        warnings.append(
            Warning_(
                code=WarningCode.W7_CONFIDENCE_COMPUTED.value,
                field="confidence",
                message=f"upstream did not provide confidence; computed = {computed:.2f}",
                severity=Severity.INFO,
            )
        )
        return
    try:
        c_f = float(c)
    except (TypeError, ValueError) as e:
        raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, f"confidence not numeric: {c!r}") from e
    clamped = max(0.0, min(1.0, c_f))
    if clamped != c_f:
        warnings.append(
            Warning_(
                code=WarningCode.W11_CONFIDENCE_CLAMPED.value,
                field="confidence",
                message=f"confidence {c_f} clamped to {clamped}",
                severity=Severity.WARN,
            )
        )
    data["confidence"] = clamped
