# AI 数字员工 inventory — 2026-05-23 W3D3 晚

**Trigger**: founder 2026-05-23 23:55 PDT "招聘人员换成 AI 数字员工,我这里各种类型的数字员工都招齐了"
**Founder clarification**: "AI 数字员工 = 业务职能代理(如 sales agent / 客服 agent),补 founder lane 那些染金坊职能"
**Status**: ✅ **EXECUTION MECHANISM CONFIRMED** @ 2026-05-24 W3D4 — founder 说 "Claude Code 已经加载了这些 subagent,需要的时候可以直接 invoke"。
- §1 roster:✅ PM 已填(8 critical + 6 候选)
- 执行层:✅ Claude Code Agent tool(`subagent_type` 参数命中名字即 invoke)— PM session 内可直调,无需 cron / 外部 dispatch shell
- §2 per-agent cadence/失败信号:**改为按需 PM 主动 invoke,不再固定 schedule**(每 cohort 事件触发对应 agent)— 见 §1.5 PM dispatch playbook
- 仍待 founder:(a)确认 8 critical 映射对应你心目中的真实任务,(b)真启动 W4D1 后,founder 决定哪些 agent 是 founder 亲启 vs PM 代调
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

## 1. AI 数字员工 roster(PM 已根据 `~/github/agency-agents/` 仓库填,2026-05-24 W3D4)

**Source**: `/Users/kang/github/agency-agents/` — Mike Sitarzewski "The Agency" — ~200 个 specialized AI agent personality files,按 department 组织(marketing / sales / product / support / specialized / strategy 等)。每 agent 是一个独立 markdown文件,描述 identity + capabilities + workflows。Cascade 可作为 Claude Code subagent 调用 OR 自建 dispatch shell。

Provider = "agency-agents repo MD personality + Claude Code subagent 加载",**统一在此栏标注 agency-agents:<path>**。

### 1.1 Critical 8 agents(Phase 1 founder lane 直接替换)

| Cascade Agent Slot | 工作类型 | 对应 founder lane | 触发 | 产物落地 | Backing agency-agents file |
|---|---|---|---|---|---|
| **Sales-DM-Agent** | 小红书/抖音 cold DM 招募 + ICP 研究 | `recruitment.md` 每日 ≥5 条 `- DM` 行;替代 founder_punchlist §2.2 | scheduled 每日 18:00 跑 5 条 | append `recruitment.md` | `marketing/marketing-xiaohongshu-specialist.md`(主,中文 native + 算法理解)+ `specialized/sales-outreach.md`(副,consultative 文案 + ICP) |
| **Content-Seed-Agent** | 小红书 seed 帖起草 + 9 图准备 + caption 禁用词扫 + 评论区互动 | `founder_log/seed_post_url_*.md` URL 填入;founder_punchlist §3 | on-call(W4D1 第一篇)+ scheduled 每周 1 篇 | `seed_post_url_*.md` 顶部 + `founder_log/xhs_post_<date>.md` × N | `marketing/marketing-xiaohongshu-specialist.md`(主)+ `marketing/marketing-content-creator.md`(副,multi-platform 改写) |
| **UserResearch-Q&A-Agent** | creator 回 DM 后文字 Q&A(替代 shrink mode 砍掉的 30min discovery call) | concierge_onboarding_script §1+§2 + 落 `interview_logged` event | on-call(creator 回复后 2h 内) | `founder_log/dm_qa_<creator_id>.md` + POST `/api/events` `interview_logged` | `sales/sales-discovery-coach.md`(主,SPIN + 三框架 discovery)+ `product/product-feedback-synthesizer.md`(副,文字 Q&A 整理 + 热点抽取) |
| **Concierge-FirstRun-Agent** | 1h first-run together 陪跑 — creator 跑 Cascade 改写流水线 + 三反馈点收集 | concierge_onboarding_script §3 完整脚本 | on-call(creator commit first-run) | `founder_log/concierge_run_<date>_<creator>.md`(5 列观察表 + 3 反馈点逐字) | `specialized/customer-service.md`(temperate friendly tone + 引导用户产品体验) |
| **D+7-FollowUp-Agent** | D+7 后跟踪 creator 真实复用次数 + churn 原因 | concierge_onboarding_script §3.6 + KPI rubric §4 | scheduled +7 天 from first-run | append `concierge_run_*.md` 末尾 + (可选)写 `founder_log/cohort_status_<week>.md` | `product/product-feedback-synthesizer.md`(主,churn pattern 分析)+ `specialized/customer-service.md`(副,re-engage tone) |
| **Compliance-Algo-Filing-Agent** | 算法备案 4 项扫描件 + 自助申报 + 母婴/育儿 niche 健康内容合规审查 | P0-A(`algo_filing_2026-05-21.md` 受理回执);母婴 niche 健康声明触发 | on-call(执照下来后 / 每 batch creator output 前) | `founder_log/algo_filing_*.md` 受理回执号 + 每条 creator 改写 W14 minor audit | `specialized/healthcare-marketing-compliance.md`(主,中国 母婴/医疗营销 合规)+ `support/support-legal-compliance-checker.md`(副,通用 PIPL/广告法) |
| **Legal-Review-Agent** | 协议 v0 / 隐私 v0 复核 + 公测前重写 + 合同审 | `docs/legal/*` v0 → 公测前 v1 升级承诺 | scheduled(公测前 30 天) | commit `docs/legal/*_v1.md` 替代 v0 | `specialized/legal-document-review.md`(合同/协议/版本对比审查) |
| **Cohort-Coordinator-Agent** | cohort 节奏跟踪 + churn risk 预警 + PM 周报 input | 我(Claude PM 自己) cycle 的一部分;agent 协助提供 daily metrics 给 PM | scheduled daily | `founder_log/cohort_status_<date>.md` daily metrics dump | `specialized/specialized-chief-of-staff.md`(高层 cross-functional coordination)OR `project-management/project-manager-senior.md` |

### 1.2 Phase 2+ Cascade-relevant candidates(暂不启,W5+ 评估)

| Cascade 未来需求 | Agent file |
|---|---|
| WeChat 私域 creator 长留存 | `marketing/marketing-private-domain-operator.md` |
| Douyin niche 扩展(辅食外 niche)| `marketing/marketing-douyin-strategist.md` |
| 知乎 / B站 / 微博 跨平台分发 | `marketing/marketing-zhihu-strategist.md` + `bilibili-content-strategist.md` + `weibo-strategist.md` |
| niche 热点感知 → Cascade prompt iteration 反向输入 | `product/product-trend-researcher.md` |
| 跨地区文化敏感性 check(若 Cascade 扩到广东/东北/海外华人 niche)| `specialized/specialized-cultural-intelligence-strategist.md` |
| creator retention nudges(D+14/+30 拉回)| `product/product-behavioral-nudge-engine.md` |

### 1.3 已排除的 superficially-相关 agent(命名相似但实际不 fit)

- `specialized/recruitment-specialist.md` — 名字 "recruitment specialist" 看似匹配,但实际是 **HR talent acquisition**(招员工进公司),不是"招 creator 加入 cohort"。**不用**。
- `sales/sales-coach.md` / `sales-deal-strategist.md` — B2B 大客户销售;不适用 Phase 1 creator 招募(creator 不是 B2B buyer)。
- 其他 30+ marketing agents(LinkedIn / Twitter / Instagram / Reddit / TikTok 海外平台等)— niche overlap 弱。

### 1.4 执行层(Claude Code Agent tool invoke 模式)

**Claude Code 已加载所有 agency-agents subagent**(founder 2026-05-24 W3D4 确认 + PM 物理验证)。Cascade PM session 直接通过 Agent tool invoke,**无需自建 cron / Coze 集成 / 外部 dispatch shell**。

**安装路径验证**(2026-05-24 PM 物理检查):
- 源:`~/github/agency-agents/`(~200 markdown files)
- 安装脚本:`~/github/agency-agents/scripts/install.sh`
- 安装目标:`~/.claude/agents/`(已存在 205 个 .md,涵盖全部 8 critical + 6 候选 + 其他)
- Claude Code 通过 `subagent_type=<agent display name>` 加载文件 → spawn agent session

替代安装方式(若想 update / re-install):`mkdir -p ~/.claude/agents && cp ~/github/agency-agents/**/*.md ~/.claude/agents/`(per founder 2026-05-24 备注)。

调用契约(Anthropic Agent tool):
```
Agent(
  subagent_type="<agent display name 精确大小写,例如 'Xiaohongshu Specialist'>",
  description="<3-5 字英文 task summary>",
  prompt="<完整 brief — agent 不知道当前 cohort context,要在 prompt 内塞 cohort 状态 + Cascade artifact 路径 + 期望产物 + 字数/格式限制>",
  run_in_background=False  # 默认 foreground;长任务可后台
)
```

**关键**:每次 invoke 都是 cold start(无 memory),prompt 必须自包含。PM 是 orchestrator,负责:
- 把 Cascade artifact(`recruitment.md`, `founder_log/*.md`, events DB)的相关上下文拼到 prompt 里
- 把 agent 返回的 markdown / 结构化输出**写回**Cascade artifact(append `recruitment.md`,落 `concierge_run_*.md`,emit event)
- 跨 agent 协调(例如 DM 拿到回复后 PM 自动调 UserResearch-Q&A 接续)

### 1.5 PM dispatch playbook(每 cohort 事件 → invoke 对应 agent)

| Cohort 事件 | PM 触发 invoke | subagent_type | Expected 产物 | PM 写回 |
|---|---|---|---|---|
| Cohort 启动 W4D1(每日 5 DM)| 每日 18:00 PM session | `Xiaohongshu Specialist` | 5 条 DM 文案(每条引一个具体作品细节)+ 候选 creator 名单 | append `recruitment.md` 5 行 `- DM` |
| Creator 回复 DM | 收到 founder 转发 / 平台告警 | `Discovery Coach` + `Feedback Synthesizer` | text Q&A 文案 + 收到 reply 后解读 + niche 信号摘要 | `founder_log/dm_qa_<creator_id>.md` + POST `/api/events` `interview_logged` |
| Creator 答应 first-run | founder ping PM "creator X 答应" | `Customer Service` | 1h 陪跑脚本 + 5 列观察表模板 + 3 反馈点问题清单 | `founder_log/concierge_run_<date>_<creator>.md`(空模板)|
| First-run 结束 | founder 跑完 把 5 列观察 + 反馈点给 PM | `Feedback Synthesizer` | 反馈语义聚类 + value-statement match / would_pay_39 判定 + 下一步建议 | append `concierge_run_*.md` 末尾 `## 反馈解读` |
| D+7 follow-up | scheduled +7 天 | `Customer Service` + `Feedback Synthesizer` | re-engage DM 文案 + 收到回复后 churn analysis | append `concierge_run_*.md` `## D+7 复盘` |
| 母婴 niche 内容审 | 每条 Cascade creator 改写出 publish_pack 前 | `Healthcare Marketing Compliance Specialist` | 风险点 + 修改建议(广告法 §10/§16 + 母婴营销规) | `events` 表 `compliance_audit` event 或 W14 minor_audit 强化 |
| Seed 帖发布 | W4D1 + 每周 1 篇 | `Xiaohongshu Specialist` + `Content Creator` | caption + 9 图 brief + 禁用词扫 | `founder_log/xhs_post_<date>.md` |
| Cohort 周报 | scheduled 每周 W?D7 | `Chief of Staff` | cohort 状态摘要 + churn 风险榜 + 下周 critical-path 提醒 | `founder_log/cohort_status_W?_<date>.md` |
| 算法备案 / 公测前协议复核 | on-demand | `Legal Document Review` | 协议 v0 → v1 diff + 风险点 | commit `docs/legal/*_v1.md` |
| 趋势热点感知 | scheduled 每周 | `Trend Researcher` | niche 周热点 + Cascade prompt iteration 候选 | `founder_log/trend_<date>.md` → 反向输 prompt 调整 |

**dispatch 边界**(per "spawn agents 不主动" 原则):
- PM **不主动** spawn agents 做"分析" / "审视" — 这些用主 PM 工具自己做
- PM **只在** 真实 cohort 事件触发 + 需要产 founder-lane artifact 时调
- founder 可以**直接** 在 chat 里说"PM,启 Sales-DM-Agent 拉 5 条" → PM 立刻 invoke + 落 `recruitment.md`
- founder 也可以**绕过 PM** 自己 invoke(任何 Claude Code 终端 `/agents <name>`)— PM 在下次 cycle 读 git diff / probe 就能看到

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
