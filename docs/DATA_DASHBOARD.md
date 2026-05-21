# Cascade · 数据统计 / 数据看板设计

**Document Status**: Dashboard v0
**Date**: 2026-05-18
**Owner**: 创始人 + 工程
**Related**: `PRODUCT_VISION.md` §7 / `TOPIC_TO_CREATION_PIPELINE.md` §8 / `MVP_SCOPE.md` §1.F / `CANVAS_DESIGN.md` §7

---

## 0. 摘要

Cascade 数据统计模块分 **3 层**，对应不同读者：

| 层 | 名字 | 读者 | 路径 | 实现形态 | MVP |
|---|---|---|---|---|---|
| **A** | 运营管理后台 | 创始人 / 运营 / 财务 | `/admin/*` + Metabase | **混合**：Metabase 直连 Postgres 做深度查询 + /admin 内嵌运营仪表盘做日常 KPI 卡片 | ✅ |
| **B** | 创作者数据中心 | 单个创作者 | `/me/dashboard` | 独立 Cascade 页面，中等密度（创作趋势 + 成本拆解 + 用过的热点 + 锚点复用率） | ✅ |
| **C** | B2B 运营报告 | MCN / 品牌客户 | hotspot HTML 报告链接 | 已通过 hotspot 整合覆盖（ops-insight / ops-topic-pick / ops-account-radar） | V1.5 |

**核心承诺**：3 层共享同一个**事件埋点底座**（`events` 表 + `daily_metrics` 聚合表 + `user_funnels` 漏斗表），不重复采集，schema 一次设计支撑长期演化。

---

## 1. 设计原则

1. **埋点先行**：M1 就把事件 SDK 接好，后续随时能补维度
2. **聚合表与原始表分离**：原始 events 永不删（审计 + 日后挖掘）；daily_metrics 加速查询
3. **隐私 day-1**：B 层用 RLS（Row Level Security），用户只看自己的；A 层有独立 admin 角色
4. **A 层混合策略**：用 Metabase 解决"任意切片"需求，省掉 80% 自建 BI 页面工时；/admin 只做最常看的 KPI 卡片
5. **B 层中等密度**：MVP 不追求"专业数据分析师"体验，**只放创作者能直接行动的指标**
6. **C 层不重写**：hotspot HTML 报告产品化即可，不另外做 dashboard
7. **不连第三方播量**：MVP 不接抖音/小红书 OAuth，所以数据回流 V2 才做（PRODUCT_VISION §3.3 已确认）

---

## 2. 事件埋点底座（A/B/C 共用）

### 2.1 核心 schema

```sql
-- 原始事件表（永久保留，全量）
CREATE TABLE events (
  id              BIGSERIAL PRIMARY KEY,
  user_id         UUID,                 -- nullable（匿名访客）
  tenant_id       UUID,                 -- 多租户
  session_id      VARCHAR(64),          -- 客户端生成
  event_name      VARCHAR(100) NOT NULL,
  properties      JSONB NOT NULL DEFAULT '{}',
  occurred_at     TIMESTAMPTZ NOT NULL, -- 客户端时间
  received_at     TIMESTAMPTZ DEFAULT NOW(),  -- 服务端时间
  
  -- 客户端上下文
  client_ip       INET,
  user_agent      TEXT,
  referrer        TEXT,
  utm_source      TEXT,
  utm_campaign    TEXT,
  
  INDEX (user_id, occurred_at DESC),
  INDEX (event_name, occurred_at DESC),
  INDEX (tenant_id, occurred_at DESC) WHERE tenant_id IS NOT NULL
);

-- 按天聚合（为常用 admin 查询加速）
CREATE TABLE daily_metrics (
  date            DATE NOT NULL,
  metric_name     VARCHAR(100) NOT NULL,
  dimension_key   JSONB NOT NULL DEFAULT '{}',  -- e.g. { tenant_id, mode, niche_id }
  value           BIGINT NOT NULL DEFAULT 0,
  computed_at     TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (date, metric_name, dimension_key)
);

-- 用户漏斗状态
CREATE TABLE user_funnels (
  user_id           UUID NOT NULL,
  funnel_stage      VARCHAR(50) NOT NULL,
  -- signup | activated | first_create | first_complete | repeat_create_d7 | retained_d14 | paid
  reached_at        TIMESTAMPTZ NOT NULL,
  context_properties JSONB DEFAULT '{}',
  PRIMARY KEY (user_id, funnel_stage)
);

-- 数据保留策略（V2 上线时按需引入）
-- events 表 ≥ 13 个月做归档（拆 archive 表）
-- daily_metrics 永久保留（数据量小）
```

### 2.2 事件目录（MVP 必埋的 25 个事件）

| Category | event_name | properties | 触发位置 |
|---|---|---|---|
| **生命周期** | user_signup | source, referrer, utm_* | 注册成功 |
| | user_activated | first_action | 首次有意义操作 |
| | user_session_start | — | 每次进入产品 |
| | user_session_end | duration_ms | 退出/离开 |
| **热点工坊** | topic_card_view | source_type, opus_id, platform, rank | trending 卡片展现 |
| | hotspot_score_visible | total_score, dna, zone, replicability | 算法层数据呈现 |
| | shallow_analysis_triggered | opus_id, niche_index_id, cost_fen | ACMM 浅分析触发 |
| | deep_analysis_triggered | opus_id, cost_fen | toprador 深分析触发 |
| | enter_canvas_from_trending | trending_source, depth | 从热点进画布 |
| **创作流** | run_created | mode, source, niche_index_id, parent_template_id, parent_run_id | 创建 run |
| | gate_review_completed | gate_type, action, feedback_provided | 闸门审核 |
| | node_failed | node_type, error_code, retry_path | 节点失败 |
| | node_retry | node_type, retry_count, mode (换 prompt/换风格/跳过/重做) | 失败恢复 |
| | run_completed | duration_ms, total_cost_fen, video_count, mode | 整 run 完成 |
| | run_cancelled | abandoned_at_stage | 用户放弃 |
| | publish_pack_copied | run_id | 复制发布包 |
| **资产 / 锚点** | anchor_created | type (character/scene/grid), provider | 锚点创建 |
| | anchor_reused | anchor_id, run_id | 锚点跨 run 复用 |
| | niche_index_activated | niche_id, is_template | 切换激活赛道 |
| | niche_index_edited | niche_id, fields_changed | 编辑赛道索引 |
| **Agent 交互** | agent_triggered | trigger_kind, ui_form (modal/sheet/inline) | agent 弹起 |
| | agent_response_user | trigger_kind, action (accept/reject/feedback) | 用户响应 |
| **商业化** | quota_warning | kind, used, total | 配额预警 |
| | upgrade_clicked | from_tier, to_tier, source_page | 升级 CTA 点击 |
| | paid_conversion | tier, amount_fen, payment_method | 付费成功 |

**实现要点**：
- 前端封装 `track(eventName, properties)` SDK，自动注入 user_id / session_id / utm_*
- 后端 FastAPI 提供 `POST /events/batch` 批量接收（每 5 秒 flush 一次，减少请求数）
- 关键服务端事件（run_completed、paid_conversion）由后端直接写库（不依赖客户端）
- PostHog **可选并行**部署（双写）——免费层 1M events/月够用 6 个月

### 2.3 漏斗定义

```
signup
  ↓
activated（完成 onboarding / 看到首页 / 主动点过一次"创作"）
  ↓
first_create（创建首个 run）
  ↓
first_complete（首个 run 跑到 done）
  ↓
repeat_create_d7（7 天内第 2 条）
  ↓
retained_d14（注册后第 14 天还在用）
  ↓
paid（首次付费）
```

每个 stage 由后端 cron 每 10 分钟扫一遍 events 计算 → 写 `user_funnels`。

### 2.4 daily_metrics 聚合任务

每日 02:30（CST）跑一次 cron，按下表聚合：

| metric_name | dimension_key | value 计算 |
|---|---|---|
| `dau` | `{}` | DISTINCT user_id WHERE event_name='user_session_start' |
| `signup_count` | `{}` | COUNT(*) WHERE event_name='user_signup' |
| `runs_created` | `{mode}` | COUNT WHERE event_name='run_created' GROUP BY mode |
| `runs_completed` | `{mode}` | COUNT WHERE event_name='run_completed' GROUP BY mode |
| `run_success_rate` | `{mode}` | runs_completed / runs_created |
| `avg_run_cost_fen` | `{mode}` | AVG(properties.total_cost_fen) WHERE event_name='run_completed' |
| `node_failure_rate` | `{node_type}` | node_failed / (node_failed + node_success) |
| `gate_approve_rate` | `{gate_type}` | approve / (approve + reject) |
| `trending_to_create_conversion` | `{source_type}` | enter_canvas_from_trending / topic_card_view |
| `anchor_reuse_count` | `{type}` | SUM(anchor_reused) GROUP BY type |
| `paid_conversion_rate` | `{}` | paid / signup（cohort 30 天） |
| `revenue_fen` | `{tier}` | SUM(paid_conversion.amount_fen) GROUP BY tier |

---

## 3. A 层 · 运营管理后台

### 3.1 形态：混合 Metabase + /admin 内嵌仪表盘

```
┌──────────────────────────────────────────────────────────┐
│ A 层 · 运营后台                                            │
│ ──────────────────────────────────────────────────────  │
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────────┐ │
│  │  /admin（内嵌）        │  │  Metabase（独立 BI）       │ │
│  │  ──────────────────  │  │  ────────────────────────│ │
│  │  • 首日 5 核心 KPI     │  │  • 任意 SQL 查询          │ │
│  │  • 7 天用户漏斗       │  │  • 自定义图表 / 仪表盘     │ │
│  │  • 实时活跃曲线        │  │  • 财务分析（成本/利润）   │ │
│  │  • 当前 ARR / DAU     │  │  • 用户 cohort 分析       │ │
│  │  • 错误聚类卡片        │  │  • 内容质量分析（A/B）     │ │
│  │  • 上线 / 灰度开关     │  │  • 实验跟踪              │ │
│  │                      │  │                          │ │
│  │  实时（毫秒级）        │  │  小时级延迟（接 daily_*）│ │
│  │  Cascade 内 React 页 │  │  独立 docker 部署        │ │
│  └──────────────────────┘  └──────────────────────────┘ │
│            ↑                          ↑                  │
│            └──── 共用 Postgres ────────┘                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 3.2 /admin 内嵌运营仪表盘（MVP 必做 8 个核心 KPI 卡片）

```
╔═════════════════════════════════════════════════════════╗
║ Cascade Admin · 运营仪表盘   [今日 / 7天 / 30天]   [⚙]   ║
╠═════════════════════════════════════════════════════════╣
║                                                         ║
║  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   ║
║  │ DAU       │ │ MAU      │ │ 新增      │ │ 付费转化  │   ║
║  │ 142       │ │ 1,250    │ │ 23       │ │ 8.5%     │   ║
║  │ ↑12%      │ │ ↑34%     │ │ ↑5       │ │ ↑1.2pp   │   ║
║  └──────────┘ └──────────┘ └──────────┘ └──────────┘   ║
║                                                         ║
║  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   ║
║  │ 今日 ARR  │ │ 创作成功率│ │ 平均成本  │ │ 毛利率   │   ║
║  │ ¥4,732    │ │ 94%      │ │ ¥13.2/条 │ │ 47%      │   ║
║  │ ↑¥320     │ │ ↑2pp     │ │ ↓¥0.8    │ │ ↑3pp     │   ║
║  └──────────┘ └──────────┘ └──────────┘ └──────────┘   ║
║                                                         ║
║  ─── 7 天用户漏斗 ──────────────────────────────────     ║
║  signup     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 234                   ║
║  activated  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 189 (81%)                  ║
║  first_create ▓▓▓▓▓▓▓▓▓▓ 121 (52%)                     ║
║  first_complete ▓▓▓▓▓▓▓▓ 98 (42%)                      ║
║  repeat_d7  ▓▓▓▓ 47 (20%)                              ║
║  retained_d14 ▓▓ 28 (12%)                              ║
║  paid       ▓ 14 (6%)                                  ║
║                                                         ║
║  ─── 实时活跃曲线（最近 24h） ──────────────────────     ║
║  [实时折线图]                                            ║
║                                                         ║
║  ─── 错误聚类（最近 24h Top 5） ───────────────────       ║
║  1. PROVIDER_FAILED · 12 次 · Seedance · 抖音视频       ║
║  2. RATE_LIMITED · 8 次 · 火山豆包 TTS                  ║
║  3. CONTENT_FILTERED · 4 次 · Apimart                  ║
║  ...                                                    ║
║                                                         ║
║  ─── 灰度 / Feature Flag ────────────────────────       ║
║  □ image-grounded video [当前 25%]  [↑ 提到 50%]        ║
║  □ 渐进式四层 UX  [当前 100%]                            ║
║  □ 创作者雷达 Tab [当前 10%]                             ║
║                                                         ║
╚═════════════════════════════════════════════════════════╝
```

### 3.3 Metabase 部署（深度查询 / 财务）

| 项 | 选择 |
|---|---|
| 部署 | Docker compose（与 Cascade 同 VPC） |
| 数据源 | 直连 Postgres（read-only 角色） |
| 鉴权 | 单独 admin 账户，仅创始人 + 财务（不接 Clerk） |
| 看板模板 | 启动时种子化 10-15 个标准 dashboard（cohort / 收入 / 成本 / 漏斗 / topics conversion / niche 表现 / 创作者活跃） |
| 备份 | Metabase metadata DB 独立备份（不污染 Cascade 主 DB） |

### 3.4 A 层与生产 DB 的安全隔离

- **read-only role**：Metabase 用 `cascade_readonly` 角色，没有 INSERT/UPDATE/DELETE
- **PII 脱敏视图**：通过 `vw_users_anonymized` 等视图屏蔽 email / phone
- **审计**：Metabase 查询日志 → 独立 audit 表
- **/admin 鉴权**：Clerk role-based + IP allowlist（仅创始人 + 运营白名单）

---

## 4. B 层 · 创作者数据中心（/me/dashboard）

### 4.1 路径与定位

- **URL**：`/me/dashboard`（账户菜单第一项）
- **目标**：让创作者**在数据里看到自己变强**，提升留存
- **不包含**：抖音/小红书播量回流（V2 才做）
- **包含**：在 Cascade 内可观察的所有指标（创作量、成本、用过的热点、锚点复用、模板效果）

### 4.2 页面结构（MVP · 4 个核心模块）

```
╔═══════════════════════════════════════════════════════╗
║ 我的数据中心   [本月 / 30天 / 全部]                       ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  ─── 1. 本月概览 ────────────────────────────────      ║
║                                                       ║
║  ┌───────────┐ ┌───────────┐ ┌───────────┐           ║
║  │ 已创作      │ │ 总成本     │ │ 节省时间   │           ║
║  │ 12 条       │ │ ¥156      │ │ ~24h     │           ║
║  │ 配额 12/30  │ │ 平均 ¥13   │ │（vs 手作）│           ║
║  └───────────┘ └───────────┘ └───────────┘           ║
║                                                       ║
║  ─── 2. 创作趋势 ────────────────────────────────      ║
║                                                       ║
║  [30 天创作折线图]                                      ║
║  本周 +3 条（vs 上周 +1）                               ║
║                                                       ║
║  按模式分布：                                          ║
║  ⚡ 闪电  ▓▓▓ 3        平均用时 4 分                   ║
║  🎯 标准  ▓▓▓▓▓▓▓▓ 8   平均用时 22 分                  ║
║  ✨ 精修  ▓ 1          平均用时 1h 12m                  ║
║                                                       ║
║  ─── 3. 成本拆解 ────────────────────────────────      ║
║                                                       ║
║  [饼图]                                                ║
║  • 视频生成（Seedance）¥88 · 56%                       ║
║  • 图像生成（Apimart）  ¥34 · 22%                      ║
║  • TTS 配音            ¥12 · 8%                       ║
║  • 深度分析            ¥10 · 6%                       ║
║  • 浅分析              ¥6  · 4%                       ║
║  • BGM / 合成 / 字幕    ¥6  · 4%                       ║
║                                                       ║
║  ─── 4. 用过的热点 + 锚点复用 ───────────────────────    ║
║                                                       ║
║  我看过的热点：47 条                                    ║
║  我做了浅分析的：23 条                                  ║
║  我做了深分析的：6 条                                   ║
║  最终成片的：9 条 → 选题→创作转化率 19%                  ║
║                                                       ║
║  最多用过的热点话题：                                    ║
║  • #自律早起（3 条成片，hotspot 得分 87）                ║
║  • #宝妈一日（2 条成片，hotspot 得分 81）                ║
║  • #辅食打卡（1 条成片，hotspot 得分 79）                ║
║                                                       ║
║  ─── 5. 我的锚点（复用排行）                            ║
║                                                       ║
║  角色：                                                ║
║  👤 小张妈妈 · 跨 5 个 run 使用                          ║
║  👤 小娃 · 跨 3 个 run 使用                             ║
║  👤 邻居阿姨 · 跨 1 个 run 使用                          ║
║                                                       ║
║  场景：                                                ║
║  🏠 厨房-早晨 · 跨 4 个 run 使用                         ║
║  🏠 卧室-暗 · 跨 2 个 run 使用                           ║
║                                                       ║
║  推荐：将"小张妈妈"作为模板上架，复用价值最高              ║
║                                                       ║
║  ─── 6. 我用过的模板（V1）                              ║
║                                                       ║
║  • 早起 vlog 模板 · 用过 2 次                            ║
║  • ColorOS 示例 · 用过 1 次                              ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

### 4.3 数据来源

- 创作趋势：events 中 `run_created` / `run_completed` 按用户聚合
- 成本拆解：`cascade_runs.cost_breakdown_json` 聚合
- 用过的热点：events 中 `topic_card_view` / `enter_canvas_from_trending` 关联 runs
- 锚点复用：`anchor_usage` 表 + `anchors.usage_count`
- 模板使用：`runs.parent_template_id` 关联 templates

### 4.4 隐私（RLS）

```sql
-- /me/dashboard 所有查询走 user_id 过滤
CREATE POLICY user_own_data ON cascade_runs
  FOR SELECT USING (user_id = current_user_id());

CREATE POLICY user_own_events ON events
  FOR SELECT USING (user_id = current_user_id());

-- 类似 RLS 应用到 anchors / anchor_usage / templates 等
```

### 4.5 商业化 hook

- **Free**：仅本月概览 + 创作趋势
- **Pro**：完整 4 个模块（含成本拆解 + 用过的热点 + 锚点复用）
- **Team**：+ 团队成员产能视图
- **Enterprise**：+ 跨项目对比 + 导出 CSV

---

## 5. C 层 · B2B 运营报告

已通过 hotspot 整合在 V1.5 覆盖（详见 `TOPIC_TO_CREATION_PIPELINE.md` §8.5）。**本文档不重复**。

简要回顾：
- 4 种报告（选题推荐 / 深度洞察 / 账号雷达 / 主题三轨）
- hotspot 已有 HTML 生成能力
- V1.5 接入 Cascade UI：Team/Enterprise 用户可在 /me/dashboard 看到"生成报告"按钮 → 调 hotspot tools → 返回 URL

---

## 6. 数据隐私与合规

### 6.1 用户数据可见性

| 数据 | A 层（运营） | B 层（创作者本人） | C 层（B2B 客户） |
|---|---|---|---|
| 个人 PII（email/phone） | ❌（脱敏视图） | ✅（自己的） | ❌ |
| 创作内容（script / 锚点 / 成片 URL） | ✅（仅在调查事故时） | ✅（自己的） | ❌ |
| 行为事件 | ✅（聚合） | ✅（自己的） | ❌ |
| 成本数据 | ✅ | ✅（自己的） | ❌ |
| 跨用户对比 | ✅（聚合后） | ❌ | ❌ |

### 6.2 中国个保法合规

- 注册时明示数据采集范围 + 同意书
- /me 提供"导出我的数据"按钮（V1.5）
- /me 提供"删除账户"按钮（V2，含 30 天软删）
- A 层运营每次访问用户原始数据需记录审计（V2）

### 6.3 行为埋点的"用户主导"

- **明示**：FAQ 解释埋点用途
- **opt-out**：Pro+ 用户可关闭非必要埋点（仅保留计费 + 安全相关）
- **DNT**：尊重浏览器 Do Not Track 头

---

## 7. 实施工时

| 任务 | 工时 |
|---|---|
| **底座层** | |
| events / daily_metrics / user_funnels schema + 索引 | 1d |
| 前端事件 SDK 封装（自动注入 ctx + 批量 flush） | 1d |
| 后端 `POST /events/batch` 接收 + 异步写库 | 1d |
| 25 个核心事件埋点接入（前端 + 后端） | 4d |
| daily_metrics 聚合 cron + user_funnels 计算 cron | 2d |
| **A 层** | |
| Metabase Docker 部署 + Postgres readonly 连接 + 10-15 个种子 dashboard | 2d |
| /admin 内嵌运营仪表盘（8 个 KPI 卡片 + 漏斗 + 实时曲线 + 错误聚类 + 灰度开关） | 4d |
| /admin 鉴权（Clerk role + IP allowlist） | 1d |
| PII 脱敏视图 + 审计日志 | 1d |
| **B 层** | |
| /me/dashboard 4 个模块前端 | 4d |
| RLS 策略 + 查询性能优化 | 1d |
| 成本拆解后端聚合（cost_breakdown_json 解析） | 1d |
| 锚点复用统计（anchor_usage 聚合） | 0.5d |
| **C 层** | |
| 已在 hotspot 整合工时内（见 TOPIC §9） | — |
| **测试 + buffer** | ~3d |
| **合计** | **~26d ≈ 5 周** |

---

## 8. 与 MVP 的关系

### 8.1 必上（M1-M4 完成）

- ✅ events 底座（M1）
- ✅ 25 事件埋点接入（M1-M4 随功能开发同步）
- ✅ daily_metrics + user_funnels cron（M3）
- ✅ Metabase 部署 + 种子 dashboard（M1）
- ✅ /admin 内嵌运营仪表盘（M5）

### 8.2 V1.5 完成

- /me/dashboard 4 个模块（M5）
- C 层 B2B 报告 UI 接入（V1.5）
- 数据导出 / 删除按钮（V1.5）

### 8.3 V2+ 延后

- 抖音/小红书 OAuth → 真实播量回流
- "复盘"产品词
- 多平台对比看板
- 实验跟踪（A/B test 框架）
- 业务智能告警

---

## 9. 关键 SQL 模板（创始人手册）

### 9.1 7 天新增 → 付费转化漏斗

```sql
WITH cohort AS (
  SELECT user_id, MIN(reached_at) AS signup_at
  FROM user_funnels WHERE funnel_stage='signup'
  AND reached_at >= NOW() - INTERVAL '7 days'
  GROUP BY user_id
)
SELECT
  COUNT(*) AS signups,
  COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM user_funnels uf WHERE uf.user_id = c.user_id AND uf.funnel_stage='paid')) AS paid_count,
  ROUND(100.0 * COUNT(*) FILTER (WHERE EXISTS (...)) / COUNT(*), 2) AS conversion_pct
FROM cohort c;
```

### 9.2 不同 hotspot 得分段的复刻转化率

```sql
SELECT
  CASE
    WHEN (properties->>'total_score')::int >= 90 THEN '90+'
    WHEN (properties->>'total_score')::int >= 80 THEN '80-89'
    WHEN (properties->>'total_score')::int >= 70 THEN '70-79'
    ELSE '<70'
  END AS score_band,
  COUNT(DISTINCT properties->>'opus_id') AS topics_seen,
  COUNT(*) FILTER (WHERE event_name='enter_canvas_from_trending') AS entered_canvas,
  ROUND(100.0 * COUNT(*) FILTER (WHERE event_name='enter_canvas_from_trending') / COUNT(*), 2) AS conv_pct
FROM events
WHERE event_name IN ('hotspot_score_visible', 'enter_canvas_from_trending')
GROUP BY 1
ORDER BY 1 DESC;
```

### 9.3 三档模式的成本 / 完成率对比

```sql
SELECT
  properties->>'mode' AS mode,
  COUNT(*) FILTER (WHERE event_name='run_created') AS runs_created,
  COUNT(*) FILTER (WHERE event_name='run_completed') AS runs_completed,
  ROUND(100.0 * COUNT(*) FILTER (WHERE event_name='run_completed') / NULLIF(COUNT(*) FILTER (WHERE event_name='run_created'), 0), 2) AS completion_pct,
  AVG((properties->>'total_cost_fen')::int) FILTER (WHERE event_name='run_completed') AS avg_cost_fen
FROM events
WHERE event_name IN ('run_created', 'run_completed')
AND occurred_at >= NOW() - INTERVAL '30 days'
GROUP BY 1;
```

### 9.4 Top 锚点复用率（推荐用户上架的赛道索引）

```sql
SELECT
  a.id, a.name, a.type, u.email,
  COUNT(au.run_id) AS reuse_count
FROM anchors a
JOIN anchor_usage au ON au.anchor_id = a.id
JOIN users u ON u.id = a.owner_user_id
WHERE a.created_at >= NOW() - INTERVAL '30 days'
GROUP BY 1, 2, 3, 4
HAVING COUNT(au.run_id) >= 5
ORDER BY reuse_count DESC
LIMIT 50;
```

更多模板由 Metabase 种子 dashboard 提供（M1 完成）。

---

## 10. 决策固化（新增到 PRODUCT_VISION §12.6）

| # | 决策 |
|---|---|
| 47 | 数据统计 3 层：A 运营后台 + B 创作者数据中心 + C B2B 报告 |
| 48 | A 层混合形态：Metabase 深度查询 + /admin 内嵌运营仪表盘 |
| 49 | B 层独立 /me/dashboard（4 模块：概览 / 趋势 / 成本拆解 / 用过热点+锚点复用） |
| 50 | C 层已在 hotspot V1.5 通过 HTML 报告产品化 |
| 51 | 埋点底座 day-1：25 个核心事件 + events/daily_metrics/user_funnels 三表 |
| 52 | 数据隐私 day-1：RLS（B 层）+ PII 脱敏视图（A 层）+ 审计日志 |
| 53 | 数据回流（抖音/小红书播量）保持 V2 才做（不接 OAuth） |
| 54 | PostHog 可选并行：免费层 1M events/月够 6 个月，作为埋点冗余 |

---

## 11. 相关文档

- `PRODUCT_VISION.md` §7 North Star（数据看板里看的指标）/ §12.6 决策
- `TOPIC_TO_CREATION_PIPELINE.md` §8.7 选题工坊埋点 / §5 渐进式四层学习的转化漏斗
- `MVP_SCOPE.md` §1.F 数据统计交付清单
- `ROADMAP_6M.md` M1 埋点底座 / M5 /admin 与 /me/dashboard 上线
- `CANVAS_DESIGN.md` §7 schema（events/daily_metrics/user_funnels）

---

*数据是产品的眼睛。MVP 上线时如果埋点不完整，6 个月后我们看不清自己赢在哪里、输在哪里。所以"先埋点、再优化"是 day-1 必须坚守的原则。*
