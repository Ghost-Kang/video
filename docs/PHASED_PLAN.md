# Cascade / OpenRHTV · 分阶段目标与实施计划

**Date**: 2026-05-19
**Status**: v1（综合六位评审反馈后的修订版）
**Replaces**: `MVP_SCOPE.md` 的 6 个月一次性大计划部分
**Related**: `BUFFETT_*` · `ELON_*` · `NAVAL_*` · `STEVE_JOBS_*` · `ILYA_*` · `KARPATHY_*` Review

---

## 0. 一句话定位（统一收敛）

> **Cascade 是「把别人的爆款变成你的版本」的中文创作者工作系统。**

不是 AI 视频生成器。生成是基础设施，模型层不竞争。
真正卖的是：选题确定性 + 爆款理解 + 赛道改写 + 可复用资产 + 学习闭环。

---

## 1. 评审共识与原 MVP 的对照

| 维度 | 原 `MVP_SCOPE.md` | 评审共识 | 本计划采纳 |
|---|---|---|---|
| 周期 | 6-8 个月一次性 | 先 6 周验证，再分阶段 | 4 阶段，节点门 |
| 工时 | ~160 人天 | 不该全量投入 | Phase 0+1 控制在 ~30 人天 |
| 目标 | 30 Beta + 60s 完整成片 | 10 真实用户 + 重复创作 | 见 §3 Gate |
| 上游 contract | 默认可用 | schema 未稳定，先证 | Phase 0 第一交付物 |
| 自动化承诺 | URL → 全自动 60s 成片 | 关键节点人类兜底 | 草稿 → 用户确认 → 生成 |
| Agent | 5 触发器 | 砍到 0-1 | Phase 1 不做 |
| 画布模式 | 标准 / 闪电 / 精修 / 手动 | 一个最小画布 | Phase 1 仅 1 种 |
| `/admin` | 完整后台 | 砍 | Phase 3 之后再议 |
| `/me/dashboard` | 4 模块 | 砍 | Phase 3 之后再议 |
| `/topics` | 6 Tab | 砍到 1 入口 | Phase 1 单入口 |
| Deep Topic Intelligence | 新增完整推荐/预测系统 | 先做规则分 + TopicBrief + 反馈回流 | Phase 1-3 分段验证 |
| 商业化 | day-1 字段全埋 | 先证留存，再收费 | Phase 2 接配额 |
| B2B / marketplace | V1.5-V2 | 全部砍 | 不在路线图 |

---

## 2. 四阶段总览

```text
Phase 0  ─ Schema 与 Contract 稳定        (2 周, ~10 人天)
Phase 1  ─ 6 周验证版（火箭发动机）       (4 周, ~20 人天)
Phase 2  ─ 30 人 Beta 产品化              (8-10 周, ~50 人天)
Phase 3  ─ 资产复利与商业化               (8-12 周, ~70 人天)
```

每个阶段之间有 **Gate**。不通过不进入下一阶段。
不是日历驱动，是证据驱动。

---

## 3. Phase 0 — Schema 与 Contract 稳定（W1-W2）

**目标**：先稳定上游表示，再做任何下游。Karpathy 视角：先证 march of nines 的起点。

### 3.1 必做

| # | Deliverable | 工时 |
|---|---|---|
| P0-1 | 抓取 20 条真实抖音/小红书视频，保存 raw `analysis_result` JSON 到 fixture corpus | 2d |
| P0-2 | 产出 `TOPRADOR_SCHEMA.md`：字段表（名/类型/必填/缺失率/消费者/fallback） | 2d |
| P0-3 | 定义 `CascadeAnalysisContract` TypeScript / Pydantic 类型 + `schema_version` | 1d |
| P0-4 | 实现 `normalize_analysis_result()` adapter + validator | 2d |
| P0-5 | Contract tests：必填字段、scenes 数量、时间戳递增、warnings、fallback 标记 | 2d |
| P0-6 | Failure taxonomy 定义 + 每种失败的恢复路径 | 1d |

### 3.2 Gate（进入 Phase 1 的条件）

| 指标 | 通过线 |
|---|---:|
| 深分析成功率（20 条样本） | ≥ 80% |
| 核心字段完整率 | ≥ 90% |
| 静默失败 | 0 |
| 每类失败都有 UI 可见的恢复路径 | 100% |
| 单条分析成本 | < ¥5 |

不通过 → 回到 prompt / parser 调优，或换 provider。**不进入 Phase 1。**

---

## 4. Phase 1 — 6 周验证版（W3-W6）

**目标**：证明「热点 → 改写 → 草稿 → 复用 → 发布包」单一闭环对真实创作者有用且会重复使用。
Jobs 视角：这是 iPod 时刻，不是 PC。

### 4.1 唯一保留的体验

```text
粘贴一条爆款 URL（或选择系统推荐的一条）
  → 看懂它为什么火（hook / 节奏 / 情绪 / 公式）
  → 选一个赛道（如：宝妈辅食 / 3C 测评 / 本地生活）
  → 系统给出改写后的脚本
  → 生成 3-5 张关键镜头草稿图（image grounded）
  → 复用 1 个角色锚点 + 1 个场景锚点
  → 导出发布包（标题 / 标签 / 脚本 / 素材路径）
```

### 4.2 必做

| # | Deliverable | 工时 |
|---|---|---|
| P1-1 | 单一首页：URL 输入框 + 一句赛道描述 + 5 条系统精选热点 | 2d |
| P1-2 | 浅分析卡片：whyItHit + howToAdapt（基于 P0 contract） | 2d |
| P1-3 | 赛道改写 prompt + 输出脚本（dialogue + 镜头切分） | 3d |
| P1-4 | 最小画布：脚本节点 + 3-5 个镜头节点 + 发布包节点（无 Agent UI） | 4d |
| P1-5 | Image 生成接入（沿用 OpenRHTV 的 Apimart + Gemini） | 1d |
| P1-6 | 角色锚点 + 场景锚点的「跨 run 复用」最小可用版（不做三视图，先做单图引用） | 3d |
| P1-7 | 发布包导出（剪贴板：标题 / 标签 / 脚本 / 镜头图 URL） | 1d |
| P1-8 | UI warnings：缺失字段、fallback 使用、置信度可见 | 2d |
| P1-9 | 成本统计与上限（单 run cap，超限提示） | 1d |
| P1-10 | 10 位真实创作者试用 + 每人 1 次访谈 | 2d |

**合计 ~21 人天**，留 25% buffer = 26 人天 ≈ 5-6 周。

### 4.3 不做（明确反对）

- ❌ 完整 60s 自动成片（不做 TTS / BGM / 字幕 / ffmpeg 合成）
- ❌ 多模式画布（精修 / 手动 / 闪电）
- ❌ Agent UI 5 触发器
- ❌ `/admin` 任何后台
- ❌ `/me/dashboard` 任何创作者数据中心
- ❌ `/topics` 6 Tab 雷达
- ❌ 三视图角色锚点（保留单图引用即可）
- ❌ OAuth 一键发布
- ❌ Stripe / 配额 / 多档商业化
- ❌ B2B 报告 / marketplace
- ❌ 多租户 / RLS / 审计

### 4.4 Gate（进入 Phase 2 的条件）

| 指标 | 通过线 | 出处 |
|---|---:|---|
| 真实创作者试用 | ≥ 10 人 | 共识 |
| 完成第一条内容 | ≥ 5 人 | 共识 |
| 一周内回来做第二条 | ≥ 3 人 | 共识 |
| 用户能一句话说出价值 | ≥ 2 人说「它帮我把爆款变成我的内容」 | Jobs |
| 单条成本 | < ¥15 | Elon / Naval |
| 热点 → 创作转化率 | ≥ 15% | Elon |
| 失败时用户知道下一步 | 100% | Karpathy |
| 至少 2 人开始沉淀角色或场景锚点 | ≥ 2 | Ilya |

**不通过 → 停。回到核心假设排查（见 §7 假设清单），不堆功能。**

### 4.5 Deep Topic Intelligence 投资边界

新增的 `TOPIC_INTELLIGENCE_DEEPENING_PLAN.md` 方向可以进入路线图，但必须按学习闭环拆分，不能一次性建设大推荐系统。

Phase 1 只允许做：

```text
/topics 今日值得拍
  -> opportunity_score 规则分 / mock 输出
  -> 一句话判断
  -> 为什么值得拍
  -> 怎么拍
  -> TopicBrief 进入画布
```

Phase 2 才允许做：

- `video_content_features` 入库。
- `ViralMechanism` 结构化。
- 深分析结果从"报告"变成可训练字段。
- 运营可手动校正 hook / emotion / pain_point。

Phase 3 才允许做：

- `PerformanceSnapshot`。
- 手动录入或截图 OCR 发布表现。
- 预测 vs 实际复盘。
- 账号画像开始累积。

明确暂缓：

- LightGBM / XGBoost：等 1000+ 有效样本后再做。
- 多模态 Transformer：不进入当前路线图。
- 全平台全垂类预测：不进入当前路线图。
- 复杂 6 Tab 决策中台：不进入当前路线图。

六视角共识：

| 视角 | 判断 |
|---|---|
| Elon Musk | 投最小闭环，不投推荐系统大工程 |
| Buffett | 小额下注，等留存和复用证明安全边际 |
| Naval | 值得投代码 / 数据杠杆，不能变成人工服务 |
| Steve Jobs | 用户只需要"今天最该拍什么"，默认界面必须极简 |
| Ilya | 投数据闭环，让系统从反馈中学习 |
| Karpathy | 先 contract 化，LLM 不直接做最终排序 |

---

## 5. Phase 2 — 30 人 Beta 产品化（M3-M5）

**前提**：Phase 1 Gate 通过。否则不启动。

**目标**：从「能跑通」升级到「能稳定支撑 30 人重复使用并收费」。
Naval 视角：先证 specific knowledge，再加杠杆。

### 5.1 必做（按优先级排序）

| # | Deliverable | 备注 |
|---|---|---|
| P2-1 | 完整视频生成链路（Kling + Seedance image-grounded video） | 不做完整 60s 合成，先做单镜头视频 |
| P2-2 | 锚点三视图（仅当 P1 用户真的复用了才升级） | 否则保留单图 |
| P2-3 | 单 Tab 的 `/topics` 雷达（60s 热搜 + 新榜，二合一） | 不做 6 Tab |
| P2-4 | 浅分析 + 深分析的 4 层渐进 UX | 砍到 2 层（浅 + 深进画布） |
| P2-5 | 配额 + 基础付费（freemium ¥0 / Pro ¥39） | 暂不做 Team |
| P2-6 | TTS（火山豆包，仅当 Phase 1 用户提出强需求） | 否则推到 Phase 3 |
| P2-7 | 字幕（从 dialogue 直接出 SRT，不做时码精修） | |
| P2-8 | 最小 BGM 推荐（关键词 → CC0 库） | 不做 ducking |
| P2-9 | 简单 ffmpeg 合成（多镜头 + 字幕，无 BGM 也可发布） | |
| P2-10 | 25 个核心事件埋点（events 表） | Metabase 暂不部署 |
| P2-11 | 30 人 Beta 招募 + 反馈通道 | |

### 5.2 仍然不做

- `/admin` 完整后台（手 SQL 查 events 表即可）
- `/me/dashboard`（Phase 3 才考虑）
- Agent 5 触发器（最多 1 个：node 失败时的恢复建议）
- B2B 报告 / marketplace / API
- 多租户 / Team 套餐
- OAuth 一键发布

### 5.3 Gate（进入 Phase 3 的条件）

| 指标 | 通过线 |
|---|---:|
| 30 人 Beta 注册 | ≥ 30 |
| Day 1 完成首条 | ≥ 40% |
| 14 天留存 | ≥ 25% |
| 7 天人均创作 | ≥ 3 条 |
| 单条 60s 完整成片成本 | < ¥15 |
| 锚点跨 run 复用率 | ≥ 60% Beta 用户 |
| 至少 5 人付 ¥39/月 | ≥ 5 |

不通过 → 不扩规模，回到产品深度优化。

---

## 6. Phase 3 — 资产复利与商业化（M6-M9）

**前提**：Phase 2 Gate 通过。

**目标**：从「30 人重复用」扩到「300 人付费用」。同时验证 Buffett 视角下的护城河：
**学习闭环是否真的让系统随用户沉淀变更聪明？**

### 6.1 候选投入（按 Phase 2 数据决定优先级）

- `/me/dashboard` 4 模块（本月 / 趋势 / 成本 / 复用）
- `/admin` 运营仪表盘（8 KPI + 漏斗 + 错误聚类）
- Metabase + readonly Postgres
- 赛道索引私有知识库 UI（用户可编辑）
- 创作者雷达订阅
- 模板库 + 「拿同款」复刻飞轮
- OAuth 一键发布抖音 / 小红书
- 多人协作 / Team 座位
- B2B 报告订阅（仅当 Phase 2 出现自然 B2B 需求）

### 6.2 仍不做（V3 之后）

- 视频审稿流 / 创作者作品集公开页 / 跨语言版本 / 自研模型 / 实时直播创作 / SDK

### 6.3 Gate（成为持续业务的条件）

| 指标 | 通过线 |
|---|---:|
| 付费用户 | ≥ 300 |
| 月留存 | ≥ 40% |
| 单用户 LTV / CAC | ≥ 3 |
| 角色 + 场景资产人均沉淀数 | ≥ 5 |
| 「系统随我使用变得更懂我」用户主观打分 | ≥ 4/5 |

---

## 7. 核心假设清单（每个 Gate 必查）

来自评审：当 Gate 不通过时，不是堆功能，是回这张表找真正错的假设。

| # | 假设 | 验证手段 |
|---|---|---|
| H1 | 用户真的从热点开始（而非自带选题） | Phase 1 行为漏斗 |
| H2 | 浅分析「为什么火」对赛道改写真的有用 | 用户访谈 + 改写采用率 |
| H3 | 赛道改写产物质量足以让用户继续而非弃稿 | 改写 → 进画布转化率 |
| H4 | 锚点跨 run 复用是用户能感知并主动使用的 | 复用次数 / 用户 |
| H5 | 生成质量足以支撑实际发布 | 发布率 / 草稿数 |
| H6 | 单条成本 < ¥15 时 ¥39/月 模型成立 | 成本采集 + 定价测试 |
| H7 | 失败可恢复时用户不流失 | 失败后下一步行动率 |
| H8 | 系统从重复使用中变聪明（复利） | Phase 3 沉淀数据 + 主观打分 |

---

## 8. 资源投入

### 8.1 Phase 0 + Phase 1（2 个月内）

- 1 名全栈工程
- 创始人做产品判断 + 用户访谈
- 设计：仅基础 Tailwind / Radix UI，不做设计系统
- 10 位真实创作者样本

### 8.2 Phase 2（前提：Phase 1 Gate 通过）

- +1 名产品设计师（M3 招到位）
- 保留 1 全栈
- 30 位 Beta

### 8.3 Phase 3（前提：Phase 2 Gate 通过）

- +1 增长 / 内容运营
- 视情况 +1 后端
- 300+ 付费用户

**不建议任何阶段提前投入**：B2B 销售 / 完整 BI / 支付深度建设 / 多人协作 / marketplace / 大规模数据中台。

---

## 9. 与原 `MVP_SCOPE.md` 的关系

`MVP_SCOPE.md` 中以下内容**被本计划替换或推迟**：

- §1 A-F 六大块的一次性 160 人天计划 → 拆为 4 个 Gate 阶段
- §1 E 块 `/topics` 6 Tab → Phase 2 单 Tab，Phase 1 不做
- §1 F 块数据统计中台 → Phase 2 仅埋点，Phase 3 才考虑仪表盘
- §1 C 块 Agent UI 5 触发器 → Phase 2 最多 1 个
- §4.5 商业化验收 → 推迟到 Phase 2
- §6 7 个反共识假设 → 整合为本文档 §7 的 H1-H8

`MVP_SCOPE.md` 中以下内容**保留**：

- §2 V2 砍掉清单（schema 字段 day-1 备好的策略仍合理）
- §5 风险与缓解（多数风险仍存）
- §7 「不要做」清单（与本计划方向一致）
- §8 沿用比例表（OpenRHTV / toprador / ACMM 的复用策略）

---

## 10. 最终判断

六位评审从不同视角得出相同结论：

- **Buffett**：观察票，不重仓。先证复用与单位经济。
- **Elon**：先造发动机，不建火星城市。6 周白痴指数验证。
- **Naval**：先找 specific knowledge，再加代码与媒体杠杆。
- **Jobs**：MVP 是 iPod，不是早期 PC。一句话定位。
- **Ilya**：learning loop 比 scale 重要。先证压缩，再扩。
- **Karpathy**：先稳 contract，再做产品。march of nines 从 80% boring reliability 开始。

合成行动：

```text
Phase 0  稳 contract        →  下游不在沙地上盖楼
Phase 1  6 周验证发动机     →  证明用户会重复使用
Phase 2  30 人 Beta 产品化  →  证明留存与单位经济
Phase 3  资产复利与商业化   →  证明系统随使用变聪明
```

**每个阶段过 Gate 才进下一步。不通过就停，回 §7 找错的假设，不堆功能。**
