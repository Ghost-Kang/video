# Founder W4D1 — 2026-05-28(AI 数字员工启动日)

**Date target**: W4D1 = 2026-05-28(下周一)
**Rewrite**: 2026-05-24 W3D4 — 原 "founder 亲手 5h/w" 模型 → "PM 调 agent + founder 仅决策" 模型(per founder 2026-05-24 标准 instruction "我只决策" + W4D1 分工 OK)
**Founder weekly load 新目标**: **1-2 h/w**(只做决策 + sample review,不亲手做 DM/帖/Q&A)
**Goal**: W4D7 收盘前 ≥ 1 个真实 creator 跑完 first-run + 3 反馈点 + 真实情绪记录到 cohort_status

---

## ⚡ 心法

- **AI 数字员工已加载 185 个 Claude Code subagents**(`docs/nexus/agents/catalog.md`),Cascade Phase 1 选定 8 critical + 4 supplementary(`ai_digital_employee_inventory_2026-05-23.md`)
- W4D1 founder 只做 5 件事:**决策 / 启动 / sample-review / 亲调 first-run / 亲调 legal**。其他全 PM 代调
- 任何时刻 founder 可以在 chat 说 "PM,启 X 做 Y" 立刻触发 invoke
- 任何时刻 founder 可以亲自 `/agents <name>` invoke,绕过 PM

---

## 1. 09:00-09:15 · 决策签字(已默认接受,可推翻)

PM 已代签 2 个 decision points:
- `PM_phase0_crisis_2026-05-22.md §5` = **A+C**(Phase 1 立即起 + P0-A 转公测前)
- `PM_founder_capacity_audit_2026-05-22.md §6` = **(b' AI agents)**(原 (b) shrink + (c) outsource 子集 → AI 数字员工 替执行)

**默认接受 = 什么都不用做,直接进 §2**。

不同意 → 任一文档 §5/§6 末尾追加 `**FOUNDER OVERRIDE @ 2026-05-28**: <新>` 行 → commit → PM 下次 session 重排。

**Override deadline**:今天 W4D1 上午 — 过此点 agents 已启动到回退成本不低。

---

## 2. 09:00-09:43 · DM batch — founder sourcing + PM 调 agent 改文案

> **W3D4 dry-run 修正**:Sales-DM-Agent (Xiaohongshu Specialist) 已验证(`dm_dryrun_W3D4_2026-05-24.md`)— agent 可产高质量 DM 文案,**但不能自动抓 candidate 名单**;founder 需先手动 sourcing。

### 2.1 09:00-09:30 · Founder 自己刷小红书拿 5 个真名单(30 min)

按 `recruitment.md §"选人 4 条标准"`(30-40 岁女性 + 粉丝 1k-50k + 7 天有更新 + niche 纯辅食),刷小红书 30 min 拿 5 个 candidate。

每个 candidate 在 chat 给 PM 一行:
```
@<用户名> | <作品 URL> | <1 句具体作品细节,例如"她结尾切开拉丝的镜头">
```

### 2.2 09:30-09:35 · Founder 在 chat 说

> **PM,这是今天 5 个 baomam_fushi 名单,改 DM 文案。剩 <X> 个名额。**

剩名额 X = founder 实际心里的真数字(per W4D1 决策点 §1.2 Risk 2)。

### 2.3 09:35-09:38 · PM invoke Xiaohongshu Specialist + Sales Outreach

PM 调 agent 产 5 条 DM 文案(质量基线已由 dry-run 验证,~3 min);append `recruitment.md` 5 行 `- DM`。

### 2.4 09:38-09:43 · Founder review + 实际发到平台

founder 看 5 条文案 < 30 秒/条 sample 1-2 条质量(其他信任 agent dry-run 验证基线);copy → 小红书/抖音 app 实际发送。

### 2.5 commit

→ commit:`founder: W4D1 DM batch sent — <X> candidates via Xiaohongshu Specialist`

**Total time**:43 min(包括 founder sourcing 30 min — 这是不可代理的真实人力)。后续 W4D2-D7 daily DM 节奏:若 founder 累计 sourcing 一批 20-30 个,可以每天只用 5-10 min 让 PM 选 5 个改写文案。

---

## 3. 09:30-09:45 · PM 启 Content-Seed-Agent(15 min 监督)

founder 在 chat 说:
> **PM,启 Content-Seed-Agent 起 baomam_fushi seed 帖 9 图 brief + caption**

PM invoke `Xiaohongshu Specialist` + `Content Creator`,产出:
- 完整 caption(500 字内,禁用词扫过)
- 9 图 brief(每图描述 + Canva / 美图秀秀模板建议)
- 落 `founder_log/xhs_post_2026-05-28.md`

founder 30 秒 review:
- ✅ caption 干净 → 拍 1 张封面 + 发出
- 拍封面 = founder 唯一**亲手**做的物理动作(手机抓 1 张厨房 + 食材 + 爆款手机屏照,5 min)
- 发出后 URL 贴 `seed_post_url_2026-05-28.md`(从原 W4D1 文件改名 / 直接覆盖 W3D2 的 .md)

→ commit:`founder: W4D1 seed post published`
→ probe 验:`bash scripts/check_progress.sh` 出 `Marketing seed=YES`

---

## 4. W4D1-W4D3 · 后台自动等回复(0 founder action)

无 founder action。PM 设 daily 09:00 + 18:00 routine 自动:

| Trigger | PM 代调 | 产物 |
|---|---|---|
| 收到 creator DM 回复(founder 转发或 PM 检测)| `Discovery Coach` + `Feedback Synthesizer` | `dm_qa_<creator_id>.md` + `interview_logged` event |
| 每日 18:00(若昨日 DM 0 回复) | `Xiaohongshu Specialist` | 再拉 5 条 DM 候选 |
| 每条 candidate 改写出 publish_pack 前 | `Healthcare Marketing Compliance` | 母婴 niche 合规审 → `compliance_audit` event |

founder 只需:**每天早上 1 min** 看 `bash scripts/check_progress.sh` 一眼。`Recruit dms=` 数字涨即正常。

---

## 5. W4D5-W4D7 · Founder 亲调 first-run(unique 不可代理)

某位 creator 答应陪跑 → founder 在 chat 说:
> **PM,起 Cascade Concierge 给 @<creator> 跑 first-run,源 URL = <抖音/小红书 URL>**

PM invoke `Cascade Concierge`,产出 1 小时陪跑全程材料:
- 5 列观察表(空模板,founder 现场填)
- 3 反馈点逐字问题清单
- `/admin/cost` 实时监控提醒(¥1.5 stop-gate)

**founder 亲临 1 小时陪跑**(微信视频 / 飞书 / 现场),按 cascade-concierge 8 步脚本 + 5 列表填写。这是**不可代理**的环节 — creator 听到真人声音 + 真情绪反馈,**这 1 小时是 Phase 1 唯一真实信号源**。

结束 1 小时内 founder 把 5 列表 + 3 反馈逐字给 PM:
- PM 调 `Feedback Synthesizer` 做反馈聚类 + value/pay 判定
- PM 落 `concierge_run_<date>_<creator>.md` 完整文件
- POST `/api/events` `interview_logged`

→ commit:`founder: first concierge first-run with @<creator> — strong/weak signals`

---

## 6. W4D7(2026-06-03)· Cohort 周报 + 决策点

PM 调 `Chief of Staff` 产出 `cohort_status_W4_2026-06-03.md`:
- 本周 DM 总数 + 回复率 + first-run 数 + churn
- 强信号 creator 名单(value match + would_pay_39)
- W5 critical-path 提案(继续 cohort 扩 OR 暂停优化)

founder 5 min 看,在末尾签 1 行决策(继续 / 调整 / 暂停)。

→ commit:`founder: W4 周报 decision = <继续/调整/暂停>`

---

## 7. 不在 W4D1-D7 范围

PM 代调,founder 不需要看:
- Legal review v0→v1(`Legal Document Review`,公测前 30 天才启)
- WeChat 私域 retention(`Private Domain Operator`,W5+ creator 沉淀后)
- Trend research(`Trend Researcher`,W5+ weekly 节奏)
- 跨地区文化(`Cultural Intelligence Strategist`,cohort 扩到 ≥ 5 时)
- 算法备案(P0-A,等执照下来才能跑)

---

## 8. 每日 founder 最小动作清单(W4D1-W4D7)

每日 5-10 min(对齐 capacity audit 重定义后的 1-2 h/w 节奏):

- [ ] 早上 9:00 — chat 说 "PM,起今日 DM batch"(15 sec)
- [ ] PM 给 5 条 → review + 实际发到平台(2.5 min)
- [ ] (W4D1 only)拍 1 张封面图 + 发 seed 帖(5 min)
- [ ] (W4D5-7 only)亲临 1 小时 first-run 陪跑
- [ ] 晚 18:00 — `bash scripts/check_progress.sh` 看一眼(1 min)
- [ ] 任何时刻 chat 跟 PM 说 "我决定 ..."(决策可零成本立刻落地)

**Cumulative weekly load**:DM review × 7 × 2.5 min(17 min)+ seed × 5 min + first-run × 60 min + 周报决策 × 5 min ≈ **~90 min / week = 1.5 h/w**(达成 capacity audit (b' AI) 设计的 1-2 h/w 节奏)

---

## 9. 卡住怎么办

任何 PM 调的 agent 产出**质量差**:
- founder chat 说 "PM,刚才 X agent 输出不行,因为 <一句>" → PM 重 invoke 调 prompt
- 不需要 founder debug agent;PM 负责

任何 **founder 自己**卡:
- 拍封面 5 min 拍不出来 → chat 说 "卡封面" → PM 调 `Content Creator` 给 5 个 phone-friendly 拍摄角度
- 不会发小红书 / 抖音 → chat 说 "不会发" → PM 给 step-by-step 截图
- 任何动作 ≥ 5 min 卡顿 → 立刻 chat 求救,不要硬抗

---

## 10. 心理预期(W4 实际信号场景)

| 实际信号 | 应对 |
|---|---|
| W4D1-W4D3 0 回复 DM | 正常;Niche 平均回复率 5-15%,5-10 条 DM 拿 1 个回复 |
| 某 creator 回复但说"不感兴趣" | PM 让 agent 自动归档 + 切下一个;不要 push |
| 第一个 first-run creator 跑完后说 "改写不太像我" | **strongest signal** — 不是失败,是 prompt iteration 的精准方向;PM 立刻调 `Feedback Synthesizer` + 触发 W5 P5-x prompt iteration |
| 第一个 first-run creator 跑完后说 "好用啊!" | weak signal — 客套话;追问 "下周你自己会用几次" 答 0 = 真信号弱 |
| PM 某个 agent 产出 5 次都不达标 | flag founder + 提案换 agent(参考 `catalog.md` 找替补) |

---

## 11. 此 punchlist 来源

- §1 from `PM_phase0_crisis_2026-05-22.md §5` + `PM_founder_capacity_audit_2026-05-22.md §6`(PM-proxy 决策)
- §2-§3 from `ai_digital_employee_inventory §1.5 dispatch playbook`
- §5 from `cascade-concierge.md`(自建 agent)+ `concierge_onboarding_script_2026-05-23.md §3`(被 cascade-concierge 替执行)
- §6 from PM_W5_allocation 周报 cadence
- §10 from `concierge_onboarding_script §4 KPI rubric`

每节都跨链到 source-of-truth,future PM cycle 可顺藤摸瓜。
