# Topic Intelligence integration brief

**Date**: 2026-05-20
**Reconciles**: `TOPIC_INTELLIGENCE_DEEPENING_PLAN.md` (TIP v0.2) with the existing `PHASED_PLAN.md` (Cascade Phase 0/1/2/3).
**Status**: Phase 0 type-only work landed (50/51 tests pass). Phase 1 implementation routed.

---

## 0. The reframing

TIP v0.2 expands Cascade's pitch from "AI video tool" to:

> **不是生成视频，而是决定今天拍什么、为什么拍、怎么拍、拍完如何复盘。**

Six reviewers (re-cited in TIP §14) agree this is the right reframing AND that the implementation must be incremental — contract first, ingestion second, rules third, models LAST.

This brief documents what landed today, what's routed for Phase 1, and what's explicitly deferred.

---

## 1. What landed today (2026-05-20)

### 1.1 Contract module (Phase 0 type-only)

`backend/src/agent/cascade/topic_intelligence.py` — 15 Pydantic types:

| Type | Purpose | Karpathy 5-attr enforced? |
|---|---|---|
| `ScoreSignal` | Every numeric signal in /topics | ✓ — source / confidence / fallback_used / user_visible / used_in_ranking are ALL `Field(...)` required (no defaults) |
| `RecommendationSignals` | TIP §3.1 — 5 rec-system signals | n/a (composes ScoreSignal × 5) |
| `BusinessSignals` | TIP §3.1 — 4 business signals | n/a (composes ScoreSignal × 4) |
| `PlatformPrediction` | Per-platform opportunity_score + optional ML probs | ✓ — model_version + prediction_method required |
| `AccountFit` | TIP §3.4 | ✓ via fit_score (ScoreSignal) |
| `ReplicationBlueprint` | Materials + script formula + shot plan | n/a (descriptive) |
| `ViralMechanism` | Bridges Cascade analysis → TopicBrief | ✓ — source + confidence required |
| `OfficialSignals` | TIP §1.1 抖音热点宝 / 官方热门视频 | ✓ via official_hotspot_score |
| `XhsSignals` | TIP §1.2 小红书种草信号 (6 scores) | ✓ via each score |
| `DeepTopicIntelligence` | TIP §6.1 — block on /topics card | composes all above |
| `TopicBrief` | TIP §7.3 — canvas-entry payload | composes all above |
| `PerformanceSnapshot` | TIP §5.3 — post-publish feedback | provenance via source |
| 3 enums: `SignalSource`, `TrendStage`, `PredictionMethod` | provenance + status taxonomy | required everywhere they appear |

Frontend mirror: `frontend/src/types/topic_intelligence.ts` — same shape, hand-mirrored.

Tests: `backend/tests/test_topic_intelligence.py` — 14 tests, all pass. Includes:
- `test_score_signal_requires_karpathy_five` — removing any of the 5 attrs MUST fail validation (no silent defaults)
- `test_topic_brief_composes` — end-to-end instantiation works
- `test_xhs_signals_distinct_scoring_from_douyin` — XHS does NOT define `completion_potential`; scoring is intentionally distinct per TIP §1.2

### 1.2 Cross-references

- `TOPRADOR_SCHEMA.md` now declares `topic_intelligence.py` as a sibling contract, cross-ref by `analysis_id` only
- `docs/nexus/03_routing.md` updated to declare TopicBrief as the canvas-entry contract (drives Cursor P1-4 brief content)

---

## 2. Reconciling TIP with PHASED_PLAN

The two plans use the word "Phase" with different meanings. Mapping:

| TIP phase | PHASED_PLAN phase | What it actually means |
|---|---|---|
| TIP-Phase-1 (types + mock rules + /topics card extension + TopicBrief into canvas) | partly Cascade-Phase-0 + partly Cascade-Phase-1 | Types are DONE today; mock rules + UI happen in Cascade Phase 1 W3-W5 |
| TIP-Phase-2 (video mechanism structured into DB) | Cascade-Phase-2 | After Cascade-Phase-1 Gate passes |
| TIP-Phase-3 (manual / OCR perf feedback) | Cascade-Phase-2 → 3 boundary | Manual entry begins late Cascade-Phase-2 |
| TIP-Phase-4 (LightGBM / XGBoost) | Cascade-Phase-3 (with explicit gating) | Not before 1000 samples |
| TIP-Phase-5 (multimodal Transformer) | **NOT IN ROADMAP** | Defer indefinitely |

**Bottom line**: TIP does not extend Cascade-Phase-1's 21-person-day budget. It adds *types* (small, done today) + a *reframing of P1-4's canvas-entry contract* (no extra days). Anything that would extend the Phase 1 build (XHS ingestion, Douyin 热点宝 ingestion, LightGBM training) is explicitly deferred to Cascade-Phase-2 or later.

---

## 3. What Phase 1 (Cascade) now includes (incremental, not additive)

### 3.1 P1-2 浅分析 endpoint — UNCHANGED
Already routed to Codex via `handoff/codex_backend_P1-2.md`. The new `topic_intelligence.py` types are NOT imported by P1-2. P1-2 returns `CascadeAnalysisContract` as-is.

### 3.2 P1-3 改写 prompt chain — MILD UPDATE
The chain's output now optionally constructs a `TopicBrief` (with `derived_from_analysis_id` referring to the P1-2 analysis). Mock rule-based opportunity_score is fine for Phase 1 — set `prediction_method="rule"` and `model_version="rule-v0.1"`. No ML training in Phase 1.

### 3.3 P1-4 卡片栈 UI — RECONTRACTED
The canvas now accepts a `TopicBrief` (not a topic string). Cursor brief already says this implicitly; updated `03_routing.md` makes it explicit:
- ScriptCard renders `topic_brief.viral_mechanism` as the 三段式人话
- ShotCards seed from `topic_brief.replication_blueprint.shot_plan`
- PublishPackCard adds `topic` + `target_audience` to the clipboard payload

### 3.4 P1-6 锚点 — UNCHANGED
Anchor reuse is its own contract. No TIP types referenced.

### 3.5 Phase 1 Gate metrics — APPENDED
TIP §9.1 product metrics overlap with Phase 1 Gate metrics. Reconciliation:

| TIP §9.1 metric | Cascade Phase 1 Gate (PHASED_PLAN §4.4) | Resolution |
|---|---|---|
| `topic_card_view → deep_analysis_open` ≥ 20% | not in Cascade Gate | Track via existing `analysis_returned` event but DO NOT make Gate-blocking in Phase 1 (N=10 too noisy) |
| `deep_analysis_open → enter_canvas` ≥ 15% | maps to G6 conversion rate | Already tracked |
| `enter_canvas → export` ≥ 35% | maps to G2 (5/10 finish) | Different denominator; not equivalent. Keep G2 as written. |
| `topic_reuse_7d` ≥ 30% | maps to G3 (≥ 3 return) | G3 wins — it's the harder, less manipulable metric |
| `paid_conversion` ≥ 3% | NOT in Cascade Phase 1 Gate | TIP §9.1 is for TIP-Phase-3+; deferred |

**No Gate metric changes for Cascade Phase 1.** TIP metrics are observed, not gating.

### 3.6 No new ingestion in Cascade Phase 1
- `ingest_douyin_hotspot_signals` (TIP §6.5) — NOT in Phase 1
- `ingest_xhs_trend_signals` (TIP §6.6) — NOT in Phase 1
- `log_video_performance` (TIP §6.4) — NOT in Phase 1
- `recommend_topic_directions` (TIP §6.3) — NOT in Phase 1
- `analyze_viral_mechanism` (TIP §6.2) — NOT in Phase 1 as standalone API; its OUTPUT shape (`ViralMechanism`) IS in the contract, populated from existing `CascadeAnalysisContract.viral_analysis` via a simple LLM call invoked inside P1-3

The contracts EXIST so future ingestion is unblocked. The ingestion itself is Cascade-Phase-2.

---

## 4. Stage 4 verdicts — are they invalidated?

| Verdict from Stage 4 | TIP changes it? | Notes |
|---|---|---|
| Reality Checker: CONDITIONAL PASS | NO | TIP adds types, not features. Real-fixture corpus still gates Phase 0. |
| Legal Compliance Checker: CONDITIONAL | YES — minor | New surfaces: `PerformanceSnapshot.source = OCR_SCREENSHOT` means user-uploaded backend screenshots may contain PII. Phase 1 doesn't accept these yet, but spec should declare a redaction step before TIP-Phase-3 begins ingestion. Already noted in §5 below. |
| API Tester: NEEDS SPEC PATCH (all applied) | NO | The 4 spec patches stand; TIP types use the same RecoveryAction / FailureCode / HTTP_STATUS error envelope when surfaced over HTTP. |

---

## 5. New open items added by TIP

These join the existing open items in `04_*.md` reports:

1. **Performance snapshot OCR PII** — when TIP-Phase-3 begins manual import, creator-center screenshots will contain account_id / nickname / view counts that may be sensitive. Add a redaction step to the `log_video_performance` handler before that phase starts. Owner: Codex (deferred).

2. **`prediction_method="rule"` model_version naming** — Phase 1 uses "rule-v0.1". Locking that string in code means changes need a migration. Acceptable; document in events schema.

3. **`explain[]` provenance** — currently free-form strings. Per Karpathy §14.7, should each `explain` string declare its source (rule-derived vs LLM-paraphrase)? Decision: deferred. For 10-user trial, `explain` quality is judged qualitatively; if LLM is used, set `viral_mechanism.source = LLM_INFERENCE`.

4. **Cross-platform `TopicBrief.platform` ambiguity** — a brief may apply to multiple platforms simultaneously. `DeepTopicIntelligence.prediction.platform` chooses one. For Phase 1 (Douyin-leaning 10-user trial), default to "douyin". Add a multi-platform shape only if cross-niche reuse becomes a real need post-Phase-1.

5. **The `extracted_from_analysis_id` cross-reference is not enforced.** This is a string, not a foreign key. Two interpretations possible: (a) the analysis still exists in storage and can be re-read; (b) it's a stale reference. Phase 1 spec: treat as best-effort, don't fail if missing. Document in P1-3 handoff.

---

## 6. What the founder should know

- **No new Phase 1 days were added.** Types are small. UI changes are reframings of existing P1-4 work.
- **The reframing is real.** Marketing copy and Stage 6 launch kit should reflect "选题决策系统" framing, not "AI video tool" — even though the product internally still does video generation.
- **The 5-Karpathy-attribute contract on ScoreSignal is the load-bearing decision.** It forces every future Phase-2/3 ingestion to declare provenance and ranking-use explicitly. This is what prevents the "推荐系统 demo easy, deployment hard" failure mode Karpathy §14.7 warned about.
- **Cascade-Phase-2 explicitly unlocks** the Douyin / XHS ingestion functions. Until then, treat `OfficialSignals` and `XhsSignals` as types-without-producers.

---

## 7. Test verification today

```
$ cd backend && uv run pytest tests/test_topic_intelligence.py tests/test_cascade_contract.py
50 passed, 1 skipped in 0.04s
```

The skipped test is `test_phase0_gate_field_completeness_real` — waits on hand-labeled `real_v1/` corpus, unchanged by TIP.
