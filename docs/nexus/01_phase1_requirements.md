# Phase 1 需求合成（6 周验证版 · 工作规格）

**Status**: Draft v1 · 工作规格（非愿景文档）
**Date**: 2026-05-19
**Author**: PM (Alex)
**Authoritative source**: `docs/PHASED_PLAN.md` §4 · 本文件 = 该章节的可执行视图
**Scope budget**: ~21 人天（+25% buffer ≈ 26 人天 ≈ 5-6 周）· 10 位真实创作者
**One-liner**: 证明「热点 URL → 改写 → 草稿 → 复用 → 发布包」单一闭环对真实中文创作者有用且会重复使用

---

## 1. 核心用户故事

唯一保留的闭环（不偏离这条线即可）：

```
粘贴爆款 URL（或选系统精选 5 条之一）
  → 浅分析卡片：whyItHit + howToAdapt
  → 一句话赛道描述
  → 系统改写脚本（dialogue + 镜头切分）
  → 进入最小画布（脚本节点 + 3-5 个镜头节点 + 发布包节点）
  → 1 个角色锚点 + 1 个场景锚点（可跨 run 复用）
  → 导出发布包到剪贴板（标题 / 标签 / 脚本 / 镜头图 URL）
```

### 1.1 用户故事清单

| ID | As a | I want to | So that | 必须可验证 |
|---|---|---|---|---|
| US-1 | 中文个人创作者 | 粘贴一条抖音/小红书爆款 URL（或选首页 5 条精选之一） | 我不需要自己想选题 | 输入框接 URL；同时显示 5 条系统精选热点；点任一条进入下游 |
| US-2 | 同上 | 看到一张「为什么火 + 怎么改」的浅分析卡片 | 我能在 30 秒内判断这条值不值得复刻 | 卡片显示 whyItHit 与 howToAdapt 两段；字段来自 P0 contract；缺失字段有 UI warning |
| US-3 | 同上 | 用一句话描述我的赛道（如「宝妈辅食」） | 系统按我的赛道改写而不是泛泛改 | 单行文本输入；存为 run 上下文；用于改写 prompt |
| US-4 | 同上 | 系统给我一份改写后的脚本（含台词 + 3-5 个镜头切分） | 我有可直接拍/生成的素材 | 输出 markdown 脚本 + 切分镜头列表；用户能审核并继续 |
| US-5 | 同上 | 进入一个极简画布看到脚本节点 + 3-5 个镜头节点 + 发布包节点 | 我能在一个空间里管整条片 | React Flow 渲染上述节点；无 Agent UI 弹起；无模式切换器 |
| US-6 | 同上 | 复用我之前创建过的「小张妈妈」角色锚点和「厨房」场景锚点 | 我下一条片不用重画人和场景 | 锚点跨 run 列表可见；可拖入当前 run；单图引用即可，不做三视图 |
| US-7 | 同上 | 一键复制发布包到剪贴板（标题 / 标签 / 脚本 / 镜头图 URL） | 我能直接去抖音/小红书 App 发布 | clipboard 含 4 字段；用户测试可粘贴到目标 App 输入区 |
| US-8 | 同上 | 在任何失败时看到「下一步」的具体指引 | 我不会卡死不知道做什么 | 每类失败有 UI 可见的恢复路径；无静默失败 |
| US-9 | 同上 | 看到本次创作累计花了多少钱 | 我知道单条成本是否能接受 | 每次 run 显示累计 ¥；超过单 run 上限时阻断并提示 |

### 1.2 单条 run 的体验时长目标

| 阶段 | 目标耗时 |
|---|---:|
| 粘贴 URL → 看到浅分析卡片 | ≤ 30s |
| 输入赛道 → 看到改写脚本 | ≤ 30s |
| 进入画布 → 生成 3-5 张镜头草稿 | ≤ 5min |
| 复制发布包 | ≤ 5s |

---

## 2. 功能清单（P1-1 ~ P1-10）

直接对应 `PHASED_PLAN.md` §4.2，**不增不减**。

- [ ] **P1-1 单一首页**（2d）
  - URL 输入框（接抖音/小红书链接）
  - 单行赛道描述输入
  - 5 条系统精选热点（运营手动配置，**不做雷达 / 不做 6 Tab**）
  - 入口直接进 P1-2，无其它分支

- [ ] **P1-2 浅分析卡片**（2d）
  - 字段：`whyItHit`（为什么火）+ `howToAdapt`（怎么改造，要结合赛道）
  - 数据来源：调 P0 contract 出的 `CascadeAnalysisContract`
  - 必须呈现：置信度、缺失字段 warning、fallback 标记（联动 P1-8）

- [ ] **P1-3 赛道改写**（3d）
  - 输入：浅分析 + 用户赛道一句话
  - 输出：脚本 markdown（dialogue + narration + 3-5 个镜头切分）
  - prompt 模板可迭代，但 schema 固定（下游 P1-4 依赖）

- [ ] **P1-4 最小画布**（4d，**最大单项**）
  - 节点类型仅 3 种：`script` × 1 + `shot` × 3-5 + `publish_pack` × 1
  - **不做** Agent UI 5 触发器（无 modal / bottom sheet / inline 主动弹起）
  - 复用 OpenRHTV 现有 React Flow + Zustand + WS 协议

- [ ] **P1-5 Image 生成接入**（1d）
  - 复用 OpenRHTV 现有 Apimart + Google Gemini 通道
  - 每个 shot 节点可触发一次镜头草稿图生成

- [ ] **P1-6 角色锚点 + 场景锚点的跨 run 复用**（3d）
  - 单图引用即可（**不做三视图**，不做风格定稿板）
  - 1 个 character 锚点 + 1 个 scene 锚点
  - 跨 run 列表可见，可在新 run 中拖入

- [ ] **P1-7 发布包导出**（1d）
  - 剪贴板内容：标题 + 标签 + 脚本 + 镜头图 URL
  - 一键复制；**不接 OAuth**，不调发布 API

- [ ] **P1-8 UI warnings**（2d）
  - 缺失字段：UI 明确标示「字段缺失」
  - fallback 使用：UI 标示「降级数据」
  - 置信度：每条分析卡片显示

- [ ] **P1-9 成本统计与上限**（1d）
  - 每次 run 实时累计 ¥
  - 单 run 上限：硬阻断 + 提示
  - 阈值参考 Gate ¥15

- [ ] **P1-10 10 位真实创作者试用 + 每人 1 次访谈**（2d）
  - 招募渠道：创始人个人推特/小红书
  - 每位用户至少完成 1 次端到端 run
  - 每人 1 次结构化访谈（含 §4 Gate 中「能否一句话说出价值」问题）

**合计：21 人天 + 25% buffer = 26 人天**

---

## 3. 明确的 NOT-DOING 边界

直接复制 `PHASED_PLAN.md` §4.3。**这是执行边界，不是愿望清单。任何 PR 引入下列任一项 = 越界，直接驳回。**

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

**补充：以下 `MVP_SCOPE.md` 内容被 PHASED_PLAN 明确推迟，Phase 1 不做：**

- ❌ A5 多租户 schema（Phase 1 单用户 / 默认 thread 即可）
- ❌ B4 TTS / B5 BGM / B6 字幕 / B7 剪辑合成
- ❌ C3 Agent UI 5 触发器 / C5 闪电模式 / C6 模板库
- ❌ D1 商业化（freemium / Pro / Stripe）
- ❌ E 块 hotspot 整合（4 张表、9 个 Skills、赛道索引架构、创作者雷达、报告）
- ❌ F 块 25 个事件埋点 / daily_metrics / Metabase / RLS

---

## 4. 验收指标（Phase 1 Gate · §4.4）

**这些是上面用户故事的硬验收线。不通过 Gate → 停，回 §7 假设清单查错的假设，不堆功能。**

| # | 指标 | 通过线 | 关联用户故事 | 出处 |
|---|---|---:|---|---|
| G1 | 真实创作者试用 | ≥ 10 人 | US-1..US-9 全链 | 共识 |
| G2 | 完成第一条内容 | ≥ 5 人 | US-7 复制发布包成功 | 共识 |
| G3 | 一周内回来做第二条 | ≥ 3 人 | US-6 锚点复用 | 共识 |
| G4 | 用户能一句话说出价值 | ≥ 2 人说「它帮我把爆款变成我的内容」 | 整体定位 | Jobs |
| G5 | 单条成本 | < ¥15 | US-9 + P1-9 | Elon / Naval |
| G6 | 热点 → 创作转化率 | ≥ 15% | US-1 → US-7 漏斗 | Elon |
| G7 | 失败时用户知道下一步 | 100% | US-8 + P1-8 | Karpathy |
| G8 | 至少 2 人开始沉淀角色或场景锚点 | ≥ 2 | US-6 + P1-6 | Ilya |

### 4.1 测量方式

| Gate | 测量方式 |
|---|---|
| G1 / G2 / G3 | run 表手 SQL 查（无 Metabase / 无 admin） |
| G4 | P1-10 结构化访谈逐字稿 |
| G5 | P1-9 成本统计累计 |
| G6 | 「点击精选热点或粘贴 URL」到「点击复制发布包」漏斗（手 SQL） |
| G7 | P1-10 访谈 + 失败日志人工核对 |
| G8 | niche-anchor 跨 run 复用计数（DB 查询） |

---

## 5. 现状对照表（OpenRHTV 已有 vs Phase 1 需要）

### 5.1 可直接复用（不写代码）

| 能力 | 现状（OpenRHTV） | Phase 1 用途 |
|---|---|---|
| Director DeepAgent + Gemini | `backend/src/agent/main.py` 已工作 | 复用为改写 / 浅分析的 LLM 调用入口 |
| WS 服务 + 多会话 LRU | `backend/src/agent/server.py` POOL_SIZE=5 | 复用为 run 通信层 |
| SQLite 画布持久化（nodes + edges） | `tools/canvas.py` 已工作 | 复用为画布存储；无需迁 Postgres |
| 节点两阶段状态（node_status / asset_status） | 已有 `reviewing` / `confirmed` + `idle/generating/done/failed/timeout` | 复用为草稿审核 + 生成态 |
| 节点 HIERARCHY 规则 | `tools/canvas.py` HIERARCHY 字典 | 复用：script → image(character/scene) → image(grid) |
| Image gen（Apimart + Google Gemini） | `config.py` 已配置；按节点选择 provider | 直接对应 P1-5 |
| 镜头草稿图节点（image subtype="grid"） | 已实现 | 直接对应 shot 节点 |
| React Flow + Zustand + dagre 自动布局 | `frontend/src/components/Canvas.tsx` | 直接对应 P1-4 画布 |
| ScriptNode / ImageNode / VideoNode / AudioNode | 已实现 | 复用 ScriptNode + ImageNode；本 phase 不需要 VideoNode/AudioNode |
| NodeDetail 审核 / 拒绝 / 反馈 / 重生成 | 已实现 | 复用：失败处置走「驳回 + 反馈」即可，不需要 4 选 1 弹卡 |
| Prompt optimization (LLM 改写 prompt) | 已实现 | 复用为 shot 草稿图重生成的优化能力 |
| Session sidebar / 多 thread 管理 | 已实现 | 直接复用为「我的 runs」入口 |
| S3 上传（镜头图托管） | `config.py` S3_* 字段 | 复用为发布包 URL 生成 |

**结论**：底盘 ≈ 60% 已就位。Phase 1 主要是**接业务上游 + 加 3 个产品视图**，不是重写底盘。

### 5.2 必须新写（gap list）

| Gap | 对应 Deliverable | 备注 |
|---|---|---|
| P0 `CascadeAnalysisContract` 类型 + `normalize_analysis_result()` adapter | 前置（Phase 0） | **Phase 1 严格依赖 Phase 0 Gate 通过**。Phase 0 不过 → Phase 1 不能启动 |
| URL 输入接入抖音/小红书爬取（或 mock 数据流） | P1-1 / P1-2 | **未确认**：toprador 是否已脱敏可用？若否，Phase 1 可先用 fixture corpus 跑（见 §6 开放问题） |
| 「5 条系统精选热点」配置入口 | P1-1 | 运营手配置（hardcoded JSON 或简单 admin 接口都可，**不做 6 Tab 雷达**） |
| 浅分析卡片组件（whyItHit + howToAdapt + warnings） | P1-2 / P1-8 | 新前端组件；后端 LLM 调用包一层 |
| 单行赛道输入 + 存入 run 上下文 | P1-3 | 极简 input；存 SQLite |
| 赛道改写 prompt + 输出 schema | P1-3 | 新 prompt 文件；输出经 parser → script 节点 description |
| 发布包节点类型 `publish_pack` | P1-4 | 新节点类型；HIERARCHY 加一行 |
| 跨 run 锚点列表（list + 拖入当前 run） | P1-6 | 新 API：`list_anchors_by_user`；前端新组件 |
| 发布包导出（clipboard 拼装 + 复制） | P1-7 | 前端 navigator.clipboard.writeText |
| 成本统计：每 LLM / image-gen 调用打点 + run 累计 | P1-9 | 后端 middleware；前端展示 |
| 单 run 成本上限阻断 | P1-9 | 后端拦截 + 前端提示 |
| 失败 → 下一步指引（每类失败定义恢复路径） | P1-8 | 后端 error taxonomy + 前端文案表 |
| 10 人用户招募 + 访谈 | P1-10 | 创始人执行，非工程 |

### 5.3 现在已经存在但 Phase 1 不用的能力（不要删，但也不要扩）

- VideoNode / AudioNode 组件 → Phase 1 不出现
- canvas-manager subagent 拓扑推理 → 可复用，但画布只有 3 类节点，必要性低；若简化路径更省工时则砍掉
- 节点位置同步（sendPosition） → 可保留，零成本

---

## 6. 开放问题（标记给创始人裁决）

| # | 问题 | 影响 | 建议默认值（若无回复） |
|---|---|---|---|
| Q1 | **toprador 视频分析模块是否已脱敏可调用？** Phase 0 contract 测试需要 20 条真实样本 raw `analysis_result`。若不可用，Phase 0 是否改用人工标注 fixture？ | 高（卡 Phase 0 启动） | 默认走人工 fixture，绕开 toprador 脱敏延迟 |
| Q2 | **「5 条系统精选热点」由谁选？** 创始人手挑 / 简单脚本拉 60s 服务 / mock？ | 中（卡 P1-1） | 创始人每周一手挑 5 条写入 JSON，零工程成本 |
| Q3 | **「赛道一句话」是结构化（dropdown）还是纯文本？** | 低 | 纯文本，让用户自由表达；Phase 2 再考虑结构化 |
| Q4 | **「3-5 个镜头」的具体数是 3 / 4 / 5 哪个？** 影响改写 prompt 与画布默认布局 | 低 | 默认 4 个；改写 prompt 留可调参数 |
| Q5 | **单 run 成本上限是 ¥15 硬卡，还是 ¥10 软提示 + ¥15 硬卡？** | 低 | ¥10 软提示 + ¥15 硬阻断 |
| Q6 | **10 位创作者的赛道分布要不要约束？** 全宝妈 vs 跨 5 个赛道，对 G6 转化率结论影响很大 | 中 | 至少覆盖 3 个不同赛道；避免单一赛道证伪/证实偏差 |
| Q7 | **失败时「下一步指引」的 UI 形态？** 内嵌 inline 文案 / toast / modal？ | 低 | inline 文案（不弹卡，避开 Agent UI 5 触发器红线） |
| Q8 | **锚点复用 G8「至少 2 人开始沉淀」如何判定「开始」？** 创建即算 / 跨 run 用过 1 次才算？ | 中（Gate 判定） | 跨 run 用过 1 次才算「沉淀」，比「创建」更强信号 |
| Q9 | **6 周时钟从哪天起算？** Phase 0 Gate 通过日 / Phase 1 启动 PR 第一条 / 招到第一位用户？ | 低 | Phase 0 Gate 通过日为 T=0 |
| Q10 | **Phase 1 期间允许哪种程度的产品文案/视觉打磨？** 还是「Tailwind 默认 + Radix」一行不超 | 低 | 默认值 + 极简打磨；M2 招到设计师再统一升级 |

---

## 7. 附录：本文件与上游文档的关系

| 上游文档 | 在本文件中的角色 |
|---|---|
| `PHASED_PLAN.md` §4 | **本文件的权威源**。任何冲突以 PHASED_PLAN 为准 |
| `PHASED_PLAN.md` §7 假设清单 H1-H8 | Gate 不通过时回查的根因表（不在本文件复述） |
| `PRODUCT_VISION.md` | 仅用于「持续校准定位」；其中 § 3.5 三档模式 / § 3.2 5 触发器 / § 4 hotspot 等内容在 Phase 1 **明确不做** |
| `MVP_SCOPE.md` §1 + §5 | §1 大部分被 PHASED_PLAN 砍掉；§5 风险仍生效（特别是 toprador 脱敏 / 锚点效果 / 法律风险） |
| `TOPIC_TO_CREATION_PIPELINE.md` | Phase 1 仅用其「URL → 浅分析」单链；hotspot 算法层 / 4 数据源 / 赛道索引架构 **不做** |
| `README.md` + 实际代码 | §5 现状对照表的依据 |

---

*本文件是 Phase 1（6 周验证）的工作规格，不是愿景文档。任何新增需求先来 §3 NOT-DOING 清单核对，再来 §2 P1-x 列表登记。**任何引入 §3 禁列项的 PR 直接驳回**。*
