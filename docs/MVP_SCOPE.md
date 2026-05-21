# Cascade · 6 个月 MVP 范围定义

**Document Status**: Scope v0
**Date**: 2026-05-18
**Owner**: 创始人 + 工程
**Related**: `PRODUCT_VISION.md` · `CANVAS_DESIGN.md` · `TOPIC_TO_CREATION_PIPELINE.md` · `ROADMAP_6M.md`

---

## 0. MVP 定义

> **6 个月内（M6 末），1–2 人团队 + 1 名招聘中的产品设计师，向外部 Beta 创作者交付一个能完成"从抖音热搜话题 → 60s 完整成片（画面+字幕+TTS+BGM）→ 复制发布包到抖音"的产品级体验。**

**成功标准 = North Star**：
- ≥ 30 位 Beta 创作者注册
- ≥ 40% 在 Day 1 完成首条视频
- ≥ 25% 14 天留存
- 人均 7 天内 ≥ 3 条重复创作

---

## 1. MVP 必做清单（4 大块 × 14 个 deliverable）

### A · 基础设施层（M1）

| # | Deliverable | 工时 | 验收 |
|---|---|---|---|
| A1 | toprador 脱敏 + 公网部署（Flask + MySQL → Postgres） | 5d | 视频分析、Kling、Seedance 接口可用 |
| A2 | 60s 服务公网部署 + Cascade 后端代理 | 0.5d | `/api/trending/realtime?platform=dy` 返回有效数据 |
| A3 | Newrank Node sidecar（包 ACMM 现成 TypeScript） | 2d | `/api/trending/deep` 4 平台数据可用 |
| A4 | Cascade 后端主服务（FastAPI + LangGraph） | 5d | WebSocket 协议跑通，可创建 run |
| A5 | 用户系统 + 项目层 + Postgres schema（含商业化字段 day-1） | 3d | 登录、创建项目、跨 run 锚点复用基础打通 |
| A6 | 前端工程 + 画布基础（React Flow + Zustand from OpenRHTV） | 3d | 标准模式画布可显示节点 |

### B · 创作能力层（M2-M3）

| # | Deliverable | 工时 | 验收 |
|---|---|---|---|
| B1 | **锚点系统**（character / scene / grid，含三视图 + 风格定稿板） | 12d | 用户能创建小张妈妈 + 厨房锚点 + 宫格图 |
| B2 | Image gen 接入（Apimart + Google Gemini，from OpenRHTV） | 0.5d | image-grounded video 可用 |
| B3 | 视频生成（Kling + Seedance，from toprador） | 0.5d | image-grounded video 可生成 |
| B4 | TTS 接入（火山豆包） | 3d | script 文本可一键生成配音 + 时间戳 |
| B5 | BGM 选取（关键词 → 素材库，BGM_LIBRARY from toprador） | 2d | 自动选 BGM，可手动覆盖 |
| B6 | 字幕渲染（从 script.dialogue_and_narration 直接生成 SRT，from toprador subtitle_watermark） | 2d | 字幕烧入合成成片 |
| B7 | 剪辑合成（ffmpeg server-side，扩展 toprador video_compose） | 5d | 多 clip + 字幕 + TTS + BGM → 单个 MP4 |

### C · 工坊体验层（M4）

| # | Deliverable | 工时 | 验收 |
|---|---|---|---|
| C1 | **首页三入口**（轮播 + 输入框对话 + /topics 独立页） | 3d | 三入口都能进入画布 |
| C2 | **渐进式三段学习 UX**（浅 → 深 → 画布） | 5d | 用户从 trending 卡片走到画布全程顺畅 |
| C3 | **Agent UI 5 触发器**（modal / bottom sheet / inline 混合） | 5d | 5 触发场景都按设计弹起 |
| C4 | 标准模式画布（剧本/锚点/镜头/合成/发布 5 节点 + 闸门） | 5d | 三闸门可审核可驳回 |
| C5 | 闪电模式画布（进度条 + 缩略图流） | 2d | 5 分钟出片体验 |
| C6 | 模板库 MVP（运营手动配 5-10 个模板 + "用模板"流） | 4d | 用户可用模板快速启动 |
| C7 | 失败处置 UX（4 选 1） | 2d | 任何节点失败都能恢复 |
| C8 | 复制发布包（MP4 + 标题 + 标签 + 封面 → 剪贴板） | 1d | 一键复制完成后可去抖音粘贴 |

### D · 上线必备（M5-M6）

| # | Deliverable | 工时 | 验收 |
|---|---|---|---|
| D1 | 商业化基础（freemium ¥0 / Pro ¥39 / Team 预留） | 3d | 配额追踪、超额引导、Stripe 接入或类似 |
| D2 | 关键监控（生成成功率 / 用户漏斗 / cost / quota） | 2d | Grafana / PostHog / Sentry 三件套 |
| D3 | 内测邀请系统（邀请码 + 反馈通道） | 1d | 30 个邀请码可分发 + 反馈表单 |
| D4 | 性能 + 稳定性（错误恢复、断网重连、大文件） | 5d | 95% 创作完成率 |
| D5 | E2E 测试 + Beta 用户引导（onboarding + 帮助文档） | 4d | 首次用户 5 分钟内完成第一条视频 |

### E · 选题情报中台（hotspot 整合 · v1 新增）

| # | Deliverable | 工时 | 验收 |
|---|---|---|---|
| E1 | hotspot 仓库脱敏 + 公网部署（Flask → FastAPI 化、去 OPPO 内网依赖） | 5d | hotspot sidecar 公网可调用 |
| E2 | 4 张表 MySQL → Postgres 迁移 + 定时入库任务（02:00/06:00/08:00 等） | 2d | 60s 热搜 + 新榜数据按时入库 |
| E3 | 9 个 Skills 算法整合到 sidecar（hotsearch 双轨 / newrank 五维 / DNA / 可复刻 / 飙升 / 空位 / 创作者雷达 / 三池 / topic-pipeline） | 3d | `search_trending` agent tool 调用 hotspot pipeline 跑通 |
| E4 | 去 ColorOS 化 + 赛道索引架构（niche_indices 表 + ColorOS 示例种子 + scenario_map 重构）| 5d | 用户可创建私有赛道索引 + 看到 ColorOS 示例 |
| E5 | /topics 雷达页 6 Tab（实时 + 视频爆款 + 飙升 + 创作者 + 蓝海 + AI 专项）+ NichePanel | 4d | 6 个 Tab 数据展示正确 |
| E6 | 首页热点轮播（带 hotspot 评分 + 5min 缓存） | 2d | 首页可见实时热点 + 综合得分 + 蓝海标签 |
| E7 | 卡片渐进式四层 UX（算法 → AI 翻译 → 深 → 进画布） | 5d | 用户可看 4 层、每层可单独进画布 |

### F · 数据统计中台（v2 新增 · 详见 `DATA_DASHBOARD.md`）

| # | Deliverable | 工时 | 验收 |
|---|---|---|---|
| F1 | events / daily_metrics / user_funnels schema + 索引 + 前端 SDK + 后端 `POST /events/batch` | 3d | 25 个核心事件可端到端入库 |
| F2 | 25 个核心事件埋点接入（前端 + 后端，随 A-E 块功能开发同步） | 4d | events 表能看到所有事件 |
| F3 | daily_metrics 聚合 cron + user_funnels 计算 cron | 2d | 每日 02:30 聚合任务正常，漏斗按 10min cron 推进 |
| F4 | Metabase Docker 部署 + Postgres readonly 连接 + 10-15 个种子 dashboard | 2d | 创始人能在 Metabase 看 cohort / 收入 / 成本 |
| F5 | /admin 内嵌运营仪表盘（8 KPI 卡片 + 7 天漏斗 + 实时曲线 + 错误聚类 + 灰度开关） | 4d | 创始人每日打开 /admin 看核心指标 |
| F6 | /me/dashboard 4 模块前端（本月概览 + 创作趋势 + 成本拆解 + 用过热点+锚点复用） | 4d | 用户可在 /me/dashboard 看到自己的数据 |
| F7 | RLS 策略 + PII 脱敏视图 + 审计日志 + /admin 鉴权（Clerk role + IP allowlist） | 3d | 用户只能看自己的数据；运营访问有审计 |

**注**：F 块 C 层（B2B 报告）已包含在 E 块的 hotspot 整合工时里。

### 工时合计（v2 更新 · 含数据统计）

| 阶段 | 工时 | 备注 |
|---|---|---|
| A · 基础 | ~18d | 不变 |
| B · 创作能力 | ~25d | 不变 |
| C · 工坊体验 | ~22d | 不变 |
| D · 上线必备 | ~15d | 不变 |
| E · hotspot 整合 | ~26d | 不变 |
| **F · 数据统计中台（v2 新增）** | **~22d** | A 运营后台 + B 创作者数据中心 + 埋点底座 |
| 测试 + buffer（25%） | ~32d | 同比例放大 |
| **总计** | **~160d ≈ 32 周 ≈ 8 个月** | 比 v1 增 28d；**埋点工作随各阶段同步做，不集中在一段** |

**关键 trade-off（v2 现实校正）**：
- v0 (106d) → v1 (132d) → v2 (160d)
- v2 比 6 个月目标（~132d，1.5 人）多 28d
- **解法 1**：M3 末招到设计师后增加 1 人产能（净 +5 人月）→ 容纳得下
- **解法 2**：F 块的部分功能后置（如 /admin 错误聚类、灰度开关推到 V1.5）
- **解法 3**：埋点 + Metabase 部署 M1 就做，其余 F 块功能跨 M3-M5 分批上线
- **不建议**：F 块整体砍——埋点不做，6 个月后看不清自己赢在哪里输在哪里

**重要 trade-off**：v0（106d）→ v1（132d）看似多 26d，但**没用 hotspot 时从零写算法层 = 额外 +50-70d**。

**净效果**：v1 比"v0 + 自建算法层"省 ~25-45d，且**算法成熟度从 MVP 级跃升到工业级**（OPPO 内部已生产验证）。

**1.5 人全职 × 26 周 = 39 人周 ≈ 总工时**——比 v0 紧（v0 是 31.5 人周）。**M3 招到设计师** + **可能需要把 hotspot 一些非核心 Skill 推到 V2**（如 ops-trending / douhot）。

---

## 2. V2 砍掉清单（schema 已备好）

> 这些是产品讨论确定要做、但 **MVP 不做、V2 启用** 的功能。每项 schema 字段已在 day-1 备好。

| Feature | 关联字段 | V2 启用条件 |
|---|---|---|
| **中长视频（1-3 分钟）** | `chapters` 表已 day-1，UI 不开 | M9-M10 |
| **章节层 UI（开场/中段/高潮/结尾）** | 同上 | M9 |
| **精修模式 + 手动模式** | `mode` enum 已 day-1 包含 | M8 |
| **数据回流 / 复盘** | `runs.trending_source_meta` + `hotspot_snapshot` 已存 | M12+ |
| **OAuth 一键发布抖音/小红书** | 暂无 schema 改动 | V2.5 |
| **关键词订阅推送** | `keyword_subscriptions` 表 V2 加 | M9 |
| **UGC 模板上架 + 创作者分成** | `templates.origin`/`rev_share_pct` 已 day-1 | M10 |
| **"拿同款"复刻飞轮** | `runs.parent_run_id` 已 day-1 | M10 |
| **算法推荐（首页 5 卡片）** | MVP 是运营手动 | V2 |
| **品牌库（Logo/字体/调色板/禁用词）** | `projects.brand_pack_json` + `niche_indices.brand_pack` 已 day-1 | M12+（B2B 客单触发） |
| **多人协作 / 团队座位** | `tenant_id` / `seat_id` 已 day-1 | M12+ |
| **API 开发者生态** | `api_keys` 表 V2 加 | V3 |
| **品牌词监控 + 舆情报告** | `brand_monitor`/`intel_reports` V2 加 | V2.5（B2B 触发） |
| **关键词广告位** | `hot_search_snapshot.sponsored_by` V2 加 | V3（DAU 起来后） |
| **行业垂类雷达** | `niche_indices.vertical_tag` 已 day-1 | V2 |
| **移动端** | 整个前端响应式改造 | V2.5 |
| **赛道索引市场（marketplace）**（v1 新增） | `niche_indices.visibility`/`price_fen` 已 day-1 | V2 |
| **创作者雷达 Pro / Team 升级**（v1 新增） | `account_radar_subscriptions` 表 V2 加 | V2 |
| **运营报告订阅**（v1 新增 · hotspot HTML 报告产品化） | hotspot 已有 HTML 报告生成能力，UI 接入 | V1.5（hotspot 整合后） |
| **hotspot ops-trending / douhot 专项**（v1 新增） | hotspot 已有 Skill，但 MVP 不接 UI | V2 |

---

## 3. V3 砍掉清单

> 这些 MVP **甚至 schema 不需要预留**，等 V3+ 真要做时再设计。

- 视频审稿流（品牌 SaaS）
- 创作者作品集公开页
- 平台版权审查
- AI 配音克隆（用户自己声音）
- 实时直播创作
- 跨语言版本（英文创作）
- 自研视频模型 / 微调

---

## 4. 验收标准（按 Track 拆）

### 4.1 锚点系统（差异化锁点 · 强验收）

- [ ] 用户能创建一个 character 锚点，含三视图（正面/侧面/背面）
- [ ] 三视图必须视觉一致（眼睛颜色、发型、衣着一致）
- [ ] 跨 run 复用：同一个角色在两条不同 run 中外观完全一致
- [ ] 场景锚点：master 定稿图 + 3-5 个关键元素描述
- [ ] 宫格图：character × scene 组合的视觉一致性 ≥ 主观 85%（用户测试盲评）
- [ ] image-grounded video：每个镜头的 first frame 与对应宫格图相似度 ≥ 主观 80%

### 4.2 完整成片闭环

- [ ] 60s 视频从 input 到 MP4 全自动闭环（标准模式 ≤ 25 分钟）
- [ ] 闪电模式 ≤ 5 分钟完成
- [ ] 字幕与 TTS 时间戳对齐（误差 ≤ 0.3 秒）
- [ ] BGM 自动选取 + 音量自动 ducking（人声段降低 BGM 6-12dB）
- [ ] 复制发布包到剪贴板：含 MP4 文件路径 + 标题文本 + tags 列表 + 封面图

### 4.3 热点工坊

- [ ] 首页热点轮播：5 分钟内 60s 刷新一次，至少 5 条
- [ ] /topics 雷达：4 平台 × 12 条 = 48 条卡片可用
- [ ] 浅分析（ACMM）3 秒内返回 whyItHit + howToAdapt
- [ ] 深分析（toprador）30 秒内返回完整 analysis_result
- [ ] 渐进式三段：可任意阶段进画布，可回退
- [ ] Trending 溯源：从 trending 卡片来的 run，画布底部永远显示原视频出处链接

### 4.4 Agent

- [ ] 5 触发器全部在正确时机出现
- [ ] 不在错误时机打扰用户（用户驳回率 ≤ 30%）
- [ ] modal 阻塞期间，用户能看到画布上 agent 正在哪个节点工作（不黑屏）
- [ ] inline 卡片在节点上下方就位，不挡视野
- [ ] bottom sheet 可拖拽收起、二次展开

### 4.5 商业化

- [ ] 免费配额：3 条 60s 视频 / 月
- [ ] 配额耗尽：明确引导升级 Pro
- [ ] Pro 配额：30 条 / 月
- [ ] 节点级成本预估准确（误差 ≤ 20%）
- [ ] 总成本实时累加显示
- [ ] 单次创作中途看到"超免费档预算"软提醒
- [ ] 数据源分层：Free 仅 60s，Pro 解锁新榜
- [ ] 浅分析免费 10 次/天，深分析 Free 1 次/天 / Pro 10 次/天

### 4.6 用户体验

- [ ] 首次用户 5 分钟内完成第一条视频（onboarding 简化）
- [ ] 任何错误都有友好提示 + 恢复路径
- [ ] 断网 → 自动重连 → 状态恢复
- [ ] 浏览器刷新 → 画布状态完整恢复
- [ ] 跨设备打开同一个 run → 状态同步

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 招不到产品设计师（M2-M3） | UI 质量低 → 体验滑坡 | M1 内同步招聘，自己出基础 wireframe；最坏外包 |
| toprador 脱敏耗时超预期 | A1 延迟 → 全链路 push 后 | 把 toprador 当作"已工作"接管，避免重写，仅做 MySQL→Postgres + 去 SSO |
| 锚点一致性效果不达预期 | 差异化锁点失效 | M2 内做 spike，验证 Apimart + Google Gemini 哪个能稳定输出三视图 |
| TTS 中文质量差 | 成片质量崩 | 火山豆包 TTS 是国内最稳的，备选腾讯云语音合成 |
| BGM 版权 | 上线被下架 | 仅用 CC0 库（Free Music Archive / Pixabay Music），用户上传需勾选"我有版权" |
| 视频生成成本超预期 | 单条 > ¥30 | M2 末做成本审计，提前调整 freemium 配额 |
| 抖音/小红书复制粘贴不顺畅 | UX 摩擦 | M4 内做用户测试，验证"复制完真的能粘贴用" |
| 内测 30 人凑不齐 | North Star 数据样本不足 | 创始人个人品牌 + 推特/小红书 内容铺垫从 M1 就开始 |
| 法律风险（toprador 视频分析） | 直接下架 | 用户输入 URL 的视频分析仅用作"学习公式"，不存储原视频 > 24h，明确用户协议条款 |

---

## 6. 实验设计（验证产品 7 个反共识假设）

| # | 反共识假设 | 实验设计 | 成功阈值 |
|---|---|---|---|
| 1 | "画布 + agent" 对个人不是负担 | 比较"标准模式"和"闪电模式"的完成率 | 标准 ≥ 闪电 × 0.7 |
| 2 | "锚点为主角" 用户感受得到差异 | 用户访谈："你觉得这产品和即梦/可灵不同的地方在？" | ≥ 60% 提到角色/场景一致性或剧组概念 |
| 3 | "从抖音 URL 学习" 被市场接受 | "/topics → 深分析 → 进画布"漏斗转化率 | 端到端 ≥ 8% |
| 4 | 三档模式不让用户选择困难 | 用户在入口页停留时间 | < 8 秒 |
| 5 | 三数据源融合用户能消化 | 用户测试问"60s/新榜/toprador 分别是什么" | ≥ 50% 能用人话讲清楚 |
| 6 | "一句话直发" + 5 触发器合适 | Agent 弹起被驳回率 | < 30% |
| 7 | "锚点跨 run 复用"是真实需求 | M4 末发现：60% 以上 Beta 用户复用过同一个角色 | ≥ 60% |

每个假设有具体实验、阈值、采集方式。M5 内测期间收集数据，M6 发布前评审。

---

## 7. 范围保护 / "不要做"清单

明确反对在 MVP 阶段做的事（创始人 + 团队需共同抵制）：

❌ **不做完美的 UI 库**——招到设计师前用基础 Tailwind / Radix UI，M4 才开始定稿 design system
❌ **不做完整的鉴权多层级**（OAuth、SAML、2FA）——MVP 只支持 email + Google 登录
❌ **不做完整的国际化**——纯中文 UI，i18n 框架 V2 加
❌ **不做完整的搜索引擎**（项目搜索 / 锚点搜索）——MVP 是简单 SQL LIKE
❌ **不做完整的图表 / 数据看板**——基础 Grafana / 日志足够
❌ **不接外部 OAuth 发布**（抖音/小红书）——复制发布包路径走通就行
❌ **不做 admin 后台**（除了运营手动配模板的简单 form）
❌ **不做完整的支付**——MVP 接 Stripe 即可，国内支付 V2
❌ **不写 SDK**——API for developers 是 V3 的事

---

## 8. 与原 OpenRHTV / toprador / ACMM 的关系

### 8.1 沿用比例（v1 含 hotspot）

| 模块 | 来源 | 沿用率 |
|---|---|---|
| 画布前端（@xyflow/react + Zustand + WS） | OpenRHTV | **100%** |
| LangGraph agent + DeepAgents | OpenRHTV | **100%** |
| 锚点 HIERARCHY 规则 | OpenRHTV | **100%**（搬到 Python module） |
| Image gen providers（Apimart + Gemini） | OpenRHTV | **100%** |
| 视频分析（多模态 LLM） | toprador | **95%**（脱敏） |
| Kling + Seedance 生成 | toprador | **100%** |
| 剧本生成 | toprador | **90%**（改造 prompt + agent 集成） |
| 字幕水印 + 视频合成 | toprador | **80%**（扩展为完整剪辑合成） |
| 60s 服务 | toprador | **100%** |
| Douyin_Download | toprador | **100%** |
| Newrank trending + topic analysis | ACMM | **100%**（包成 Node sidecar） |
| NichePanel + TopicCard UI | ACMM | **90%**（迁到 Cascade 前端） |
| **hotspot 4 张表 schema** | **hotspot** | **100%**（MySQL → Postgres 字段映射） |
| **hotspot 双轨/五维评分算法** | **hotspot** | **100%**（直接搬） |
| **hotspot 互动 DNA / 可复刻 / 飙升 / 空位** | **hotspot** | **100%** |
| **hotspot 创作者雷达** | **hotspot** | **95%**（去 ColorOS 化） |
| **hotspot topic-pipeline 主题流水线** | **hotspot** | **100%**（直接作为 search_trending 实现） |
| **hotspot 三池过滤 + 葵花宝典风格** | **hotspot** | **85%**（重构为赛道索引架构） |
| **hotspot HTML 报告生成** | **hotspot** | **90%**（V1.5 接入产品 UI） |
| **hotspot ColorOS 功能索引** | **hotspot** | **作为示例种子保留** |
| **hotspot 定时任务（02/06/08:00）** | **hotspot** | **100%** |

### 8.2 新写的部分

- 项目层 + 资产库 schema（Postgres）
- 多租户 + 配额 + 商业化中间件
- 模板库（运营手动 + V2 UGC）
- TTS provider 接入（toprador 没有真 TTS）
- BGM 选取 + 音量 ducking
- 剪辑合成的"多 clip + 字幕 + TTS + BGM" 一体化
- 三入口 + 渐进式**四层**学习 UX（hotspot 算法 → AI 翻译 → 深 → 画布）
- Agent 5 触发器智能弹起
- 锚点为主角的画布形态
- 一键复制发布包
- **赛道索引架构 + niche_indices 表 + UI 编辑器**（v1 新增）
- **hotspot 4 表 + 算法层 + sidecar 部署**（v1 新增）

---

## 9. 月度 milestones 快查

详见 `ROADMAP_6M.md`。

| 月 | 主题 | 关键交付 |
|---|---|---|
| M1 | 基建月 | A1-A6 全部完成，画布能跑空 run |
| M2 | 锚点 + 视频月 | B1-B3 完成，锚点 + image-grounded video 跑通 |
| M3 | 音频 + 剪辑月 | B4-B7 完成，60s 完整成片闭环 |
| M4 | Agent + 工坊月 | C1-C8 完成，三入口 + 三数据源 + 模板库 |
| M5 | 内测打磨月 | D1-D5 + 30 位 Beta 用户 + 反馈迭代 |
| M6 | 公测发布月 | Pro 套餐上线、第一批付费用户、第一条爆款 |

---

## 10. 团队规模与时间表的张力

**当前 1-2 人 × 6 个月 = 6-12 人月，本文 MVP 估计 ~31.5 人周 ≈ 7.5 人月**。

接近边界但不可行。**关键依赖**：
- M3 之前必须招到产品设计师（净加 1 人 = +5 人月余量）
- toprador 脱敏不超时（最大风险）
- 锚点系统效果 M2 末就要 spike 验证（如果不达标，差异化崩塌，要紧急调整 PRODUCT_VISION）

如果 M3 没招到设计师：
- 砍掉 C3（Agent UI 5 触发器精修）→ 只做基础 modal
- 砍掉 C6（模板库）→ V2 再做
- 砍掉精修模式（已经在砍掉列表）

如果锚点效果不达标：
- 不能砍——差异化锁点；改方向（比如更倚重深度分析 + agent 引导）

---

## 11. Beta 招募计划

- **M5 第 1 周**：从创始人个人推特 / 小红书发布"找 30 位个人创作者内测，你的赛道是 X"邀请帖
- **M5 第 2 周**：发出邀请码、收到 30 个 commit
- **M5 第 2-4 周**：30 位用户分批进入，每周访谈 5 个
- **M6 第 1-2 周**：迭代用户反馈
- **M6 第 3 周**：正式公测，引入付费档
- **M6 第 4 周**：Public launch + Pro Hunt + 推特发推

---

*本文档是 6 个月内必须 ship 的范围承诺。任何"我们也要做 XX" 的提案，先来这里登记，由创始人决定是否补入 MVP 或推到 V2 砍掉清单。*
