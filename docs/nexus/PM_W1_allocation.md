# PM · Week-1 Work Allocation

**Date**: 2026-05-20
**PM**: Senior PM (Claude session in PM mode)
**Cadence**: daily check at 09:00 + 18:00 (founder timezone) via `scripts/check_progress.sh`
**Reading order**: this doc → owner-specific briefs in `handoff/` → execute

---

## 0. Allocation philosophy

Every ticket has:
- **ONE owner** (Claude session / Codex tool / Cursor tool / Founder)
- **ONE done-signal** observable by `scripts/check_progress.sh` (no opinion-based "done")
- **ONE upstream dependency** (or NONE)
- **ONE deadline expressed in elapsed-W1-days** (no calendar dates — flexible to actual W1 Day 1)

**Routing rule recap** (from `03_routing.md`):
- Claude owns contract-touching work (anything in `cascade/contract.py`, `failures.py`, `topic_intelligence.py`, or their TS mirrors) AND prompt engineering AND learning-loop events
- Codex owns backend-only work that exercises the contract (analysis service, rewrite chain, cost guard)
- Cursor owns frontend-only work (landing, card stack, anchor sidebar, publish-pack, warnings)
- Founder owns work that no tool can do (real fixtures, compliance docs, recruitment, interviews, 算法备案)

---

## 1. Phase 0 closure (must close before W1 Day 1)

| # | Owner | Ticket | Done-signal |
|---|---|---|---|
| P0-C | Founder | Hand-label ≥ 20 real `analysis_result` samples across 3 niches | `find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" \| wc -l` ≥ 20 |
| P0-T | Founder | Re-run contract tests against real_v1 | `uv run pytest tests/test_cascade_contract.py -v` shows 0 skipped |
| P0-R | Founder | 5 compliance items per `04_compliance_check.md` §"Top 5 must-do" | `docs/nexus/founder_log/compliance_done_<date>.md` exists with 5 ticks |
| P0-A | Founder | 算法备案 paperwork filed; 受理回执 number recorded | `docs/nexus/founder_log/algo_filing_<date>.md` exists |
| P0-P | Founder | Pre-registration committed + dated | `docs/nexus/founder_log/pre_registration_<date>.md` exists |

**Phase 0 closes when all 5 above tick.** Phase 1 W1 cannot start before this.

---

## 2. W1 Day 0 (kickoff — happens day Phase 0 closes)

| # | Owner | Ticket | Done-signal |
|---|---|---|---|
| W1D0-1 | Founder | Publish 小红书 seed post per `06_launch_kit.md §1` | Post URL recorded in `founder_log/W1_*.md` |
| W1D0-2 | Founder | Post 即刻 thread 段 1-3 | Post URLs recorded |
| W1D0-3 | Founder | Initial DM batch (20 creators) | DM tracker has 20 entries in `founder_log/recruitment.md` |
| W1D0-4 | Claude | Verify all P1 handoff briefs exist + are current | `ls docs/nexus/handoff/*.md \| wc -l` = 8 |

---

## 3. W1 W2 — Engineering tickets (parallel; critical path = P1-2 → P1-3 → P1-4)

### 3.1 Critical path

| Day | Ticket | Owner | Brief | Done-signal | Upstream dep |
|---|---|---|---|---|---|
| W1D1-2 | P1-2 endpoint | Codex | `handoff/codex_backend_P1-2.md` | `POST /api/analysis/shallow` returns 200 with valid contract; `tests/test_analysis_service.py` ≥ 12 cases green | Phase 0 closed |
| W1D1-2 | P1-1 landing | Cursor | `handoff/cursor_frontend_P1-1.md` | `npm run build` clean; card stack renders 3 hand-picked cards on `/` | none |
| W1D3-5 | P1-3 prompts | Claude | (this session writes) `handoff/claude_prompts_P1-3.md` | 3 prompt files in `backend/src/agent/prompts/rewrite_<niche>.md`; smoke test produces 4/5 usable scripts on 5 reference URLs per niche | P0-C real fixtures landed |
| W1D3-5 | P1-3 chain | Codex | `handoff/codex_backend_P1-3.md` | `POST /api/rewrite` returns valid `{script, shots}`; `script_rewritten` event emitted | P1-2 + P1-3 prompts |
| W1D4-7 | P1-4 card stack | Cursor | (existing) `handoff/cursor_frontend_P1-4.md` | Default route renders card stack; `?view=pro` renders canvas; 5 internal testers identify next action ≤ 5s | P1-2 endpoint live |

### 3.2 Non-critical path (parallel)

| Day | Ticket | Owner | Brief | Done-signal | Upstream dep |
|---|---|---|---|---|---|
| W1D5-7 | P1-6 anchor backend | Claude | `handoff/claude_backend_P1-6.md` | `anchors` table created; `GET/POST /api/anchors` work; `anchor_created` event fires | none |
| W1D6-8 | P1-6 anchor sidebar | Cursor | `handoff/cursor_frontend_P1-6.md` | "你之前用过的" sidebar drag→drop onto ShotCard fills `subject` + emits `anchor_reused` | P1-6 backend |
| W1D6-7 | P1-7 publish-pack | Cursor | `handoff/cursor_frontend_P1-7.md` | Click "复制" copies titles + tags + script + image URLs; emits `publish_pack_copied` | P1-4 card stack |
| W1D7-8 | P1-8 warnings | Cursor | `handoff/cursor_frontend_P1-8.md` | `confidence < 0.5` banner; warning chips per code; failure banner with 3 recovery buttons from `RECOVERY_ACTIONS` | P1-4 card stack |
| W1D5-7 | P1-9 cost guard | Codex | `handoff/codex_backend_P1-9.md` | Middleware blocks at ¥3/run + ¥30/user/day; emits `generation_cost` event | P1-2 endpoint live |

### 3.3 Sequencing summary

```
Phase 0 close ─┬─ P1-2 (Codex) ─┬─ P1-3 chain (Codex) ─── P1-4 (Cursor)
               │                ├─ P1-9 cost guard (Codex)
               │                └─ P1-7 publish-pack (Cursor)
               ├─ P1-1 landing (Cursor) [parallel]
               ├─ P1-3 prompts (Claude) [parallel; feeds P1-3 chain]
               ├─ P1-6 backend (Claude) ─── P1-6 sidebar (Cursor)
               └─ P1-8 warnings (Cursor) [parallel; needs P1-4]
```

---

## 4. W1 — Founder tickets (parallel to engineering)

| Day | Ticket | Done-signal |
|---|---|---|
| W1D1 | Publish seed post + start DM batch | seed URL + 20 DMs in tracker |
| W1D2-4 | Discovery calls #1-3 (concierge mode) | 3 `interview_logged` events with `phase=discovery` |
| W1D3-5 | Daily 小红书 post (per `06_launch_kit.md §2`) | 5 post URLs in founder_log |
| W1D5-7 | Reply 朋友圈 / DM follow-ups | 0 unread DMs by W1D7 |
| W1D6 | Publish WeChat OA article (per `06_launch_kit.md §4`) | OA post URL recorded |
| W1D7 | Record Douyin Script 1 (per `06_launch_kit.md §3.1`) | Douyin post URL recorded |
| End-of-W1 | Weekly status report (per `05_launch_package.md §8`) | `founder_log/W1_status.md` exists |

---

## 5. W2 — Engineering tickets (after W1 lands)

W2 absorbs P1 work that didn't fit W1 OR cleanup tickets from Reality Checker's 6 deferred items.

Pre-W2 evaluation (PM responsibility, runs at end of W1):
- Are all 9 W1 engineering tickets done? Hard stop on any with red done-signal.
- If yes: W2 absorbs creator-onboarding work + Reality Checker hazard #1 + hazard #2.
- If no: W2 absorbs the unfinished W1 tickets first, all others slip.

Anticipated W2 work IF W1 lands cleanly:
| Ticket | Owner | Brief |
|---|---|---|
| Concierge onboarding for creators 4-6 | Founder | (no engineering ticket) |
| `analysis_returned` event double-emit fix | Codex | (Reality Checker hazard #1) |
| S7/S8 upstream wiring | Codex | (Reality Checker hazard #2) |
| Daily 小红书 post cadence (per kit §2.5-§2.10) | Founder | (no eng ticket) |
| Bug bash from creator feedback | Codex / Cursor | (driven by `founder_log/blockers.md`) |

---

## 6. W3-W6 (placeholder)

PM re-evaluates at end of W2 based on:
- Did P1 tickets all close?
- Did creator-onboarding actually happen (4-6 onboarded by W2 end)?
- Are there any newly-discovered Phase-1 blockers?

W3-W6 work generated from W2 evaluation; no preemptive allocation.

---

## 7. Check-in cadence

PM runs `scripts/check_progress.sh` twice daily (09:00 + 18:00 founder timezone). Output is structured:

```
Phase0: closed=YES|NO  fixtures=20  tests=37/37 skipped=0  compliance=5/5  algo_filing=YES  prereg=YES
PM_W1:  briefs=8  P1-2=open|done  P1-1=open|done  P1-3prompts=open|done  P1-3chain=open|done  P1-4=open|done  P1-6back=open|done  P1-6sb=open|done  P1-7=open|done  P1-8=open|done  P1-9=open|done
Recruit: dms=20 calls=3 commits=10 runs=5 returns=3
Marketing: seed=YES posts=10/10 douyin=5/5 wechat=YES jike=YES
Risk:   blockers=N quotes_collected=N cost_p95=¥X
```

When output changes meaningfully, PM (this session or a future fired-up one) regenerates allocation for next batch.

---

## 8. Auto-progression rules

When all 9 W1 engineering tickets show `done`:
- PM writes `PM_W2_allocation.md` (next-batch allocation)
- Founder is pinged (via the founder log) — "W1 closed, W2 ready, review allocation"
- W2 tickets are added to TaskCreate queue (or to a future session via /loop / /schedule)

When ANY of P0-C / P0-T / P0-R / P0-A / P0-P is missing on a check:
- PM does NOT advance to W1
- PM writes `PM_phase0_block_<date>.md` listing the blocker
- Marketing tickets continue in parallel (they don't depend on Phase 0 closure)

When a critical-path engineering ticket (P1-2 / P1-3 / P1-4) is blocked > 2 days:
- PM writes `PM_blocker_<ticket>_<date>.md`
- Founder reviews and decides: extend Phase 1 by N days, OR cut the ticket from Gate, OR escalate

---

## 9. PM session contract

When this allocation doc and progress script are run from a future Claude session (via /loop, /schedule, or fresh invocation), the new session:
1. Reads `docs/nexus/PM_W1_allocation.md` (this file)
2. Runs `scripts/check_progress.sh` once
3. Compares output against allocation
4. If a batch is complete → writes the next allocation doc
5. If a batch is in-progress → updates this doc's "status" column inline
6. If a batch is blocked → writes the blocker doc

The session-to-session continuity is owned by these documents, not by conversation memory.
