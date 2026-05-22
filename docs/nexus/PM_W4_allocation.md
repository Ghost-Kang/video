# PM · Week-4 Work Allocation

**Date**: 2026-05-22 (W3D2 morning)
**PM**: Senior PM (Claude session in PM mode)
**Trigger**: W3 engineering closed early — `w3_eng_done=6/6` on `scripts/check_progress.sh` 2026-05-22; idle backend/frontend bandwidth — draft W4 ahead of W3D7 to avoid Codex+Claude 3-day idle gap
**Status**: **DRAFT** (formal start = W4D1 = 2026-05-28; locks when Phase 0 decision made per `PM_phase0_crisis_2026-05-22.md`)
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

| Ticket | Brief | Done-signal | Upstream dep |
|---|---|---|---|
| **P4-1 LLM judge baseline (Doubao mode)** | `handoff/claude_eval_P4-1.md`(草稿待写)— P3-1 原本等 `GOOGLE_API_KEY`;P3-R2 切完 Doubao 后改用 `LLM_PROVIDER=doubao` 跑 `p2-6_eval.py --mode llm`,产 baseline JSON | `docs/nexus/founder_log/p2-6_baseline_<UTC>.json` 含 `mode=llm` 且 `judge_realism_avg > 0`(非 skipped);`mode=fixture` 与 `mode=llm` 两份 baseline 同期保留 | `ARK_API_KEY` + `DOUBAO_MODEL` 已在 `.env` |
| **P4-2 admin events firehose 面板** | `handoff/claude_frontend_P4-2.md`(草稿待写)— `/admin/events` 新页,反向时间序展示 `events` 表最近 200 条,前端 filter by `event_type` / `phase` / `user_id`;后端 `/api/events?limit=200&type=*` 端点 | 页面存在;后端 endpoint 返回数组;3 个 vitest 用例(filter / paging / live refresh);手动验证 fire 一条 `consent_accepted` event 能在前端看到 | P3-3 admin layout(done)|

### 3.2 Codex(后端)

| Ticket | Brief | Done-signal | Upstream dep |
|---|---|---|---|
| **P4-3 cascade observability counters** | `handoff/codex_backend_P4-3.md`(草稿待写)— 把 P3-7 加的 retry/circuit-breaker/cache 内部状态以 events 形式发出来:`cascade_retry`, `cascade_circuit_open`, `cascade_cache_hit/miss`,带 `endpoint` + `duration_ms` + `reason` payload。**不引入 Prometheus / OTel,只复用现有 events 表**(P4-2 面板会用到) | events 表里新事件类型有数据;6 个 unit tests 覆盖每种触发路径;Toprador 失败仿真 → 看到 cascade_circuit_open event | P3-7(done) |
| **P4-4 events 表索引优化** | `handoff/codex_backend_P4-4.md`(草稿待写)— `(thread_id, ts DESC)` 复合索引 + `(event_type, ts DESC)` 索引;Alembic / 手写 migration script;EXPLAIN 验证 admin events 查询用上索引 | migration 文件存在;`pragma index_list(events)` 列出 2 个新索引;`uv run pytest tests/test_events_index.py` 跑通(新增的 1 个 perf-shape 测试,断言 EXPLAIN 输出含 `USING INDEX`) | P4-2 endpoint 不阻塞,可并行 |

### 3.3 Cursor — deprecated(no W4 allocation)

Per `03_routing.md §0.1`(founder decision 2026-05-21),Cursor 仍 deprecated。W4 **zero** Cursor 新票。理由与 W3 §3.4 相同:无新 frontend 票路由到 Cursor,统一由 Claude 接管前端。

只在以下情况重新启用 Cursor:
- founder 在 W4D1-7 内显式撤销 `03_routing.md §0.1` 的 deprecation
- 或 Claude 前端工时严重 over-load(W4 4 票 + frontend 维护,目前看不会出现)

### 3.4 Founder — non-engineering(§4 详列)

§4 完整列举,与本节 §3 工程线对称对位。

### 3.5 Delays carry-forward(W3 slip → W4 action)

| Owner | What slipped in W3 | W4 recovery |
|---|---|---|
| **Founder** | DM batch(0 / 35 target,W2+W3 累计),seed post,算法备案,discovery calls(0),P0-A 受理回执 | 全部进入 §4 + §2 critical path。若 W4D3 仍 0 进度 → capacity audit. |
| Codex | (none — 5 张 P3 票全 done) | 接 P4-3 + P4-4 W4D1 起 |
| Claude | (none — 4 张 P3 票全 done + 协助文档 + 协议起草) | 接 P4-1 + P4-2 W4D1 起;P4-1 等 founder 把 `ARK_API_KEY` 写入 `.env` |
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

## 9. Founder commitments locked at W4 entry(待 W4D0 写入)

(此 §9 在 W4D0 founder 完成 `PM_phase0_crisis_2026-05-22.md §5` 决策后由 PM 回填。不在 W3D2 预写。)

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
