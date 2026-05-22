# PM · Phase 0 escalation — 2026-05-22 (W3D2)

**Date**: 2026-05-22 (W3D2 morning, ahead of 18:00 gate)
**Trigger**: `PM_W3_allocation.md §2` 写明 W3D2 18:00 escalation gate — 任一 P0-* 未关 → PM 写 crisis log。本文件为 **pre-gate** 写法,目的是把决策推到 founder 桌面,**避免今晚被动触发**。
**Probe snapshot (2026-05-22 morning, post commit `6c46e32`)**:

```
Phase0   closed=NO  fixtures=15  tests=56  skipped=1  compliance=1  algo_filing=0  prereg=1
PM_W3    w3_eng_done=6/6  P3-3=done  P3-4=done  P3-5=done  P3-6=done  P3-7=done  P3-8=done
Recruit  dms=0  calls=0  commits=0  runs=0  returns=0
Marketing seed=NO  xhs=0/10  douyin=0/5  wechat=0/1  jike=0/1
```

---

## 1. P0 五件套现状

| Ticket | Owner | 状态 | 距 closed | 阻塞因 |
|---|---|---|---|---|
| **P0-P** pre-registration | Founder | ✅ done | — | — |
| **P0-R** 5 项 compliance | Founder + Claude + Codex | ✅ done(commit `6c46e32`) | — | — |
| **P0-C** real fixtures ≥ 20 | Founder | ⚠️ 15/20(差 5) | 5 条真实 URL hand-label | 仅 founder 标注精力 |
| **P0-T** contract tests vs real_v1 | Founder + Codex | ⚠️ skipped=1 | 取决于 P0-C 是否补齐 + 1 个 skip 是否要解 | 卡 P0-C |
| **P0-A** 算法备案 受理回执 | Founder | ❌ algo_filing=0 | A 章节扫描件(营业执照) + Step 2 实名提交 | 营业执照仍在办理 |

**关键拆分**:
- 3 项已 close(P0-P / P0-R / 部分 P0-T 56 passed)
- **P0-C / P0-T 是 founder-pace 问题**(5 条标注 + 1 次 pytest)→ 可压缩到 1 个工作半天
- **P0-A 是 external dep 问题**(营业执照办理周期 founder 不可控)→ 不应该再被列为 Phase 1 内测开始的硬阻塞

---

## 2. 决策模板(三选一,founder 选一条)

### Option A — cut Phase 0,以现状进 Phase 1 内测(PM 推荐 + 备选)

**口径**:
- P0-P ✅ + P0-R ✅ + P0-C 15/20(60% close,补 5 条降级到 Phase 1 滚动任务)
- P0-T 重跑 1 次(skipped=1 由 founder 看一眼判定保留 or 修)
- **P0-A 算法备案从 "Phase 1 开始前硬阻塞" 改为 "公测前硬阻塞"**(与 `04_compliance_check.md` 原口径 "100-user public launch" 对齐)— Phase 1 内测 10 人 + 邀请制可实务豁免,已在 `algo_filing_2026-05-21.md §"申报口径与豁免说明"` 写明

**Founder 今日要做**:
1. 看一眼 `backend/tests/test_cascade_contract.py` 那条 skipped(`uv run pytest tests/test_cascade_contract.py -v` 找 SKIP 行 → 评估保留 or fix)
2. 标 5 条新真实 fixture(W3D3 前补齐到 ≥ 20)
3. 在 algo_filing_2026-05-21.md `Status` 行加一句 "Phase 1 内测下豁免,公测前必交"

**风险**:fixtures 60% 比例 PM 可接受,但要确保剩下 5 条 W4 内补齐,否则永远是欠债。

### Option B — extend Phase 1 by N days,等 Phase 0 真闭环

**口径**:Phase 1 内测开始日往后推 N 天 = max(P0-C 补齐时间, P0-A 受理回执时间)。P0-C 是 founder 1 个半天,P0-A 是营业执照 30-90 天。**实际意味着 Phase 1 推迟 4-12 周**。

**Founder 今日要做**:在 `02_sprint_plan.md` / `01_phase1_requirements.md` 修改 Phase 1 起始日 + 通知所有外部承诺(小红书 seed、DM 名单、即刻贴)。

**风险**:6 周原始时间表已经在 W1/W2/W3 founder 线连续 stall,再延期会让产品-市场-时间 三方进一步脱节。PM 不推荐。

### Option C — escalate to outside reviewer

**口径**:把 P0-A 备案路径委托给第三方代理(顺企网 / 工商代办 / 律师事务所),P0-C 标注外包给一位领域内的内容审稿人(小红书 / 抖音 baomam 类目熟人)。

**Founder 今日要做**:开 1 个搜索/外包预算口子(估计 P0-A 代理 ¥2000-5000,P0-C 标注 ¥200-500),挂在 `founder_log/PM_outside_reviewer_request_2026-05-22.md`。

**风险**:成本 + 时间 + 信任三重消耗。但如果 founder 评估自己未来 2 周还会被其他事卡(招募、Discovery、内容输出),这是从根本上释放 founder 时间的唯一办法。

---

## 3. PM 推荐组合:**Option A + Option C 的子集**

具体:
- **Option A 主体**:P0-A 重定义为 "公测前硬阻塞",Phase 1 内测立刻可起;P0-C/T 在 W4D1-2 补完
- **Option C 部分**:**仅 P0-C 标注委外**(找 1 位熟人审稿人帮标 5 条,founder 复核盖章即可);**P0-A 不委外**(等执照下来自己跑流程,反正不是 Phase 1 阻塞了)

理由:
1. 不引入外部审计的额外信任/合同成本
2. 真正放出 founder 时间到 **DM 招募 + 小红书 seed**(目前 W3 founder 0 进度的主因)
3. 与 `04_compliance_check.md` 原文豁免口径一致,不是凭空降级

---

## 4. Founder 行动栏(48 小时内)

请在本文件 §5 选一项打勾 + 写一句执行 ETA,即视为 PM 收到决策。

- [ ] **A** — cut Phase 0,以现状进入 Phase 1 内测,P0-A 改公测前阻塞 / ETA: ____________
- [ ] **B** — extend Phase 1 by N 天(填 N): _____ / ETA: ____________
- [ ] **C** — outside reviewer 委外(指明项): _____ / ETA: ____________
- [ ] **A+C(PM 推荐)** — A 主体 + 委外 P0-C 标注 / ETA: ____________

## 5. Founder 决策(签字位)

> (空 — 等 founder 写一行决策 + ETA)

---

## 6. 跟进路径(无论选哪条)

无论 founder 选 A/B/C/A+C,以下 W3D2-D3 founder lane 都仍要起:

| 项 | Done-signal | 备注 |
|---|---|---|
| 小红书 seed 帖 | `founder_log/seed_post_url_2026-05-22.md` 写入 URL | W1+W2+W3 滚动欠债,已 4 周未发 |
| 招募 DM ≥ 5/天 | `founder_log/recruitment.md` ≥ 5 条新增 | W2 commitment "0/25",必须今日起 |
| Discovery call #1 | `interview_logged` event with `phase=discovery` | 本周内任意一次 |

**如果 Phase 0 卡 + founder lane 也卡持续到 W3D4,PM 写 `PM_founder_capacity_audit_2026-05-23.md`(per `PM_W3 §9 failure mode`),提出 "6 周时间表是否需要重做" 的根问题。**

---

## 7. 此文件生命周期

- 写于 W3D2 morning (pre-gate)
- 若 founder 在 W3D2 18:00 前写出 §5 决策 → 此文件标 `Status: resolved by founder @ <时间>` 并归档
- 若 W3D2 18:00 仍空 → 此文件升级为 PM_W3D2 phase0 gate triggered,**PM 强制按 PM 推荐(A+C)推进**,founder 后续可推翻
