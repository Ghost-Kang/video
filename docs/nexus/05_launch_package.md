# Cascade · Phase 1 Launch Package

**Date**: 2026-05-20
**Owner**: Founder (you read this)
**Status**: Cascade-Phase-0 = built, CONDITIONAL PASS pending real_v1 + 5 compliance items + 2 service-layer fixes
**Replaces**: subagent-generated launch + experiment docs (both failed on credit limit; this single doc covers both scopes)

---

## 1. 一页就够的发布检查表 (Launch Checklist)

This page is the founder's runbook. Tick the boxes left-to-right; don't skip.

### Cascade-Phase-0 closure (gates Phase 1 W1 start)

- [ ] `backend/src/agent/cascade/fixtures/real_v1/*.json` — ≥ 20 hand-labeled real samples across 3 niches (≥ 6 per niche, ≥ 2 per niche of each: 30s / 30-60s / 60-180s)
- [ ] `uv run pytest tests/test_cascade_contract.py` — 37/37 pass (skipped test now runs)
- [ ] `uv run pytest tests/test_topic_intelligence.py` — 14/14 pass
- [ ] Reality Checker's 2 service-layer hazards fixed in `codex_backend_P1-2.md` brief:
  - [ ] Load-then-write race: change to SELECT-then-INSERT inside a `BEGIN IMMEDIATE` (SQLite) or `BEGIN` (Postgres) transaction; emit `analysis_returned` only on the insert branch
  - [ ] S7/S8 wiring: when `CASCADE_UPSTREAM=toprador`, the upstream-call wrapper raises `HardFailure(S7_UPSTREAM_TIMEOUT)` on httpx timeout and `HardFailure(S8_UPSTREAM_REFUSED)` on 4xx/5xx — explicit, not catch-all
- [ ] Founder + 1 helper signed off the contract is what they want before any Codex/Cursor work begins (one-pass review of `TOPRADOR_SCHEMA.md`)

### Phase 1 启动前必做 (compliance + recruitment, parallel to code work)

- [ ] 1-page 用户协议 + 隐私政策 click-through written (template in §9 below)
- [ ] PII strip list audited (3 new keys already added; founder confirms no others needed for current scope)
- [ ] `W9_CROSS_BORDER_SOURCE` hard-block toggle: env `CASCADE_REJECT_CROSS_BORDER=1` defaults on during 10-user trial; reject YouTube/TikTok/Instagram URLs entirely
- [ ] 未成年人 keyword audit: founder decides 6-10 sensitive terms (e.g. `宝宝姓名`, `学校名`, `家庭住址` patterns); add to a denylist applied to `scenes[].subject` post-adapter
- [ ] Email-based data export/deletion channel: `cascade-privacy@<your-domain>` Lambda/Mailgun mailbox; 30-day response commitment
- [ ] **算法备案 paperwork started** — file the day Phase 0 closes. 1-3 month timeline. Cannot be parallelized later.
- [ ] Founder 小红书 seed post drafted (Growth Plan §3): "看到这条 5 万赞辅食视频..." narrative + 9-image carousel
- [ ] 80 hand-curated creators identified across 3 niches (≥ 24 per niche pool to find 3-4 yes responses each)

### Cascade-Phase-1 W1 Day 1

- [ ] Founder publishes seed post on 小红书 + 视频号
- [ ] Founder DM's first 20 creators (custom 1-on-1, each cites a specific work of theirs)
- [ ] Codex starts P1-2 (analysis endpoint) against the patched `codex_backend_P1-2.md` brief
- [ ] Cursor starts P1-1 landing (card-stack hero)
- [ ] Daily founder log opens at `docs/nexus/founder_log/W1_2026-XX-XX.md` (template in §8 below)

### 每周末检查 (DoD per week — see §3 Sprint Plan for full ticket list)

- [ ] W2: Phase 0 Gate closes (real_v1 corpus + tests green)
- [ ] W3: P1-1 landing live; P1-2 endpoint live; 10 creators committed
- [ ] W4: P1-3 niche-tuned prompts producing 4/5 usable scripts; P1-4 card stack interactive
- [ ] W5: P1-6 anchors + P1-7 publish-pack + P1-8 warnings; first 3 creators have run end-to-end
- [ ] W6: Observation window for G3 return visits; founder runs interviews and Gate SQL

### Gate 评定 (the 8 Gate criteria, each with measurement source)

| # | Criterion | Target | Measurement source |
|---|---|---|---|
| G1 | Real creators try | ≥ 10 | events `run_started` distinct user_id |
| G2 | Finish first piece | ≥ 5 | events `publish_pack_copied` distinct user_id |
| G3 | Return within 7d | ≥ 3 | events: ≥ 2 `run_started` from distinct user_id with ≥ 24h gap |
| G4 | Says value in own words | ≥ 2 | events `interview_logged` with `value_sentence_matched=true` |
| G5 | Cost per run | < ¥15 | events `generation_cost` aggregated per `run_id` |
| G6 | Hot→creation conversion | ≥ 15% | `enter_canvas_from_card` ÷ `card_clicked` (events) |
| G7 | Failure→next-step | 100% | events `failure_emitted` matched 1:1 with `failure_recovered` or `run_started` within 1h |
| G8 | ≥ 2 anchor reuse | ≥ 2 | events `anchor_reused` distinct user_id |

---

## 2. 第一周作息节奏 (W1 Operating Cadence)

Hour-by-hour. Founder time cap: **≤ 10h/week**. Math: 6 days × 100min × 1 = 10h.

| Time block | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| Morning 90min | Seed post publish + monitor + reply | DM batch 1 (20 creators) | Reply yesterday's DMs + book calls | Concierge call #1 (45min + 15min notes) | Concierge call #2 | Concierge call #3 | OFF (review notes) |
| Afternoon 10min | Quick Gate SQL check | Quick Gate SQL check | Quick Gate SQL check | (rolls into morning call) | Quick Gate SQL | OFF | OFF |
| Evening | Review Codex/Cursor PRs (30min — not counted in 10h) | | | | | | |

**Total founder-active time: ~10h.** Engineering review is on top — kept short by the routing discipline.

Day-by-day discipline (daily check, ≤ 5min):
- Run `SELECT COUNT(*), event_name FROM events WHERE created_at > date('now','-1 day') GROUP BY event_name` 
- Note 1 quote from any creator interaction (verbatim, even casual)
- Track 1 number that changed (DMs sent, replies received, calls booked)

This 3-thing daily log catches what W6 review would miss.

---

## 3. 持续优化清单 (Optimization Backlog — DO NOT DO IN PHASE 1)

Ranked by leverage. Touch nothing here until Phase 1 Gate passes.

### Engineering hazards (from Reality Checker §3-4)
1. **Race in `request_shallow_analysis`** — already in Phase 0 closure checklist. If it slips past Phase 0, becomes Phase 1 bug. Severity: data-correctness.
2. **S7/S8 upstream wiring** — same. Phase 0 closure should land this.
3. **Catch-all `S5_INVALID_PAYLOAD` mapping** — API Tester §4 noted ValidationError → S5 hides specific upstream issues. Tighten by parsing `ValidationError.errors()` into specific S codes. Defer.
4. **No `JSON Schema codegen` for cascade.ts / topic_intelligence.ts mirrors** — drift caught only at runtime. Add `pydantic.json_schema()` + `git diff --exit-code` CI step. Defer.
5. **`severity=info` warnings leak through HTTP response** — API audit P6. Filter before `to_payload()`. Defer.
6. **`Platform/source_url` consistency check** — Evidence Collector audit issue #6. Latent Phase-1 bug if creators paste from wrong-platform URLs. Defer.

### TIP scope (from `03_topic_intelligence_integration.md` §5)
7. **`PerformanceSnapshot` OCR PII redaction** — Cascade-Phase-2.
8. **`explain[]` source attribution** — defer.
9. **Cross-platform `TopicBrief` ambiguity** — Cascade-Phase-2 if multi-platform need emerges.
10. **Douyin 热点宝 ingestion** — `ingest_douyin_hotspot_signals`. Cascade-Phase-2.
11. **XHS trend ingestion** — `ingest_xhs_trend_signals`. Cascade-Phase-2.
12. **Performance snapshot manual entry** — Cascade-Phase-2.

### Trend Researcher / Growth Hacker deferrals
13. **`/topics` 6 Tab** — explicitly killed by PHASED_PLAN §4.3. Stays dead.
14. **OAuth one-click publish** — Phase 3 candidate (per `PHASED_PLAN.md §6.1`).
15. **Anchor 三视图** — Phase 2 if H4 evidence demands it.
16. **TTS / BGM / ffmpeg compose** — Phase 2.
17. **`/admin` dashboard** — Phase 3 candidate.
18. **`/me/dashboard` 4 modules** — Phase 3 candidate.
19. **Stripe / 配额 / multi-tier** — Phase 2 at earliest, after Gate passes.

### Marketing deferrals
20. **Paid KOL push** — explicitly out per Growth Plan §6.
21. **Full 30-day editorial calendar** — Growth Hacker §2; Phase 2 if Gate passes.

Adding ANY item to Phase 1 requires explicit PM sign-off + corresponding cut elsewhere. The cut list ranked above protects the order: cut from §6.6 onward first; never cut #1-#5 until paid back.

---

## 4. 事故应对手册 (Incident Runbook)

For each failure mode: detection signal, first action within 1h, escalation, creator communication, standup line.

### 4.1 创作者完不成第一条 (G1 < 5 by W5 end)

- **Detection**: Wed of W5 evening: `SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='publish_pack_copied'` < 3
- **1h action**: Pick the creator with the most events but no `publish_pack_copied`. Call them within 4h. Watch them try. Take notes.
- **Escalation**: If 3 creators give the same blocker (e.g. "step X confused me"), that's a P1-x ticket — file in `docs/nexus/founder_log/blockers.md`. Engineer fix lands within 24h or it's a Gate-fail signal.
- **Creator comms**: "你不需要做完整版本 — 哪一步卡住了我想听" (lowers pressure, surfaces blocker)
- **Standup line**: "G1 in danger. {N}/{N_attempted}. Top blocker: {X}. Action: {Y} by {when}."

### 4.2 没人在一周后回来 (G3 < 3 by W6 mid)

- **Detection**: W6 Wed: `SELECT user_id, COUNT(*) FROM events WHERE event_name='run_started' GROUP BY user_id HAVING COUNT(*) ≥ 2`. If < 3, G3 in danger.
- **Cause spectrum**: (a) first piece quality too low to justify return; (b) friction on second start; (c) life simply got in the way (W6 happens to be a major holiday week — check). For (a) — H4 falsification possible. For (b) — UX gap. For (c) — extend.
- **1h action**: DM the 5 who finished but didn't return: "好奇你下一条想拍什么 — 要不要我陪你一起开始?". One offered concierge per return. If they convert, the friction is real; capture it. If they don't, H4 weakening.
- **Escalation**: If only 1-2 return AND none of them say the first piece was useful → consider H4 (anchor reuse) falsified. Stop Phase 1 extension; return to assumption sheet (PHASED_PLAN §7).
- **Creator comms**: Honest. Don't fake a launch.
- **Standup line**: "G3 at risk. {N}/3. Likely cause: {evidence}."

### 4.3 单条成本超 ¥15 (G5 fails)

- **Detection**: Daily Gate SQL: `SELECT user_id, SUM(cost_cny) FROM events WHERE event_name='generation_cost' GROUP BY user_id, run_id`. Watch median + P95.
- **1h action**: Activate cost cap (P1-9). Verify the middleware actually blocks at ¥3/run. Compute median across last 20 runs.
- **Escalation**: If median ≥ ¥10 — investigate immediately. Is the rewrite chain re-running on every change? Is the image gen being called for every Shot card refresh? Is doubao billing changed? Engineer fix within 24h or pause the trial.
- **Creator comms**: None — internal.
- **Standup line**: "G5 in danger. Median ¥{X}, P95 ¥{Y}. Cap engaged. Root cause: {Z}."

### 4.4 toprador / doubao 不可用 (upstream outage)

- **Detection**: `failure_emitted` event spike with `code IN ('S7_UPSTREAM_TIMEOUT', 'S8_UPSTREAM_REFUSED')`. Threshold: > 3 in 10 minutes.
- **1h action**: Switch `CASCADE_UPSTREAM=fixture` env var for the 10-user trial. Communicate to creators (banner): "今天系统升级，热点分析暂停 24 小时 — 你画布上的内容都安全". Resume when upstream recovers.
- **Escalation**: > 24h outage → call doubao / toprador contacts. Have a backup provider mocked but not wired (Phase 2 work).
- **Creator comms**: Banner + DM to creators in flight: "正在跑的不受影响 — 新的明天恢复".
- **Standup line**: "Upstream {X} down at {Y}. Trial switched to fixture mode. ETA {Z}."

### 4.5 创作者公开抱怨 (复盘 / 反馈 channel saturation)

- **Detection**: > 2 creators independently message about the same issue, or a creator posts publicly.
- **1h action**: Apologize first. Don't defend. Ask what they need. Offer a 1-on-1 call.
- **Escalation**: If the public post gains traction — write a transparent reply on 小红书 explaining what's a 10-user trial, what they should expect, what's broken. Don't hide behind "Beta".
- **Creator comms**: Personal. Use your own name + face. No company-speak.
- **Standup line**: "Public negative feedback from {creator}. Cause: {X}. Action: {Y}."

### 4.6 法规突袭检查 (algorithm filing not yet done; 网信办 / 工信部 contact)

- **Detection**: Inbound official communication.
- **1h action**: Do not respond from product. Pause the trial in writing to creators (1 message, polite, no detail). Engage compliance lawyer (per `04_compliance_check.md` 第14项).
- **Escalation**: Lawyer-led from this point.
- **Creator comms**: "系统暂停一段时间，你的数据都保留" — no detail, no speculation.
- **Standup line**: NO standup. Lawyer-only.

---

## 5. 10 位创作者邀请与访谈剧本

### 5.1 Outreach DM templates (3 variants by niche)

**Niche 1 — 宝妈辅食**:
> 嗨，[名字]，我刷到了你的 [具体作品标题]。我们做了一个工具帮辅食创作者把别人的爆款变成你自己的版本（不是搬运，是拆爆点 + 改写到你的人设）。 我个人手动跟 10 位辅食创作者做试用，6 周，免费。 你这周有 30 分钟跟我聊聊你目前怎么选题吗？

**Niche 2 — 育儿日常**:
> 嗨，[名字]，看了你的 [具体作品]，[一句真诚的评价 — 不是夸"你拍得真好"，而是说出一个具体细节，例如"那个夜灯转场我想了一下]。我们做了一个工具，帮育儿账号找今天最值得拍的方向 + 直接生成草稿镜头。10 个名额内测，6 周免费，要不要聊聊？

**Niche 3 — 家庭厨房**:
> 嗨，[名字]，你做的 [具体作品] 让我意外好看。我们做的工具能从一条抖音爆款拆解出"为什么火"，然后帮你改成你家厨房版本。10 人试用，6 周，免费。 你愿意花 30 分钟跟我聊吗？

DM discipline:
- Hand-written, every one. NO copy-paste.
- Cite a real work of theirs. If you haven't watched it, don't DM.
- 80 DMs total over W1-W2. Expected: ~20 reply, ~15 take a call, ~10 commit.

### 5.2 Concierge 30-min discovery call agenda

Time | What | Listening for
-----|------|---------------
0-5 | Introduce yourself (founder, what Cascade is, why you're calling personally) | Comfort signals
5-15 | Walk through their current workflow: how do they pick topics? Where do they spend most time? What's the bottleneck? | H1: do they start from hot topics? (Yes = H1 supported)
15-22 | Show 30-second product demo (the card stack on baomam_fushi/001 fixture) | Friction visible in their face
22-27 | "Would this fit your workflow? What's missing?" | H3: is the rewrite useful?
27-30 | Schedule first creation session (must happen within 7 days) | Commitment signal

Take notes verbatim. Quotes go in the founder log.

### 5.3 Day-1 hand-holding sequence

Within 7 days of the discovery call: a 60-min screen-share session where the founder watches the creator do their first run.

- Founder shares Zoom / 腾讯会议 link
- Creator opens Cascade, pastes a URL OR picks a card
- Founder STAYS QUIET unless creator gets visibly stuck for ≥ 60 seconds
- Note: where they hesitated, what they said out loud, what they tried before reading the UI
- After: ask "What was the most surprising thing about this?"

Notes log to founder's notebook AND `interview_logged` event with `phase=day1_observation`.

### 5.4 W6 exit interview (5 questions, ≤ 20 min)

1. "你这 6 周用 Cascade 做了几条? 哪一条你最满意?" (G2 verification)
2. "一句话: Cascade 对你是什么?" (G4 — the value sentence)
3. "你下一周还会用吗? 为什么?" (G3 / H4)
4. "如果今天我让你交 ¥39 一个月，你会交吗? 为什么?" (soft prepay test — Trend Researcher §8.3)
5. "我把你 6 周做的 [X 条] 视频里有 [Y 个] 复用了之前的角色/场景。这个'复用'你有感觉吗? 它帮到你了吗?" (H8 verification)

Notes → `interview_logged` event with `phase=exit`.

### 5.5 Compensation: nothing

The 10 creators get the product free. NO cash, NO equity, NO promises. They're trading their time + feedback for early access. In exchange, founder writes a case study with their name + work IF the trial goes well — published as a 小红书 long-post at month 3.

### 5.6 Interview event template

```json
{
  "event_name": "interview_logged",
  "user_id": "creator_X",
  "run_id": null,
  "payload": {
    "phase": "discovery" | "day1_observation" | "midweek_check" | "exit",
    "duration_min": 28,
    "notes_path": "founder_log/2026-XX-XX_creator_X_discovery.md",
    "key_quotes": ["...", "..."],
    "value_sentence_matched": true,
    "h1_supported": true,
    "h3_supported": null,
    "h4_supported": null,
    "h8_supported": null
  }
}
```

The `h*_supported` fields are filled by the founder, not derived. They're the qualitative signal that Phase 1 cannot do without (Reviewer Synthesis §5).

---

## 6. 实验设计 (Experiment Design with N=10)

### 6.1 假设矩阵 (H1-H8 mapped to events + falsification clauses)

| H | Hypothesis (PHASED_PLAN §7) | Operationalized via | Passes if | Directionally passes | Falsified if |
|---|---|---|---|---|---|
| H1 | Users start from hot topics, not own ideas | events `enter_canvas_from_card` ÷ `enter_canvas_from_url` | ratio ≥ 0.5 | ratio ≥ 0.3 | < 5 of 10 creators ever clicked a hot card |
| H2 | Shallow analysis (whyItHit) is useful for rewrites | interview Q + `script_rewritten.parser_warnings` low | 7/10 say "it helped me see why it worked" | 4/10 | 0/10 say it helped |
| H3 | Rewrite output is good enough to continue | `script_rewritten` → `publish_pack_copied` rate | ≥ 50% | ≥ 30% | < 20% |
| H4 | Anchor reuse is perceived + used | `anchor_reused` distinct user_id | ≥ 3 | ≥ 2 | 0 users reuse |
| H5 | Generation quality supports actual posting | self-report "I posted this on 抖音/小红书" | ≥ 3 | ≥ 1 | 0 |
| H6 | ¥39/mo viable at <¥15/run | G5 median + W6 Q4 | < ¥10 median AND ≥ 2 say "would pay" | < ¥15 median | median ≥ ¥15 OR 0 say "would pay" |
| H7 | Failure recovery prevents churn | `failure_emitted` followed by `run_started` within 24h | ≥ 80% | ≥ 50% | < 25% |
| H8 | System gets smarter with reuse | interview Q5 + anchor reuse pattern | ≥ 2 explicitly say "yes, it remembered me" | ≥ 1 | 0 |

### 6.2 Statistical honesty for N=10

| Observed | 95% Wilson CI | Interpretation |
|---|---|---|
| 5/10 | [27%, 73%] | "About half" — very wide |
| 3/10 | [11%, 60%] | "Some" — barely informative |
| 7/10 | [40%, 89%] | "Most" — directional only |

**No Gate criterion is statistically significant at N=10.** Every one is a directional signal that needs to align with qualitative evidence. The "≥ 3 return" threshold for G3 is the pre-committed level we agreed to call "directionally positive" — not a proof.

### 6.3 W6 Decision Tree

```
                    All 8 Gate criteria passed?
                              │
              ┌───────────────┼────────────────┐
              │ YES                            │ NO
              ↓                                ↓
       Interview signals also positive?   Which Hs are directional?
              │                                │
       ┌──────┼─────┐               ┌──────────┼──────────┐
       │YES        │NO              │                     │
       ↓           ↓                ↓                     ↓
   PROCEED      Iterate 4w     H1+H3+H4 all green   H1 or H4 falsified
   PHASE 2     (focus weak                                │
                signal)        ITERATE 4 weeks       STOP — return to
                                                     §7 assumption sheet
                                                     Do NOT add features
```

**Critical pre-registration**: the founder commits in writing on Day 0 to the above tree. No 5th branch invented at W6.

### 6.4 Pre-registration commitment (founder writes + dates this)

> On {DATE}, before any creator opted in, I commit:
> 
> 1. I will declare Phase 1 PASSED only if all 8 Gate criteria hit their numeric thresholds AND the interview signals confirm at least H1, H3, H4 directionally.
> 
> 2. I will NOT add features in W2-W6. Engineering capacity goes to Phase 0 closure + the routed P1-1 through P1-9 tickets only.
> 
> 3. If G3 < 3 AND no creator reports the first piece was useful, I will declare H4 weakened and consider returning to assumptions, not extending Phase 1.
> 
> 4. If costs exceed ¥15/run median, I will pause the trial until P1-9 cost guard is properly engaged.
> 
> 5. I will not count creators who are personal friends as part of the 10. Personal-friend feedback is anecdote, not data.
> 
> Signed: {founder_name}, {date}

The founder writes this physically to `docs/nexus/founder_log/pre_registration_<date>.md` before Day 1 of recruitment. Date-stamp matters.

### 6.5 Anti-self-deception checklist

Things the founder will WANT to believe at W6 — watch for them:

| What you'll tell yourself | What to do to detect the self-deception |
|---|---|
| "The 2 most engaged creators are my friends; without them G3 still passes" | Check the friend list against the engaged-creator list. If a friend is in the engaged set, recount EXCLUDING them. |
| "The 1 prepay was a sympathy purchase" | If you genuinely think this, treat G5/H6 as failed, not passed. |
| "H8 reuse showed because I told them to reuse anchors" | Review the interview logs for "told them" mentions. If > 1, the H8 signal is contaminated. |
| "The bad week was a 国庆 / 学校开学 outlier" | Calendars are visible in advance. If you planned around a holiday, that's not an outlier — it's a confounder you accepted. |
| "Quality issues are 1-off" | If 3 creators independently mention the same friction, it's not 1-off. |
| "We just need more users" | More users won't fix friction. Read §7.3 first. |
| "Pivot to MCN to find the real users" | If you couldn't make 10 个人创作者 use a product they wanted, MCN won't help. |

---

## 7. Phase 0 closure checklist (the exact gating steps)

Founder ticks each, no shortcuts.

1. [ ] `git status` clean; all Phase 0 code committed (founder runs `git add backend/src/agent/cascade frontend/src/types/cascade.ts frontend/src/types/topic_intelligence.ts docs/TOPRADOR_SCHEMA.md docs/TOPIC_INTELLIGENCE_DEEPENING_PLAN.md docs/nexus/`)
2. [ ] Hand-label corpus: `ls backend/src/agent/cascade/fixtures/real_v1/**/*.json | wc -l` ≥ 20
3. [ ] All real fixtures validate: write a one-liner `for f in backend/src/agent/cascade/fixtures/real_v1/**/*.json; do uv run python -c "import json; from agent.cascade import normalize_analysis_result as N; N(json.load(open('$f')))" || echo "FAIL: $f"; done` — zero FAIL lines
4. [ ] Tests pass: `cd backend && uv run pytest tests/test_cascade_contract.py tests/test_topic_intelligence.py -v` — 51 pass, 0 skipped (the skip turns into a pass once real_v1 exists)
5. [ ] Service-layer hazards addressed in P1-2 brief (the brief reflects the fixes, even if Codex hasn't built P1-2 yet)
6. [ ] Founder reviewed `04_*.md` (Reality Check, Compliance, API Audit) — sign-off in writing
7. [ ] 算法备案 paperwork filed (founder confirms 受理回执 number recorded somewhere — even just in your notebook)
8. [ ] Pre-registration written (§6.4 above)

When all 8 are ticked, Phase 0 closes. Then and only then, Phase 1 W1 starts.

---

## 8. Weekly status report template (founder fills 6 times)

```markdown
# Cascade Phase 1 — Week {N} Status

**Date**: 2026-XX-XX
**Founder time spent**: {X}h (cap 10h)

## What happened
- {short bullet}
- {short bullet}

## Gate metric snapshot
G1: {actual}/{target} | G2: {x}/{y} | G3: {x}/{y} | G4: {x}/{y}
G5: ¥{median} median / ¥{P95} P95 | G6: {pct}% | G7: {pct}% | G8: {x}/{y}

## One quote
"{verbatim from a creator this week}"
— {creator's first name only}, niche

## One number that surprised me
{number} {what it measures}, {why it surprised me}

## One blocker
{what's stuck, who needs to unstick it, by when}

## Decision for next week
{exactly one decision — keep current course, focus on X, or stop}
```

6 of these laid side-by-side at W6 is the trend you'll actually trust.

---

## 9. Honest open questions for the founder

Not for agents, not for the docs. These are decisions only you can make.

1. **Recruitment niche balance** — Do you actually have access to 8-10 creators in EACH of 3 niches, or does 1 niche dominate? If 宝妈辅食 makes up 7/10 of your reachable creators, that's the actual scope of Phase 1; reword the gate accordingly.

2. **算法备案 timing** — Are you willing to file paperwork the day Phase 0 closes, even though the trial might fail at Week 6? (Filing has a small cost; not filing has a large cost if you continue.)

3. **The ¥0 marketing budget** — Are you actually willing to NOT buy 小红书 投流 if the seed post flops at W2? (Growth Plan §6 says no paid; this is a real discipline test.)

4. **The "no friends" rule** — Do you personally know any 宝妈辅食/育儿/厨房 creators? If yes — are they out? (Reviewer Synthesis §3.1 implies "real users only".)

5. **Phase 1 OWNERSHIP model** — Is the 9-month story Phase 0 → 1 → 2 → 3 actually compatible with whatever funding / runway you have? If you have < 6 months of runway, you don't have time for Phase 3 even if the gates pass — and that should reframe what Phase 1's "success" looks like.

These 5 questions get answered in writing before W1 Day 1. The answers go in `docs/nexus/founder_log/open_questions_<date>.md`.

---

## 10. Sign-off

When the founder is ready to start Phase 1 W1, they write a one-paragraph sign-off at the bottom of this file:

> Phase 0 closed on {DATE}. Pre-registration filed at {PATH}. 算法备案 paperwork at {STATUS}. I'm starting Phase 1 W1 with my eyes open: G1-G8 are directional, not significant; H1-H8 are testable but only weakly powered at N=10; the launch kit is hand-built; the budget is ¥0. If the Gate fails at W6, I'll go to PHASED_PLAN §7 and not add features. — {founder_name}

This package becomes the single document the founder refers to weekly through W6.
