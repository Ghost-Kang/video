# PM · Week-3 Work Allocation

**Date**: 2026-05-21
**PM**: Senior PM (Claude session in PM mode)
**Trigger**: W2 closed — `w2_eng_done=5/5` on `scripts/check_progress.sh` 2026-05-21
**Cadence**: daily check at 09:00 + 18:00 (founder timezone) via `pm-check-progress` routine
**Reading order**: this doc → `PM_W2_allocation.md` → `PM_W1_allocation.md` → owner-specific briefs in `handoff/`

---

## 0. Allocation philosophy

Same as W1/W2 (see `PM_W1_allocation.md §0`). One owner, one done-signal, one upstream dep, one deadline in elapsed-W3-days.

**Routing recap** (post `03_routing.md §0.1`):
- Claude owns: contract-touching work, prompt engineering, learning-loop events, **AND all frontend**
- Codex owns: backend-only work (cleanup tickets carried from W2, new infrastructure)
- Cursor: deprecated for new tickets
- Founder owns: everything no tool can do

---

## 1. Pre-W3 evaluation

| Signal | Status | Implication |
|---|---|---|
| All W2 engineering tickets done | ✅ 5/5 | Engineering capacity available for W3 |
| Phase 0 closed | ❌ 0/5 (fixtures, compliance, algo_filing, prereg, tests) | **Crisis-level blocker**. W3 P0-block rule fires if not closed by W3D2 |
| Marketing seed started | ❌ NO | Founder action lapsed across W1 + W2; W3 absorbs again |
| Recruitment started | ❌ dms=0 | "≥ 5 DM/day" W2 commitment didn't execute; W3 retries |
| LLM judge baseline | ⚠️ skipped (no API key) | Defer until env configured |
| Founder qualitative on P2-4 fixture | ⚠️ 0 ticks on disk (verbal pass) | Adequate for W3 entry; ledger update optional |

**Conclusion**: W2 was "engineering crushes it, founder lane stalls." W3 cannot continue the same pattern — founder lane must be the primary focus or the whole sprint plan fails. Engineering scope in W3 is intentionally light to avoid widening the gap.

---

## 2. W3 — Critical path (founder-led; PM escalation if slipped)

| Day | Ticket | Owner | Done-signal | Severity |
|---|---|---|---|---|
| W3D1 | P0-P pre-registration committed | Founder | `founder_log/pre_registration_<date>.md` exists | **P0** |
| W3D1-2 | P0-C real fixtures ≥ 20 hand-labelled | Founder | `find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" \| wc -l` ≥ 20 | **P0** |
| W3D1-3 | P0-R 5 compliance items per `04_compliance_check.md §"Top 5"` | Founder | `founder_log/compliance_done_<date>.md` with 5 ticks | **P0** |
| W3D2 | P0-A 算法备案 受理回执 | Founder | `founder_log/algo_filing_<date>.md` with 受理回执 number | **P0** |
| W3D2 | P0-T re-run contract tests against real_v1 | Founder | `uv run pytest backend/tests/test_cascade_contract.py` shows 0 skipped | **P0** (blocked by P0-C) |

**Escalation rule** (per `PM_W1_allocation.md §8`): if any of P0-C/P0-T/P0-R/P0-A/P0-P is still open after **2026-05-23 18:00 Asia/Shanghai** (W3D2), PM writes `founder_log/PM_phase0_crisis_<date>.md` listing the slipped items with a forced-choice decision template (cut Phase 0 / extend Phase 1 by N days / escalate to outside reviewer).

---

## 3. W3 — Engineering tickets (intentionally light)

### 3.1 LLM-mode baseline (unblocked when API key wires)

| Ticket | Owner | Brief | Done-signal | Upstream dep |
|---|---|---|---|---|
| P3-1 LLM eval baseline | Claude | (extends `claude_eval_P2-6.md` §3) | `p2-6_baseline_<UTC>.json` exists with `mode=llm` and `judge_realism_avg > 0` (non-skipped) | `GOOGLE_API_KEY` configured by founder |
| P3-2 prompt iteration from `p1-3_qualitative_signoff` F-1-b / F-3-a regression | Claude | (TBD) | re-run `p2-6_eval.py --mode llm` shows delta_from_baseline mechanical_pass_rate ≥ 0 AND realism_avg delta ≥ 0 | P3-1 |

### 3.2 Codex backend tickets

(Added 2026-05-21 post-W3-D0 PM review per the 4-owner allocation rule —
PM must explicitly route work to all four owners every cycle.)

| Ticket | Owner | Brief | Done-signal | Upstream dep |
|---|---|---|---|---|
| P3-6 `/api/anchors/<id>/reuses` endpoint | Codex | `handoff/codex_backend_P3-6.md` | endpoint returns array of reuse rows; `test_anchor_reuses_endpoint.py` passes; unlocks frontend `days_since_last_reuse` | P1-6 backend (done) |
| P3-7 Toprador production hardening | Codex | `handoff/codex_backend_P3-7.md` (STUB) | retry policy (exponential backoff), circuit breaker, timeout metrics on `analysis_returned` events, in-memory cache layer | P2-2 (done) |
| P3-8 Reality Checker remaining hazards #3+ | Codex | `handoff/codex_backend_P3-8.md` (STUB — depends on founder triage of `03_evidence_audit.md`) | each remaining hazard either fixed with a new test OR explicitly punted to W4 with rationale | founder triage |

### 3.3 New surface area (mostly UI polish + creator onboarding tooling)

| Ticket | Owner | Brief | Done-signal | Upstream dep |
|---|---|---|---|---|
| P3-3 creator onboarding admin view | Claude (frontend) | `handoff/claude_frontend_P3-3.md` ✅ | `/admin/creators` lists creators with status (invited / registered / rewritten / published / looping); backend `/api/creators` aggregation endpoint | P1-1 landing + P0 closure for real-creator load |
| P3-4 PR template | Claude ✅ | `.github/PULL_REQUEST_TEMPLATE.md` (shipped) | template auto-applies on web PRs | none |
| P3-5 anchor reuse analytics page | Claude (frontend) | `handoff/claude_frontend_P3-5.md` ✅ | `/analytics/anchors` shows reuse_count top-N + distribution histogram + by-kind | P1-6 + P2-6 baseline (both done) |

### 3.4 Cursor — deprecated for new tickets (no W3 allocation)

Per `03_routing.md §0.1` (founder decision 2026-05-21), Cursor is deprecated for new tickets. W3 has **zero** Cursor work by design. Cursor's W1 deliverables (P1-1 / P1-4 / P1-6 sidebar / P1-7 / P1-8) remain its historical contributions; only regression-fix maintenance would route to Cursor.

If founder reverses the deprecation, W4 allocation should re-introduce Cursor with explicit ticket assignments.

### 3.5 Delays carry-forward (last cycle slip → this cycle action)

(Per the 4-owner allocation rule: name slipped commitments + propose recovery.)

| Owner | What slipped in W2 | W3 recovery |
|---|---|---|
| **Founder** | DM batch (0 / 25 target), seed post (NO), 算法备案 (not filed), discovery calls (0), 5 条 compliance (not done) | All re-listed in §2 (P0 critical path) + §4 (founder tickets). Strict W3D2 18:00 escalation gate. |
| **Founder** | P2-1 / P2-2 brief 口述 30min | Optional retrospective only — Codex shipped without 口述; existing STUB §0 in briefs remains unfilled but non-blocking. Note in §9. |
| Codex | (none — P2-1 + P2-2 closed W2) | Picks up P3-6 / P3-7 / P3-8 in §3.2 |
| Claude | (none — W2 work delivered + 3 W3 tickets already shipped: P3-3 / P3-4 / P3-5) | Continues P3-1 once API key wires; P3-2 once P3-1 closes |
| Cursor | (deprecated; n/a) | No W3 work expected |

---

## 4. W3 — Founder tickets (catch-up + creator onboarding)

| Day | Ticket | Done-signal |
|---|---|---|
| W3D1 | Publish 小红书 seed post (carry from W1D0) | seed URL in `founder_log/seed_post_url_*.md` |
| W3D1-7 | 7 daily 小红书 posts (catch-up + W3 cadence) | 7 post URLs in `founder_log/xhs_post_*.md` |
| W3D1-3 | Initial DM batch (carry from W2; 20 creators) | 20 entries in `founder_log/recruitment.md` |
| W3D2-5 | Discovery calls #1-3 (concierge mode) | 3 `interview_logged` events with `phase=discovery` |
| W3D3 | Publish 即刻 thread 段 1-3 (carry) | 3 post URLs in `founder_log/jike_thread_*.md` |
| W3D4 | Publish WeChat OA article (carry) | `founder_log/wechat_oa_*.md` with URL |
| W3D5 | Record Douyin Script 1 (carry) | `founder_log/douyin_post_*.md` with URL |
| W3D5-7 | Onboard concierge creator #1 (assuming P0 closed) | `interview_logged event with phase=onboarded` + creator's first run completed |
| End-of-W3 | Weekly status report | `founder_log/W3_status.md` exists |

---

## 5. Sequencing diagram

```
W3D1 ──┬─ P0-P pre-reg (10 min)
       ├─ P0-C real fixture standup (≥ 3 half-days)
       ├─ P0-R compliance ticks
       ├─ Marketing seed post
       └─ DM batch start
W3D2 ──┼─ P0-A algo filing submitted (受理回执)
       ├─ P0-T contract tests vs real_v1 (depends P0-C)
       ├─ Discovery call #1
       └─ [PM escalation gate] if any P0-* still open → PM_phase0_crisis log
W3D3 ──┼─ Discovery call #2
       ├─ P0 should be closed
       └─ founder configures GOOGLE_API_KEY → P3-1 unblock
W3D4-5 ┼─ P3-1 LLM baseline + P3-2 prompt iteration (Claude)
       ├─ Discovery call #3
       └─ Creator #1 onboarded (concierge)
W3D6-7 ┼─ P3-3 creator admin view (Claude frontend)
       ├─ P3-5 anchor analytics (Claude frontend)
       └─ W3 weekly status report
```

---

## 6. W4-W6 placeholder

PM re-evaluates at end of W3 based on:
- Did Phase 0 finally close? If still no, scope cut becomes unavoidable
- Did creator #1 complete a real run? Concierge model validated?
- Did LLM-mode mechanical pass rate hold or regress vs fixture baseline?

W4-W6 work generated from W3 evaluation. No preemptive allocation.

---

## 7. Check-in cadence

Unchanged from W2 (`PM_W2_allocation.md §7`):
- `pm-check-progress` routine fires daily at 北京 09:00 + 18:00, produces snapshot, writes blocker docs on §8 triggers
- `upstream-sync-watch` routine fires daily at 北京 10:00, batched PR proposals
- W3 should grow new probes for P3-1/P3-2/P3-3 once briefs land; PM extends `check_progress.sh` accordingly

`check_progress.sh` output expansion for W3 (to be added when P3-* probes ship):

```
PM_W3   active=W3  w3_eng_done=N/3  P3-1=open/done  P3-3=open/done  P3-5=open/done
```

---

## 8. Auto-progression rules (same as W1/W2)

- All W3 engineering tickets done → write `PM_W4_allocation.md`
- Phase 0 still blocked after W3D2 → write `PM_phase0_crisis_<date>.md` with founder forced-choice template
- Critical-path engineering ticket (P3-1 / P3-3 / P3-5) blocked > 2 days → write `PM_blocker_<ticket>_<date>.md`

---

## 9. Founder commitments locked at W3 entry (2026-05-21)

(Inherited from `PM_W2_allocation.md §10` that did not execute; reset for W3.)

| Commitment | Status | W3 reset |
|---|---|---|
| P0-C ≥ 3 half-days | ❌ not executed in W2 | W3D1-2 strict |
| 15 real URLs for P2-4 | ✅ delivered (v2.0 + taxonomy) | Done — used by P2-4/P2-6 |
| Recruit ≥ 5 DM/day | ❌ 0 DMs in W2 | W3D1 strict start |
| 算法备案 2h | ❌ not executed | W3D2 strict |
| P2-1/P2-2 brief 30min 口述 | (Codex shipped P2-1 + P2-2 without brief 口述; brief stubs remain unfilled) | Optional retrospective; not blocking |
| 小红书 seed post | ❌ not posted | W3D1 strict |
| 5 条 compliance (P0-R) | ❌ not executed | W3D1-2 strict |

**Failure mode**: if W3 founder lane lapses identically to W2, PM writes `PM_founder_capacity_audit_<date>.md` raising the deeper question — is founder solo bandwidth realistic for this 6-week timeline, or does the timeline itself need a major revision?

---

## 10. PM session contract

When this allocation doc loads in a future Claude session (via `pm-check-progress` routine or fresh invocation):
1. Read this doc + `PM_W2_allocation.md` + `PM_W1_allocation.md` for context
2. Run `scripts/check_progress.sh` once
3. Compare output against §2-§4
4. If all W3 done → write `PM_W4_allocation.md`
5. If P0 still open after W3D2 → write phase0 crisis log
6. If founder lane stays at 0 by W3D3 → write capacity audit log

Continuity is owned by these documents, not conversation memory.

---

## 11. Open questions for founder (decide at W3D1 morning)

1. Phase 0 — can you commit ≥ 6h on W3D1 + W3D2 combined to close all 5 P0 items?
2. Recruitment — accept the (A) recovery path from `PM_W2 §10` (≥ 5 DM/day) or downshift to (B) accept delivery delay?
3. LLM judge — can you wire `GOOGLE_API_KEY` in `.env` on W3D3, or should P3-1 slip to W4?
4. Creator onboarding — should W3D5-7 be "best-effort onboard #1" or "we accept slippage if P0 isn't done"?
5. Prompt iteration — `p1-3_qualitative_signoff` carries 10 调整诉求 mostly absorbed by P2-4 (H1-H9 + 营养 + 菜名). Do you want a P3-2 explicit pass on the remaining (F-2-c, F-2-a in-context exemplar etc.) or is the current state acceptable?
