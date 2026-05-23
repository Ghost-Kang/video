# PM · 整体风险审视 — 2026-05-23 W3D3 中午

**Date**: 2026-05-23 W3D3(local 2026-05-22 21:48 PDT;Asia/Shanghai 2026-05-23 12:48)
**Trigger**: founder ping "整体审视项目进度及风险"
**Status**: open · 7 个风险维度量化 + mitigation
**Reading order**: this doc → `PM_phase0_crisis_2026-05-22.md` → `PM_founder_capacity_audit_2026-05-22.md` → `PM_W4_allocation.md`

---

## 0. 一句话总结

> **Engineering 在飞,founder lane 在原地,真实创作者反馈仍为 0**。本周内若不进入 Phase 1 真实使用,4 周后会有"产品 ship 完了但没人验证方向是否正确"的根问题。

---

## 1. 风险地图(按严重度排序)

| # | 风险 | 严重度 | 概率 | 当前状态 | mitigation 是否已有 |
|---|---|---|---|---|---|
| 1 | Founder lane 4 周连续 0 进度 | **致命** | 已发生 | capacity audit 在 founder 桌上 | ⏳ 等 W4D3 决策 |
| 2 | 工程节奏严重领先验证节奏 | **高** | 已发生 | W4 已 4 张 shipped + 1 baseline pending | ⚠️ 部分(下面 §3) |
| 3 | P4-1 LLM baseline 阻塞 commit 链路 | 中 | 已发生 | eval 跑 28+ min,可能挂死 | 见 §5 |
| 4 | Codex 利用率配置错误 | 中 | 已发生 | 本 audit 同步纠正 + 补 3 brief | ✅ 已 fix |
| 5 | 营业执照 / 算法备案外部依赖 | 中 | 已发生 | 30-90 天审批 | ✅ phase0_crisis 已重定义为公测前阻塞 |
| 6 | Toprador 上游未真实部署 | 中 | 中 | fixture mode 为主,真上线 reliability 未知 | 部分(P3-7 + P4-3 已加硬化和观察)|
| 7 | README + 路线图与代码长期不同步(已 fix)| 低 | 低 | W3D3 中午已重写 | ✅ 已 fix(待 commit) |

---

## 2. 风险 1:Founder lane 4 周连续 0 进度(致命)

### 2.1 量化

| 指标 | W1 | W2 | W3 | W3D2-D3 累计 |
|---|---|---|---|---|
| DM 招募 | 0/--- | 0/25 | 0/35 | **0** |
| 小红书 seed 发布 | 0/1 | 0/1 | 0/1 | **0**(模板就位) |
| Discovery call | 0 | 0/3 | 0/3 | **0** |
| 算法备案 | --- | 0/1 | 0/1 | **0**(等执照) |
| phase0_crisis §5 签字 | --- | --- | W3D2 18:00 前 | **空** → PM 代签 A+C |
| founder_capacity_audit §6 决策 | --- | --- | --- | **空**(W4D3 前) |

3 周累计 founder 真实亲手投入 ≈ < 6 小时;原始 6 周计划假设 ≈ 120+ 小时;**完成率 ~5%**。

### 2.2 根因(已诊断 `PM_founder_capacity_audit_2026-05-22.md §2-§3`)

不是"再努力"能修的差距 — 是 founder solo bandwidth 与 6 周时间表假设的根本不匹配。

### 2.3 状态

PM 已写 capacity audit + 给 4 个 escalation paths(a/b/c/d)+ PM 推 (b)+(c) 子集。**等 founder 在 §6 写决策**,W4D3(2026-05-30)上午自动触发 (d) Pause+reset。

---

## 3. 风险 2:工程节奏严重领先验证节奏(高)

### 3.1 量化

| 维度 | W1-W3 累计交付 | 真实创作者用过 |
|---|---|---|
| 工程票 ship | 20 张(P1×9 + P2×5 + P3×6) | 0 |
| W4 工程票 ship | 4 张(P4-2 + P4-3 + P4-4 + P4-5) + 1 pending(P4-1)| 0 |
| 改写流水线端到端 | ✅ fixture 模式 work | 0 真实 creator 跑 |
| 锚点系统 | ✅ CRUD + 复用统计 | 0 真实 anchor 复用 |
| 4 张 admin 看板 | ✅ creators / events / cost / anchors | 0 founder 真用过 admin |
| LLM 改写 baseline | ⏳ Doubao seed-1.6 baseline 跑中 | 0 |
| Discovery call | 0 | 0 |
| 真实 fixture(P0-C)| 15/20 | --- |

**Engineering : Validation ratio ≈ 24 : 0**。

### 3.2 风险表现

- 现在 ship 的工程**没有任何反馈通道矫正方向**
- 6 周后若发现 niche 选错 / hook 分类不准 / 改写质量不行,**所有 W4 工程都是沉没成本**
- Phase 1 内测原本就是为了拿到这反馈,但 founder lane 0 导致反馈通道一直关着

### 3.3 mitigation

**短期(W4D1-D3)**:
- (a) Founder 必须在 W4D3 capacity audit §6 决策 — 选 (b) shrink scope 路径让 Phase 1 内测进入 minimum viable validation
- (b) 即使 founder 不决策,PM 也可在 W4D2 撮合 founder + 1 位 friendly creator 做 1 次 30min concierge 体验 — 不需要正式 cohort 就能拿到第一手反馈

**中期(W4-W5)**:
- (c) **暂停新工程票开发**(除 Codex 已堆的 P4-6/7/8 收尾外不再开)— 工程已超前,继续 ship 边际收益 < 验证收益
- (d) Claude bandwidth 改路由到"协助 founder lane"(写小红书 caption 草稿、起 DM 模板、扫真实 URL 标注)

**长期(W5+)**:
- 把"真实 creator 跑通 1 次"作为下一 PM cycle 的 critical-path KPI,而不是再 ship 工程

---

## 4. 风险 3:P4-1 LLM baseline 阻塞 commit 链路(中)

### 4.1 现状

- Eval 后台跑 28+ min(PID 79084,起 9:22 PM)
- 0 stdout(`| tail -25` 缓冲导致看不到流式)
- 进程 CPU 0%,网络 ESTABLISHED → 等 Doubao 响应中
- 无错误信号

### 4.2 假设

最可能:Doubao seed-1.6 模型对 15 次 judge 调用 + 内部还有 rewrite 调用(每 case 改写 + judge,总 N=15+ 次 LLM 往返)在 thinking 模式下 5-10s/次,合理总耗时 5-15 min。**28 min 偏长但仍可能正常**。

### 4.3 mitigation

**等待 ≤ 1h 总耗时**: 让它继续跑;若 1h 仍无产物,kill + 切单 niche `--niche baomam_fushi` 重跑验证 + 单独跑其余两 niche。

**Commit 链路问题**:
- README rewrite + P4-1 baseline 当前打包等 baseline → 若 baseline 失败,README 也卡住
- **建议(本 audit 触发):**README 单独 commit,不等 baseline;baseline 跑出来后单独再 commit。两件事主题独立,合并是 anti-pattern。
- 用户原意是"等 baseline 合起来",但 baseline 不确定性升高时该重新协商

---

## 5. 风险 4:Codex 利用率配置错误(中,已 fix)

### 5.1 量化

- W3D3 早盘 Codex 队列(handoff/ 待选)只有 1 张(P4-3 + 已 ship 的 P4-4)
- P4-4 ship 后队列瞬间空 → Codex 没东西可挑
- PM 误判为 "Codex 不响应",re-route P4-3 给 Claude

### 5.2 founder 反馈 + 修正

founder ping "Codex 模式 = 快,合理安排他们中间工作" → PM 修正口径,见 `PM_W4_allocation.md §3.6 教训`。

### 5.3 修正动作(本 audit 同步执行)

- ✅ 已开 3 张 Codex backend brief(P4-6 / P4-7 / P4-8)→ 队列从 0 恢复到 3
- ✅ `PM_W4_allocation.md §3.6` 加 re-route discipline 教训
- ✅ 后续 Phase 1 全生命周期 PM 保持 Codex 队列 ≥ 2 张 brief 不空作为硬规则

---

## 6. 风险 5:营业执照 + 算法备案外部依赖(中)

### 6.1 现状

- 营业执照办理周期 founder 未明示;假设 30-60 天(外部)
- 算法备案 受理回执 24-72h,完整审批 30-90 天
- phase0_crisis §5 PM 代签 A+C 已把 P0-A 重定义为 **公测前** 硬阻塞,**不再阻塞 Phase 1 内测**

### 6.2 mitigation

- Phase 1 内测豁免口径已在 `docs/nexus/founder_log/algo_filing_2026-05-21.md §"申报口径与豁免说明"` 写明 + 跟 `04_compliance_check.md` 原口径对齐
- W4 founder commitment §9 不再列 P0-A 为 W4D1 必做项
- 公测前 90 天必须完成 — 假设公测目标 2026-09,W4D1 = 2026-05-28,有 ~16 周窗口;若 founder 在 W6-W7 开始正式申报来得及

### 6.3 残留风险

- 营业执照若 6-8 周仍未办下 → 公测推迟,但 Phase 1 内测不受影响

---

## 7. 风险 6:Toprador 上游未真实部署(中)

### 7.1 现状

- 所有 W1-W4 工程基于 `synthetic_v1` fixture(`backend/src/agent/cascade/fixtures/synthetic_v1/`)
- `real_v1` fixture 仅 15/20(P0-C 卡 5 条)
- `CASCADE_UPSTREAM=toprador` 路径 P3-7 已加 retry + breaker + cache,P4-3 已加观察事件,但 **没真实流量验证过**
- Toprador 自身的稳定性 / 延迟 / 限流口径 founder 未与 PM 同步

### 7.2 mitigation

- (a) P4-6 cache 持久化(Codex 队列已开)→ 容忍上游短时不可用
- (b) Phase 1 内测前需要至少 1 次端到端 staging:真实 URL 经 Toprador → 改写 → 看输出。可以在 founder 决策 capacity audit (b) shrink scope 后顺手做。
- (c) 若 Toprador 实际不稳,fallback 路径是 fixture mode + 文档说明"上游不可用时降级体验";已在 `CASCADE_UPSTREAM=fixture` 默认值里实现

### 7.3 残留风险

- 真上线后才发现 Toprador schema 与 contract.py 偏移 → 适配层(`adapter.py`)需要修;P2-1/P2-2 已做的 wiring 是按 schema 假设的,真实数据可能有 surprise

---

## 8. 风险 7:README 与代码长期不同步(低,已 fix)

### 8.1 现状

- 旧 README(`5b3b16e^` 起)描述 5-agent + ReactFlow 协同的"早期愿景",代码实际是 Cascade 短视频改写流水线 + 单 Director agent
- W3D3 中午已重写,341 行新版本对齐当前架构
- 但 uncommitted,等 P4-1 baseline 一起 commit(见风险 3)

### 8.2 mitigation

按 §4.3 建议:README 单独 commit,不等 baseline。

---

## 9. 综合建议(优先级排序)

| 优先级 | 动作 | 触发条件 | Owner | ETA |
|---|---|---|---|---|
| P0 | **founder 在 capacity audit §6 写决策** | 现在就可以做 | Founder | W4D3 上午 |
| P0 | **README 单独 commit(不再等 baseline)** | 现在 | Claude(PM)| 本 session 内 |
| P1 | **PM cycle 中途暂停新工程开发,转 Phase 1 validation 路径** | founder 选 (b) shrink scope 后 | PM + Claude | W4D1 |
| P1 | **若 P4-1 baseline 1h 后仍无产物,kill + 切单 niche 重跑** | 22:48 PDT 还无产物 | Claude | 实时观察 |
| P2 | **Codex 接 P4-6/P4-7/P4-8 三张 brief 之一**(选哪个由 Codex 自决)| 现在 | Codex | W4D1-2 |
| P2 | **PM 协助 founder 做 1 次 concierge friendly creator 体验** | 若 W4D2 仍无正式 cohort | PM + Founder | W4D2-D4 |
| P3 | **真实 Toprador 端到端 staging** | 在第一个真实 creator 跑之前 | Founder + Codex | W4D5 之前 |

---

## 10. 此 audit 文件生命周期

- **open** @ 2026-05-23 W3D3 中午
- 每个风险维度状态变化(尤其 1 + 2 + 3)时 PM 在对应 §X 更新
- W4 末 PM 写 `PM_W4_close_audit_<date>.md` 回顾本 7 维度是否解除
- 若某风险升级到 catastrophic → 单独写 `PM_<risk>_escalation_<date>.md`

---

## 11. PM 自查清单(W3D3 收尾)

- [ ] founder 看完本 audit 后是否在 capacity audit §6 决策?
- [ ] README 是否 commit 了?
- [ ] P4-1 baseline 是否完成或被合理 kill?
- [ ] Codex 队列是否仍 ≥ 2 张 brief?(本 audit 后:3 张)
- [ ] 下次 PM cycle 是否要把 "validation 节奏" 列入 W4 critical-path?(强烈是)
