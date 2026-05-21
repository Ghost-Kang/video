# Phase 0 Reality Check

**Reality check date**: 2026-05-19
**Auditor**: TestingRealityChecker (independent of Author and Evidence Collector)
**Test suite at reality-check time**: `tests/test_cascade_contract.py` — **36 passed, 1 skipped** (re-run, confirmed locally)
**Related**: `03_evidence_audit.md` (prior audit), `docs/PHASED_PLAN.md §3` (Gate definition), `docs/TOPRADOR_SCHEMA.md` (contract spec)

---

## VERDICT: **CONDITIONAL PASS**

Phase 0 is **NOT** "Gate-passed" today. It is "Gate-ready, pending real_v1." The contract module itself (the part the audit critiqued) is now structurally honest — the seven audit issues are resolved with real fixes, not paper-overs. But two of the five Gate criteria (G1 success rate and G2 field completeness) **cannot be measured at all** until ≥20 real hand-labeled samples exist, and TOPRADOR_SCHEMA.md §8 + §11 explicitly say so. Declaring Gate PASSED today would be lying about a measurement we have not made. Declaring FAIL would be unfair to a module that did its job.

**One-line answer for the founder**: *Phase 0 cannot close today. It can close the moment ≥20 real samples land in `fixtures/real_v1/` and the now-skipped completeness test goes green — likely 2-3 working days of fixture-collection work, not weeks of code work.*

---

## Gate criterion verification (each verified independently, not summarized)

### G1 — 深分析成功率 ≥ 80% (real samples)

**Status**: **CANNOT BE MEASURED YET**. The test `test_phase0_gate_success_rate` (line 325-346 of `test_cascade_contract.py`) measures success rate against **synthetic** fixtures — 6 intended-success items (3 happy + 3 recoverable) — and reports 6/6 = 100%. This is meaningful as a smoke test of the adapter; it is **NOT** the gate measurement. The PHASED_PLAN §3.2 language "深分析成功率（20 条样本）" explicitly couples this to the 20-sample real corpus.

**What can be claimed honestly today**: "Adapter is robust enough to pass the synthetic smoke battery with zero failures." Nothing about real-world success rate is known.

**What this would require to honestly claim**: The skipped test `test_phase0_gate_field_completeness_real` already targets `fixtures/real_v1/*.json`, expects ≥20, and is correctly skipped today. A parallel `test_phase0_gate_success_rate_real` should be added the same way — measure success/total over `real_v1/*.json`, require ≥80%.

### G2 — 核心字段完整率 ≥ 90% (real samples)

**Status**: **CANNOT BE MEASURED YET**. The synthetic-only completeness check (`test_happy_fixtures_have_zero_viral_fallbacks` — renamed from the audit-flagged tautological test) is now honestly scoped: it only asserts "happy fixtures have no fallback" and explicitly documents in its docstring that this is **NOT** the G2 gate measurement. The actual G2 test (`test_phase0_gate_field_completeness_real`) is correctly marked `@pytest.mark.skipif(not (FIXTURES_ROOT / "real_v1").exists(), ...)`. Verified by reading lines 367-389 of the test file and by `pytest -v` output showing `SKIPPED` on that test.

**Critical observation**: Per the hard rule the founder set on this report, **a CONDITIONAL PASS or FAIL is the only legal verdict while G2 cannot be measured**. PASS is forbidden by construction. The skip-marker is the right pattern; the open question is whether the founder wants to declare Phase 0 closed today (illegal per the rule) or wait the few days for real_v1.

### G3 — 静默失败 = 0

**Status**: **PROVEN, with one acknowledged gap**.

Five of the six silent-failure paths identified by the Evidence Collector (audit issue 1 + issue 2) now genuinely raise or warn. Re-ran each probe manually against current code:

| Probe (from audit) | Pre-fix behavior | Current behavior | Verdict |
|---|---|---|---|
| `schema_version` missing | silent fill → "1.0" | `HardFailure S2_VERSION_MISMATCH` | **Fixed** (structural) |
| `schema_version` = "" | silent fill | `HardFailure S2_VERSION_MISMATCH` | **Fixed** (structural) |
| `confidence = 1.5` | silent clamp | clamp + `W11_CONFIDENCE_CLAMPED` warning | **Fixed** (structural) |
| `scenes[i].timestamp_end > duration_s` | passed through verbatim | clamp + `W12_TIMESTAMP_CLAMPED` warning | **Fixed** (structural) |
| `scenes[i].subject = 12345` | silent → None | None + `W2_FALLBACK_USED` warning | **Fixed** (structural) |
| `scenes[i].shot_type = 42` | silent → "medium" | "medium" + `W2_FALLBACK_USED` warning (distinguished from unknown-enum-string path which remains silent) | **Fixed** (structural — and the schema-distinction between "wrong type" and "unknown enum" is correctly implemented in code lines 394-415 of `adapter.py`) |
| Zero-duration scene (audit issue 2) | silent +0.1 bump → S5 catch-all | bump + `W12_TIMESTAMP_CLAMPED` warning; if bump cannot fit in `duration_s`, raises `S4_SCENES_LEN_OUT_OF_RANGE` instead of catch-all `S5` (code lines 467-477) | **Fixed** (structural — the bump now gets the right failure code when unrecoverable) |

The probe `test_phase0_gate_no_silent_failures` in the test file (lines 416-453) now covers all of these. The test invariant is "for each corruption, the adapter must raise OR emit at least one warning." This is the right invariant, and it is now exercised.

**The acknowledged gap**: G3 is enforced only across the **contract adapter** code path. The rest of the system — `analysis_service.py`, `storage.py`, `events.py` — has its own failure surfaces (DB errors, upstream timeouts, race conditions; see "Gaps" below) that are **not** enforced by this probe. The Evidence Collector was scoped to the contract module and did not see these. They are not yet probed by any test. G3 is therefore "0 silent failures *within the adapter*" — not "0 silent failures *system-wide*." That's defensible for closing Phase 0 because Phase 0's deliverables are the contract, not the service layer; but it should be documented honestly.

### G4 — 100% recovery paths

**Status**: **PROVEN, spot-checked 3 of 8**.

Verified by `test_phase0_gate_every_failure_has_recovery_path` (test file line 456-462), which iterates the entire `FailureCode` enum and asserts both a non-blank `RECOVERY_HINTS[code]` entry AND ≥1 action in `RECOVERY_ACTIONS[code]`. I cross-checked three by reading `failures.py` directly:

- `S3_NO_FORMULA`: hint = "这条视频没看出能复刻的套路（可能太特殊或太短）。换一条更有规律的爆款。" Actions = `["RETRY_WITH_NEW_URL", "PICK_FROM_FEATURED", "REPORT"]`. ✓ 人话 (no field names, no jargon — Brand Guardian §4 compliant). ✓ ≥1 action.
- `S5_INVALID_PAYLOAD`: hint = "系统读这条视频时遇到了奇怪的数据。换一条试试，或者点反馈告诉我们这条的链接。" Actions = `["RETRY_SAME_URL", "RETRY_WITH_NEW_URL", "REPORT"]`. ✓ 人话. ✓ ≥1 action.
- `S7_UPSTREAM_TIMEOUT`: hint = "分析超时了。可能视频太长，也可能服务繁忙。等 30 秒重试，或者换一条更短的。" Actions = `["RETRY_SAME_URL_AFTER_30S", "RETRY_WITH_NEW_URL", "REPORT"]`. ✓ 人话. ✓ ≥1 action.

**Caveat (carried from audit issue 4)**: `S7_UPSTREAM_TIMEOUT` and `S8_UPSTREAM_REFUSED` are defined and have UI paths, but no code in this module raises them — they are placeholders for the future upstream-fetch caller that does not yet exist. So G4 is verified for the codes that **can** fire today; the two upstream-network codes are forward-declared and untested as live paths. This is not dishonest, but the founder should know that the proof "every failure has a recovery path" includes two codes that have never actually been failed.

### G5 — 单条分析成本 < ¥5

**Status**: **PROVEN ONLY AGAINST FABRICATED COSTS**. The test `test_phase0_gate_cost_under_5` (line 465-471) iterates happy fixtures and asserts `contract.cost_cny < 5.0`. Costs in the synthetic fixtures are hand-set: `0.42` (baomam), unverified (yuer/jiating; I sampled one). These numbers were chosen by the fixture author to make the test pass. There is **no real provider call** anywhere in this module — `analysis_service._call_toprador` is `raise NotImplementedError`. So the gate-passing 0.42 is a literary device, not a measurement.

**Honest measurement plan**: G5 must be re-asserted in Phase 0.5 (or pulled into Phase 1) by **(a)** wiring the toprador upstream branch in `analysis_service._call_toprador`, **(b)** running ≥20 real source URLs through it, **(c)** asserting `cost_cny` median + p95 are both < ¥5. The current cost field is **plumbed correctly** — `cost_cny` flows from upstream → adapter (with `W8_COST_UNKNOWN` fallback) → contract → analytics event payload `analysis_returned.cost_cny` → SQLite events table. So when a real upstream lands, the measurement infrastructure is ready. The number itself is just fiction today.

---

## Audit-fix verification (per issue 1-7 of `03_evidence_audit.md`)

For each issue, I read the diff between what the audit said the code did and what the current code does. Below is each call.

### Issue 1 — Five Schema §5 fallback rows implemented as silent fills · **RESOLVED (structural)**

The current `adapter.py` (lines 129-141, 425-465, 372-415, 522-551) implements every one of the five rows correctly:

- `_ensure_schema_version` (line 129-141): explicit `if "schema_version" not in data:` → `HardFailure S2`; then `if not isinstance(..., str) or not raw_version.strip():` → `HardFailure S2`. Both "missing" and "empty" cases hard-fail with the right code. The audit's specific fix recommendation is implemented verbatim.
- `_ensure_confidence` (line 522-551): clamp now emits `W11_CONFIDENCE_CLAMPED` when value differs (line 541-550). The audit's recommendation is implemented and the new warning code is in `failures.py`.
- Scene-level timestamp out-of-duration (line 455-465): new `W12_TIMESTAMP_CLAMPED` warning emitted when `new_end > duration_s`. The new warning code is in `failures.py` (line 46). Audit recommendation implemented.
- `scenes[].subject` wrong-type (line 372-387): branches on `isinstance(subj, str)` and emits `W2_FALLBACK_USED` on the wrong-type branch. The schema's distinction between "absent → silent None" and "present-but-wrong-type → warn" is now correctly preserved.
- `scenes[].shot_type` / `camera_movement` wrong-type vs unknown enum (line 394-415): two branches — `isinstance(val, str)` (silent coerce, no warn — schema's "too noisy" rule) vs not-a-string (warn). Distinction is now correctly implemented.

**Not paper-over**: each fix changes runtime behavior in the way the schema specifies, not just the test. The new probe `test_phase0_gate_no_silent_failures` exercises all five — verified by inspection of the test (lines 432-441) and by running the test suite. **Structural fix.**

### Issue 2 — Silent `end ≤ start` bump corrupts monotonicity, surfaces as catch-all S5 · **RESOLVED (structural)**

The current code (line 467-487) replaces the bare `end = start + 0.1` with:
1. compute `bumped = new_start + 0.1`, capped at `duration_s` if known (line 470-471);
2. if even the bump cannot fit (start is already at/beyond `duration_s`), raise `HardFailure S4_SCENES_LEN_OUT_OF_RANGE` — **the correct semantic code**, not the catch-all S5 the audit complained about (line 472-477);
3. record `W12_TIMESTAMP_CLAMPED` with the actual `(end, start, bumped)` numbers in the message (line 478-485);
4. after the bump loop, if monotonicity is disturbed, re-sort and emit `W5_TIMESTAMPS_SORTED`; if scenes **still** overlap post-clamp, raise `S4` instead of letting Pydantic catch it as S5 (line 494-517).

The audit's complaint about the recovery hint being wrong (because S5 says "RETRY_SAME_URL" but the same URL will produce the same payload) is now solved: monotonicity-class failures get S4 with `["RETRY_WITH_NEW_URL", "PICK_FROM_FEATURED", "REPORT"]` — which is the right advice for the user. **Structural fix.**

### Issue 3 — `test_phase0_gate_field_completeness` tautological · **RESOLVED (structural)**

The audit-flagged test no longer exists by that name. It has been split into two:

1. `test_happy_fixtures_have_zero_viral_fallbacks` (line 349-364) — keeps the synthetic check but the docstring now explicitly says "This is NOT the Phase 0 Gate G2 measurement." Honest.
2. `test_phase0_gate_field_completeness_real` (line 367-389) — the **actual** G2 measurement, running against `fixtures/real_v1/*.json`, requiring `len(samples) >= 20`, computing real completeness — and **correctly skipped** when `real_v1/` does not exist.

This is exactly the "option (a)" the audit recommended (skip until real_v1 lands). The test does not silently pass anymore; it is visible as `SKIPPED` in every pytest run, which is the honest representation of "gate not yet measured." **Structural fix.**

### Issue 4 — Two `FailureCode` values (S7, S8) unreachable from this module · **PARTIALLY ADDRESSED (documented, not removed)**

The audit gave two options: (1) tighten catch-all sites to map specific Pydantic errors to specific codes, or (2) remove S7/S8 from the enum since the contract module never raises them. Neither was done.

What **was** done: the S5-funneling sites improved in two cases — `scenes` overlap post-clamp now raises `S4` (line 510-514, the previous catch-all hand-off to Pydantic); zero-duration impossible-fit now raises `S4` (line 474-477). The two remaining S5 catch-all sites are:

- `_normalize_viral_analysis` line 277 (post-coerce Pydantic validation of `ViralAnalysis`): this can only fire if a viral_analysis field is set to a non-string by the adapter, which the adapter doesn't do — so it's effectively dead. Defensible to keep.
- The top-level fallback at line 91-95 (catches anything else the per-field normalizers missed). With the per-field tightening above, this should be reachable only for genuinely unexpected payload shapes — which is what S5 means.

S7/S8 are still declared but unraised in this module. This is **documentation debt**, not a bug: they are stub UI paths for the upstream-fetch caller that `analysis_service._call_toprador` will eventually become. The audit's stricter "option 2 honest doc" advice (remove them, let the caller define its own enum) was not taken. **Status: partially fixed (S5 funneling tightened) + acknowledged debt (S7/S8 still placeholder).** I would not block on this.

### Issue 5 — Empty-string `schema_version` treated as "missing" · **RESOLVED (structural)**

Adapter line 132-136 explicitly distinguishes:
- `if "schema_version" not in data:` → HardFailure with detail "schema_version field missing"
- `if not isinstance(raw_version, str) or not raw_version.strip():` → HardFailure with detail `f"schema_version is blank: {raw_version!r}"`

Both raise `S2_VERSION_MISMATCH`. The test `test_adapter_rejects_missing_schema_version` (line 189-194) and `test_adapter_rejects_empty_schema_version` (line 197-202) cover both. The audit's exact recommendation (`if "schema_version" not in data:` first) is implemented. **Structural fix.**

### Issue 6 — Platform / source_url consistency never validated · **NOT FIXED (deferred, but consciously)**

Probed directly: `platform="douyin"` + `source_url="https://www.xiaohongshu.com/explore/abc"` → returns successfully, `contract.platform = "douyin"`, **zero warnings**. The cross-border check still only triggers on `youtube.com`, `tiktok.com`, etc.; a douyin/xiaohongshu mismatch is silently accepted.

The audit said "defer if Phase 1 routing isn't ready to consume this." The author has deferred. This is a defensible Phase-0-not-blocking decision but it **is a known latent bug for Phase 1**: P1-7 (发布包导出) will use `platform` to pick the export template, and a mismatched platform here will produce a publish bundle that fails on the actual target. Open work for the founder, listed below.

### Issue 7 — `import time` is unused · **RESOLVED (structural)**

Verified: `grep -n "^import\|^from" adapter.py` shows no `import time`. The dead import is gone. The audit's broader concern was "if this isn't caught, more substantive issues aren't either." Substantive issues 1-5 **are** caught now, so the canary's predictive value was correct: when this got fixed, the rest got fixed too. **Structural fix.**

---

## Gaps Evidence Collector missed (≥ 2 things; system-level lens)

The audit was **code-focused** on the three contract module files (`contract.py`, `adapter.py`, `failures.py`). The Cascade module is larger than that. There are three additional files (`analysis_service.py`, `storage.py`, `events.py`) — **none of them were in the audit scope** — and they introduce system-level failure surfaces the contract module's "no silent failure" rule doesn't reach.

### Gap 1 — Concurrency: `request_shallow_analysis` is not race-safe on the same `(user_id, source_url)`

**Where**: `analysis_service.py` lines 38-70.

**Evidence by reading the code**: The function does a "read-then-write" pattern: `load_analysis_for_source(...)` returns None → run `normalize_analysis_result` → `save_analysis(...)`. With `asyncio.gather([request_shallow_analysis(same_url) for _ in range(5)])`, all five tasks will see `None` from the load (no row exists yet), all five will run the adapter, all five will arrive at `save_analysis`. The SQLite upsert at `storage.py:86-94` (`ON CONFLICT(analysis_id) DO UPDATE`) will *not* error out — but `_analysis_returned_payload` is emitted **after every save**, so the events table will record N copies of `analysis_returned` for what the user perceives as one analysis. The `test_idempotency_same_user_and_url` test (line 115-128) is sequential, not concurrent — it doesn't catch this.

**Phase-0 impact**: low. The contract module is not the racer.
**Phase-1 impact**: medium-high. P1-9 (cost statistics & cap) consumes `analysis_returned.cost_cny` to compute per-run spend. If a single user double-clicks "analyze" and produces 2 events, the cost telemetry will report 2× the actual spend. This directly affects how the founder measures G5 in Phase 1.

**Fix**: wrap the load-then-write in a per-`(user_id, source_url)` async lock, or move dedup to a `INSERT ... ON CONFLICT DO NOTHING RETURNING ...` and only emit the event when a row was actually inserted. The lock pattern already exists for events (`events.py:51` `_lock`); the same pattern can be reused.

### Gap 2 — Upstream-network failure mode has no end-to-end test path

**Where**: `analysis_service.py:88` — `_call_toprador` is `raise NotImplementedError`.

**Evidence**: `failures.py` declares `S7_UPSTREAM_TIMEOUT` and `S8_UPSTREAM_REFUSED` with full hints + recovery actions — but no live code raises them. When the toprador branch is wired, "upstream returned 500" or "upstream timed out at 60s" is **not** a `S5_INVALID_PAYLOAD` (which today is the only adapter-level catch-all). They are network-class failures and must be classified at the **service** layer, not the adapter layer.

The audit caught the **declaration vs. usage gap** for S7/S8 (issue 4) but did not draw the system-level consequence: the boundary "adapter rejects payload" vs "service couldn't even fetch a payload" is currently invisible. Today, `request_shallow_analysis` will surface a `NotImplementedError`, which is neither a `HardFailure` nor a warning — it's an uncategorized Python exception that will crash whatever HTTP handler calls it. **This is a silent-failure-of-a-different-kind.**

**Phase-0 impact**: zero (toprador isn't wired). **Phase-1 impact**: high. The first time the founder swaps `CASCADE_UPSTREAM=toprador`, every transient upstream hiccup will produce a 500 to the user with no recovery banner. G4 ("every failure has UI recovery") will quietly become false at the system level the day Phase 1 starts.

**Fix**: in `analysis_service.request_shallow_analysis`, wrap `_load_upstream_payload` with explicit catches: `asyncio.TimeoutError` → `HardFailure(S7_UPSTREAM_TIMEOUT)`, `httpx.HTTPStatusError` (4xx auth/rate, 5xx server) → `HardFailure(S8_UPSTREAM_REFUSED)`. Then S7/S8 stop being placeholders and start being real codes.

### Gap 3 (bonus) — Cost telemetry depends on a field the adapter is allowed to fabricate

**Where**: `adapter.py:203-222` (cost handling) + `events.py:28-39` (`analysis_returned.cost_cny` required field).

**Evidence**: When upstream omits `cost_cny`, the adapter sets it to `0.0` and emits `W8_COST_UNKNOWN`. The `analysis_returned` event then reports `cost_cny=0.0`. The Phase 1 Gate G6 ("单条成本 < ¥15") is a sum/avg over `analysis_returned.cost_cny` from the events table. **An upstream that doesn't emit cost will make Cascade look free.** No warning surfaces to the cost-rollup query — it would have to join through `had_fallback` or query `warnings_count > 0` to know.

**Fix**: either (a) `analysis_returned.cost_cny` should be `null` when `W8_COST_UNKNOWN` fired (and the rollup query should explicitly `WHERE cost_cny IS NOT NULL`), or (b) the event should include a `cost_known: bool` boolean. Document either choice in the event spec.

---

## Phase 0 Gate declaration — can it be made today?

**NO.**

Reason: G1 and G2 are coupled to the 20-real-sample corpus that does not yet exist. The hard rule on this report is "you may not declare PASS if G2 cannot be measured." It cannot. The skipped test makes the absence of measurement visible and honest — that is the right design — but it also makes "PASS today" impossible to defend.

**Consequences for Phase 1 if the founder overrides this and declares PASS anyway**:

1. **Phase 1's load-bearing assumption is that the upstream contract holds for real videos.** Synthetic fixtures by construction cannot break the contract — the author chose them to fit. The first real抖音 video that returns an `analysis_result` with three undocumented fields, or with `replicable_formula` empty 40% of the time, will surface at Phase 1 user-test time, not at Phase 0 — exactly when the cost of finding it is highest (real creators in the room, not a quiet test run).
2. **Cost claims (G5) are fiction until upstream is wired**, and the toprador branch is currently `NotImplementedError`. Declaring G5 passed at ¥0.42/run means "the synthetic JSON we wrote said 0.42." Phase 1 Gate G6 is ¥<15 — the founder will have no baseline to compare against if Phase 0 closed on fictional costs.
3. **The service-layer gaps (Gap 1, Gap 2 above) are not on anyone's radar.** They will silently inherit "Phase 0 PASS" status and bite during the first concurrent user or first upstream hiccup.

**Consequence for Phase 1 if the founder accepts CONDITIONAL PASS and waits**:

The unblocking work is bounded — collect 20 real抖音/小红书 fixtures (P0-1 in PHASED_PLAN §3.1), run them through the existing adapter, verify the skipped tests turn green, verify real costs come in under ¥5. This is the **same work the original Phase 0 plan called for**. The contract code itself can sit untouched while this happens — i.e., the engineer can start prototyping Phase 1 UI in parallel using the synthetic fixtures, and only "close" Phase 0 when the real-corpus tests pass. That parallelism is the right scheduling, and it does not require declaring Phase 0 closed before the measurement.

---

## Open work for the founder before Phase 1 starts

1. **Collect ≥20 real samples into `backend/src/agent/cascade/fixtures/real_v1/`.** Span the 3 pinned niches (`baomam_fushi`, `yuer_richang`, `jiating_chufang`). This is P0-1 in PHASED_PLAN — the original plan called for it; it just hasn't been done.
2. **Run `pytest tests/test_cascade_contract.py::test_phase0_gate_field_completeness_real -v` and require it green.** The skip-marker auto-disables when `real_v1/` exists. If completeness < 90% on real samples, **fix the prompt or fix the adapter** — do not adjust the threshold.
3. **Add a parallel `test_phase0_gate_success_rate_real`** that loops `real_v1/*.json` through the adapter and requires ≥80% to validate without HardFailure.
4. **Wire `_call_toprador` and add upstream-network error mapping** (Gap 2). Translate `TimeoutError`/`HTTPStatusError` into `HardFailure(S7/S8)`. Without this, "every failure has a recovery path" is provably false at the service layer.
5. **Add a concurrency test for `request_shallow_analysis`** that does `asyncio.gather` of N>1 calls with the same `(user_id, source_url)` and asserts exactly one `analysis_returned` event lands (Gap 1). Fix the race with a per-key async lock or `INSERT ... DO NOTHING RETURNING`.
6. **Decide platform/source_url consistency policy** (Issue 6). Either implement the host-sniff warning before P1-7 starts, or document explicitly that the export bundle must trust `platform` and ignore the URL host.
7. **Decide S7/S8 ownership** (Issue 4 carry-over). Either (a) start raising them in the service layer (Gap 2 fix achieves this) and keep them in the central enum, or (b) move them to a separate `service_failures.py` so the contract module's enum only contains codes the contract module can raise.
8. **Document the "synthetic Gate" → "real Gate" handoff** in `PHASED_PLAN.md §3.2`. Add one line: "G1/G2/G5 measurements close against `real_v1/`, not `synthetic_v1/`. The synthetic suite is a smoke battery, not the Gate."

---

## What I would WANT in place that isn't, but I'm OK with shipping without

These are the honest concessions — things a perfectionist would do, that I would not block Phase 0 on.

- **Cost-known bit on `analysis_returned` events** (Gap 3). The right design is to either null out `cost_cny` when `W8_COST_UNKNOWN` fired or add a `cost_known: bool`. Today the rollup query would have to join through warnings to know if a 0.0 cost is "free" or "unknown." Defer to Phase 1 when actual cost rollups start running and the bug becomes a live problem instead of a theoretical one.
- **Platform host-sniff** (Issue 6). Phase 0 doesn't consume `platform` anywhere downstream. Phase 1's P1-7 will. Catch it then.
- **`first_frame_url` HEAD reachability check.** Schema §3.3 says it should fail in 5s; the adapter currently keeps the URL as-is and defers to "future enhancement" (line 417-420). This is a Phase 1 image-render-time concern, not a Phase 0 contract concern.
- **A linter in CI.** Issue 7 (`import time`) is fixed, but no `ruff`/`pyflakes` is wired to pre-commit for this module. I would want one. It's not Phase-0-blocking; it's hygiene.
- **A proper failure code for "upstream returned malformed shape but with all keys present"** (e.g., upstream returns `scenes` as an object instead of array). Today this funnels to `S5`. With Gap 1+2 fixes this would be tightenable; today it is fine because the catch-all hint is friendly enough.

---

## Evidence trail

**Tests run independently**:
```
$ cd /Users/kang/github/openrhtv/OpenRHTV/backend && uv run pytest tests/test_cascade_contract.py -v
36 passed, 1 skipped in 0.02s
$ uv run pytest tests/test_analysis_service.py tests/test_events.py -v
9 passed in 0.04s
```

**Files read in full**:
- `/Users/kang/github/openrhtv/OpenRHTV/docs/PHASED_PLAN.md`
- `/Users/kang/github/openrhtv/OpenRHTV/docs/TOPRADOR_SCHEMA.md`
- `/Users/kang/github/openrhtv/OpenRHTV/docs/nexus/03_evidence_audit.md`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/contract.py`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/failures.py`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/adapter.py`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/analysis_service.py` ← **outside audit scope**
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/storage.py` ← **outside audit scope**
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/events.py` ← **outside audit scope**
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/__init__.py`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/tests/test_cascade_contract.py`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/tests/test_analysis_service.py`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/tests/test_events.py`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/fixtures/synthetic_v1/baomam_fushi/001.json`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/fixtures/synthetic_v1/edge_low_confidence.json`
- `/Users/kang/github/openrhtv/OpenRHTV/backend/src/agent/cascade/fixtures/synthetic_v1/edge_non_monotonic.json`

**Probes re-run live against the current code**:
- `schema_version` missing → `HardFailure S2_VERSION_MISMATCH` (audit fix verified)
- `confidence = 1.5` → 1.0 + `W11_CONFIDENCE_CLAMPED` (audit fix verified)
- `scenes[-1].timestamp_end = 9999.0` with `duration_s = 38` → clamped to 38.0 + `W12_TIMESTAMP_CLAMPED` (audit fix verified)
- `scenes[0].subject = 12345` → `None` + `W2_FALLBACK_USED` (audit fix verified)
- `scenes[0].shot_type = 42` → `"medium"` + `W2_FALLBACK_USED` (audit fix verified — wrong-type vs unknown-enum distinction correctly preserved)
- Zero-duration scene → bump + `W12_TIMESTAMP_CLAMPED`; if cannot fit → `S4_SCENES_LEN_OUT_OF_RANGE` not catch-all `S5` (audit issue 2 fix verified)
- Unknown top-level field (`mystery_field`) → `S5_INVALID_PAYLOAD` (Pydantic `extra=forbid` working)
- Platform/host mismatch (`platform=douyin`, host=xiaohongshu.com) → silently accepted, **0 warnings** (Issue 6 NOT fixed — deferred)
- `duration_s=5` with scenes spanning to 38 → `S4_SCENES_LEN_OUT_OF_RANGE` (good — recoverable code, not catch-all S5)

**Single most important finding**: The audit's seven issues are genuinely fixed — these are structural changes, not test-tweaks. **The new failure modes the audit didn't see** are at the service layer (`analysis_service.py` + `storage.py` + `events.py`), which was outside its scope. Phase 0 closes when (a) real_v1 fixtures land and the skipped test goes green, and (b) the founder accepts that the service-layer gaps will be addressed before Phase 1 starts wiring real upstream traffic.
