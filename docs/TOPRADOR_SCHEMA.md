# Cascade · Analysis Contract (formerly TOPRADOR_SCHEMA)

**Status**: v1 (Phase 0, NEXUS-Sprint output)
**Date**: 2026-05-19 (last touched 2026-05-20 — TIP §14.7 cross-reference added)
**Replaces investigation in**: `TOPRADOR_SCHEMA_INVESTIGATION.md` (kept for historical context)
**Sibling contract**: `TOPIC_INTELLIGENCE_DEEPENING_PLAN.md` defines `TopicBrief`, `DeepTopicIntelligence`, `ViralMechanism`, `AccountFit`, `PerformanceSnapshot`. Implementation: `backend/src/agent/cascade/topic_intelligence.py`. The two contracts intentionally decouple: this one normalizes upstream video analyses; the sibling defines decision-grade topic artifacts. Cross-reference is by `analysis_id` only (no shared field types).
**Reframing**: This is the **Cascade-required contract** that any upstream analyzer (toprador, ad-hoc, or future) must produce. Karpathy review consensus: stabilize the contract first; do not let downstream code drift to match an upstream that has not been stabilized yet.

---

## 0. 关键原则

1. **Cascade defines the contract.** Upstream analyzers conform. If toprador (or any future analyzer) cannot emit a field, the adapter (P0-4) supplies a `fallback` value AND emits a `warning` — never silently.
2. **`schema_version` is mandatory.** Every `analysis_result` carries `schema_version: "1.0"`. Mismatches are explicit failures (P0-6 failure taxonomy `S2_VERSION_MISMATCH`).
3. **Required vs optional is binary.** No "sometimes required" fields. Optional fields, if absent, have an exact fallback semantic documented in §5.
4. **No silent failures.** Any field missing, malformed, or fallback-substituted is recorded in `warnings[]`. UI surfaces this (PHASED_PLAN §4.4 G7).

---

## 1. Top-level shape

```jsonc
{
  "schema_version": "1.0",                 // REQUIRED · string · semver
  "analysis_id":    "ana_01H...",          // REQUIRED · string · ULID
  "source_url":     "https://...",         // REQUIRED · string · http(s)
  "platform":       "douyin",              // REQUIRED · enum: douyin | xiaohongshu | other
  "created_at":     "2026-05-19T...",      // REQUIRED · string · RFC3339 UTC
  "model":          "doubao-seed-2-0-pro", // REQUIRED · string · provider/model identifier
  "cost_cny":       0.42,                  // REQUIRED · number · this run's cost
  "duration_s":     58,                    // REQUIRED · int · source-video duration in seconds
  "viral_analysis": { ... },               // REQUIRED · object · see §2
  "scenes":         [ ... ],               // REQUIRED · array · 3..12 entries · see §3
  "warnings":       [ ... ],               // REQUIRED · array · see §4 (may be empty)
  "confidence":     0.86                   // REQUIRED · number · 0..1 · overall analysis confidence
}
```

**Notes**:
- All timestamps RFC3339 UTC. No locale strings.
- `analysis_id` is a ULID (lexicographically sortable). Postgres-friendly.
- `cost_cny` is per-run, all-inclusive (model + storage + any second-pass).
- `confidence` is the **system's** confidence, not the user's. Below 0.5 the adapter degrades to `fallback` mode.

---

## 2. `viral_analysis` (the "why-it-hit" block)

All fields are **REQUIRED**. Strings are short Chinese explanations (≤ 80 chars each). Cascade UI surfaces these as the "为什么火" card — Brand Guardian §4 rule: **never expose field names to users**.

| 字段 | 类型 | 范围 / 形式 | Cascade 消费者 | Fallback if missing |
|---|---|---|---|---|
| `hook` | string | ≤ 80 char | 浅分析卡片 §1 "开头怎么抓人" / P1-2 | `"未识别开场钩子"` + warning |
| `pacing` | string | ≤ 80 char | 浅分析卡片 §2 "中间为什么不快进" | `"未识别节奏特征"` + warning |
| `climax` | string | ≤ 80 char | 浅分析卡片 §3 "结尾为什么忍不住点赞" | `"未识别爆点"` + warning |
| `visual_style` | string | ≤ 80 char | P1-3 改写 prompt 注入 | `"自然风格"` + warning |
| `emotional_arc` | string | ≤ 80 char | P1-3 改写 prompt 注入 | `"未识别情绪轨迹"` + warning |
| `target_audience` | string | ≤ 80 char | P1-3 改写 prompt 注入（赛道匹配） | `"未识别目标人群"` + warning |
| `engagement_levers` | string | ≤ 80 char | 内部分析（不直接展示给创作者） | `"未识别互动钩子"` + warning |
| `replicable_formula` | string | ≤ 120 char | P1-3 改写 prompt 注入（最重要） | **HARD FAIL** — without this, rewrite cannot proceed |

**HARD-FAIL** rule: if `replicable_formula` is missing or empty, the entire `analysis_result` is rejected (P0-6 `S3_NO_FORMULA`). Other missing dimensions degrade to fallback; this one cannot.

---

## 3. `scenes[]` (per-shot structure)

Length: **3..12 entries**. Outside this range → failure `S4_SCENES_LEN_OUT_OF_RANGE`.

```jsonc
{
  "scene_index":     1,                              // REQUIRED · int · 1-based
  "timestamp_start": 0.0,                            // REQUIRED · number · seconds
  "timestamp_end":   4.2,                            // REQUIRED · number · seconds (must > start)
  "scene":           "宝妈在厨房切菜板上准备食材",        // REQUIRED · string · ≤ 120 char · Cascade scene 锚点候选
  "dialogue_and_narration": "今天给宝宝做胡萝卜泥...",   // REQUIRED · string · may be empty if no audio
  "visual_content":  "暖色调俯拍，木质砧板，新鲜胡萝卜", // REQUIRED · string · ≤ 200 char · imagePrompt 注入
  "subject":         "妈妈",                          // OPTIONAL · string · character 锚点候选; fallback null
  "shot_type":       "medium",                       // OPTIONAL · enum (§3.1); fallback "medium"
  "camera_movement": "static",                       // OPTIONAL · enum (§3.2); fallback "static"
  "first_frame_url": "https://...",                  // OPTIONAL · string · http(s); fallback null
  "warnings":        []                              // REQUIRED · array · per-scene warnings (may be empty)
}
```

**Timestamp monotonicity**: `scenes[i].timestamp_start ≥ scenes[i-1].timestamp_end` for all i ≥ 1. Violations → `S5_TIMESTAMPS_NOT_MONOTONIC` (recoverable: adapter sorts + emits warning).

### 3.1 `shot_type` enum (optional)

`close_up` | `medium` | `wide` | `aerial` | `pov` | `unknown`

### 3.2 `camera_movement` enum (optional)

`static` | `push` | `pull` | `pan` | `tilt` | `tracking` | `handheld` | `unknown`

### 3.3 `first_frame_url`

- If present: must be reachable (HEAD 200) within 5s during adapter validation. Unreachable → strip + warning.
- If absent: Cascade can derive at generation time (out of scope for Phase 0).
- **24h retention rule** (per MVP_SCOPE §10): if the URL points to Cascade-owned storage, the adapter records it in a separate retention table; the URL becomes invalid after 24h but the textual fields survive.

---

## 4. `warnings[]` taxonomy

Each warning:

```jsonc
{
  "code":     "W2_FALLBACK_USED",
  "field":    "viral_analysis.pacing",
  "message":  "Pacing dimension absent in upstream output; default used.",
  "severity": "info"     // info | warn | error (error always blocks; warn surfaces in UI; info is silent log)
}
```

Codes are stable. UI maps codes → 人话 via Brand Guardian §4 term table. See P0-6 (`failures.py`) for full catalog.

---

## 5. Field-level fallback policy summary

| Field | Missing → | Wrong type → | Out of range → |
|---|---|---|---|
| `schema_version` | HARD FAIL `S2_VERSION_MISMATCH` (missing OR explicit empty) | HARD FAIL | n/a |
| `analysis_id` | adapter generates ULID + warning `W1_AUTO_ID` | HARD FAIL | n/a |
| `source_url` | HARD FAIL `S1_NO_SOURCE_URL` | HARD FAIL | n/a |
| `viral_analysis.replicable_formula` | HARD FAIL `S3_NO_FORMULA` | HARD FAIL | n/a |
| `viral_analysis.*` (other 7) | fallback string + `W2_FALLBACK_USED` | drop + warning | n/a |
| `scenes` length 0..2 | HARD FAIL `S4_SCENES_LEN_OUT_OF_RANGE` | HARD FAIL | n/a |
| `scenes` length 13+ | adapter truncates to 12 + `W3_SCENES_TRUNCATED` | HARD FAIL | n/a |
| `scenes[].scene` empty | scene generated as `"镜头{i}"` + `W4_GENERIC_SCENE_LABEL` | HARD FAIL | n/a |
| `scenes[].dialogue_and_narration` empty | OK (no warning — silent scenes are normal) | HARD FAIL | n/a |
| `scenes[].timestamp_*` non-monotonic | adapter sorts + `W5_TIMESTAMPS_SORTED` | HARD FAIL | clamp to [0, duration_s] + `W12_TIMESTAMP_CLAMPED` |
| `scenes[].timestamp_end ≤ timestamp_start` | adapter bumps end + `W12_TIMESTAMP_CLAMPED`; if still inconsistent → HARD FAIL `S4` | HARD FAIL | n/a |
| `scenes[].subject` missing | null (character anchor skipped — silent) | drop + `W2_FALLBACK_USED` | n/a |
| `scenes[].shot_type` missing/unknown-string | `"medium"` (silent — too noisy) | drop + `W2_FALLBACK_USED` | n/a |
| `scenes[].camera_movement` missing/unknown-string | `"static"` (silent) | drop + `W2_FALLBACK_USED` | n/a |
| `scenes[].first_frame_url` unreachable | strip + `W6_FIRST_FRAME_UNREACHABLE` | strip + warning | n/a |
| `confidence` missing | adapter computes from warnings: `1.0 - 0.1 × len(warnings)` capped [0, 1] + `W7_CONFIDENCE_COMPUTED` | HARD FAIL | clamp [0, 1] + `W11_CONFIDENCE_CLAMPED` |
| `cost_cny` missing | `0.0` + `W8_COST_UNKNOWN` (blocks G6 ¥<15 measurement!) | HARD FAIL | n/a if <0 → HARD FAIL `S6_NEGATIVE_COST` |

---

## 6. Consumer-by-field matrix

Which Cascade module reads which field:

| Field | P1-2 浅分析卡 | P1-3 改写 prompt | P1-4 卡片栈 UI | P1-6 锚点 | P1-7 发布包 | P1-9 成本 |
|---|---|---|---|---|---|---|
| `viral_analysis.hook` | ✓ | — | — | — | — | — |
| `viral_analysis.pacing` | ✓ | — | — | — | — | — |
| `viral_analysis.climax` | ✓ | — | — | — | — | — |
| `viral_analysis.visual_style` | — | ✓ | — | — | — | — |
| `viral_analysis.emotional_arc` | — | ✓ | — | — | — | — |
| `viral_analysis.target_audience` | — | ✓ (赛道匹配) | — | — | — | — |
| `viral_analysis.replicable_formula` | — | ✓ (load-bearing) | — | — | — | — |
| `viral_analysis.engagement_levers` | — | — (内部) | — | — | — | — |
| `scenes[].scene` | — | — | ✓ shot label | ✓ scene 锚点候选 | — | — |
| `scenes[].dialogue_and_narration` | — | ✓ | ✓ script card | — | ✓ 文案 | — |
| `scenes[].visual_content` | — | ✓ | — | — | — | — |
| `scenes[].subject` | — | — | — | ✓ character 锚点候选 | — | — |
| `scenes[].first_frame_url` | — | — | ✓ thumbnail | — | — | — |
| `cost_cny` | — | — | — | — | — | ✓ |
| `confidence` | ✓ (置信度可见) | — | ✓ low-confidence banner | — | — | — |
| `warnings[]` | ✓ (Karpathy 100% recoverability) | — | ✓ banner | — | — | — |

---

## 7. Compliance & retention

Per MVP_SCOPE §10 + healthcare/PII review notes:

- `source_url`, `first_frame_url`, `scenes[].first_frame_url`: pointer to potentially copyrighted content. Cascade stores the URL string but **does not** persist the binary content beyond 24h.
- No author UID, no author handle, no author avatar URL is required by the contract. If upstream emits these, the adapter **strips them silently** (no warning — by design).
- Cross-border source URLs (non-mainland platforms) are allowed but flagged `W9_CROSS_BORDER_SOURCE` for the founder's manual review during Phase 1.

---

## 8. Synthetic fixtures (P0-1) vs real samples

Phase 0 ships **synthetic-v1 fixtures** marked clearly (`"_provenance": "synthetic_v1"` field added to fixtures but NOT part of the production contract). These are hand-crafted to exercise:

| Fixture | What it tests |
|---|---|
| `synthetic_v1/baomam_fushi/001.json` | Happy path · 5 scenes · all fields populated · 宝妈辅食 niche |
| `synthetic_v1/yuer_richang/001.json` | 3 scenes · `subject` missing in 2 · `shot_type` mixed · 育儿日常 niche |
| `synthetic_v1/jiating_chufang/001.json` | 8 scenes · 1 empty `dialogue_and_narration` (silent scene) · 家庭厨房 niche |
| `synthetic_v1/edge_no_formula.json` | HARD FAIL — missing `replicable_formula` |
| `synthetic_v1/edge_scenes_too_short.json` | HARD FAIL — 2 scenes |
| `synthetic_v1/edge_scenes_too_long.json` | Recoverable — 14 scenes (truncated to 12) |
| `synthetic_v1/edge_non_monotonic.json` | Recoverable — timestamps unsorted |
| `synthetic_v1/edge_low_confidence.json` | Recoverable — confidence 0.32, triggers degraded UI |

**Before Phase 0 Gate closes**, these synthetic fixtures must be supplemented by **≥ 20 real hand-labeled samples** spanning the 3 pinned niches (Sprint Plan §2). The contract MUST validate cleanly against all 20 real samples without modification, OR the contract is wrong (not the samples).

---

## 9. Migration: what becomes JSONB vs columnar (future Phase 2)

For Phase 1 + SQLite-first: store entire `analysis_result` as a single `JSON` blob keyed by `analysis_id`. No columnar decomposition.

For Phase 2 + Postgres: see future migration plan. Don't decide now (YAGNI per Reviewer Synthesis).

---

## 10. Versioning policy

- `schema_version: "1.0"` is the only accepted value for Phase 1.
- Future field additions: bump to `"1.x"` (minor). Adapter must accept all `1.x` versions.
- Required-field removals or type changes: bump to `"2.0"` (major). Hard fail by adapter unless explicit `--accept-2.0` flag set.
- The string `"1.0"` is hard-coded in `contract.py` `SCHEMA_VERSION`.

---

## 11. Acceptance for Phase 0 Gate (per PHASED_PLAN §3.2)

| Criterion | Source of truth | How verified |
|---|---|---|
| 深分析成功率 ≥ 80% on 20 real samples | This contract + adapter | P0-5 contract test runs over `fixtures/real_v1/*.json` once they exist |
| 核心字段完整率 ≥ 90% on those 20 | `viral_analysis.*` + `scenes[].{scene,dialogue,visual_content}` | aggregated warnings count |
| 静默失败 = 0 | adapter emits warning OR raises — never silently drops | code-level invariant in `adapter.py` |
| Every failure has UI recovery path | `failures.py` + P1-4 banner | P1-4 manual test |
| 单条分析成本 < ¥5 | `cost_cny` per fixture | aggregated query over 20 samples |

---

## 12. Open questions explicitly deferred to post-Phase-0

- Multi-language support (English / 繁体): Phase 3+
- Whisper/ASR re-transcription if `dialogue_and_narration` is empty but `duration_s > 0`: Phase 2 if it shows up as friction
- Confidence calibration (current formula `1 - 0.1 × warnings` is heuristic): Phase 2 if any creator complains the banner is wrong
