# AI 数字员工 inventory — 2026-05-23 W3D3 晚

**Trigger**: founder 2026-05-23 23:55 PDT "招聘人员换成 AI 数字员工,我这里各种类型的数字员工都招齐了"
**Founder clarification**: "AI 数字员工 = 业务职能代理(如 sales agent / 客服 agent),补 founder lane 那些染金坊职能"
**Status**: ⛔ **BLOCKED · 待 founder 填 §1 roster + §2 每 agent 的可观察 done-signal**
**Why this matters**: 直接破解 `PM_risk_audit_2026-05-23.md §2 R1 致命风险`(Founder lane 4 周连续 0 进度)— 不靠 founder 时间,靠 AI agent 替执行。但前提是 PM 知道每 agent 能做什么、produce 什么artifact可观察。
**Related docs**: `PM_founder_capacity_audit_2026-05-22.md` · `founder_punchlist_W4D1_2026-05-28.md` · `concierge_onboarding_script_2026-05-23.md` · `recruitment.md`

---

## 0. 核心问题

我(PM)目前**只知道 AI 数字员工存在**,**不知道**:
- 都有哪些 agent(roster)
- 每个 agent 能做什么(capability)
- 每个 agent 跑完后落什么文件 / 写什么数据(observable artifact)
- 信任 / 边界(哪些能 autonomous,哪些必须 founder review)
- 成本结构(per-task 还是 per-agent 月费)
- 与现有 Cascade 工程线接口(它们 emit 什么 events?写什么 db?)

没解决这些,我无法把"founder 5h/w 亲手"重新分配成"AI agent 自动 + founder 决策"。

---

## 1. AI 数字员工 roster(请 founder 填)

每个 agent 一行,**复用 W4D1 punchlist 第 §2/§3 founder lane 工作**作为对位参考:

| Agent 显示名 | 工作类型 | 与 Cascade founder lane 对应 | 触发方式(autonomous/on-call/scheduled) | 产物落地位置 | 真实身份 / Provider |
|---|---|---|---|---|---|
| `<例:Sales-DM-Agent>` | 抖音/小红书冷启 DM 招募 | recruitment.md `- DM` 行(替代 founder W4D1 punchlist §2.2) | scheduled(每日 N 条) | append `recruitment.md` | (Coze 智能体 / 内部 RPA / 自建) |
| `<例:UserResearch-Q&A-Agent>` | 收 creator 回复后 follow-up Q&A(替代 30min discovery call) | concierge_onboarding_script §1+§2 (shrink mode 已砍 30min call) | on-call(creator 回复后触发) | `founder_log/dm_qa_<creator_id>.md` 或 `interview_logged` event | TBD |
| `<例:Content-Seed-Agent>` | 小红书 / 抖音 / 即刻 seed 帖发布 + 评论区互动 | founder_punchlist W4D1 §3 + W3 carry forward seed post | scheduled(节奏由 founder 拍板)| `founder_log/seed_post_url_*.md` 顶部填 URL | TBD |
| `<例:Concierge-FirstRun-Agent>` | 1 小时 first-run together 陪跑 | concierge_onboarding_script §3 1h 陪跑 | on-call(creator 答应起) | `founder_log/concierge_run_<date>_<creator>.md` | TBD |
| `<例:D+7-FollowUp-Agent>` | D+7 复盘 + 拉留存数据 | concierge_onboarding_script §3.6 follow-up | scheduled +7 天 | append `concierge_run_*.md` 末尾 | TBD |
| `<例:Algo-Filing-Agent>` | 算法备案 4 项扫描件 + 自助申报 | P0-A 老 founder-only ticket | on-call(执照下来后)| `founder_log/algo_filing_*.md` 更新 受理回执号 | TBD |
| `<例:Legal-Review-Agent>` | 协议 / 隐私 v0 复核 + 公测前重写 | founder 留的法务复核责任 | scheduled(公测前)| commit `docs/legal/*` review notes | TBD |
| `<例:Cohort-Coordinator-Agent>` | cohort 进度跟踪 + creator churn risk 预警 | PM 角色的一部分(我目前在做这个)| daily | `founder_log/cohort_status_*.md` | TBD |

**请 founder 把 `<例:...>` 改为真实 agent 名字 / 删/加行,并填 真实身份 + provider**。

PM 拿到 roster 后会:
- 把每 agent 任务转化为 `check_progress.sh` 可探测的 artifact(events / file presence)
- 重写 founder_punchlist 为 "AI 数字员工调度表"(founder 只需 W4D1 启动 agents,不再亲手做 DM/帖)
- 重写 capacity audit:weekly load 5h/w → "founder 决策 + AI agent 跑" 模式,scaling 突破

---

## 2. 每 agent 的可观察 done-signal(请 founder 在 §1 填完后回 PM 确认)

对每个 agent,PM 需要 3 个信息才能让 probe 看见它工作:

1. **每跑一次产出什么 file/event**(必须 git-trackable 或 events 表)
2. **每次跑的频率上限 / 触发条件**(例如:每天 18:00 / 收到 DM 回复后 2h 内 / 手动触发)
3. **PM 如何判定 agent 失败**(没产出 OR 产出但质量不行?)

格式 sample:

```
Sales-DM-Agent:
  artifact:  append `recruitment.md` 至少 1 行 `- DM <date> ...` 格式
  cadence:   每天 18:00 跑 5 条
  failure:   24h 内 `recruitment.md` 无新 `- DM` 行 → PM 拉黑名单
```

---

## 3. 与现有 4-owner allocation rule 的关系

当前 4 owners = Claude / Codex / Cursor / Founder。AI 数字员工**不是新的 owner**,而是 founder 的"延展手"(act as founder, produce artifacts in founder's lane)。

修正 routing:
- "Founder lane work"(DM / seed / discovery / concierge / algo / legal)→ 由 founder 决定**哪个 agent 跑哪部分**
- Agent 输出 = founder 输出(probe 看不出差别)
- Founder 最小责任 = (a) 启动 agents(W4D1)+ (b) 每天 sample review 1-2 个 agent 产物 + (c) 关键决策(签字 / 升级 / 退订)
- PM 在 cycle 文档里仍写 "Founder",不展开到 agent 粒度,除非 agent 失败需要 PM 干预

修正口径写进 `03_routing.md` 一节(等 §1 roster 确认后)。

---

## 4. 紧迫性(可选启动顺序)

不必所有 agent 都 W4D1 启动。PM 推 staged:

| Phase | Day | Critical agents |
|---|---|---|
| 0 启动 | W4D1 (2026-05-28) | Sales-DM-Agent + Content-Seed-Agent(直接破 founder lane 4 周 0 进度)|
| 1 跟进 | W4D2-D3 | UserResearch-Q&A-Agent(接 DM 回复)+ Cohort-Coordinator-Agent(跟踪)|
| 2 真实 first-run | W4D5-D7 | Concierge-FirstRun-Agent(陪跑首 creator)|
| 3 公测 prep | W5+ | Algo-Filing-Agent(等执照)+ Legal-Review-Agent |

各 agent 启动失败 = 1-day delay,**不致命**;每 agent 启动成功 + 产物自动落地 = founder lane 突破。

---

## 5. PM 接下来要做(等 founder §1 填完)

1. ✅ 写本 inventory 文档(本次 commit)
2. ⏳ 等 founder §1 roster 填回
3. 重写 `PM_founder_capacity_audit_2026-05-22.md §6`(b)+(c) → (b'+AI)新口径
4. 重写 `founder_punchlist_W4D1_2026-05-28.md` 改为"AI agent 启动顺序 + founder 决策点"
5. 更新 `recruitment.md` cadence:"founder 每天 5 DM" → "founder 跑 Sales-DM-Agent 拉 5 条,每周 review 一次"
6. 更新 `concierge_onboarding_script §1-§3`:加 "agent 替founder 做" 注释
7. 在 `check_progress.sh` 加 per-agent probe(file mtime / event filter / count)
8. 写 `PM_W5_allocation §"AI 数字员工 dispatch table"`,把 agents 装进 W5+ 节奏

工时估:约 0.5d PM 工作(等 roster 后 1 次 sit-down)。

---

## 6. 此 doc 生命周期

- **open** @ 2026-05-23 W3D3 23:55 PDT
- founder 填完 §1 roster + §2 done-signal → 状态 `partial-resolved`
- PM 跑完 §5 的 7 项 → 状态 `resolved` + 触发 W4D1 重排
- W4D1 启动 first batch agents → 状态 `live`,W4 周报评估 cohort 真实数据
