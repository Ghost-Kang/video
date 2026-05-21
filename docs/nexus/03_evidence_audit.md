# Phase 0 Evidence Audit

**Audit date**: 2026-05-19
**Auditor**: EvidenceQA (skeptical pass, no fantasy reporting)
**Test suite at time of audit**: `tests/test_cascade_contract.py` — **30/30 PASS** (confirmed by re-running)

## Verdict: NEEDS WORK

The contract module is well-factored, the failure taxonomy is the cleanest part of the codebase, and the happy-path fixtures are honest. But there is a **systemic pattern of silent fills that the test suite cannot detect** because the tests check that the happy fixtures stay clean and that a handful of cherry-picked corruptions raise. The adapter **routinely violates Karpathy's "no silent failure" rule on at least six concrete code paths**, and Schema §5's fallback table is not implemented as written. The Phase 0 Gate criterion "静默失败 = 0" is currently false in production behavior; the test that claims to prove it (`test_phase0_gate_no_silent_failures`) only tests cases the adapter already handles loudly.

This is not the contract module shipping in its current form. It is the contract module needing a tightening pass before being declared upstream-of-record.

---

## Issues found

### 1. [BUG] [BLOCKER] — Five Schema §5 fallback rows are implemented as silent fills

**Where**: `backend/src/agent/cascade/adapter.py:130-200`, `:374-378`, `:406-425`

**Evidence** (each row from Schema §5, observed adapter behavior, no warning emitted in any case):

| Schema §5 row | Schema-promised behavior | Actual adapter behavior |
|---|---|---|
| `schema_version` missing | **HARD FAIL S2_VERSION_MISMATCH** | `_ensure_schema_version` (line 130-141) sets `data["schema_version"] = "1.0"` and returns. No warning, no failure. |
| `confidence` out of range | clamp `[0,1]` **+ warn** | `_ensure_confidence` line 425: `data["confidence"] = max(0.0, min(1.0, c_f))` — silent clamp, no warning |
| `scenes[].timestamp_*` out of range | clamp to `[0, duration_s]` **+ warn** | Not implemented at all. `_normalize_scenes` only checks `end > start`; never compares against `duration_s`. Reproduced: `timestamp_end=9999.0` with `duration_s=10` returns 9999.0, zero warnings. |
| `scenes[].subject` wrong type | drop **+ warning** | Line 370: silently sets to `None` when not a string. No warning. |
| `scenes[].shot_type` **wrong type** (vs unknown enum) | drop **+ warning** | Line 374-375: collapses both "missing/unknown" (silent OK per schema) and "wrong type" (warn-required per schema) into the same silent coercion to `"medium"`. The schema explicitly distinguishes these two cases; the adapter does not. |

Reproductions (all four ran on a clean fixture):

```python
# missing schema_version
>>> c = normalize_analysis_result({...no schema_version...})
>>> c.schema_version, c.warnings
('1.0', [])

# confidence 1.5
>>> c = normalize_analysis_result({...'confidence': 1.5...})
>>> c.confidence, c.warnings
(1.0, [])

# timestamp out of duration range
>>> c = normalize_analysis_result({...duration_s=10, scenes[2].timestamp_end=9999.0...})
>>> c.scenes[2].timestamp_end, c.warnings
(9999.0, [])

# subject wrong type
>>> raw['scenes'][0]['subject'] = 12345
>>> c = normalize_analysis_result(raw)
>>> c.scenes[0].subject, c.warnings
(None, [])
```

**Why this matters**: This is Karpathy's hardest rule — "No silent failures. Any field missing, malformed, or fallback-substituted is recorded in warnings[]" (TOPRADOR_SCHEMA.md §0.4). It is also Phase 0 Gate criterion **G3 "静默失败 = 0"** (PHASED_PLAN §3.2, restated in TOPRADOR_SCHEMA.md §11). Five silent fills means the gate cannot honestly be claimed closed. Downstream Cascade UI will trust whatever this returns; a bad `schema_version` upstream right now becomes a confident "1.0" downstream with no banner, no recovery action, no audit trail.

**Fix**:
- `_ensure_schema_version`: when `raw_version` is missing **or empty**, raise `HardFailure(S2_VERSION_MISMATCH, "schema_version missing")`. Do not silently fill.
- `_ensure_confidence`: when clamping, append `Warning_(code="W?_CONFIDENCE_CLAMPED", field="confidence", ...)`. Add the warning code to `failures.py`.
- `_normalize_scenes` clamp loop (line 389-401): after `_ensure_duration`, check each `timestamp_end > duration_s`; clamp + emit a new `W?_TIMESTAMP_OUT_OF_DURATION` warning.
- `subject` wrong-type and `shot_type`/`camera_movement` wrong-type: append a `W2_FALLBACK_USED` warning. Distinguish from the "unknown enum string" path (which the schema explicitly says is silent).

---

### 2. [BUG] [MAJOR] — `timestamp_end <= timestamp_start` silent bump can corrupt downstream monotonicity and surfaces as catch-all S5

**Where**: `backend/src/agent/cascade/adapter.py:389-401`

**Evidence**: Lines 398-401 silently set `end = start + 0.1` when `end <= start`. Then the bumped end is **never re-sorted** relative to the next scene's start. Reproduction:

```python
scenes = [
    {scene_index:1, timestamp_start:0.0, timestamp_end:5.0, ...},
    {scene_index:2, timestamp_start:5.0, timestamp_end:5.0, ...},  # zero-duration
    {scene_index:3, timestamp_start:5.0, timestamp_end:10.0, ...},
]
# After silent bump: scene 2 becomes (5.0 -> 5.1)
# Contract validator at contract.py:144-153 then sees scene 3 start (5.0) < scene 2 end (5.1)
# -> Pydantic raises ValueError -> caught at adapter.py:96
# -> re-raised as HardFailure(S5_INVALID_PAYLOAD)
```

Observed: `HARDFAIL S5_INVALID_PAYLOAD: scenes[2].timestamp_start (5.0) < previous timestamp_end (5.1)`

Two problems compound:
1. The bump is silent (no `W5_TIMESTAMPS_SORTED` or equivalent), violating the same "no silent failure" rule.
2. The synthesized monotonicity violation surfaces as `S5_INVALID_PAYLOAD` (catch-all) rather than something recoverable. The user gets the S5 recovery actions `["RETRY_SAME_URL", "RETRY_WITH_NEW_URL", "REPORT"]`, but retrying the same URL will produce the same payload — the recovery hint is wrong because the **failure code is wrong**.

**Why this matters**: Catch-all S5 hides real upstream patterns. The Karpathy rule isn't only "raise something" — it's "raise the stable code that has the right UI recovery hint." Phase 0 Gate criterion **G4 "Every failure has UI recovery path"** is implemented in `failures.py`, but the adapter routes legitimate recoverable issues into a code whose recovery path doesn't apply.

**Fix**: After the bump at line 399, either (a) re-run the sort, or (b) collapse the zero-duration scene into the next one with a warning, or (c) raise `S4_SCENES_LEN_OUT_OF_RANGE` if the bump would violate monotonicity. The simplest fix is (a): re-sort `normalized` by `timestamp_start` after the bump loop, and emit `W5_TIMESTAMPS_SORTED` if the order changed.

Additionally, the bump itself (end ← start + 0.1) needs a warning. Currently it is the **only** scene-level mutation with no recorded provenance.

---

### 3. [TEST] [MAJOR] — `test_phase0_gate_field_completeness` is tautological

**Where**: `backend/tests/test_cascade_contract.py:292-307`

**Evidence**: The test iterates only over `HAPPY_FIXTURES`, which by definition have zero `W2_FALLBACK_USED` warnings (asserted in `test_happy_fixture_validates` at line 78-80). Therefore `fallback_count` is always 0, and `completeness = 1.0 - 0/total = 1.0`. The 0.90 threshold is trivially met every run, regardless of adapter behavior.

Reproduction:

```
fallback_count=0, total=24, completeness=100.00%
```

The test does not exercise the metric it claims to measure. The metric is meaningful only over a mixed corpus that **includes degraded inputs**, and the docstring (PHASED_PLAN §3.2) explicitly says this measurement should be over the 20 real samples — which do not yet exist.

**Why this matters**: This is the exact "test that proves the adapter agrees with itself" pattern you asked me to look for. Anyone reading the green checkmark assumes Phase 0 Gate G2 ("核心字段完整率 ≥ 90%") is satisfied. It is not — the gate is not even being measured.

**Fix**: Either (a) skip the test with `pytest.skip("requires real_v1 fixtures")` until the 20 real samples exist (which TOPRADOR_SCHEMA.md §8 already says is a precondition for closing the gate), or (b) include `EDGE_RECOVERABLE` fixtures in the corpus so the denominator includes payloads that legitimately need fallbacks. Option (a) is more honest because synthetic fixtures by design have the answer baked in.

---

### 4. [DESIGN] [MAJOR] — Two `FailureCode` values are unreachable from this module

**Where**: `backend/src/agent/cascade/failures.py:28-29` (declarations) — never raised in `adapter.py`

**Evidence**: `grep -nE "S7_UPSTREAM_TIMEOUT|S8_UPSTREAM_REFUSED" backend/src/agent/cascade/adapter.py` returns zero matches. They appear only in `failures.py` (definitions + recovery tables). The contract module is purely a normalizer — it never calls upstream — so these codes cannot be raised here.

This is not strictly a bug (upstream callers might raise them), but it interacts badly with **issue 1 and 2**: the adapter funnels things it could legitimately classify as `S2`/`S4`/etc. into `S5_INVALID_PAYLOAD` instead. Specifically:

- `adapter.py:96` — catch-all from `CascadeAnalysisContract(**data)` ValidationError → S5. When the underlying cause is a known one (timestamps, enums, types), the adapter loses information.
- `adapter.py:277` — re-raises a ViralAnalysis validation error as `S5_INVALID_PAYLOAD`. But the only way a ViralAnalysis validation error gets here is if `replicable_formula` was somehow set to a non-string after the line 252-253 check — in which case `S3_NO_FORMULA` is the right code.
- `adapter.py:329` — `scenes[i] not a dict` is mapped to `S5_INVALID_PAYLOAD`, but it's structurally a "scenes list malformed" condition that `S4_SCENES_LEN_OUT_OF_RANGE` (or a new `S4b`) covers more honestly.

**Why this matters**: Buffett's "circle of competence" rule applies in reverse here. The failure taxonomy is the **interface to the UI**. Wrong code = wrong recovery banner = user gets bad advice. The frontend cannot tell from `S5_INVALID_PAYLOAD` whether to suggest "try a different URL" or "the analyzer hit a corner case, retry once" — and right now both go to the same generic message.

**Fix**: Two options, pick one:
1. Tighten the catch-all sites: examine the Pydantic `ValidationError.errors()` and map specific paths to specific codes (e.g., `scenes.*.timestamp_*` → `S4` or a new code).
2. Remove S7/S8 from `FailureCode` since they are not raised by the contract module; let upstream-fetch callers define their own enum. Then document that `S5` is genuinely a catch-all of last resort.

Option 1 is the better long-term fix; option 2 is honest documentation if option 1 is deferred.

---

### 5. [BUG] [MINOR] — `_ensure_schema_version` accepts an explicit empty string by treating it as "missing"

**Where**: `backend/src/agent/cascade/adapter.py:131-136`

**Evidence**: Line 131: `if not raw_version:` is falsy-true for both `None` (missing) and `""` (explicit blank). Both paths default to `"1.0"` silently. An upstream that emits `"schema_version": ""` is signaling **active corruption**, not absence — and the adapter cannot tell the difference.

This is a corollary of issue 1 but worth calling out separately because the falsiness pattern repeats in `_ensure_model` (line 199) and `_ensure_created_at` (line 194). In all three cases, "field present but empty" is treated identically to "field missing." For `model` and `created_at` that's defensible (they have weak semantics); for `schema_version` it's not.

**Why this matters**: Karpathy review §1 — "schema_version is mandatory. Mismatches are explicit failures." An empty string IS a mismatch.

**Fix**: In `_ensure_schema_version`, change `if not raw_version:` to `if "schema_version" not in data:`, then handle the explicit-empty case separately (HardFailure).

---

### 6. [DESIGN] [MINOR] — Platform/source_url consistency is never validated

**Where**: `backend/src/agent/cascade/adapter.py:158-191`

**Evidence**: An analysis with `"platform": "douyin"` and `"source_url": "https://www.xiaohongshu.com/explore/abc"` validates cleanly with zero warnings. The cross-border host check (line 173) only fires on a small allowlist (`youtube.com`, `tiktok.com`, etc.); a `douyin`/`xiaohongshu` mismatch is silently accepted.

**Why this matters**: Phase 1 features (per the consumer matrix in TOPRADOR_SCHEMA.md §6) use `platform` for routing decisions: P1-7 发布包 generates platform-specific export bundles. A wrong platform string here will produce a publish bundle that fails on the actual target. This isn't a Phase 0 blocker, but it's a known latent bug for Phase 1.

**Fix**: Add a host→platform sniff (e.g., `xiaohongshu.com → "xiaohongshu"`, `douyin.com → "douyin"`); if the sniffed value disagrees with the declared `platform`, emit a warning (or override + warn). Defer if Phase 1 routing isn't ready to consume this.

---

### 7. [MINOR] — `import time` is unused

**Where**: `backend/src/agent/cascade/adapter.py:13`

**Evidence**: `grep -n "time" adapter.py` shows only the import line; `time.` is never called. Dead import, harmless, but is the canary that nobody ran a linter (or it isn't wired into CI).

**Why this matters**: If `ruff`/`pyflakes` isn't in pre-commit for this module, more substantive issues (issues 1-5) wouldn't be caught either.

**Fix**: Remove the import; add `ruff check` to CI if not already there.

---

## Things that worked well

1. **`failures.py` is genuinely excellent.** `HardFailure.to_payload()` is the right shape for a frontend, `RECOVERY_HINTS` are written in Brand Guardian §4-compliant 人话 (not English jargon, not field names), and `RECOVERY_ACTIONS` give the UI a stable contract independent of the message text. This is the cleanest part of the codebase.
2. **Defensive copy at adapter.py:65** (`data = dict(raw)`) is the right call and is not always obvious to do — many adapters mutate the caller's payload.
3. **`viral_analysis.replicable_formula` HARD-FAIL is correctly implemented** with both a Pydantic-level validator (`contract.py:78-80`) AND an adapter-level early raise (`adapter.py:251-253`). Belt-and-suspenders, the right pattern for a load-bearing field.
4. **PII strip is silent but emits an audit Warning** (`W10_AUTHOR_PII_STRIPPED`, severity=INFO). The fact that the UI hint for W10 is the empty string is intentional and well-documented inline (line 87 of failures.py). This is the cleanest "silent but auditable" pattern in the module.
5. **The `extra="forbid"` config on every BaseModel** turns unknown fields into hard failures rather than silent accept — this catches PII keys the adapter doesn't know about (e.g., `author_email`) instead of letting them through. Good default.
6. **Happy fixtures are honest.** No fantasy content; the dialogue and scenes are plausible for the niches they claim. The `_provenance: "synthetic_v1"` and `_purpose` keys are properly stripped by `_strip_metadata` — and the test for that strip is implicit but correct.

---

## My evidence trail

**Files read** (all absolute):
- `/Users/kang/github/openrhtv/OpenRHTV/docs/TOPRADOR_SCHEMA.md` (full)
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/contract.py` (full, 154 lines)
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/failures.py` (full, 153 lines)
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/adapter.py` (full, 425 lines)
- `/Users/kang/github/openrhtv/OpenRHTV/backend/tests/test_cascade_contract.py` (full, 363 lines)
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/fixtures/synthetic_v1/baomam_fushi/001.json`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/fixtures/synthetic_v1/edge_no_formula.json`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/fixtures/synthetic_v1/edge_low_confidence.json`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/fixtures/synthetic_v1/edge_non_monotonic.json`

**Searches performed**:
- `grep -nE "S7_UPSTREAM_TIMEOUT|S8_UPSTREAM_REFUSED" backend/src/agent/cascade/` — to confirm unreachable failure codes
- `grep -n "FailureCode\." backend/src/agent/cascade/adapter.py` — to enumerate every failure-code raise site
- `grep -n "time" backend/src/agent/cascade/adapter.py` — to confirm dead import

**Tests run**:
```
$ cd /Users/kang/github/openrhtv/OpenRHTV/backend && uv run pytest tests/test_cascade_contract.py -v
30 passed in 0.02s
```
All 30 pass at the time of audit. This is not contested; the audit finds gaps the tests do not cover, not failures the tests catch.

**Behavioral probes** (each ran via `uv run python -c ...` against `normalize_analysis_result`):
- Missing `schema_version` → returned `"1.0"`, 0 warnings (issue 1)
- `confidence: 1.5` → clamped to 1.0, 0 warnings (issue 1)
- `timestamp_end=9999.0` with `duration_s=10` → returned 9999.0, 0 warnings (issue 1)
- `subject: 12345` → returned `None`, 0 warnings (issue 1)
- `shot_type: 42` → coerced to `"medium"`, 0 warnings (issue 1)
- Zero-duration scene → silent +0.1 bump → S5_INVALID_PAYLOAD masking a recoverable monotonicity problem (issue 2)
- `platform: "douyin"` + `source_url: xiaohongshu.com` → silently accepted (issue 6)
- `author_email` (PII not in allowlist) → caught by `extra="forbid"` as S5; documents the PII allowlist gap (positive observation in "things that worked")
- Empty-string `schema_version` → silently defaulted (issue 5)

---

**Most important single finding**: **Issue 1** — five Schema §5 rows are implemented as silent fills. This is the rule the whole module exists to enforce, and it is broken in five places. Everything else is downstream of fixing this.
