# PM · Week-5 Work Allocation — AI 数字员工 dispatch table

**Date**: 2026-05-24 W3D4 写;**Active starts W5D1 = 2026-06-04**(W4 结束次日)
**PM**: Senior PM (Claude session in PM mode)
**Trigger**: W4 ends with first concierge first-run done OR 0-progress fallback
**Cadence**: PM cycle 每日 09:00 + 18:00 routine
**Reading order**: this → `PM_W4_allocation.md` → `ai_digital_employee_inventory_2026-05-23.md` → `founder_punchlist_W4D1_2026-05-28.md`

---

## 0. Allocation philosophy(post W3D4 pivot)

4-owner allocation 模型保留(Claude / Cursor / Codex / Founder)但 **Founder lane 执行已委托 AI 数字员工**(per `ai_digital_employee_inventory §1.4` 执行层 confirmed);**Founder = decision-only**。

新的工作流:
```
真实业务事件 → PM 检测 → invoke 对应 agent → agent 产 artifact → PM 写回 → founder 看 cohort_status 决策
```

185 agents 在 `~/.claude/agents/`,catalog `docs/nexus/agents/catalog.md`,Cascade Phase 1 选定 8 critical(`inventory §1.1`)+ 4 supplementary(`§1.2`)。

---

## 1. Pre-W5 evaluation(W5D1 PM session 重跑)

PM 在 W5D1 早盘读以下信号决定本周节奏:

| 信号 | 来源 | 含义 |
|---|---|---|
| W4 DM 总数 | `recruitment.md` grep `- DM` | < 35 = founder lane partially active; = 0 = agents 没启 |
| W4 first-run 数 | `concierge_run_*.md` 个数 | 0 = 致命(R1 没解);1 = 解药 work;≥ 2 = scaling 信号 |
| W4 真信号(value match + would_pay_39) | `interview_logged` events | 0 strong = pivot;1 = continue;≥ 2 = scaling W5 |
| W4 cost 实际(cohort 7 天)| `/admin/cost` cumulative | < ¥30 = under-budget;> ¥100 = need PREDICT recheck |

---

## 2. W5 — Critical path

| Day | Ticket | 调 agent / owner | Done-signal |
|---|---|---|---|
| W5D1 | PM 写 `cohort_status_W4_*.md` 周报 | `Chief of Staff` | founder 看 + 1 行决策(继续 / 调整 / 暂停) |
| W5D1-7 | DM cohort 扩到 35 累计 | `Xiaohongshu Specialist` daily | `recruitment.md` ≥ 35 行 |
| W5D2-5 | 真实 trend research 反向输 Cascade prompt 迭代 | `Trend Researcher`(supplementary #9 启用)| `founder_log/trend_W5_<date>.md` + W5 prompt iteration brief |
| W5D3-7 | first-run 第 2 + 第 3 位 creator | founder + `Cascade Concierge` | 2-3 个 `concierge_run_*.md` |
| W5D7 | W5 周报 | `Chief of Staff` | `cohort_status_W5_*.md` + founder 决策 |

**Escalation**:任一 critical agent 5 次 invoke 后产出仍不达标 → PM 在 W5 周报 raise + 提换 agent。

---

## 3. W5 — Engineering tickets(intentionally light — agents 自治第一周观察期)

### 3.1 Claude

| Ticket | Brief | Done-signal | Upstream dep |
|---|---|---|---|
| P5-1b prompt iteration based on W4 first-run signal | TBD post W4 周报 | rewrite_<niche>.md per W4 weak-signal | `concierge_run_*.md` × ≥ 1 + Feedback Synthesizer 分析 |
| P5-4 fix `test_judge_skips_without_api_key` stale assumption | 把 test 改成 mock 无 key 环境(目前 .env 有 ARK_API_KEY)| `uv run pytest tests/test_eval_harness.py` 全绿 | none |

### 3.2 Codex

| Ticket | Brief | Done-signal | Upstream dep |
|---|---|---|---|
| P5-5 toprador URL resolver wiring(若 W4 first-run 暴露 page-URL 痛点) | `mediakit/url_resolver.py` 加 `toprador_http` mode 实现 | `TOPRADOR_RESOLVER_MODE=toprador_http` env 启用后 page URL → 直接 .mp4 work | founder confirm接续协议 |
| P5-6 events table cleanup(retention sweep + admin cost calibration) | 跑 P4-7 retention_sweep + P4-8 cost_calibration 第一次 真实 run | sweep log + calibration report 落 founder_log | events 表 ≥ 50 行真实数据 |

### 3.3 Cursor — deprecated 维持

### 3.4 Founder — agent 调度 + 决策(per `founder_punchlist_W4D1` 模板,W5 节奏同)

| Day | 任务 | 触发 |
|---|---|---|
| W5D1 | 读 W4 周报 + 签 1 行 W5 决策 | `cohort_status_W4_*.md` |
| W5 任意日 | first-run 陪跑 ≥ 1 次 | creator 答应 |
| W5D7 | 读 W5 周报 + 签 W6 决策 | `cohort_status_W5_*.md` |

**Total founder load**:~1.5 h/w(同 W4 设计)。

### 3.5 Security review follow-ups(2026-05-28 Opus 4.8 review)

来源:`docs/nexus/architecture_review_2026-05-28_opus.md`。P0–P3 **已修复并上线**(commit `20f34f1`,公网实测 auth gap 已堵死)。以下为遗留 follow-up,**非阻塞**,按 gating 排入合适周期 —— 不要在 W5 提前拉起 SR-2/SR-3。

| Ticket | Owner | Brief | Done-signal | Gating |
|---|---|---|---|---|
| SR-1 轮换 `CASCADE_ADMIN_TOKEN` | Founder | 现 token 出现在 2026-05-28 session transcript;`openssl rand -hex 24` 重生,更新 prod `.env` + admin 页重填一次 | 新 token 生效 + 旧 token 失效(`curl -H 'X-Admin-Token: <旧>' /api/creators` → 401) | 即时(凭证卫生);与 `reference_prod_server` 轮换清单合并 |
| SR-2 cost_guard 服务端身份 | Codex / Claude | cost_guard 现按 **client 自报** `user_id`/`run_id` 计额度,cohort 内可轮换绕过 per-user 日额度。改为服务端验证身份(invite → 服务端发会话 token,额度绑定该身份) | 同一 invite 下轮换 user_id 不能突破 per-user 日额度 | **gate:cohort 扩到 > 10 人前**(W6 scaling 决策时重评);公网无上限 DoS 已堵死,当前 10 人熟人可接受 |
| SR-3 FastAPI/Starlette transport 迁移 | Claude | 退掉手写 HTTP parser;`_check_auth` 已抽好,迁移时映射成 typed route deps + OpenAPI | 见 `architecture_transport_storage_P2_plan.md` done-signal | **gate:measured contention OR > 30 creator**(per perf review)—— 非 W5 |

> PM 注:SR-1 是唯一需要本周期内动作的项(founder lane,凭证卫生)。SR-2/SR-3 在 §6 W6+ 重评时按 cohort 规模 gating 决定是否拉起。

---

## 4. AI 数字员工 W5 dispatch table

| Trigger | invoke | Expected产物 | PM 写回 |
|---|---|---|---|
| Daily 18:00 — DM batch 5 条 | `Xiaohongshu Specialist` + `Sales Outreach` | 5 候选 + DM 文案 | append `recruitment.md` |
| Creator DM 回复 | `Discovery Coach` + `Feedback Synthesizer` | text Q&A | `dm_qa_<id>.md` + `interview_logged` event |
| Creator 答应 first-run | founder 亲调 `Cascade Concierge` | 1h 陪跑材料 | `concierge_run_*.md` |
| First-run 反馈整理 | `Feedback Synthesizer` | value/pay 判定 + 改写质量信号 | append `concierge_run` `## 反馈解读` |
| 母婴 niche 改写 → publish_pack | `Healthcare Marketing Compliance` | 风险点 + 修改建议 | `compliance_audit` event |
| Weekly seed 帖 | `Xiaohongshu Specialist` + `Content Creator` | caption + 9 图 brief | `xhs_post_<date>.md` |
| Weekly cohort 周报 | `Chief of Staff` | 摘要 + 决策提案 | `cohort_status_W5_<date>.md` |
| Weekly trend 热点 | `Trend Researcher`(supplementary #9 启用)| niche 周热点 + prompt iteration 候选 | `trend_W5_<date>.md` |
| D+7 follow-up | `Feedback Synthesizer` + `Customer Service` | re-engage DM + churn 分析 | append `concierge_run_*.md` `## D+7 复盘` |
| Legal v0→v1(若到公测前 30 天倒数)| founder 亲调 `Legal Document Review` | v1 diff + 风险点 | commit `docs/legal/*_v1.md` |

---

## 5. Sequencing(W5)

```
W5D1 ──┬─ PM 写 W4 周报 ← Chief of Staff invoke
       ├─ founder 签 W5 决策
       └─ DM batch 继续 daily

W5D2-D3 ┼─ 第 2 位 creator 进入 DM Q&A 阶段
        ├─ Trend Researcher 跑首次 niche 热点
        └─ P5-4 fix stale test(Claude)

W5D4-D5 ┼─ 第 2 位 first-run 陪跑(founder + Cascade Concierge)
        ├─ Feedback Synthesizer 整理反馈
        └─ P5-5 toprador URL resolver(Codex,若 W4 first-run 需要)

W5D6-D7 ┼─ 第 3 位 first-run 备选
        ├─ 周报准备
        └─ P5-1b prompt iteration 起跑

W5D7    ┴─ 周报 + founder 决策 W6 路径
```

---

## 6. W6+ placeholder

PM 在 W5D7 重评:
- 真实 first-run 达 2+ 强信号?→ W6 scaling cohort 到 5-7 人
- 真实 first-run 显示产品 fit 弱?→ W6 暂停 cohort,先 prompt iteration + 锚点系统优化
- founder load 实际 ≤ 1.5 h/w?→ 节奏 sustainable;> 3 h/w?→ inventory R1 重审
- agent 产出质量?→ catalog 里挑替补 OR 自建更多 cascade custom
- **若 W6 决定 scaling cohort → 同时拉起 §3.5 SR-2(cost_guard 服务端身份),它的 gate 正是 "cohort > 10 人前"**;SR-3 transport 迁移仍按 contention/30-creator gating,通常晚于 W6

---

## 7. Check-in cadence

PM session 每 cycle 跑:
1. 读 `cohort_status_*.md` 最新 + `recruitment.md` grep counts
2. 决定是否 invoke 哪些 agents(per §4 table)
3. founder 任何 chat ping 立即响应

---

## 8. Auto-progression rules

- 任一 agent 5 次 invoke 后产出 < 70% 达标 → PM 在周报 raise 换 agent
- founder 7 天 0 决策动作 → PM 写 `PM_founder_engagement_W5_<date>.md`
- 真实 first-run 0 个 by W5D7 → PM 写 `PM_phase1_rethink_W5_<date>.md`

---

## 9. Founder commitments locked at W5 entry(W5D1 由 founder 在 W4 周报末追加)

待 founder 在 W5D1 读完 W4 周报后,在 `cohort_status_W4_*.md` 末尾签:
- W5 weekly load 目标(默认 1.5 h/w)
- W5 cohort 数(默认 3)
- W5 critical agents 是否调整(默认沿用 W4 8 critical + 1 added Trend Researcher)

---

## 10. PM session contract

每个 PM session 进入时:
1. 读本 doc + `PM_W4_allocation.md` + `ai_digital_employee_inventory` + `agents catalog`
2. 跑 `bash scripts/check_progress.sh`
3. 检查 founder 是否在 chat 有未响应的 ping
4. 根据 §4 table 决定本 cycle 调哪些 agents
5. 任何 cohort 事件触发 → invoke agent → 写回 → 通知 founder
6. 任何 founder 决策需求 → 提案 + 等签字

continuity 由文档保证,not session memory。
