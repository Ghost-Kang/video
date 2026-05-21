# Cascade Phase 0 + Phase 1 · Sprint Plan (6-Week Executable)

**Date**: 2026-05-19
**Author**: Sprint Prioritizer (Stage 2)
**Inputs (Stage 1)**:
- `docs/nexus/01_phase1_requirements.md` (P1-1..P1-10 spec)
- `docs/nexus/01_ux_research.md` (card-stack UI pivot)
- `docs/nexus/01_reviewer_synthesis.md` (5 red lines + learning-loop gap)
- `docs/PHASED_PLAN.md` §3-§4 (source of truth)
**Authority**: `PHASED_PLAN.md` §4 trumps this file on any scope conflict.
**One-liner**: 30-day budget, 6 calendar weeks, 1 full-stack + founder, gated by Phase 0 contract before Phase 1 starts.

---

## 0. Decisions applied (do not re-litigate)

1. **P1-4 = vertical card stack UI** on top of existing DAG data model. DAG stays in SQLite + React Flow; the creator-facing surface is `Script card → Shot cards (3-5) → Publish card`. "Pro view" toggle exposes raw React Flow to MCN seeds. No `节点 / 锚点 / DAG` term ever reaches creators.
2. **Phase 1 niches pinned to 3**: 宝妈辅食 / 育儿日常 / 家庭厨房. P1-3 gets +2d for niche-specific prompt tuning → **5d total** (vs. PHASED_PLAN §4.2 baseline 3d). Hard rule: do not pay this +2d unless P0 passes.
3. **toprador upstream is unknown** → plan must hold under both branches. See §4 (scenarios) for the +2d delta.
4. **Learning-loop instrumentation is mandatory in Phase 1**, even if dashboards wait for Phase 3. Closes Silent Risk S3 (reviewer synthesis §5).
5. **Card-stack UI does not add work** — it changes WHAT P1-4 is, not how big. P1-4 stays at 4d.

---

## 1. Budget math (≤30 person-days, 25% buffer baked in)

### 1.1 Raw effort

| Ticket | Raw | Notes |
|---|---:|---|
| P0-1 Fixture corpus (20 videos, 13-type coverage) | 2.0 | Karpathy §3.5 + Silent Risk S1 |
| P0-2 `TOPRADOR_SCHEMA.md` | 2.0 | field × type × required × consumer × fallback |
| P0-3 `CascadeAnalysisContract` types + `schema_version` | 1.0 | TS + Pydantic, both sides |
| P0-4 `normalize_analysis_result()` adapter + validator | 2.0 | maps raw → contract |
| P0-5 Contract tests (fields, scenes, timestamps, warnings, fallback) | 2.0 | green = Phase 0 Gate ok |
| P0-6 Failure taxonomy (8 classes) + recovery paths | 1.0 | Karpathy §3.9 |
| **Phase 0 subtotal** | **10.0** | matches `PHASED_PLAN §2` (~10 person-days) |
| P1-1 Single landing (3-5 hot cards + URL field, niche autoselect) | 2.0 | UX research §3.1 variant A |
| P1-2 Shallow analysis card (3-段人话 streaming, warnings) | 2.0 | UX research §1.3 |
| P1-3 Niche rewrite prompts (3 niches × tuning) | **5.0** | 3d baseline + 2d for niche-specific tuning |
| P1-4 Card-stack canvas (script + 3-5 shot + publish), Pro view toggle | 4.0 | DAG underneath; vertical stack on top |
| P1-5 Image gen wiring (reuse Apimart + Gemini) | 1.0 | one shared character ref per run |
| P1-6 Anchor cross-run reuse (character + scene, single-image) | 3.0 | UX research §6 wording |
| P1-7 Publish-pack export (4-button block copy + image zip) | 1.0 | clipboard + S3 URL list |
| P1-8 UI warnings (missing field / fallback / confidence) | 2.0 | inline only, no modal |
| P1-9 Cost meter + per-run cap (¥10 soft / ¥15 hard) | 1.0 | middleware + UI |
| P1-10 10-creator trial + 1 interview each | 2.0 | founder + helper, non-engineering |
| **+ Learning-loop instrumentation (S3 closeout)** | **1.0** | events for second-run anchor reuse |
| **Phase 1 subtotal** | **24.0** | |
| **Grand subtotal (raw)** | **34.0** | over budget if taken literally |

### 1.2 Where the 25% buffer comes from (vs. budget)

`PHASED_PLAN §4.2` already includes 25% buffer over P1-1..P1-10 nominal (21 → 26). The 30-day cap from `PHASED_PLAN §2` is the hard ceiling.

Raw 34d - 30d cap = **4d that must absorb via parallelism and re-use of OpenRHTV scaffolding**. That parallelism is:

- P1-10 (recruitment + interviews) runs **in parallel** with W1-W6 (founder/helper, not engineer). Removes 2d from critical path.
- P1-5 (image gen wiring) is 1d but **reuses 100% of existing Apimart+Gemini integration** — already proven in OpenRHTV. Realistic delivery ≈ 0.5d.
- P1-8 warnings overlap with P1-2 card rendering (same component tree). Realistic incremental cost ≈ 1d (vs. nominal 2d).
- Learning-loop instrumentation (+1d) folds into P1-9 (same middleware pattern). Realistic incremental ≈ 0.5d.

**Adjusted critical-path engineering days = 34 - 2 (P1-10 parallel) - 0.5 (P1-5 reuse) - 1 (P1-8 overlap) - 0.5 (learning loop fold-in) = 30.0d** → fits cap, with the 25% buffer expressed as: **5 weeks engineering + 1 week buffer/interview/cut-list activation = 6 calendar weeks**.

Buffer location: **Week 6 is the buffer**. If anything slips W1-W5, Week 6 absorbs without changing scope. If nothing slips, Week 6 is for second-run anchor-reuse observation (the G3 metric needs ≥7 days from first-run-completion to second-run for ≥3 creators).

### 1.3 Person-day ledger

| Role | Phase 0 | Phase 1 | Total |
|---|---:|---:|---:|
| Full-stack engineer | 10 | 18 | 28 |
| Founder (product + interviews + ops) | 0 (helps if P0 fallback) | 2 (interviews) | 2 |
| Helper (founder's network, recruitment + scheduling) | parallel | parallel | 0 (uncounted) |
| **Total engineering + founder PM** | **10** | **20** | **30** |

**At cap. No room for new features.**

---

## 2. Dependency graph

### 2.1 Phase 0 → Phase 1 hard dependencies

```
P0-1 fixture corpus ────┬─→ P0-2 schema doc ─┬─→ P0-3 contract types ─┬─→ P0-4 adapter ─→ P0-5 tests ─┐
                        │                    │                        │                              ├─→ Phase 0 GATE
                        │                    │                        └─→ P0-6 failure taxonomy ─────┘
                        │                    │
                        │                    └─→ (consumer list informs P1-2/P1-3 prompt design)
                        │
                        └─→ (sample data feeds P1-3 niche prompt tuning)
```

| Phase 0 deliverable | Phase 1 tickets that hard-block on it |
|---|---|
| P0-1 fixtures | P1-3 (need real samples to tune niche prompts), P1-10 (referenced URLs for recruitment) |
| P0-2 schema doc | P1-2 (knows which fields to render + warn), P1-8 (warning catalog) |
| P0-3 contract types | P1-2, P1-3 (input shape), P1-4 (script node payload) |
| P0-4 adapter | P1-1 (URL → analysis flow), P1-2 (consumes adapter output) |
| P0-5 contract tests | Phase 0 Gate — Phase 1 cannot start engineering until green |
| P0-6 failure taxonomy | P1-8 (warning copy per failure class), P1-9 (cost-cap failure path), learning-loop instrumentation (failure events) |

### 2.2 Intra-Phase 1 dependencies

```
P1-1 landing ──────┐
                   ├─→ P1-2 shallow analysis ─→ P1-3 niche rewrite ─┐
recruitment (P1-10)│                                                ├─→ P1-4 card-stack canvas ─┬─→ P1-7 publish pack
parallel ──────────┘                                                │                          │
                                                                    P1-5 image gen ────────────┤
                                                                                               │
                                                  P1-6 anchor reuse ──────────────────────────┤
                                                                                               │
                                                                    P1-8 warnings (overlay) ───┤
                                                                                               │
                                                                    P1-9 cost meter (overlay) ─┘
                                                                                               │
                                                  learning-loop events (overlay) ──────────────┘
                                                                                               │
                                                                                               └─→ P1-10 interviews
                                                                                                  → Phase 1 GATE
```

### 2.3 Critical path (the only sequence that can slip the date)

`P0-1 → P0-2 → P0-3 → P0-4 → P0-5 → [GATE] → P1-1 → P1-2 → P1-3 → P1-4 → P1-7 → first creator run → P1-10 (week+1 return) → GATE`

Everything else (P0-6, P1-5, P1-6, P1-8, P1-9, learning-loop events) is **off critical path** and can slip into Week 6 buffer.

---

## 3. Recruitment timeline (parallel to engineering)

| Week | Recruitment milestone | Owner | Gate-check |
|---|---|---|---|
| W1 (Phase 0 start) | Founder posts on personal Weibo/Xiaohongshu/Twitter; targets 3 pinned niches. Drafts screener (30-40 age, female, ≥50 followers, 母婴/育儿/家庭厨房, willing 45min interview + 1w follow-up). | Founder | ≥ 15 leads contacted |
| W2 (Phase 0 end) | First 5 candidates screened + scheduled. **Lock 3-niche balance**: 4 宝妈辅食 / 3 育儿日常 / 3 家庭厨房. | Founder | ≥ 5 confirmed slots in W3-W4 |
| W3 | 5 more candidates confirmed (total 10). Build interview script from `01_ux_research.md §5.2`. | Founder | 10/10 confirmed, calendar slots booked |
| W4 | Pilot interview with 1 friendly creator (founder's network) on whatever ships from W3. **Catch UI showstoppers before opening to other 9.** | Founder | ≥ 1 pilot run feedback logged |
| W5 | 9 remaining creators run end-to-end + 45min interview each. Use `01_ux_research.md §5.2` script. Record screen + audio. | Founder + helper | ≥ 10 / 10 completed first run; ≥ 5 completed publish-pack export (G2) |
| W6 | Day-7 return check (G3): ≥ 3 creators come back and do a second run. **This is the gate-critical observation window.** | Founder | ≥ 3 / 10 return; ≥ 2 reuse a prior anchor (G8) |

**Hard rule**: Recruitment starts **Week 1** (parallel to Phase 0 schema work). If founder waits for Phase 0 to finish before recruiting, the 6-week clock breaks — by the time the product is testable in W4, candidates ghost.

---

## 4. Two scenarios (toprador works vs. fallback)

### 4.1 Scenario A — toprador upstream usable (planned path)

**Phase 0 effort = 10d as planned.** P0-1 fixture corpus = engineer pulls 20 raw `analysis_result` JSON from toprador (with the 13-type coverage from Karpathy §3.5).

| Phase | Eng days | Calendar weeks |
|---|---:|---:|
| Phase 0 | 10 | W1-W2 |
| Phase 1 | 20 | W3-W6 |
| **Total** | **30** | **6 weeks** |

### 4.2 Scenario B — toprador unavailable (fallback path)

**Phase 0 effort = 12d (+2d for hand-labeled fixtures).** Founder + helper hand-label 20 videos to mimic toprador raw output schema. P0-2 schema doc becomes a **forward-looking spec** rather than reverse-engineered.

| Phase | Eng days | Calendar weeks |
|---|---:|---:|
| Phase 0 | 10 (eng) + 2 (founder+helper, parallel) | W1-W2 (no eng delta) |
| Phase 1 | 20 | W3-W6 |
| **Total engineering** | **30** | **6 weeks** |
| **Founder/helper added** | **+2** | within W1-W2 |

**Delta**: 0 engineering days, +2 founder/helper days. **Calendar does not slip** because the +2d hand-labeling runs in parallel with P0-2..P0-6 (the engineer does not need 20 fixtures on Day 1 — only by end of W1 for P0-4 adapter testing).

**Risk in Scenario B**: hand-labeled fixtures may not reflect real toprador output drift once toprador comes online. Mitigation: P0-2 schema doc explicitly versions `schema_version: "phase0-handlabeled-v1"`; P0-3 contract is the stable surface, fixtures are swappable.

### 4.3 Decision point (founder gate, Day 3 of W1)

By **end of W1 Day 3**, founder must declare A or B. If toprador status is still "unknown" at that point, **default to B** (fallback) to protect the calendar. Switching B → A mid-stream is cheap (just replace fixtures); switching A → B mid-stream costs 3-4 days of context loss.

---

## 5. Week-by-week timeline

Each ticket follows the format: `[ID.subID] description | days | depends: X,Y | owner | accept: verifiable criterion`

### 5.1 Week 1 — Phase 0 start (contract foundations)

| Ticket | Days | Depends | Owner | Acceptance |
|---|---:|---|---|---|
| `[P0-1.1] Pull/curate 20 video fixtures with 13-type coverage matrix (口播/Vlog/图文/多人剧情/无人场景/商品种草/字幕多/字幕少/下载失败/审核失败/长视频截断/无角色/强音乐弱对白)` | 2.0 | toprador access OR fallback decision | Claude (Scenario A) / founder+helper (Scenario B) | 20 JSON files in `fixtures/`; coverage matrix CSV; ≥ 2 fixtures per critical type |
| `[P0-2.1] Field inventory: name × type × required × null_rate × consumer × fallback strategy` | 2.0 | P0-1.1 (partial OK by Day 3) | Claude | `docs/TOPRADOR_SCHEMA.md` lists every field observed in fixtures + null rates |
| `[P0-6.1] Failure taxonomy: 8 classes (network / parse / LLM timeout / LLM content policy / image gen failure / image gen NSFW false-pos / quota exceeded / contract violation) + recovery path per class` | 1.0 | none | Claude | `docs/FAILURE_TAXONOMY.md` with 8 rows × {trigger, detection, user-facing copy, retry path} |
| `[RECRUITMENT W1] Founder posts to Weibo/Xiaohongshu/Twitter; targets 15 leads in 3 pinned niches` | parallel | none | Founder | ≥ 15 leads contacted by W1 end |

**Critical path this week**: P0-1.1 → P0-2.1. P0-6.1 is parallel.

**W1 Definition of Done**:
- 20 fixtures committed to repo (path: `backend/fixtures/phase0/`)
- `TOPRADOR_SCHEMA.md` covers ≥ 90% of fields seen in fixtures
- `FAILURE_TAXONOMY.md` enumerates 8 classes
- Founder has ≥ 15 recruitment leads logged in a sheet
- Scenario A/B locked by W1 Day 3 (latest)

---

### 5.2 Week 2 — Phase 0 end (contract types + tests + GATE)

| Ticket | Days | Depends | Owner | Acceptance |
|---|---:|---|---|---|
| `[P0-3.1] Define CascadeAnalysisContract: Pydantic (backend) + TypeScript (frontend) + schema_version` | 1.0 | P0-2.1 | Codex | Types compile; `schema_version: "0.1.0"` constant exported; matches §3 of TOPRADOR_SCHEMA.md |
| `[P0-4.1] normalize_analysis_result(raw) → CascadeAnalysisContract with field-level fallback + warning emission` | 2.0 | P0-3.1 | Codex | Adapter handles all 20 fixtures; emits `warnings: [{field, reason}]` for any missing field; static type checked |
| `[P0-5.1] Contract tests: required fields, scenes count ≥ 1, timestamps monotonic, warnings emitted when expected, fallback marker present` | 2.0 | P0-4.1 | Cursor (test scaffolding) → Claude (verification) | Pytest passes on all 20 fixtures; CI green; ≥ 90% core-field completion measured; deep-analysis success rate ≥ 80% |
| `[RECRUITMENT W2] Screen first 5 candidates; confirm 3-niche balance (4/3/3); book W3-W4 slots` | parallel | W1 leads | Founder | ≥ 5 candidates confirmed with calendar invites |

**Critical path this week**: P0-3.1 → P0-4.1 → P0-5.1 → **Phase 0 GATE**.

**Phase 0 GATE check (end of W2, mandatory before Phase 1 engineering starts)**:
- [ ] Deep analysis success rate ≥ 80% on 20 fixtures (P0-5.1 output)
- [ ] Core field completion ≥ 90%
- [ ] Silent failures = 0 (every fixture either parses or emits a typed warning)
- [ ] Every failure class in P0-6 has a UI-visible recovery path defined (copy + retry button + escalation)
- [ ] Single-analysis cost < ¥5 (measured on 20 fixtures × cost ledger)
- [ ] ≥ 5 creators confirmed for W3-W4 sessions

**If GATE fails**: do NOT start Phase 1 engineering. Loop back on prompts/parser/provider. Burn down to Week 6 timeline by cutting from §6 deletion list.

**W2 Definition of Done**:
- Phase 0 GATE green (all 6 checkboxes)
- 5+ creator slots booked
- Engineer is unblocked to start P1-1 on Monday W3

---

### 5.3 Week 3 — Phase 1 start (landing + shallow analysis)

| Ticket | Days | Depends | Owner | Acceptance |
|---|---:|---|---|---|
| `[P1-1.1] Single landing page: 3 hot cards (hand-curated by founder for 3 pinned niches) + URL fallback input + niche auto-preselect on card click` | 2.0 | Phase 0 GATE | Cursor (scaffold) + Claude (logic) | Landing renders 3 cards; clicking card pre-fills niche; URL input accepts douyin/xhs links and routes to P1-2 |
| `[P1-2.1] Shallow analysis card component: 3-段人话 (开头怎么抓人 / 中间为什么不快进 / 结尾为什么忍不住点赞), streaming, no field names exposed` | 2.0 | P1-1.1, P0-3/P0-4 | Claude | Card streams 3 paragraphs from WS; backend reads `CascadeAnalysisContract` only; ≤ 30s to first byte; no `hook_strength` / `narrative_arc` strings ever appear in DOM |
| `[P1-3.1] Build niche-specific rewrite prompt for 宝妈辅食 (using P0 fixtures as in-context examples)` | 1.5 | P1-2.1, P0-1 fixtures | Claude | Produces ≥ 4/5 usable scripts on 5 reference URLs (founder spot-check) |
| `[RECRUITMENT W3] Confirm remaining 5 creators (total 10); send onboarding doc with screen-recording instructions` | parallel | W2 leads | Founder | 10/10 confirmed with W4-W5 slots |

**Critical path this week**: P1-1.1 → P1-2.1 → P1-3.1.

**W3 Definition of Done**:
- Landing renders for any logged-out visitor; 3 hot cards configurable via JSON
- Shallow analysis card visible end-to-end for at least 1 sample URL
- 宝妈辅食 niche prompt produces a believable script (≥ 4/5 founder-rated)
- 10 creators booked

---

### 5.4 Week 4 — Phase 1 mid (rewrite + card-stack canvas)

| Ticket | Days | Depends | Owner | Acceptance |
|---|---:|---|---|---|
| `[P1-3.2] Build niche-specific rewrite prompt for 育儿日常` | 1.5 | P1-3.1 | Claude | ≥ 4/5 usable scripts on 5 reference URLs |
| `[P1-3.3] Build niche-specific rewrite prompt for 家庭厨房 + shared 3-5-shot output schema` | 2.0 | P1-3.2 | Claude | ≥ 4/5 usable on 家庭厨房; output schema validates against P1-4 expected shape |
| `[P1-4.1] Card-stack canvas frontend: vertical layout (script card → 3-5 shot cards → publish card); reuse Zustand store + WS protocol; do NOT expose React Flow node/edge UI in default view` | 3.0 | P1-3.3 | Codex (Canvas.tsx refactor) + Claude (review) | Renders 5 cards in vertical stack; click-to-edit script; click-to-regen per shot; reuses existing `node_status` reviewing/confirmed states; no `节点` / `锚点` / `DAG` strings in user-facing copy |
| `[P1-4.2] "Pro view" toggle: gates React Flow exposure to MCN seed users (env flag or hidden URL param for Phase 1)` | 1.0 | P1-4.1 | Codex | Toggle hidden by default; `?proview=1` reveals full Canvas.tsx; default users never see it |
| `[RECRUITMENT W4] Pilot interview with 1 friendly creator on whatever ships this week` | parallel | W3 build | Founder | Pilot run logged; UI showstoppers caught before W5 |

**Critical path this week**: P1-3.2 → P1-3.3 → P1-4.1.

**W4 Definition of Done**:
- All 3 niche prompts produce usable scripts (≥ 4/5 each)
- Card-stack canvas renders for a real end-to-end run (URL → analysis → script → 3-5 shots → publish placeholder)
- Pro-view toggle works behind a flag
- Pilot interview completed; pilot's blockers triaged into W5 fixes vs. cut-list
- **G6 funnel instrumentation in place** (events: landing_view, card_click, analysis_view, niche_set, rewrite_view, canvas_enter, publish_copy) — required for ≥ 15% conversion measurement

---

### 5.5 Week 5 — Phase 1 end (image gen + anchors + publish + warnings + cost)

| Ticket | Days | Depends | Owner | Acceptance |
|---|---:|---|---|---|
| `[P1-5.1] Wire shot cards to existing Apimart + Gemini image gen; enforce single shared character reference image across all shots in a run` | 1.0 | P1-4.1 | Claude | Each shot card triggers gen; same character_ref image-id passed to all shots; provider default = Gemini 2.5 for Asian-face fidelity |
| `[P1-6.1] Cross-run anchor list API + frontend: GET /api/anchors?user_id=X returns character+scene anchors with thumbnails; drag-into-run UX = "用上次的妈妈和厨房？" pre-fill button` | 3.0 | P1-5.1 | Codex (API) + Claude (UI) | Second-run user sees pre-fill prompt with thumbnails; clicking confirm pulls character_ref + scene_ref into the new run; copy uses UX research §6 wording (no `anchor` / `锚点` strings) |
| `[P1-7.1] Publish-pack export: 4 separate copy buttons (标题 / 标签 / 文案 / 镜头图链接) + zip download of all images; QR for mobile download` | 1.0 | P1-4.1 | Cursor | All 4 buttons present; clipboard verified via Cypress; zip downloads; QR opens on phone |
| `[P1-8.1] UI warnings overlay: missing-field badge, fallback-data ribbon, confidence pill on analysis card; copy from P0-6 taxonomy` | 1.0 | P0-6, P1-2.1 | Cursor | Every contract warning surfaces as inline UI; no silent failure path; warnings match P0-6 class IDs |
| `[P1-9.1] Cost meter middleware: log every LLM + image-gen call with ¥, accumulate per run; soft prompt at ¥10, hard block at ¥15` | 1.0 | P1-5.1 | Claude | UI shows running ¥; ¥10 triggers toast; ¥15 disables further gen with recovery copy from P0-6 |
| `[LEARNING-LOOP.1] Emit events: first_run_anchor_created, second_run_anchor_reused, second_run_improvement_vs_first (timing + edits count)` | 0.5 | P1-6.1, P1-9.1 | Claude | 3 event types written to SQLite events table; query returns counts per user; closes Silent Risk S3 |
| `[RECRUITMENT W5] 9 remaining creators run end-to-end + 45min interview each; screen recording + audio` | parallel | W4 build | Founder + helper | ≥ 10/10 first runs (G1); ≥ 5/10 reach publish copy (G2); interview transcripts logged |

**Critical path this week**: P1-5.1 → P1-6.1. Everything else is overlay/parallel.

**W5 Definition of Done**:
- A real creator (not founder) completes a full run: URL → publish copy, end-to-end, in ≤ 30 minutes
- ≥ 10 creators have tried (G1 hit)
- ≥ 5 creators completed publish copy (G2 hit)
- Cost per run logged for all 10 (G5 measurable)
- Funnel from card_click to publish_copy ≥ 15% measurable (G6)
- Every observed failure has a UI recovery path (G7)
- Learning-loop events firing

---

### 5.6 Week 6 — Buffer + interview wrap + return-visit gate (G3, G8)

This week is **buffer week**. Two scenarios:

**Scenario W6-Happy (W1-W5 on schedule)**:

| Ticket | Days | Depends | Owner | Acceptance |
|---|---:|---|---|---|
| `[RETURN.1] Day-7 return-visit window: 10 creators get +1 reminder ping; 6-day silent gap; track second-run starts` | parallel | W5 first runs | Founder | ≥ 3/10 return without prompting (G3); ≥ 2/10 reuse a prior anchor (G8) |
| `[P1-10.1] Structured interview synthesis: 10 transcripts → friction map + verbatim "把爆款变成我的内容" quotes` | 2.0 | W5 interviews | Founder | G4 hit: ≥ 2 verbatim quotes; PHASED_PLAN §7 H1-H8 check completed |
| `[GATE.1] Phase 1 Gate scorecard against §4.4 of PHASED_PLAN (G1-G8)` | 0.5 | all above | Founder + Engineer | Scorecard written; pass/fail per indicator; if fail → loop H1-H8 |

**Scenario W6-Slip (W1-W5 has slipped, e.g., P1-4 took 6d instead of 4d)**:
- Activate cut list (§6 below) starting from top.
- Maintain G1, G2, G3 as non-negotiable; everything else can degrade.
- Final scorecard moves to W7 if needed, but engineering must still close by end-of-W6.

**W6 Definition of Done**:
- Phase 1 GATE scorecard complete (8 indicators)
- ≥ 3 second runs observed (G3)
- ≥ 2 anchor reuses observed (G8)
- ≥ 2 verbatim value statements captured (G4)
- Decision: enter Phase 2, OR loop on failed H assumption

---

## 6. Cut list — ranked by drop-first (Naval's "deletion is acceptance criterion")

If any week slips, cut from the top. Each item is paired with the P1-x ID it deletes and the user-story IDs that get re-scoped.

| Drop order | What to cut | Saves | What we lose | Why this dies first |
|---:|---|---:|---|---|
| 1 | **P1-3.3 家庭厨房 prompt** — ship Phase 1 with only 2 niches (宝妈辅食 + 育儿日常) | 2.0d | -33% niche coverage; 家庭厨房 creators get the 育儿日常 prompt as fallback | 家庭厨房 has highest overlap with 宝妈辅食 (kitchen scenes); fallback is least lossy |
| 2 | **P1-4.2 Pro-view toggle** — ship card-stack only; MCN seeds wait for Phase 2 | 1.0d | No MCN signal in Phase 1 | Phase 1 Gate is about individual creators (10 人 / 3 回访), not MCN |
| 3 | **P1-8.1 fallback ribbon + confidence pill** — keep missing-field badge, drop the other two | 0.5d | Slightly less transparency on degraded data | Missing-field badge alone covers G7 (failure → next-step); ribbon/pill are nice-to-have |
| 4 | **P1-7.1 zip download + QR** — keep clipboard copy only | 0.5d | Phone users have to re-download images one-by-one | Clipboard alone satisfies G2 (≥ 5 completed first content); zip is convenience |
| 5 | **Learning-loop event #3 (second_run_improvement_vs_first)** — keep #1 + #2 only | 0.5d | Lose ability to measure first→second-run quality delta | #1 + #2 alone close Silent Risk S3 minimum; #3 is for Phase 3 dashboards |
| 6 | **P1-1.1 niche auto-preselect** — ship plain landing with manual niche dropdown | 0.5d | Higher friction (UX research §1.4 calls this out) | If we got here, we're in deep slip and need to ship something |
| 7 | **P1-9.1 soft prompt at ¥10** — keep only hard block at ¥15 | 0.3d | Less early warning | G5 (< ¥15) only requires the hard block |
| 8 | **Reduce interviews from 10 → 7** — keep 3 per pinned niche minimum | 1.0d | Lose statistical room on G2/G3 | G1 line is ≥ 10; cutting below 10 fails Gate by definition — **this is the line, do not cross** |

**Hard floor (do not cut, ever)**:
- P1-3.1 宝妈辅食 prompt (the primary niche)
- P1-4.1 card-stack canvas (without this there is no Phase 1)
- P1-6.1 anchor reuse (Silent Risk S3 + G3 + G8 all depend on it)
- P1-5.1 image gen with shared character ref (UX research F4 showstopper)
- P0-5 contract tests (Phase 0 GATE)
- P1-10 minimum 10 creators (Phase 1 GATE definition)

---

## 7. Risk register

| Risk | Trigger | Probability | Impact | Mitigation | Owner |
|---|---|:---:|:---:|---|---|
| Phase 0 GATE fails (deep-analysis < 80%) | W2 end | M | High (no Phase 1) | Pre-budget 2d slip into W3 by deferring P1-1 start to W3 Wed; if still failing, switch provider or fallback to fixture-only Phase 1 demo | Engineer |
| Card-stack UI takes 6d instead of 4d | W4 mid | M | Med | Activate cut #1 (家庭厨房 prompt) at W4 Wed if P1-4.1 not 50% done | Engineer |
| Fewer than 10 creators recruited | W3 end | M | High (G1 fails) | Founder activates secondary channels (Discord, WeChat groups, 小红书 DM) by W3 Mon | Founder |
| Image gen quality fails on Asian faces | W5 first run | M | High (UX research F4) | Pre-validate provider in Phase 0 by running 5 母婴 fixtures through gen; switch to 即梦 if Gemini fails | Engineer |
| Day-7 return < 3 (G3 fail) | W6 | M | High (gate fail) | Not mitigatable in-sprint; if G3 fails, loop on H4 (anchor reuse perception), do not retry Phase 1 | Founder |
| Silent failures discovered in real-user runs (G7 broken) | W5 | L | High | P0-6 + P1-8.1 must be green before W5; if not, hold W5 launch by 1d | Engineer |
| toprador status flips mid-sprint | any week | L | Low | Scenario decision locked W1 Day 3; switching cost is fixtures-only (cheap) | Founder |

---

## 8. Per-week DoD summary (gate-check without me)

Founder can self-gate weekly using these:

- **W1 DoD**: 20 fixtures committed · `TOPRADOR_SCHEMA.md` covers ≥ 90% fields · `FAILURE_TAXONOMY.md` has 8 classes · ≥ 15 recruitment leads · Scenario A/B locked
- **W2 DoD**: **Phase 0 GATE green** (6 checkboxes in §5.2) · ≥ 5 creators booked · engineer cleared to start Phase 1
- **W3 DoD**: Landing live with 3 cards · shallow analysis streaming for ≥ 1 URL · 宝妈辅食 prompt produces ≥ 4/5 · 10/10 creators booked
- **W4 DoD**: All 3 niche prompts ≥ 4/5 · card-stack canvas end-to-end · pro-view toggle behind flag · pilot interview completed · funnel events emitting
- **W5 DoD**: ≥ 1 real creator completes E2E in ≤ 30min · G1 hit (≥ 10) · G2 hit (≥ 5) · cost ledger working · G7 verified (every failure has UI path) · learning-loop events firing
- **W6 DoD**: Phase 1 GATE scorecard complete · G3 ≥ 3 · G8 ≥ 2 · G4 ≥ 2 verbatim · decision logged (Phase 2 GO or H-loop)

---

## 9. Traceability matrix (every ticket → source ID)

| Ticket | P1-x / P0-x | Source doc |
|---|---|---|
| P0-1.1 | P0-1 + Silent Risk S1 | PHASED_PLAN §3.1 + reviewer synthesis §5 |
| P0-2.1 | P0-2 | PHASED_PLAN §3.1 |
| P0-3.1 | P0-3 | PHASED_PLAN §3.1 |
| P0-4.1 | P0-4 | PHASED_PLAN §3.1 |
| P0-5.1 | P0-5 | PHASED_PLAN §3.1 |
| P0-6.1 | P0-6 | PHASED_PLAN §3.1 + Karpathy §3.9 |
| P1-1.1 | P1-1 | PHASED_PLAN §4.2 + UX research §3.1 variant A |
| P1-2.1 | P1-2 | PHASED_PLAN §4.2 + UX research §1.3 |
| P1-3.1 / .2 / .3 | P1-3 | PHASED_PLAN §4.2 + decision §0 (+2d for niche tuning) |
| P1-4.1 | P1-4 | PHASED_PLAN §4.2 + UX research §4.3 (card stack pivot) |
| P1-4.2 | P1-4 | UX research §4.4 (MCN pro-view) |
| P1-5.1 | P1-5 | PHASED_PLAN §4.2 + UX research F4 (shared character ref) |
| P1-6.1 | P1-6 | PHASED_PLAN §4.2 + UX research §6 |
| P1-7.1 | P1-7 | PHASED_PLAN §4.2 + UX research §1.9 (4-button block) |
| P1-8.1 | P1-8 | PHASED_PLAN §4.2 + P0-6 taxonomy |
| P1-9.1 | P1-9 | PHASED_PLAN §4.2 |
| LEARNING-LOOP.1 | Silent Risk S3 closeout | reviewer synthesis §5 + §6 red line #5 |
| P1-10.1 | P1-10 | PHASED_PLAN §4.2 + UX research §5.2 |
| RECRUITMENT W1-W6 | P1-10 (split across weeks) | PHASED_PLAN §4.2 + UX research §5.1 |

**No new features. Every line traces to an existing P0-x / P1-x ID or a reviewer-synthesis red-line / silent risk.**

---

## 10. Critical-path summary (5 bullets)

- **Phase 0 contract is the single non-negotiable predecessor**: P0-1 → P0-2 → P0-3 → P0-4 → P0-5 → GATE. If this slips past W2 end, every downstream date moves day-for-day; no parallel path exists.
- **Inside Phase 1, only 4 tickets are critical-path**: P1-1.1 (W3 Mon-Tue) → P1-2.1 (W3 Wed-Thu) → P1-3.1/.2/.3 niche prompts (W3 Fri – W4 Wed) → P1-4.1 card-stack canvas (W4 Thu – W5 Mon). Slip any of these and Week 6 buffer absorbs at most 2d before the cut list activates.
- **Recruitment is the parallel critical path**: starts W1, must hit 10 confirmed by W3 end, must land 10 first runs in W5, must observe ≥ 3 second runs in W6. Founder-owned; engineering does not block on it, but Gate does.
- **Image gen + anchor reuse + learning-loop events are W5 overlays, not critical-path**: P1-5.1 + P1-6.1 + LEARNING-LOOP.1 all sit on top of the W4 canvas foundation. They can be parallelized across one engineer-week because each leverages existing OpenRHTV infrastructure (Apimart, SQLite anchors, event hooks).
- **Week 6 = G3 observation window + buffer**: there is no engineering scheduled in W6 by design. G3 (day-7 return) requires ≥ 7 calendar days from the W5 first runs, which can only happen if first runs land by W5 mid. If first runs slip to W5 Friday, G3 measurement window shrinks below 7 days and Gate measurement becomes invalid.

---

## 11. Final assessment: is ≤ 30 person-days achievable?

**Yes, but only under three conditions:**

1. **Phase 0 GATE actually closes by end of W2.** The raw P0-1..P0-6 sum is 10d for one engineer — feasible if toprador is available (Scenario A) or if the founder+helper hand-labeling runs truly in parallel (Scenario B). If P0-1 fixtures slip past W1 Wed, P0-4 adapter cannot start on schedule, and the whole 30-day budget breaks. The 25% buffer is at the back (W6), not the front — Phase 0 has no buffer.

2. **Recruitment runs in parallel from W1.** P1-10's 2-day nominal cost only fits the budget if the founder treats W1-W5 as ongoing recruitment work (not a W5 sprint). If recruitment is deferred to "after we have a product to show," W5 first-run target slips, W6 G3 window collapses, and the Gate becomes immeasurable regardless of engineering quality.

3. **The card-stack UI pivot does not balloon P1-4 past 4d.** The reviewer-synthesis red line #3 ("only single closed loop") and the UX research §4.3 layout are compatible only if we strictly reuse `Canvas.tsx` + Zustand store + WS protocol underneath. If P1-4.1 becomes a from-scratch frontend, it's 8d not 4d and we miss by a week. The decision in §0.1 ("keep DAG underneath, render as vertical stack on top") is load-bearing on this.

**Confidence level**: Medium-high (≈ 70%) for hitting 30 days exactly. **Medium (≈ 55%)** for hitting all 8 Phase 1 Gate indicators (G1-G8). The most likely failure mode is **G3 (≥ 3 second-run returns) or G8 (≥ 2 anchor reuses) coming in at 2 instead of 3 / 1 instead of 2**, which is a user-behavior outcome, not a sprint-execution failure — and that result is itself a useful signal (PHASED_PLAN §7 H4 falsification).

**Risk of overrun is concentrated in two places**: (a) Phase 0 GATE drift if fixtures fight the adapter, (b) P1-4 card-stack scope creep if "while we're refactoring let's also..." enters any PR. Both are pre-mitigated by the cut list in §6 and the hard rule in §0.5 (card stack changes what P1-4 IS, not adds).

---

**End of sprint plan v1.**
**File**: `/Users/kang/github/openrhtv/OpenRHTV/docs/nexus/02_sprint_plan.md`
**Next action**: Senior PM routes Stage 3 tickets to Claude / Codex / Cursor per the ownership column in §5. Founder begins W1 recruitment Monday.
