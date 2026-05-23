# PM · Founder capacity audit — 2026-05-22 (W3D2 收盘)

**Date**: 2026-05-22 W3D2 收盘 / 2026-05-23 W3D3 早盘写入
**Trigger**: `PM_W3_allocation.md §9 failure mode` — "若 W3 founder lane lapses identically to W2,PM 写 capacity audit 提出 6 周时间表是否需要重做的根问题"
**Status**: **open** · 等 founder 在 §6 选 escalation path
**Reading order**: this doc → `PM_phase0_crisis_2026-05-22.md` → `PM_W3_allocation.md §9` → `PM_W4_allocation.md §9`

---

## 1. 量化:3 周 founder lane 真实交付率

| 工作类 | W1 commitment | W1 delivered | W2 commitment | W2 delivered | W3 commitment | W3 delivered |
|---|---|---|---|---|---|---|
| 小红书 seed 帖 | 1 | **0** | 1 | **0** | 1 | **0**(模板就位,URL 未填)|
| 小红书 daily 帖 | — | — | 7 | **0** | 7 | **0** |
| DM 招募(≥ 5/天) | — | — | 25 | **0** | 35 | **0**(`recruitment.md` 仅模板)|
| Discovery call | — | — | 3 | **0** | 3 | **0** |
| P0-C real fixture(≥ 20) | — | — | 20 | **0** | 20 | **15**(Claude 帮 ship 15 个 A 档骨架;founder 5 条仍未补)|
| P0-A 算法备案 受理回执 | — | — | 1 | **0** | 1 | **0**(等执照外部依赖)|
| P0-P 预登记 | — | — | 1 | **1**(2026-05-21 commit `3aa4999`)| — | — |
| P0-R 5 项 compliance | — | — | 5 | **0** | 5 | **5**(2 项 Claude 起草 + 3 项 Codex 工程化,**founder 自身 0 时间投入**) |
| 协议/隐私文档 v0 | — | — | 1 | **0** | 1 | **1**(Claude 起草 `d294754`,founder 待复核署名责任)|
| 算法备案 A/B/C 章节 | — | — | — | — | A 章节 founder-only;B+C PM 填 | A 章节 **未填**(等执照);B+C 章节 Claude 填好 |
| phase0_crisis §5 决策签字 | — | — | — | — | W3D2 18:00 前 | **0**(过 14h 未签 → PM 代签 A+C)|

**实际 founder lane 净交付率 W3**:`P0-P / W3-commitments` ≈ **1/8(原始)**;扣除工具/AI 代劳后 founder 真正"亲自动手 hour" ≈ **<2 小时**(W3 整周)。

W1+W2+W3 累计净交付率(founder 亲手而非工具/AI 代劳):**3/22 ≈ 14%**。

---

## 2. 模式诊断

**不是工程能力问题** — 3 周 engineering 9+5+6 = 20 张工程票全 done(`PM_W1/W2/W3_allocation §3` 全绿)。

**不是 PM 能力问题** — PM 周期文档完整、handoff brief 全部就位、escalation gate 全部按时触发、allocation rule 严格遵守 4-owner 均衡分配。

**是 founder solo bandwidth 的根本问题**:

| 时间预算 | founder 周计划上每周需要的小时数(原始 W1 计划)| W3 实际投入小时(估算) |
|---|---|---|
| 小红书 daily(写 + 拍 + 互动)| ~5h/w | ~0 |
| DM 招募(写文案 + 群发 + 1v1)| ~5h/w | ~0 |
| Discovery calls(预约 + 30min × 3)| ~3h/w | ~0 |
| 算法备案 + 法律复核 + 协议署名 | ~2h/w | ~0(还在等执照)|
| P0-C 真实 fixture 标注 | ~3h/w | ~0(Claude 代劳了 15 条骨架)|
| concierge creator 1v1 | ~3h/w | ~0(尚未启动)|
| Phase 0 决策签字 | ~0.5h/w | ~0 |
| **合计** | **~21.5h/w** | **<2h/w** |

**Gap**:20h/w(原始计划) → ~2h/w(实际)= **founder 每周缺口 ~18 小时**。

**这不是"再努力一下"可以解决的差**。3 周连续证伪了"founder solo 能撑起 6 周时间表"的假设。

---

## 3. 失败的回归推论

**6 周时间表的隐含假设**:
1. ✅ Engineering 4 周内能 ship 完核心产品(已验证 — 3 周 ship 完 + 1 周 buffer)
2. ❌ Founder 每周能投 20h+(已证伪 — 实际 ~2h)
3. ❌ Founder solo 既写代码评审又做营销 + 招募 + 销售 + 法务(已证伪 — 全维度 0 进度)

**结论**:6 周时间表不会因为 W4/W5/W6 founder "突然有时间" 而自动恢复 — 数据规律是单调的 0。

如果 W4D1-D3 仍 0 进度,W4 也会是 0;如果 W4 是 0,W5 + W6 大概率也是 0。

---

## 4. 不做选择的代价

如果不更改 6 周时间表:
- W4D7 = 2026-06-03 仍无 Phase 1 内测启动(0 creator onboard,0 discovery call)
- W5D7 = 2026-06-10 仍无 cohort scale-up
- W6D7 = 2026-06-17 = 6 周计划终点 → **产品已 ship 但完全没有 market signal 验证**

最严重的实质后果不是错过 deadline,而是 **engineering 在没有真实 creator 反馈下持续迭代,半年后才发现做错了方向**。Claude + Codex 可以一直 ship,但 ship 错的东西就只是更精致的废稿。

---

## 5. Escalation paths(founder 选一条 + ETA)

### (a) Stay the course — founder 在 W4 全力投入 ≥ 15h/w

**前提**:founder 主动说明 W1-W3 的 0 进度是有可解释外因(健康、家务、其他工作截止),且 W4 起这些外因消失。

**风险**:已经 3 周连续证伪,再赌 1 周不实质改变什么。

### (b) Shrink scope — 把 6 周计划砍掉一半,只做 minimum viable validation

**砍法**:
- 取消"10 人 cohort"目标,改为 "3 人 cohort"
- 取消 daily 内容输出,只留 1 篇 seed + 5 条 DM/天
- 取消 discovery call,改为 DM 自助调研(收文字回答)
- Concierge creator #1 改为 2-3 周内拿到 1 个真 run + 反馈即结案

**留下的核心信号**:1 个真实 creator 改写 1 次,自然语言回答 3 个问题。其他全砍。

**预期 founder weekly load**:5h/w(seed-once + 5 DM/天 + 1 次邮件转录)— 与历史投入实测吻合。

### (c) Outsource — 把 founder lane 大部分外包

**外包项**:
- DM 招募 → 找 1 位熟人审稿人 / 营销人,¥3000-5000 包 35 条 DM + 引荐
- 小红书内容 → 雇 1 位 MCN 小编代发(¥2000-3000 / 月)
- Discovery call → 雇 1 位 UX research freelance 跑 3 个 call(¥3000-5000)
- 算法备案 → 工商代办,¥2000-3000

**总预算**:¥10000-16000 一次性。

**Founder 自己留**:法务复核(协议署名责任)+ 战略决策 + concierge creator onboarding 直接接触(不能完全外包)。

**预期 founder weekly load**:3h/w(只参与关键交接 + 决策)。

### (d) Pause + reset — 暂停 6 周计划,30 天 reset

**做法**:
- 暂停所有 founder lane 交付承诺
- Engineering 继续按 W4 路线 ship P4-3 / P4-1 / P4-5
- 30 天后(2026-06-21)founder 独立 reflect:6 周计划设计是否本身错误(scope 过大 / 时间表过紧 / single-founder assumption 不成立)
- reset 出来的新计划必须有 weekly load 实证支持(founder 实测每周能投多少 h)

**Cost**:Phase 1 内测延后 30+ 天;但避免在错的方向上加速。

---

## 6. Founder 决策位

请在下方写一行决策(选 a/b/c/d 或自定义)+ 你的 weekly load 实测承诺:

> (空 — 等 founder 写)
>
> 例:`(b) Shrink scope · 每周可投 5h · ETA W4D7 出 minimum viable validation`
>
> 例:`(c) Outsource · 预算 ¥12000 · ETA W4D3 起 outsource log 落 founder_log/`
>
> 例:`(d) Pause + reset · 2026-06-21 出新计划 · engineering 同期继续 W4 路线`

**Override deadline**:W4D3(2026-05-30)上午 — 过此点 PM 默认按 (d) Pause + reset 推,因为 (a)/(b)/(c) 任一都需要 founder 主动动作启动,而 (d) 是"什么都不做"的默认。

---

## 7. PM 推荐

**Option (b) + (c) 子集** — Shrink scope **主体** + 关键项外包:

- Phase 1 内测目标:从 "10 人 cohort + daily 内容" → "3 人 cohort + 1 个 concierge creator 完整 onboard"
- 外包(c子集):仅 P0-C 5 条标注委外(¥200-500)+ P0-A 工商代办(¥2-3k)
- Founder 留:1 篇 seed post(已写好 caption,founder 30min publish)+ 35 条 DM 中的 10 条(其余 25 委外难找 trust,先 founder 自己跑)+ 协议署名
- 预算消耗:¥2500-3500
- Founder weekly load 设计:5h/w(与历史实测对齐)
- 6 周 → 8 周(为现实节奏加 2 周 buffer)

理由:
- (a) Stay the course 已 3 次证伪,赌不起
- (d) Pause + reset 是核选项,但 founder 1 个月不行动 = engineering 没有反馈源持续 ship,实质是 (a) 的更糟版本
- (b)+(c) 子集是 "founder 实际 5h/w + 外包补短板",对齐数据现实

PM 在 §6 等 founder 决策。**若 founder 未在 W4D3 决策,§5 末尾 Override deadline 触发,PM 自动按 (d) 推**(因为 (b)/(c) 任一都需 founder 主动启动)。

---

## 8. 此 audit 文件生命周期

- **open** @ 2026-05-23 W3D3 早盘
- founder 在 §6 写决策 → 状态 `resolved` + 归档
- W4D3 上午仍空 → 状态 `auto-paused`,PM 启动 (d) Pause + reset,写 `PM_pause_recommendation_2026-05-30.md`
- 任何时刻 founder 在 §6 推翻 PM 推荐 → PM 立即按新决策重写 W4 allocation
