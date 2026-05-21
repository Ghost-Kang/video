# PM · Continuous Loop Activation

**Purpose**: Enable Claude PM sessions to wake up periodically, check progress, and dispatch the next batch of work — without burning a fresh session each time.

---

## 0. How this works

The Claude harness has two relevant primitives:

| Primitive | Best for | Invocation |
|---|---|---|
| `/loop` (no interval) | Self-paced checks driven by external signals (commits, files landing) | User types `/loop` followed by the recurring prompt |
| `/schedule` (cron) | Time-of-day cadence (e.g. 09:00 + 18:00 daily) | User types `/schedule` and provides a cron expression |
| `ScheduleWakeup` (Claude-internal) | Used INSIDE a `/loop` session to set the next wake delay | Claude calls automatically |

For Cascade PM, **`/loop` is the recommended primitive** because the work cadence is driven by Codex/Cursor PRs landing — not by clock time.

---

## 1. To activate continuous PM (you do this)

Paste this into a fresh Claude session:

```
/loop

You are the Cascade Phase 1 PM, resumed from a previous session.

Your single task each iteration:
1. Read /Users/kang/github/openrhtv/OpenRHTV/docs/nexus/PM_W1_allocation.md (the spec)
2. Run bash /Users/kang/github/openrhtv/OpenRHTV/scripts/check_progress.sh --json (the sensor)
3. Compare output against allocation; decide one of:
   (a) All 9 W1 engineering tickets show done → write PM_W2_allocation.md, then ScheduleWakeup in 3600s
   (b) Some W1 tickets done, some open → leave allocation as-is, ScheduleWakeup in 1800s
   (c) Phase 0 still closed=NO → check founder log for blockers, ScheduleWakeup in 1800s
   (d) A critical-path ticket (P1-2, P1-3 chain, P1-4) blocked > 2 days → write PM_blocker_<ticket>_<date>.md, ScheduleWakeup in 3600s
4. Take exactly ONE concrete next action this iteration (no more):
   - Update PM_W1_allocation.md status column inline
   - OR write the next allocation doc
   - OR write a blocker doc
   - OR (if a Claude-owned ticket is open AND ready) build it
5. End the iteration. ScheduleWakeup with a delay matching the situation.

Hard rules:
- ONE concrete action per iteration. No batching multiple tickets in one wake.
- Read allocation docs first; don't re-derive from old conversation context.
- If you see Codex/Cursor pushed code that doesn't match the brief, write a PM_drift_<ticket>.md but do NOT rewrite their code.
- Never commit. Never push. Stage-and-write only.
- If all 9 W1 tickets done AND PM_W2_allocation.md doesn't exist, your action this turn IS writing PM_W2_allocation.md.
- The /loop ends when PM_W6_allocation.md is written and signed off (founder writes their sign-off at the bottom of 05_launch_package.md §10).
```

Then Claude takes over. You can ignore the session until something interesting fires.

---

## 2. Alternative: cron-driven check (if you prefer scheduled time)

```
/schedule

Run every day at 09:00 and 18:00 Beijing time.

Prompt: [paste the same prompt as §1 above]
```

Cron-driven is fine but wastes wake-ups on quiet days. The self-paced loop adapts.

---

## 3. What "one concrete action per iteration" looks like

| State on wake | One action | Sleep until |
|---|---|---|
| Phase 0 not closed; no founder log activity since last check | Append a "still waiting on Phase 0 closure" line to PM_W1_allocation.md | 3600s |
| Phase 0 closes; W1 D0 ready | Write `docs/nexus/founder_log/W1_kickoff_<date>.md` with the 4 W1 D0 tickets | 1200s |
| 1 of 6 open eng tickets just shipped | Update PM_W1_allocation.md `Status` column inline; identify the next blocker | 1800s |
| Founder reports blocker in `founder_log/blockers.md` | Read blocker; recommend in PM_blocker_<id>.md; flag founder | 1800s |
| Claude-owned ticket open (P1-3 prompts or P1-6 backend) AND its deps are met | Build it in this iteration | 0 (immediately re-fire) |
| All 9 done | Write PM_W2_allocation.md | 7200s (long check next time) |
| Gate-fail signal at W6 (G3 < 3) | Write PM_phase1_gate_assessment.md with decision tree from `05_launch_package.md §6.3` | 0 (urgent) |

---

## 4. What the PM session writes vs. reads

```
Reads (every iteration):
├── docs/nexus/PM_W1_allocation.md     (the plan)
├── scripts/check_progress.sh         (run; parse output)
├── docs/nexus/handoff/*.md           (the briefs Codex/Cursor are working from)
└── docs/nexus/founder_log/*.md       (manual signals from founder)

Writes (at most one per iteration):
├── docs/nexus/PM_W{N}_allocation.md  (when ready for next batch)
├── docs/nexus/PM_blocker_<id>.md     (when blocked > 2 days)
├── docs/nexus/PM_drift_<ticket>.md   (when shipped code diverges from brief)
└── docs/nexus/founder_log/PM_to_founder_<date>.md  (when founder action needed)
```

PM never modifies:
- `docs/TOPRADOR_SCHEMA.md` (contract, frozen for Phase 1)
- `backend/src/agent/cascade/contract.py` / `failures.py` / `topic_intelligence.py` (frozen)
- Shipped code from Codex/Cursor (they own their code)
- `02_*.md` strategy docs (frozen)

---

## 5. When the loop SHOULD end

`/loop` ends explicitly when ONE of:
- Founder writes their sign-off at `05_launch_package.md §10` (Phase 1 launched)
- A W6 Gate assessment doc declares PASS / FAIL / EXTEND
- Founder types `/loop stop`

Until then, the loop self-paces with `ScheduleWakeup`.

---

## 6. Current state as of 2026-05-20 (this session's last check)

```
Phase0   closed=NO  fixtures=0  tests=51  skipped=1  compliance=0  algo_filing=0  prereg=0
PM_W1    briefs=10  eng_done=3/9  P1-2=done  P1-1=open  P1-3pr=open  P1-3ch=open  P1-4=done  P1-6bk=open  P1-6sb=open  P1-7=done  P1-8=open  P1-9=open
Recruit  dms=0  calls=0  commits=0  runs=0  returns=0
Marketing seed=NO  xhs=0/10  douyin=0/5  wechat=0/1  jike=0/1
Risk     blockers=0  quotes=0  cost_top=¥?
```

**Translation for founder**:
- Codex shipped P1-2 (analysis service + events + storage). Cursor shipped P1-4 card stack + P1-7 publish-pack.
- 6 engineering tickets remain open across Claude / Codex / Cursor.
- Phase 0 closure has NOT started — fixtures still at 0, compliance items still at 0. Phase 0 work is **the gating dependency** for everything else; without it the engineering work has nothing to validate against.
- Marketing assets unpublished (kit exists but founder hasn't posted yet).

**The next PM iteration's most-likely action** would be: write `founder_log/PM_to_founder_<date>.md` saying "Phase 0 not started; if you want to ship by W6, hand-labeling needs to start tomorrow. Here's a concrete first step."

---

## 7. Concrete next-step for the founder (independent of /loop activation)

You can run this check yourself any time:

```bash
cd /Users/kang/github/openrhtv/OpenRHTV
bash scripts/check_progress.sh
```

5-line output, no opinions. If the numbers change meaningfully, /loop's next wake catches it.

If you want to start /loop now, paste §1's prompt into a fresh `claude` session. If you want to wait until Phase 0 closure is closer, that's also reasonable — the loop is most useful when there's daily change to track.
