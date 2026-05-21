# PM · Week-2 Work Allocation

**Date**: 2026-05-21
**PM**: Senior PM (Claude session in PM mode)
**Trigger**: W1 closed — `eng_done=9/9` on `scripts/check_progress.sh` 2026-05-21
**Cadence**: daily check at 09:00 + 18:00 (founder timezone) via `scripts/check_progress.sh`
**Reading order**: this doc → `PM_W1_allocation.md` §5 (W2 anticipated work) → owner-specific briefs in `handoff/` → execute

---

## 0. Allocation philosophy

Same as W1 (see `PM_W1_allocation.md §0`). One owner, one done-signal, one upstream dep, one deadline in elapsed-W2-days.

**Routing rule recap**:
- Claude owns contract-touching work, prompt iteration, learning-loop events
- Codex owns backend-only work
- Cursor owns frontend-only work
- Founder owns everything no tool can do

---

## 1. Pre-W2 evaluation (PM responsibility)

Per `PM_W1_allocation.md §5`:
- ✅ All 9 W1 engineering tickets done (`eng_done=9/9` on 2026-05-21)
- ⚠️ Phase 0 NOT closed — `fixtures=0 compliance=0 algo_filing=0 prereg=0`. Engineering shipped ahead of Phase 0. W2 cannot launch creator onboarding without P0 closure.
- ⚠️ Marketing not started — `seed=NO xhs=0/10 douyin=0/5`. W1 D0 founder tasks slipped.
- ⚠️ Recruitment not started — `dms=0 calls=0 commits=0`. Hard rule violation per `02_sprint_plan.md`: recruitment must run in parallel from W1.

**Conclusion**: W2 absorbs Phase 0 closure + W1 founder catch-up + Reality Checker hazards #1-2 + creator concierge onboarding 1-3. New engineering scope is light — heavy execution on founder side.

---

## 2. W2 — Critical path

| Day | Ticket | Owner | Brief | Done-signal | Upstream dep |
|---|---|---|---|---|---|
| W2D1 | P0-C real fixtures (≥ 20 labelled) | Founder | (no eng ticket) | `find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" \| wc -l` ≥ 20 | none |
| W2D1 | P0-T re-run contract tests against real_v1 | Founder | (no eng ticket) | `tests/test_cascade_contract.py` shows 0 skipped | P0-C |
| W2D1-2 | P0-R 5 compliance items | Founder | `04_compliance_check.md §"Top 5"` | `founder_log/compliance_done_<date>.md` with 5 ticks | none |
| W2D2-3 | P0-A 算法备案 paperwork filed | Founder | (no eng ticket) | `founder_log/algo_filing_<date>.md` + 受理回执 number | none |
| W2D1 | P0-P pre-registration committed | Founder | (no eng ticket) | `founder_log/pre_registration_<date>.md` exists | none |
| W2D2 | P1-3 founder qualitative signoff | Founder | `docs/nexus/founder_log/p1-3_qualitative_signoff_2026-05-21.md` | signoff doc has 3 ticks (one per niche) | P1-3 prompts done |

---

## 3. W2 — Engineering tickets

### 3.1 Reality Checker hazards (must close per `03_evidence_audit.md`)

| Ticket | Owner | Brief | Done-signal |
|---|---|---|---|
| P2-1 `analysis_returned` double-emit fix | Codex | `handoff/codex_backend_P2-1.md` (Founder writes from RC §1) | One `analysis_returned` row per `analysis_id` in events table after `request_shallow_analysis` retry |
| P2-2 S7/S8 upstream wiring (real Toprador call path) | Codex | `handoff/codex_backend_P2-2.md` | `CASCADE_UPSTREAM=toprador` path resolves; `S7_UPSTREAM_TIMEOUT` and `S8_UPSTREAM_REFUSED` fire correctly under simulated failures |

### 3.2 Cleanup tickets carried from W1

(None — W1 closed clean. If founder qualitative signoff requires prompt changes, file P2-3 prompt-iteration ticket then.)

### 3.3 New surface area

| Ticket | Owner | Brief | Done-signal | Upstream dep |
|---|---|---|---|---|
| P2-4 LLM-mode rewrite end-to-end | Claude | `handoff/claude_llm_P2-4.md` (TBD) | `CASCADE_REWRITE_UPSTREAM=llm` path returns valid `RewriteResult` against 3 real founder-curated URLs per niche; cost ≤ ¥3/run | P1-3 chain + cost guard |
| P2-5 anchor sidebar visual polish | Cursor | `handoff/cursor_frontend_P2-5.md` (TBD) | drag-drop UX latency < 200 ms; reuse_count visible per anchor; sort-by-recency toggle | P1-6 sidebar |
| P2-6 LLM eval harness for rewrite | Claude | `handoff/claude_eval_P2-6.md` (TBD) | Per-niche dashboard: 4/5 mechanical + 4/5 founder qualitative on 5 real-URL inputs per niche | P2-4 |

---

## 4. W2 — Founder tickets (catch-up + new)

| Day | Ticket | Done-signal |
|---|---|---|
| W2D1 | Publish 小红书 seed post (catch-up from W1 D0) | seed URL in `founder_log/seed_post_url_*.md` |
| W2D1-7 | 5 daily 小红书 posts (catch-up + new) | 5 post URLs in `founder_log/xhs_post_*.md` |
| W2D1-3 | Initial DM batch (20 creators) | 20 entries in `founder_log/recruitment.md` |
| W2D2-5 | Discovery calls #1-3 (concierge mode) | 3 `interview_logged` events with `phase=discovery` |
| W2D3 | Publish 即刻 thread 段 1-3 (catch-up) | 3 post URLs in `founder_log/jike_thread_*.md` |
| W2D4 | Publish WeChat OA article | `founder_log/wechat_oa_*.md` with URL |
| W2D5 | Record Douyin Script 1 | `founder_log/douyin_post_*.md` with URL |
| W2D6-7 | Reply 朋友圈 / DM follow-ups | 0 unread DMs end-W2 |
| End-of-W2 | Weekly status report | `founder_log/W2_status.md` exists |

---

## 5. Sequencing diagram

```
W2D1 ──┬─ P0-C real fixtures ─┬─ P0-T contract tests
       │                      │
       ├─ P0-P pre-registration
       ├─ P0-R compliance items
       ├─ P0-A algo filing (multi-day)
       ├─ Marketing catch-up (xhs seed + DMs)
       │
       └─ P1-3 founder signoff
W2D2 ──┼─ Concierge call #1
       ├─ P2-1 double-emit fix (Codex)
       │
W2D3 ──┼─ Concierge call #2
       ├─ P2-2 S7/S8 wiring (Codex)
       │
W2D4-7 ┼─ P2-4 LLM rewrite (Claude) — needs founder-curated 15 real URLs
       ├─ P2-5 sidebar polish (Cursor)
       └─ P2-6 eval harness (Claude) — depends on P2-4
```

---

## 6. W3-W6 placeholder

PM re-evaluates at end of W2 based on:
- Did P0 close? If no, this is a P0 crisis ticket — escalate to founder for cut/extend/escalate decision per `PM_W1_allocation.md §8`.
- Did real-URL LLM rewrite hit 4/5 founder qualitative bar?
- Are creators 4-6 onboarded by W2 end?

W3-W6 work generated from W2 evaluation. No preemptive allocation.

---

## 7. Check-in cadence

Same as W1: `scripts/check_progress.sh` twice daily (09:00 + 18:00 founder timezone). The `pm-check-progress` routine (id `trig_011R8YR8TLoi1SmsvWPB7zDt`) runs this automatically — see `docs/nexus/founder_log/W1_closed_2026-05-21.md` for the trigger that brought us here.

`check_progress.sh` should grow new probes for P2 tickets when the briefs land:
- `p2_1` probe for double-emit fix
- `p2_2` probe for S7/S8 wiring
- `p2_4` probe for LLM-mode rewrite

PM extends the script as briefs are written. Until then, P2 done-signals are tracked via brief presence in `handoff/`.

---

## 8. Auto-progression rules

Same as `PM_W1_allocation.md §8`:
- When all W2 engineering tickets show `done` → write `PM_W3_allocation.md`
- When P0 closure remains blocked > 2 days into W2 → write `PM_blocker_phase0_<date>.md`, escalate to founder for cut/extend/escalate decision
- When a critical-path engineering ticket (P2-1 / P2-2 / P2-4) is blocked > 2 days → write `PM_blocker_<ticket>_<date>.md`

---

## 9. Outstanding action items from W1

(Per `founder_log/W1_closed_2026-05-21.md`)

1. Sign `founder_log/p1-3_qualitative_signoff_2026-05-21.md` (3 niches)
2. Close Phase 0 — fixtures + compliance + algo filing + pre-registration
3. Kick off W1D0 founder tasks (seed post, DM batch, discovery calls) — now folded into W2 founder tickets §4 as "catch-up"
4. Decide: P2-1 / P2-2 / P2-4 / P2-5 / P2-6 brief authoring sequence (whose handoff brief gets written first this week)

---

## 10. Founder commitments locked (2026-05-21 PM review)

(Captured live; PM treats these as deadlines unless founder updates)

| Commitment | Founder answer | PM follow-up |
|---|---|---|
| P0-C real fixtures | ≥ 3 half-days this week | PM removes from W2D3 retro blocker watchlist |
| 15 real URLs for P2-4 | Posting today | PM opened `founder_log/real_urls_for_p2-4.md` skeleton; W2D2 P2-4 starts when last URL lands |
| Recruitment cadence | (A) Recovery — ≥ 5 DM/day | PM opened `founder_log/recruitment.md` log; check_progress.sh grep parses entries |
| 算法备案 (P0-A) | Committed | PM expects `founder_log/algo_filing_<date>.md` with 受理回执 by W2D3 |
| P2-1 / P2-2 brief 口述 30min | Committed | PM wrote STUB briefs in `handoff/codex_backend_P2-{1,2}.md` — §0 awaits founder fill; suggested combined 30min slot |
| 小红书 seed post | Committed | PM expects `founder_log/seed_post_url_*.md` by W2D2 |
| 5 条 compliance (P0-R) | Committed | PM expects `founder_log/compliance_done_<date>.md` by W2D3 |

**PM threshold for escalation**: if any of the above slips > 2 days past its expected day, PM writes `PM_blocker_<X>_<date>.md` per §8.

---

## 10. PM session contract

When this allocation doc is loaded by a future Claude session (via `pm-check-progress` routine, /loop, or fresh invocation), the session:
1. Reads this doc + `PM_W1_allocation.md` for context
2. Runs `scripts/check_progress.sh` once
3. Compares output against §2-§4
4. If all W2 done → writes `PM_W3_allocation.md`
5. If a batch is in-progress → updates this doc's status inline
6. If a batch is blocked → writes the blocker doc

Continuity is owned by these documents, not conversation memory.
