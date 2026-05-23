# PM · Week-4 Work Allocation

**Date**: 2026-05-22 (W3D2 morning,DRAFT);**LOCKED 2026-05-23 W3D3 08:42 Asia/Shanghai** post phase0_crisis PM-proxy A+C
**PM**: Senior PM (Claude session in PM mode)
**Trigger**: W3 engineering closed early — `w3_eng_done=6/6` on `scripts/check_progress.sh` 2026-05-22; idle backend/frontend bandwidth — draft W4 ahead of W3D7 to avoid Codex+Claude 3-day idle gap
**Status**: **LOCKED** (formal start = W4D1 = 2026-05-28;phase0 decision per `PM_phase0_crisis_2026-05-22.md §5` = **A+C by PM-proxy**;founder override window 直到 W4D1 上午)
**Cadence**: daily check at 09:00 + 18:00 (founder timezone) via `pm-check-progress` routine
**Reading order**: this doc → `PM_W3_allocation.md` → `PM_phase0_crisis_2026-05-22.md` → owner-specific briefs in `handoff/`

---

## 0. Allocation philosophy

Same as W1/W2/W3 (see `PM_W1_allocation.md §0`). One owner, one done-signal, one upstream dep, one deadline in elapsed-W4-days.

**Routing recap** (post `03_routing.md §0.1`):
- Claude owns: contract-touching work, prompt engineering, learning-loop events, **AND all frontend**
- Codex owns: backend-only work (cleanup tickets carried, new infrastructure)
- Cursor: deprecated for new tickets (regression-fix only)
- Founder owns: everything no tool can do

---

## 1. Pre-W4 evaluation

| Signal | Status (snapshot 2026-05-22 W3D2 AM) | Implication |
|---|---|---|
| W3 engineering tickets done | ✅ 6/6 (Codex P3-6/7/8 + R1/R2; Claude P3-3/4/5/R3) | Engineering capacity is over-supplied vs Phase 0 closure; need to keep Codex+Claude productive without widening the founder gap |
| Phase 0 closed | ❌ 2/5(P0-P ✅ + P0-R ✅;P0-C 15/20,P0-T 1 skipped,P0-A waiting on biz license) | **`PM_phase0_crisis_2026-05-22.md` written**;Phase 1 internal trial gating on founder W3D2-D3 decision |
| Marketing seed started | ❌ NO(滚动欠债 W1+W2+W3) | W4 founder lane仍以 catch-up 为主 |
| Recruitment started | ❌ dms=0 | W4 founder lane仍以 catch-up 为主 |
| LLM judge baseline | ⚠️ skipped(no API key)+ Doubao 切换已落地(P3-R2) | W4 P4-1 可在 Doubao 模式下落地,不再等 GOOGLE_API_KEY |
| Creator concierge | ❌ 0 onboarded | W4 founder lane关键节点;依赖 Phase 0 决策 |

**Conclusion**:W4 是 "engineering keeps shipping mid-stack value + founder lane 必须接 §4 关键节奏 + Phase 0 决策落地"。**W4 engineering scope 设计为 4 票(Claude 2 + Codex 2),依旧 intentionally light,把空间留给 founder 内测启动**。

---

## 2. W4 — Critical path (founder-led; PM escalation if slipped)

| Day | Ticket | Owner | Done-signal | Severity |
|---|---|---|---|---|
| W4D0 (= W3D7 = 2026-05-27) | Founder 在 `PM_phase0_crisis_2026-05-22.md §5` 签字 | Founder | §5 写入一行决策 + ETA | **P0** |
| W4D1 | P0-C 补 5 条 real fixture(若 §5 选 A/A+C) | Founder | `find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" \| wc -l` ≥ 20 | **P0** |
| W4D1 | P0-T 重跑合约测试 | Founder + Codex 协助 | `uv run pytest tests/test_cascade_contract.py -q` 跑通 + skipped=0 | **P0**(blocked by P0-C) |
| W4D1-7 | Phase 1 内测开始(假设 A/A+C):邀请 + 引导 1 位 concierge creator | Founder | `interview_logged` event with `phase=onboarded` + creator first 真 run 完成 | **P1** |
| W4D2-5 | Discovery call #1-3 | Founder | 3 个 `interview_logged` events with `phase=discovery` | **P1** |
| W4D7 | W4 weekly status | Founder | `founder_log/W4_status.md` 存在 | P2 |

**Escalation rule**:if §5 决策 W4D1 仍空 → PM 强制按 PM 推荐(A+C)推进。若 W4D3 founder lane 仍 0 进度 → PM 写 `PM_founder_capacity_audit_<date>.md`(per `PM_W3 §9 failure mode`)。

---

## 3. W4 — Engineering tickets (intentionally light: 4 票)

### 3.1 Claude(LLM + frontend)

| Ticket | Brief | Done-signal | Upstream dep | 实际状态 |
|---|---|---|---|---|
| **P4-1 LLM judge baseline (Doubao mode)** | `handoff/claude_eval_P4-1.md` ✅(audit 已完成 `9eee6e1`)— P3-R2 切完 Doubao 后改用 `LLM_PROVIDER=doubao` 跑 `p2-6_eval.py --mode llm`,产 baseline JSON | `docs/nexus/founder_log/p2-6_baseline_<UTC>.json` 含 `mode=llm` 且 `judge_realism_avg > 0`;`mode=fixture` baseline 保留 | `ARK_API_KEY` + `DOUBAO_MODEL` 已在 `.env` | ⏳ blocked on founder env |
| **P4-2 admin events firehose 面板** | `handoff/claude_frontend_P4-2.md` ✅ | shipped `4d58628`:`/admin/events` 页 + `GET /api/events` + 7 pytest + 6 vitest | P3-3 admin layout | ✅ done |
| **P4-5 generation_cost admin 仪表盘**(W3D3 新加,补 P4-1 idle) | `handoff/claude_frontend_P4-5.md`(待写)| `/admin/cost` 显示 generation_cost events 聚合(by user / by day / cumulative),复用 `/api/events?type=generation_cost`;后端可能加 `/api/cost/aggregate` | P4-2 events 端点(done) | 📋 brief 待写 |

### 3.2 Codex(后端)

| Ticket | Brief | Done-signal | Upstream dep | 实际状态 |
|---|---|---|---|---|
| **P4-3 cascade observability counters** | `handoff/codex_backend_P4-3.md` ✅ | 4 个新 event_type(`cascade_retry/circuit_open/cache_hit/cache_miss`)+ 6 unit tests | P3-7(done) | ⚠️ **W3D3 中午 re-routed Codex → Claude 后 Claude 已 ship `19c699f`** — re-route 判断错误见 §3.6 教训 |
| **P4-4 events 表索引优化** | `handoff/codex_backend_P4-4.md` ✅ | shipped `74adbd9`:`idx_events_thread_ts` + `idx_events_type_ts` + migration + test_events_index | none | ✅ done(Codex 提前 ship,W4D0 前完工)|
| **P4-6 Toprador cache 跨进程持久化** | `handoff/codex_backend_P4-6.md` ✅(W3D3 新加)| `_TOPRADOR_CACHE` 升级 SQLite 持久化层;P4-3 emit hooks 保留;5 unit tests 覆盖 save/load/expire/重启/隔离 | P3-7 + P4-3 | 📋 Codex 待起跑 |
| **P4-7 events 表 retention 策略** | `handoff/codex_backend_P4-7.md` ✅(W3D3 新加)| `retention_sweep()` + CLI `scripts/retention_sweep.py`;3 类事件分级保留(永久/180d/90d);4 unit tests | P4-4 索引(done) | 📋 Codex 待起跑 |
| **P4-8 cost_guard 校准报告** | `handoff/codex_backend_P4-8.md` ✅(W3D3 新加)| `scripts/cost_calibration.py` 产 markdown 报告对比 PREDICT vs p50/p95/max 实际值;4 unit tests | P4-2 + generation_cost events | 📋 Codex 待起跑 |

### 3.3 Cursor — deprecated(no W4 allocation)

Per `03_routing.md §0.1`(founder decision 2026-05-21),Cursor 仍 deprecated。W4 **zero** Cursor 新票。理由与 W3 §3.4 相同:无新 frontend 票路由到 Cursor,统一由 Claude 接管前端。

只在以下情况重新启用 Cursor:
- founder 在 W4D1-7 内显式撤销 `03_routing.md §0.1` 的 deprecation
- 或 Claude 前端工时严重 over-load(W4 4 票 + frontend 维护,目前看不会出现)

### 3.4 Founder — non-engineering(§4 详列)

§4 完整列举,与本节 §3 工程线对称对位。

### 3.6 教训:Codex re-route discipline(P4-3 案例 + 4-owner rule 修正)

**2026-05-23 W3D3 中午 founder 反馈**:"Codex agent 每次很快就可以做完任务,请合理安排他们中间工作"。

**Root cause**:
- W3D3 早盘 PM 看到 P4-3 brief 在 handoff/ 就位 18h+ 无新 commit → 误判为 "Codex 不响应"
- 实际:Codex 没 "不响应",只是 brief 队列里只有这一张 + Codex 还没轮到 / 还没被 ping
- PM 一拍脑袋 re-routed Codex → Claude,Claude 接住 ship 了 `19c699f`
- 同时 Codex 此前已主动 ship 了 P4-4(`74adbd9`),证明 Codex 在监控 brief 队列

**4-owner rule 修正口径**:
1. **Codex idle 不是 "未响应",可能是 "队列没东西可挑"**。PM 应该多堆 brief 让 Codex 自己选最先做哪个。
2. **18h "未响应" 阈值无意义** — Codex 不像 Claude 在 session 里 always-on;它是 batch / poll 模式。
3. **Re-route 触发条件应该改为:工程线全空 + Codex 队列 ≥ 3 brief 没动 + 某 brief 标 critical-path**。任一不满足都不应跨 lane 抢票。
4. **PM 应该提前堆 brief**,Phase 1 整个生命周期保持 Codex 队列 ≥ 2 brief 不空。这次 W3D3 补 P4-6/P4-7/P4-8 三张就是这个口径的执行。

**Compensation for this re-route**:
- P4-3 已 ship by Claude(`19c699f`),不撤回(撤回成本 > 收益)
- W3D3 当下 Codex 队列从 0(P4-4 ship 后)恢复到 3 张(P4-6/P4-7/P4-8),保持 Codex idle 时不发生
- 后续若 Claude 也想接其中一张,需 PM 显式 re-route + 在此 §3.6 加记录

### 3.5 Delays carry-forward(W3 slip → W4 action)

| Owner | What slipped in W3 | W4 recovery |
|---|---|---|
| **Founder** | DM batch(0 / 35 target,W2+W3 累计),seed post,算法备案,discovery calls(0),P0-A 受理回执,**phase0 §5 决策签字过 14h 仍空** → PM 代签 A+C 2026-05-23 W3D3 | **capacity audit 已写**(`founder_log/PM_founder_capacity_audit_2026-05-22.md`);全部进入 §4 + §2 critical path;若 W4D3 founder lane 仍 0 → 升级到 founder_capacity_audit §"escalation paths" |
| Codex | (none — 5 张 P3 票全 done) | **P4-4 已提前 ship** `74adbd9`;P4-3 误 re-route 给 Claude(已 ship `19c699f`,见 §3.6 教训);**W3D3 新堆 P4-6 / P4-7 / P4-8 三张 brief 保持队列不空** |
| Claude | (none — 4 张 P3 票全 done + 协助文档 + 协议起草) | **P4-2 已 ship** `4d58628` + **P4-1 audit 已 done** `9eee6e1`;**P4-5 cost 仪表盘** 新加补位(W4D1-2 起跑);P4-1 baseline 等 founder env |
| Cursor | (deprecated;n/a) | 0 expected |

---

## 4. W4 — Founder tickets (内测启动 + 残债)

| Day | Ticket | Done-signal |
|---|---|---|
| W4D0 | `PM_phase0_crisis_2026-05-22.md §5` 决策签字 | §5 写入一行 |
| W4D1 | 配 `ARK_API_KEY` + `DOUBAO_MODEL` 到 `.env`(解锁 P4-1) | Claude 跑 `p2-6_eval.py --mode llm` 不再因 key 退出 |
| W4D1 | 小红书 seed post(carry from W1 D0,4 周欠债) | URL 写入 `founder_log/seed_post_url_2026-05-22.md` |
| W4D1-3 | P0-C 补 5 条 real fixture(若 A/A+C);或委外标注(C 部分) | fixtures=20 |
| W4D1-7 | DM ≥ 5/天 × 7 天 ≥ 35 条 | `founder_log/recruitment.md` ≥ 35 行 |
| W4D2-5 | Discovery calls #1-3 | 3 个 `interview_logged` events with `phase=discovery` |
| W4D3-7 | Concierge creator #1 onboard 真 run 完成 | `interview_logged event with phase=onboarded` + 1 个 `run_completed` event |
| W4D2-5 | 即刻 thread / WeChat OA / Douyin script catch-up(W3 滚动欠债) | 各 founder_log 文件存 URL |
| W4D7 | W4 weekly status report | `founder_log/W4_status.md` 存在 |

---

## 5. Sequencing diagram

```
W4D0  ──┬─ founder 决策 phase0_crisis §5
        └─ Phase 1 内测正式 GA(若 A/A+C)
W4D1  ──┬─ founder 写 ARK_API_KEY → P4-1 unblock
        ├─ Codex P4-3 + P4-4 起跑
        ├─ Claude P4-1 起跑(blocked on key)+ P4-2 起跑(no dep)
        ├─ founder 小红书 seed post
        ├─ founder DM batch start
        └─ founder P0-C 补 5 条
W4D2-3──┼─ P4-2 admin events 面板 ship
        ├─ P4-3 counters events 写入
        ├─ founder Discovery call #1
        └─ P0-T 重跑(blocked on P0-C close)
W4D4-5──┼─ P4-4 索引 ship + EXPLAIN 验证
        ├─ P4-1 LLM baseline 完整 baseline JSON
        ├─ Discovery call #2-3
        └─ Concierge creator #1 onboard
W4D6-7──┼─ P4-2 / P4-3 / P4-4 / P4-1 buffer
        ├─ Creator #1 真 run 完成
        └─ W4 weekly status
```

---

## 6. W5-W6 placeholder

PM 在 W4 末重评:
- Phase 1 内测真正 GA 了吗?Concierge creator #1 真 run 通了吗?
- LLM-mode baseline 出来后,realism_avg / mechanical_pass_rate 与 fixture 差距多大?需要 P5 prompt iteration 吗?
- DM ≥ 5/天 这条 cadence 自起来了吗?Discovery calls 转化率多少?
- W4 4 张工程票全 done 了吗?

W5 票根据 W4 评估生成。不预分配。**预期方向**:
- Claude P5-1 prompt iteration based on P4-1 baseline regression
- Codex P5-2 cache layer 跨 thread 持久化(目前 P3-7 是 in-memory only)
- Founder concierge creator #2-3 + 第一次 cohort scale-up

---

## 7. Check-in cadence

不变:
- `pm-check-progress` routine 09:00 + 18:00 Asia/Shanghai,写 blocker docs on §8 triggers
- `upstream-sync-watch` routine 10:00 Asia/Shanghai,批 PR 提案
- W4 新增 probe(添加到 `check_progress.sh`):
  ```
  PM_W4   active=W4  w4_eng_done=N/4  P4-1=open/done  P4-2=open/done  P4-3=open/done  P4-4=open/done
  ```
  (probe 实际新增在 W4D1 由 Claude 顺手写,与 P4-* handoff 同步落地)

---

## 8. Auto-progression rules

- 4 张 W4 工程票全 done → 写 `PM_W5_allocation.md`
- Phase 0 决策 W4D1 仍空 → PM 强制 A+C
- founder lane W4D3 仍 0 → 写 `PM_founder_capacity_audit_<date>.md`
- 任何 critical-path 工程票 blocked > 2 天 → 写 `PM_blocker_<ticket>_<date>.md`

---

## 9. Founder commitments locked at W4 entry(2026-05-23 W3D3 由 PM 按 A+C 代签回填)

按 `PM_phase0_crisis_2026-05-22.md §5` PM-proxy 决策(A+C),W4 founder lane 必须执行的承诺:

| Commitment | W4 Day | Done-signal | 失败 → 触发 |
|---|---|---|---|
| 在 `backend/.env` 写入 `LLM_PROVIDER=doubao` + `ARK_API_KEY` + `DOUBAO_MODEL` | W4D1 | `cd backend && uv run python -c "from agent.llm_factory import get_chat_model; get_chat_model()"` 不抛 RuntimeError | P4-1 baseline 继续 slip → 重写 `claude_eval_P4-1.md §8` ETA |
| 找 1 位审稿人外包标 5 条 real fixture(P0-C 剩余)| W4D1-3 | `backend/src/agent/cascade/fixtures/real_v1/*.json` ≥ 20 + `founder_log/p0-c_outsource_log_*.md` 含审稿人合约 | 升级 `founder_capacity_audit §"escalation paths"` 选 (b) 或 (c) |
| 重跑合约测试:`cd backend && uv run pytest tests/test_cascade_contract.py -q` 验证 skipped=0(Codex 协助仅 0.5h)| W4D1 | probe 输出 `skipped=0` | 若 fail 由 Codex 独立 debug,不再阻塞 founder |
| 小红书 seed 帖发布(`seed_post_url_2026-05-22.md` 顶部贴真 URL,不是 `<FILL>` 占位)| W4D1 | probe 输出 `Marketing seed=YES` | W4D3 仍 NO → capacity audit §"escalation paths" 选 (d) Claude 起草 founder 复审制 |
| DM ≥ 5/天 × 7 天(`recruitment.md` 至少 35 条 `- DM` 行)| W4D1-7 | `grep -c "^- DM" docs/nexus/founder_log/recruitment.md` ≥ 35 | W4D3 仍 0 → 升级 |
| Discovery call #1(`interview_logged` event)| W4D2 | `bash scripts/check_progress.sh` → `Recruit calls=1+` | W4D4 仍 0 → 升级 |
| Concierge creator #1 真 run | W4D5-7 | `interview_logged event with phase=onboarded` + 1 个 `run_completed` 类似事件 | W5 起转 capacity audit |

**Override 通道**: 同 phase0_crisis §5 — founder 在 §5 末尾追加 `**FOUNDER OVERRIDE**: ...` 行,本 §9 自动作废,PM 在下次 session 重新协商。**Override deadline W4D1 上午**。

**Failure escalation flow**:
- W4D1 founder lane 仍 0 → PM 更新 `PM_founder_capacity_audit_2026-05-22.md §"escalation paths"`
- W4D3 founder lane 仍 0 → PM 写 `PM_W4_replan_2026-05-30.md`,直接重新设计 6 周时间表
- W4D7 founder lane 仍 0 → PM 写 `PM_pause_recommendation_2026-06-03.md`,提议暂停 6 周计划进入 30 天 reset

---

## 10. PM session contract

当此 allocation doc 在未来 Claude session 中加载(via `pm-check-progress` routine 或 fresh invocation):
1. 读此 doc + `PM_W3_allocation.md` + `PM_phase0_crisis_2026-05-22.md`
2. 跑 `scripts/check_progress.sh`
3. 对照 §2-§4
4. W4 工程全 done → 写 `PM_W5_allocation.md`
5. founder lane 卡 > 2 天 → 写 capacity audit log
6. Phase 0 决策仍空 → 强制 PM 推荐路径

Continuity 由这些文档管,不由对话记忆。

---

## 11. Open questions for founder(W4D0 决策)

1. **Phase 0 决策**:`PM_phase0_crisis_2026-05-22.md §5` 选哪个?(A / B / C / A+C)
2. **LLM key**:何时 `ARK_API_KEY` 写入 `.env`?(W4D1 还是 W4D2?)
3. **Concierge creator #1 候选**:你心里有具体人选了吗?还是要 PM 列 candidates?
4. **小红书 seed**:草稿是否已写好,还是要 PM/Claude 协助文案?
5. **Cursor 路由**:维持 deprecation 还是 W5 起重新启用?

---

## 12. 此 W4 草稿生命周期

- W3D2 写于 PM mode(本 commit)— 状态 **DRAFT**
- W4D0 founder 完成 phase0_crisis §5 决策 → PM 把本文件改为 **LOCKED**,回填 §9
- W4D1 起 owners 按 §3-§4 行动
