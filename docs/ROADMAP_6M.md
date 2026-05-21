# Cascade · 6 个月开发路线图

**Document Status**: Roadmap v0
**Date**: 2026-05-18（D+0）
**Target Launch**: 2026-11-18（D+183 / M6 末）
**Related**: `PRODUCT_VISION.md` · `MVP_SCOPE.md` · `CANVAS_DESIGN.md` · `TOPIC_TO_CREATION_PIPELINE.md`

---

## 0. 总览

```
M0      M1          M2            M3            M4              M5          M6
│       │           │             │             │               │           │
D+0     D+30        D+60          D+90          D+120           D+150       D+180
│       │           │             │             │               │           │
准备 → 基建月 → 锚点+视频月 → 音频+剪辑月 → Agent+工坊月 → 内测打磨月 → 公测发布
        │           │             │             │               │           │
        +设计师面试  +设计师在岗   +M2 末锚点 spike  M4 末锚点验收  Beta 30 人  Pro 上线
                                                                              ▲
                                                                              D+183
                                                                            Launch
```

---

## 1. 招人节奏

| 时间 | 角色 | 来源 | 是否必需 |
|---|---|---|---|
| **D-30 ~ D+0** | 创始人个人品牌内容铺垫（推特/小红书） | 自己 | 必需 |
| **D+0 ~ D+45** | 全程招聘**产品设计师**（UI/UX） | 推特 + 同行 + 设计平台 | M3 前必须到岗 |
| **D+0**（已有） | 创始人 / 合伙人 1（工程） | 已经在岗 | — |
| **D+60** 决策点 | 如果设计师没到岗，启动外包设计 | 外包 / 朋友 | Backup |
| **D+120 ~ D+150** | 招 1 名运营 / 增长 | 推特 + 创业社区 | M6 公测前 |

---

## 2. M0 · 准备月（D-30 ~ D+0，本月前）

> 这是 MVP 正式启动前的"暖身月"，不计入 6 个月工时。

### 关键活动

- ✅ 完成 5 份产品文档（已完成）
- 🔄 创始人在推特 / 小红书发布"我在做 Cascade"预热内容，每周 2-3 条
- 🔄 注册产品域名 + 申请商标（建议尽快）
- 🔄 产品设计师招聘启动（D-30 就开始挂出去）
- 🔄 Dev 环境准备：选定云厂商（阿里云/腾讯云/AWS）、买域名、Cloudflare 接入
- 🔄 与 toprador 原作者（即创始人自己）确认代码迁移授权细节、脱敏清单
- 🔄 注册必需的 API key：
  - 火山引擎（豆包 LLM + TTS）
  - Apimart / Google Gemini（image gen）
  - Kling 开放平台
  - Seedance / 即梦
  - 新榜（如果走 Pro 数据源）
  - Vercel / Fly.io / Railway（部署）
  - Stripe / 支付宝沙箱

### M0 出口标准

- [ ] 5 份文档评审通过
- [ ] 产品设计师有 ≥ 5 个候选 + 1-2 个二轮在谈
- [ ] 所有外部 API key 已申请、能跑 hello world
- [ ] 域名 + Cloudflare + 仓库初始化

---

## 3. M1 · 基建月（D+0 ~ D+30）

**主题**：把所有"已有代码"接通成一个能跑空 run 的 Cascade 后端 + 前端骨架。

### 3.1 周计划（v1 加 hotspot 脱敏）

| 周 | 关键任务 | 验收 |
|---|---|---|
| W1 | toprador 仓库 clone + 脱敏（去 OPPO SSO、内网 LLM、wanyol.com 域）| Flask 服务能在本地起，hello world 路由通 |
| W1 | 60s 服务公网部署到 Fly.io / Railway | `https://60s.cascade.xxx/v2/douyin` 返回数据 |
| W1 | **hotspot 仓库 clone + 脱敏**（去 OPPO 内部依赖 / 去 wanyol 上传） | hotspot sidecar 本地能起 |
| W2 | toprador Flask + MySQL → FastAPI + Postgres 改造 | `analyze_single_video_task` 跑通一条抖音 URL |
| W2 | **hotspot Flask → FastAPI 化 + MySQL → Postgres 迁移** | hotspot 4 张表 Postgres 化 + 数据可入库 |
| W2 | Newrank Node sidecar 化（ACMM 5 文件 + Express + Docker） | `POST /newrank/list-files` 返回数据 |
| W3 | Cascade 后端主服务（FastAPI + LangGraph）框架 | WebSocket 协议跑通，可创建 run（空数据） |
| W3 | Postgres schema：users / projects / runs / nodes / anchors / templates / **hotspot 4 张表 + niche_indices**（含所有商业化字段） | drizzle / alembic 迁移可执行 |
| W3 | **hotspot 定时任务部署**（02:00/06:00/08:00 多时段抓取 60s 热搜 + 新榜数据） | 数据按时入库，可查询 |
| W4 | 前端工程初始化（Vite + React 19 + Zustand + @xyflow/react）| 画布可显示 placeholder 节点 |
| W4 | 用户注册 / 登录（email + Google OAuth via Clerk）| 端到端可走通 |
| W4 | **ColorOS 示例赛道索引种子化**（把 hotspot COLOROS_FEATURE_MAP + SCENARIO_FEATURE_MAP 包装为示例 niche_index） | 注册用户能看到"参考 ColorOS 示例" |
| W4 | **events / daily_metrics / user_funnels 三表 schema + 前端 SDK + 后端 batch 接口**（v2 新增） | 25 个事件可端到端入库 |
| W4 | **Metabase Docker 部署 + Postgres readonly 角色 + 5 个种子 dashboard**（v2 新增） | 创始人可在 Metabase 跑 SQL 查询 |
| W4 | 创始人个人推特/小红书：每周 ≥ 3 条内容 | KOL 关注度积累 |

### 3.2 M1 出口标准（v1 更新）

- [ ] 用户能注册 → 登录 → 看到首页（空状态）
- [ ] 后端能创建一个 run（空 DAG）
- [ ] 前端能 WS 连后端，画布显示
- [ ] toprador 视频分析 API 公网可调用（用 Postman 验证）
- [ ] 60s 热搜 API 公网可调用
- [ ] Newrank sidecar 可调用
- [ ] **hotspot sidecar 可调用，4 张表有数据**（v1 新增）
- [ ] **hotspot 定时任务运行正常**（v1 新增）
- [ ] **ColorOS 示例 niche_index 种子化完成**（v1 新增）
- [ ] **events 表能写入 5+ 种事件，前端 SDK 调通**（v2 新增）
- [ ] **Metabase 部署完成，创始人可登录查询**（v2 新增）
- [ ] 监控基础（Sentry 错误 + 简单访问日志）

### 3.3 风险

- **toprador 脱敏超时**（最高风险）→ 不重写，只做"去 OPPO 配置"，能跑就跑
- **Newrank API key 还没批下来** → 用 ACMM 现成 fixture 跑 dev
- **设计师还没到岗** → 创始人自己出 wireframe（手绘 + Figma 简版）

---

## 4. M2 · 锚点 + 视频生成月（D+30 ~ D+60）

**主题**：差异化锁点（锚点为主角）在产品里**真的能看见**；image-grounded video 跑通。

### 4.1 周计划

| 周 | 关键任务 | 验收 |
|---|---|---|
| W5 | **锚点系统数据层**（anchors 表 + anchor_usage 表 + Python ORM） | 锚点 CRUD API 可用 |
| W5 | Image gen Provider（Apimart + Google Gemini，from OpenRHTV）接入 | 单 prompt → 1 张图返回 |
| W5 | **锚点三视图生成**（character anchor 自动产 front/side/back） | "小张妈妈" 3 张图视觉一致 |
| W6 | **锚点 spike**：用 Google Gemini + Apimart 各跑 20 个测试，对比一致性 | 决定哪家做主力（基于成功率 + 成本） |
| W6 | **场景锚点 + 关键元素描述** | "厨房-早晨" 锚点可生成 + 可编辑 |
| W6 | **宫格图**：character × scene 组合定稿板 | 用户能看到"小张妈妈 + 厨房" 组合图 |
| W7 | Seedance / Kling video gen 接入（from toprador）+ image-grounded 模式 | 上传 firstFrameImage，video 真的复现 |
| W7 | HIERARCHY 规则集成 + 自动锚点路由（OpenRHTV 现有逻辑搬过来） | 创建宫格图自动找父锚点 |
| W8 | **画布锚点节点 UI**（左侧资产库 + 主画布锚点卡片） | 用户能直观看到"在管理一个剧组" |
| W8 | 锚点跨 run 复用（拖入新 run 不重新生成） | usage_count 增加，质量一致 |
| W8 | **锚点效果 M2 末验收**：5 个测试 run，主观打分 | ≥ 85% 视觉一致性 |

### 4.2 M2 出口标准（差异化锁点的关键 gate）

- [ ] 用户能创建一个 character 锚点，三视图视觉一致
- [ ] 跨 2 条 run 复用同一个角色，外观保持一致
- [ ] image-grounded video（with first frame）跑通
- [ ] 宫格图可视化：用户能看到"角色 × 场景"组合
- [ ] **锚点 spike 通过**：M2 末用 5 个真实创作场景，盲评一致性 ≥ 85%
- [ ] 产品设计师**已到岗**（最迟 W8）

### 4.3 风险

- **锚点效果不达标**（差异化崩塌）→ 已规划备选：更倚重 toprador 深度分析 + agent 引导 + 单一 character_reference 字段（即同行方案）
- 但如果到 M3 末锚点还做不出来，产品差异化逻辑要重新评估
- 设计师没招到 → 启动外包，设计稿至少在 M4 前要有

---

## 5. M3 · 音频 + 字幕 + 剪辑合成月（D+60 ~ D+90）

**主题**：60s 视频完整成片闭环跑通。

### 5.1 周计划

| 周 | 关键任务 | 验收 |
|---|---|---|
| W9 | **TTS 接入**（火山豆包 TTS） | script 文本 → mp3 + SRT 时间戳 |
| W9 | TTS 音色选择 UI（Free 3 个 / Pro 10+ 个） | 用户切换音色重生 |
| W10 | **字幕渲染**（toprador subtitle_watermark 扩展，从 dialogue_and_narration 自动生成 SRT） | 字幕可烧入 MP4，样式可配 |
| W10 | **BGM 选取**（关键词 → 素材库选取，复用 toprador AUDIO_LIBRARY） | 自动匹配 BGM，可手动覆盖 |
| W11 | **剪辑合成 pipeline**（ffmpeg server-side：多 clip + 字幕 + TTS + BGM → MP4）| 60s 视频自动合成完成 |
| W11 | 音量 ducking（人声段 BGM 自动降 6-12dB） | 听感不糊 |
| W11 | 一键复制发布包（MP4 路径 + 标题 + 标签 + 封面 → 剪贴板 JSON） | 用户能粘贴到抖音/小红书 |
| W12 | **完整闭环端到端测试**：从抖音 URL → 学习 → 锚点 → 镜头 → 字幕 → TTS → BGM → 合成 → 复制 | 1 条 60s 视频全自动完成 |
| W12 | 成本审计（每条总成本 < ¥15） | 报表 + 调整 freemium 配额 |

### 5.2 M3 出口标准

- [ ] 60s 视频从 input → MP4 全自动闭环（标准模式 ≤ 25 分钟）
- [ ] 字幕与 TTS 时间戳对齐（误差 ≤ 0.3 秒）
- [ ] BGM 自动 ducking 听感正常
- [ ] 一键复制发布包：粘贴到抖音原生应用能识别
- [ ] 单条总成本 ≤ ¥15
- [ ] 设计师产出标准模式 + 闪电模式 Figma 高保真稿

### 5.3 风险

- **火山豆包 TTS 中文质量** → spike 验证；备选腾讯云语音合成
- **BGM 版权** → 仅用 CC0 库；用户协议明确
- **ffmpeg 服务器性能** → 起 dedicated server（不在 serverless 上）
- **设计稿延迟** → 产品设计师工作量预算可能不够，必要时减 UI 复杂度

---

## 6. M4 · Agent + 工坊月（D+90 ~ D+120）

**主题**：把热点 → 选题 → 创作的"工坊"形态做出来，agent 智能弹起 5 触发器全部就位。

### 6.1 周计划（v1 加 hotspot 算法层 + 赛道索引）

| 周 | 关键任务 | 验收 |
|---|---|---|
| W13 | **首页热点轮播**（60s 实时 + **hotspot 综合得分 + 蓝海标签**，5 分钟缓存）| 首页显示 5-10 条实时热点带评分 |
| W13 | **/topics 雷达页 6 Tab**（实时 / 视频爆款 / 飙升 / 创作者 / 蓝海 / AI 专项 + NichePanel） | 6 Tab 切换正常，数据展示正确 |
| W14 | **渐进式四层学习 UX**（hotspot 算法 → AI 翻译 → toprador 深 → 画布 + 状态机） | 用户从卡片走到画布全程顺畅 |
| W14 | **agent tools 全套**（`search_trending` 接 hotspot topic-pipeline + `analyze_trending_item` 含 algo/shallow/deep + niche / creator tools） | LangGraph agent 能调用全部 tool |
| W14 | **赛道索引 UI**（NichePanel 编辑器 + 创建 / 切换 / 复制示例） | 用户能创建并激活自己的赛道索引 |
| W15 | **Agent UI 5 触发器**（modal / bottom sheet / inline 混合） | 5 触发场景在正确时机出现 |
| W15 | **标准模式画布的三闸门**（剧本 / 锚点 / 成片） | 用户审核可通过、可驳回 |
| W15 | **赛道索引影响所有层**（算法层的契合度 / AI 翻译的 howToAdapt / 画布锚点建议都基于激活的赛道） | 切换赛道索引后所有层输出变化 |
| W16 | **闪电模式画布**（进度条 + 缩略图流） | 5 分钟出片体验完整 |
| W16 | **模板库 MVP**（运营手动配 5-10 个模板 + ColorOS 示例 niche_index 作为模板之一） | 用户可用模板快速启动 |
| W16 | **失败处置 UX**（4 选 1 inline 卡片） | 任何节点失败都能恢复 |

### 6.2 M4 出口标准（产品形态完整 · v1 更新）

- [ ] 用户能从首页任一入口（轮播 / 输入框 / /topics）进入画布
- [ ] 三档模式（闪电 / 标准）可切换，数据保留
- [ ] Agent 5 触发器全部就位
- [ ] **算法层（即时）+ 浅分析（3 秒）+ 深分析（30 秒）+ 进画布**四层闭环（v1）
- [ ] **/topics 6 个 Tab 全部展示正确数据**（v1）
- [ ] **用户可创建私有赛道索引 + 看 ColorOS 示例**（v1）
- [ ] **激活赛道索引后，4 层输出（算法 / AI / 锚点建议）都变化**（v1）
- [ ] 5-10 个运营模板可用
- [ ] 任何失败有 4 选 1 恢复路径
- [ ] **锚点验收**（M2 spike 通过的基础上）：5 个真实创作场景跑通

### 6.3 风险

- **5 触发器太复杂** → 砍到 4 个（保留剧本/锚点/成片 + 出错），完成后弹起 V2 再做
- **模板库内容来源** → 创始人 + 设计师手动产 5 个高质量模板（不追多）
- **渐进式 UX 用户体验** → M4 末用 5 位早期内测者验证

---

## 7. M5 · 内测打磨月（D+120 ~ D+150）

**主题**：让 30 位 Beta 用户跑起来 + 修 bug + 调体验。

### 7.1 周计划（v2 加 /admin + /me/dashboard）

| 周 | 关键任务 | 验收 |
|---|---|---|
| W17 | **商业化基础**（freemium / Pro / 配额追踪 / Stripe 接入） | 用户能升级 / 降级 / 配额耗尽引导 |
| W17 | **Beta 邀请系统**（邀请码生成 + 反馈表单 + Slack 群） | 30 个邀请码 ready |
| W17 | **daily_metrics / user_funnels cron 部署**（v2 新增） | 02:30 每日聚合 + 10min 漏斗推进运行正常 |
| W17 | **/admin 内嵌运营仪表盘**（8 KPI 卡片 + 7 天漏斗 + 实时活跃 + 错误聚类）（v2 新增） | 创始人每日打开 /admin 看核心指标 |
| W18 | 第一批 10 位 Beta 用户进入 + 每周 5 个深度访谈 | 收集 ≥ 20 条结构化反馈 |
| W18 | **/me/dashboard 4 模块前端**（本月概览 + 创作趋势 + 成本拆解 + 用过热点+锚点复用）（v2 新增） | 用户可在 /me/dashboard 看到自己的数据 |
| W18 | **RLS 策略 + PII 脱敏视图 + 审计日志 + /admin 鉴权**（v2 新增） | 用户只能看自己的数据；运营访问有审计 |
| W19 | 第二批 10 位 Beta 用户进入 + 反馈迭代 | M2 锚点效果再验证 / 失败处置实战调优 |
| W19 | **性能 + 稳定性专项**（错误恢复 / 断网重连 / 大文件） | 95% 创作完成率 |
| W19 | **Metabase 种子 dashboard 扩充到 10-15 个**（v2 新增） | 财务 / cohort / 收入 / 成本 / 选题转化 / 创作者活跃 等 |
| W20 | 第三批 10 位 Beta 用户进入 + 准备公测 | 30 人都跑起来 |
| W20 | **Onboarding + 帮助文档** | 首次用户 5 分钟内完成首条视频 |

### 7.2 M5 出口标准（v2 更新）

- [ ] 30 位 Beta 用户注册
- [ ] ≥ 40% 在 Day 1 完成首条视频（North Star · 数据来自 events + user_funnels）
- [ ] ≥ 25% 14 天留存（North Star · 同上）
- [ ] 创作完成率 ≥ 95%（数据来自 daily_metrics.run_success_rate）
- [ ] 7 个反共识假设的实验数据全部到位（数据来自 events 聚合）
- [ ] 商业化路径打通（Pro 套餐可买）
- [ ] **/admin 运营仪表盘 8 KPI 卡片全部展示正确数据**（v2 新增）
- [ ] **/me/dashboard 4 模块全部展示正确数据**（v2 新增）
- [ ] **Metabase 创始人可自助查询任意维度**（v2 新增）

### 7.3 风险

- **Beta 用户招不到 30 人** → 创始人个人品牌从 M0 就铺；备选靠朋友圈托关系
- **核心假设没验证** → 数据出来后产品形态要不要紧急调整
- **bug 太多** → 时间预算紧，M5 最后一周专门修 bug

---

## 8. M6 · 公测发布月（D+150 ~ D+180）

**主题**：把内测的好用版本变成"任何人都能用"的公测版本。

### 8.1 周计划

| 周 | 关键任务 | 验收 |
|---|---|---|
| W21 | M5 反馈最终迭代（最重要的 5 个改进） | 产品体验质感跃升 |
| W21 | **法律 / 合规**（用户协议、隐私协议、ICP 备案、版权条款） | 上线必备文件齐全 |
| W22 | **支付**（Stripe 国际 + 支付宝 / 微信沙箱接入） | 可真实付费 |
| W22 | **登录页 + 落地页** 美化 | 首屏转化率 ≥ 5% |
| W23 | **Pro Hunt + 推特 + 小红书发布**（创始人内容铺垫已经 6 个月，账号 1k+ 粉） | 当日新增 ≥ 100 注册 |
| W23 | 第一批付费用户出现 | 验证商业模型 |
| W24 | 第一条爆款（被 Cascade 用户复刻的视频 → 在抖音 10w+ 播放） | 公开案例可宣传 |
| W24 | Public launch 复盘 + V2 roadmap 启动 | M7+ 规划完成 |

### 8.2 M6 出口标准

- [ ] 公开上线，任何人能注册
- [ ] 首日注册 ≥ 100
- [ ] 7 天活跃用户 ≥ 200
- [ ] 第一批付费用户（≥ 5 人）
- [ ] 至少一条用户产出的视频在抖音/小红书 10w+ 播放（北极星指标）
- [ ] 已有 V2 路线图 + M7 月度 plan

---

## 9. 关键 Provider 接入节奏（v1 加 hotspot）

| Provider | M1 | M2 | M3 | M4 | M5 | M6 |
|---|---|---|---|---|---|---|
| **Apimart**（image gen） | spike | 主力 | — | — | — | — |
| **Google Gemini**（image gen） | spike | 备选 | — | — | — | — |
| **Kling**（video gen） | — | 接入 | — | — | — | — |
| **Seedance**（video gen） | — | 接入 | — | — | — | — |
| **doubao 多模态**（视频分析，from toprador） | 接入 | — | — | — | — | — |
| **火山豆包 TTS** | — | — | 接入 | — | — | — |
| **腾讯云 TTS**（备选） | — | — | spike | — | — | — |
| **60s 服务**（toprador） | 部署 | — | — | — | — | — |
| **Douyin_Download**（toprador） | 部署 | — | — | — | — | — |
| **Newrank API** | sidecar | — | — | — | — | — |
| **hotspot sidecar**（v1 新增 · 选题情报中台） | **脱敏 + 部署 + 定时任务** | — | — | **算法层接入 UI + 报告生成** | — | — |
| **Clerk**（auth） | 接入 | — | — | — | — | — |
| **Stripe**（支付） | — | — | — | — | 接入 | 测试 |
| **Sentry / PostHog / Grafana** | 基础 | — | — | — | 完备 | — |

---

## 10. 上线 Checklist（M6 末）

### 10.1 产品

- [ ] 5 份文档与最新代码一致
- [ ] 首页 / 画布 / topics / 项目 / 设置 五个核心页面无 critical bug
- [ ] 移动端 fallback：至少能浏览（不能创作）
- [ ] 友好错误页（404 / 500 / 网络断开）
- [ ] Onboarding：首次注册 → 完成第一条视频流程不超过 5 步

### 10.2 工程

- [ ] 监控完备：Sentry 错误 + Grafana 资源 + PostHog 漏斗
- [ ] CI/CD：push main 自动部署到 staging，手动 promote 到 prod
- [ ] 数据库备份：每日全量 + 每小时增量
- [ ] 灰度发布：能 5%/25%/100% 滚动
- [ ] Feature flag：能在 prod 关掉问题功能不重新部署

### 10.3 商业

- [ ] Stripe 付费跑通（Pro ¥39/月）
- [ ] 配额追踪 + 超额引导
- [ ] 退款流程（手动可处理）
- [ ] 客服邮箱 + 微信群

### 10.4 法律 / 合规

- [ ] 用户协议（含视频分析的版权声明、用户上传内容的责任）
- [ ] 隐私协议（GDPR / 个保法合规）
- [ ] ICP 备案（国内域名必需）
- [ ] 内容安全（用户生成内容审核机制 + 人工兜底）

### 10.5 增长

- [ ] 创始人个人推特 / 小红书账号 1k+ 粉丝
- [ ] Pro Hunt 发布材料齐全（截图 / GIF / 文案）
- [ ] 第一批 KOL 体验（包邮 + 给 Pro 一个月）
- [ ] 第一篇技术 / 产品博客（讲 Cascade 的差异化锁点）

---

## 11. 商业化基建占位（M5-M6）

> 这是用户特别要求"先留着可扩展能力"的体现。下列功能 MVP 不启用，但 schema 字段 + 接入 hook 在 M5/M6 内**已经通线**——V2 启用时 0 改造。

| 商业化能力 | day-1 准备 | V2 启用时机 |
|---|---|---|
| **多租户 / Team** | `tenant_id` / `seat_id` 字段 ✅ M1 / 中间件 ✅ M5 | M9（首个 MCN 客户接入） |
| **品牌库** | `projects.brand_pack_json` + `niche_indices.brand_pack` ✅ M1 | M12（首个品牌客户接入） |
| **UGC 模板分成** | `templates.rev_share_pct` + `parent_template_id` ✅ M1 / 计费中间件 hook ✅ M5 | M10 |
| **"拿同款"复刻** | `runs.parent_run_id` ✅ M1 | M10 |
| **关键词订阅推送** | `keyword_subscriptions` schema 草案 ✅ M4 | M9 |
| **数据回流（trending 复盘）** | `runs.trending_source_meta` + `hotspot_snapshot` 字段 + 埋点 ✅ M4（v1） | M12 |
| **API 开发者** | `api_keys` 表草案 + rate-limit 中间件 ✅ M5 | V3 |
| **品牌词监控** | `brand_monitor` schema 草案 ✅ M5 | M12（B2B 单促发） |
| **关键词广告位** | `hot_search_snapshot.sponsored_by` 字段 ✅ M4（v1） | V3（DAU 足够） |
| **行业垂类雷达** | `niche_indices.vertical_tag` 字段 ✅ M1（v1） | M9 |
| **赛道索引市场**（v1 新增） | `niche_indices.visibility` / `price_fen` / `share_count` ✅ M1 | V2 |
| **创作者雷达升级**（v1 新增） | hotspot ops-account-radar 算法 ✅ M1 / UI 分层 ✅ M4 | V2 |
| **运营报告订阅**（v1 新增） | hotspot 已有 HTML 报告生成 ✅ M1 / UI 接入 ✅ M5 | V1.5 |

**核心承诺**：MVP 上线后**任何商业化扩展都不需要改 schema，只需要加 UI**。

---

## 12. V2 预告（M7-M12）

虽然 MVP 是 M6 末，但 V2 节奏也要预先规划：

| 月 | V2 主题 | 关键交付 |
|---|---|---|
| **M7** | 复盘 + 迭代 | M6 数据复盘 → 哪些假设错了 → 调整 |
| **M8** | 精修模式 + 手动模式 | 完整 React Flow 画布 + 自由画布 |
| **M9** | MCN / Team 套餐 + 关键词订阅 | 第一批 MCN 客户接入 |
| **M10** | UGC 模板市场 + "拿同款"飞轮 | 创作者经济 |
| **M11** | 中长视频（1-3 分钟）+ 章节层 UI | 视频长度扩展 |
| **M12** | 数据回流 + 复盘 + 品牌词监控（B2B 触发） | 产品 → 平台演化 |

---

## 13. 关键决策点（必须按时回答）

| 时间 | 决策 | 主要影响 |
|---|---|---|
| **D+0** | 全力以赴 MVP，不接咨询/外包 | 资源专注 |
| **D+15** | 设计师 1 轮 / 2 轮候选确定 | M3 招到的概率 |
| **D+45**（M2 中） | 锚点 spike 中期检查：效果如何 | 差异化锁点是否站得住 |
| **D+60**（M2 末） | **锚点最终验收**：达不达 85% 一致性 | 如不达，紧急调整 PRODUCT_VISION |
| **D+90**（M3 末） | 单条成本审计 | 调 freemium 配额或换 provider |
| **D+120**（M4 末） | 产品形态完整度 review | 决定 M5 招不招运营 |
| **D+150**（M5 末） | 30 位 Beta 数据出 | North Star 数据 → 决定公测是否如期 |
| **D+180**（M6 末） | 公测发布 | 全部就位 / 推迟 1-2 周 |

---

## 14. 应急预案

### 情况 1：M2 末锚点效果不达标

- 立即降级方案：锚点不做"主角"，回退到"上传 character_reference" 字段（同行方案）
- PRODUCT_VISION 紧急调整差异化叙事，转向"工坊体验" + "热点工坊"作为锁点
- MVP_SCOPE C 部分（工坊体验）提优先级

### 情况 2：M3 末成本超 ¥15

- 优先砍 BGM（自己用 CC0 库 + 节奏算法选）
- 视频生成降到 360p（牺牲画质保 margin）
- freemium 配额降到 1 条/月

### 情况 3：M5 末 30 人 Beta 数据不达 North Star

- 不公测，推迟 1 个月
- 集中资源迭代最大短板（基于访谈）
- 必要时找早期投资人/导师/KOL 站台

### 情况 4：M6 末公测发布反响不及预期

- 不慌，对标 OpenAI / Anthropic 的"长期下注"路径
- 继续推内容、修产品、补功能
- 6 个月再次评审是否产品方向需要 pivot

---

## 15. 与其他文档的同步

任何 milestone / 工时 / 招人节奏的变更，**必须**同步：
- `PRODUCT_VISION.md` §9 路线图
- `MVP_SCOPE.md` §9 月度 milestones 快查

任何范围变更，**必须**同步：
- `MVP_SCOPE.md` §1 必做清单 / §2 V2 砍掉清单

---

*本文档是 6 个月 ship MVP 的作战图。每月末 review 一次，必要时调整。*
