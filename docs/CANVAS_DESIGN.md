# Cascade · 画布 + Agent UI 设计

**Document Status**: Design v0
**Date**: 2026-05-18
**Owner**: 产品设计师（招聘中） + 工程
**Related**: `PRODUCT_VISION.md` · `TOPIC_TO_CREATION_PIPELINE.md` · `MVP_SCOPE.md`

---

## 0. 设计原则

1. **锚点为主角**——character/scene 锚点不是隐藏字段，是画布上视觉主体。让用户感觉"我在导演一个剧组"
2. **Agent 是伙伴，不是助手**——智能弹起 5 时机，平时隐身。打扰最小化但关键时刻必现
3. **数据模型统一，视图分层**——闪电/标准/精修同一份 DAG schema，只是渲染密度不同
4. **任何时候可切换**——动中也能切模式、回到上游节点修改、放弃当前并发任务
5. **成本透明**——节点上预留"预估费用"字段，付费功能明示
6. **schema 为商业化预留**——MVP UI 不暴露的字段（planTier / costFen / tenantId / seatId）day-1 存在

---

## 1. 三档模式 × 同一画布

### 1.1 数据模型唯一性

所有模式共用同一份 `cascade_run` 数据：

```typescript
interface CascadeRun {
  id:                UUID;
  project_id:        UUID;
  mode:              'lightning' | 'standard' | 'pro' | 'manual';
  status:            RunStatus;
  
  // 节点拓扑（DAG）
  chapters:          Chapter[];        // 顶层章节（开场/中段/高潮/结尾）
  shots:             Shot[];           // 镜头节点
  anchors:           Anchor[];         // character / scene 锚点
  
  // Trending 溯源（如果是从热点工坊进来的）
  trending_source_meta?: TrendingSourceMeta;
  
  // 商业化 hook
  plan_tier:         'free' | 'pro' | 'team' | 'enterprise';
  tenant_id:         UUID;
  seat_id?:          UUID;
  total_cost_fen:    number;
}
```

**模式 = 渲染策略**，不是数据子集：

| 模式 | 数据可见性 | UI 渲染 |
|---|---|---|
| ⚡ 闪电 | 全部存在 | 仅展示进度条 + 缩略图 + 成片预览 |
| 🎯 标准 | 全部存在 | 横向 5 节点（剧本/锚点/镜头/合成/发布），闸门显式 |
| ✨ 精修 | 全部存在 | 完整 React Flow + 自由拖拽 + 所有节点可点 |
| 🛠 手动 | 全部存在 | 空画布初始，agent 默认隐身可呼叫 |

### 1.2 模式切换不破坏数据

- 闪电中切到精修：看到 agent 自动决策的"所有节点"，可继续微调
- 精修中切到闪电：所有手工修改保留，UI 折叠到进度视图
- 任意时刻切手动：保留当前节点，agent 不再主动弹起

---

## 2. 入口页（首页）

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                          [用户头像 ▾] ║
║                                                                      ║
║                 灵感不设限，创作无边界                                ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────┐        ║
║  │ [+] 先上传参考图，再用|                                   │        ║
║  │                                                            │        ║
║  │                                                  ● Agent 在线  ║
║  │ ┌────────────┬───────────┬────┐  ┌──────────┬─────────┬──┴────┐    ║
║  │ │ Agent 模式 ▾│ 技能 ▾    │ @ │  │ 手动生成 ▾│ 生成偏好 ▾│ 爆款实验室│  ║
║  │ └────────────┴───────────┴────┘  └──────────┴─────────┴──────┘    ║
║  │                                                              [GO ↗] ║
║  └──────────────────────────────────────────────────────────┘        ║
║                                                                      ║
║  ──── 🔥 今日热点（实时） ────                                    查看全部 → ║
║  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                       ║
║  │抖音#1 │ │微博#2 │ │知乎#1 │ │B站#5 │ │AI资讯│                       ║
║  │自律早起│ │xx事件 │ │xx知识 │ │xx番剧 │ │Sora 3│                       ║
║  │↑15/24h│ │NEW    │ │HOT    │ │↑8/24h │ │      │                       ║
║  │[创作] │ │[创作] │ │[创作] │ │[创作] │ │[创作] │                       ║
║  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘                       ║
║                                                                      ║
║  ──── 推荐位 ────                                                    ║
║  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            ║
║  │热门 AI │ │新手指南│ │激励计划│ │精选案例│ │灵感库  │            ║
║  │引擎    │ │        │ │        │ │        │ │        │            ║
║  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘            ║
║                                                                      ║
║  ──── 我的项目 ────                                       查看全部 →  ║
║  ┌────┐ ┌────────┐ ┌────────┐                                       ║
║  │ +  │ │ 项目1   │ │ 项目2   │ ...                                   ║
║  │新建│ │        │ │        │                                       ║
║  └────┘ └────────┘ └────────┘                                       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 2.1 输入框控件组

| 控件 | 行为 | 商业化 |
|---|---|---|
| **[+]** 上传参考图 | 多图上传，作为锚点种子 | Free: 3 张/次；Pro: 10 张 |
| **placeholder** | "先上传参考图，再用..." 引导先输入素材 | — |
| **Agent 模式 ▾** | 选闪电/标准/精修/手动 | — |
| **技能 ▾** | 显式选 agent 能力（生剧本 / 找热点 / 复刻爆款 / 锚点设计 / 直接生成） | Pro 解锁高级技能 |
| **@** | 提及对象（@项目 / @角色 / @场景 / @模板） | — |
| **手动生成 ▾** | 旁路 agent 进空画布 | — |
| **生成偏好 ▾** | 持久化用户偏好（默认风格 / 时长 / 平台） | 账户级保存 |
| **爆款实验室** | 跳 /topics 雷达（V2 改名为运营位） | Free 入门 / Pro 深度 |
| **[GO ↗]** | 提交 → 进 onboarding 决策 | — |

### 2.2 GO 之后的 onboarding

```
USER 点 GO（输入了"我想拍 #自律早起，赛博风"）
   │
   ▼
Agent 智能弹起 bottom sheet（① 初始问风格）
   "我帮你查了：抖音 #自律早起 排第 3，有 3 条爆款可参考"
   
   [看一眼热点参考]  [先做自己的版本]
   
   ↓ 选"看一眼热点参考"
   
   跳 /topics 雷达 with keyword=自律早起
   ↓ 选"先做自己的版本"
   
   弹小卡询问 mode（如果输入框没选过）：
   "你想要的速度："
   [⚡ 5 分钟出片]  [🎯 15-30 分钟精创]  [✨ 慢慢精修]
   
   ↓ 选 mode → 进画布
```

---

## 3. 画布主体（标准模式 · MVP 默认形态）

### 3.1 画布布局

```
╔══════════════════════════════════════════════════════════════════════╗
║ [< 返回] 项目名 / 这条 run 标题      [⚡ 标准]      [总成本 ¥X.XX] [⋯]║
╠═════════════╦══════════════════════════════════════════════════════╣
║             ║                                                       ║
║ 资产库       ║         主画布区                                       ║
║ ━━━━━━━━━━ ║                                                       ║
║             ║  ┌─────────────┐                                       ║
║ 角色 (3)    ║  │ 📜 剧本节点  │                                       ║
║ ┌────────┐  ║  │ "自律早起 - │                                       ║
║ │ 小张妈妈│  ║  │  辅食版本"  │                                       ║
║ │ ☑     │  ║  │ ✓ confirmed │                                       ║
║ └────────┘  ║  └──────┬──────┘                                       ║
║ ┌────────┐  ║         │                                              ║
║ │ 小娃    │  ║  ┌──────▼──────────────────────────────┐              ║
║ │ ☑     │  ║  │ 锚点闸门（agent 已建议）             │              ║
║ └────────┘  ║  │                                       │              ║
║ ┌────────┐  ║  │  ┌──────────┐    ┌──────────┐         │              ║
║ │ 邻居阿姨 │  ║  │ │👤小张妈妈 │   │👤小娃     │         │              ║
║ │ ⌛     │  ║  │ │ 已锁定    │   │ 已锁定    │         │              ║
║ └────────┘  ║  │  └──────────┘    └──────────┘         │              ║
║             ║  │                                       │              ║
║ 场景 (2)    ║  │  ┌──────────┐    ┌──────────┐         │              ║
║ ┌────────┐  ║  │ │🏠 厨房-早│   │🏠 卧室-暗│         │              ║
║ │厨房-早晨 │  ║  │ │ 已锁定    │   │ 已锁定    │         │              ║
║ │ ☑     │  ║  │  └──────────┘    └──────────┘         │              ║
║ └────────┘  ║  └──────┬────────────────────────────────┘              ║
║ ┌────────┐  ║         │                                              ║
║ │卧室-暗  │  ║  ┌──────▼──────────────────────────────┐              ║
║ │ ☑     │  ║  │ 镜头 (8 个)                           │              ║
║ └────────┘  ║  │                                       │              ║
║             ║  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐          ║
║ + 新建      ║  │  │ 1│ │ 2│ │ 3│ │ 4│ │ 5│ │ 6│ │ 7│ │ 8│          ║
║             ║  │  │✓ │ │⚡│ │⚡│ │ │  │ │  │ │ │  │ │ │  │ │ │          ║
║ 模板 (5)    ║  │  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘          ║
║ [+ 用模板]  ║  │                                       │              ║
║             ║  └──────┬────────────────────────────────┘              ║
║             ║         │                                              ║
║             ║  ┌──────▼──────┐                                       ║
║             ║  │ 合成成片     │                                       ║
║             ║  │ (等待)       │                                       ║
║             ║  └─────────────┘                                       ║
║             ║                                                       ║
╠═════════════╩══════════════════════════════════════════════════════╣
║ Trending 溯源：抖音 #自律早起 #3 用户A "5点起床实录"   [查看原视频↗]║
║ 模式：🎯 标准  |  进度 30%  |  Agent 在线  |  剩余配额：12/30 条      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 3.2 关键设计点

#### 锚点为主角

- **左侧资产库永远在场**——角色 / 场景 / 模板 各一列
- 每个锚点是**带头像的卡片**（不是隐藏字段）
- 锚点状态：⌛生成中 / ☑已确认 / ⚠失败 / ✏️ 编辑中
- 锚点可拖入镜头节点（"把小张妈妈放到镜头 3"）
- 锚点跨 run 复用——做完辅食视频里的小张妈妈，下次育儿可直接 [+ 用现有角色]

#### 锚点闸门可视化

- 闸门是显式的**横排卡片区**（在剧本和镜头之间），不是隐藏的"已通过"状态
- 每个锚点卡片有自己的"通过/驳回"按钮
- agent 主动弹起 modal："4 个锚点已生成，请检查"

#### 镜头节点的颗粒度

- MVP：8 个镜头节点平铺，每个显示 1/✓ 状态
- V2：引入章节层（开场/中段/高潮/结尾），镜头分组归属

#### 底部状态栏

- **Trending 溯源**：从 /topics 进来的 run，永远显示原视频出处（透明度 + V2 复盘溯源）
- **模式 / 进度 / Agent 状态 / 配额**：一行说清楚

### 3.3 闪电模式渲染

```
╔══════════════════════════════════════════════╗
║ [< 返回] 自律早起 - 辅食版本                  ║
║                                              ║
║ 🔥 正在为你创作中... 预计 4 分 30 秒            ║
║                                              ║
║ [================================---] 75%    ║
║                                              ║
║ ✓ 剧本生成                                    ║
║ ✓ 锚点：小张妈妈、小娃、厨房-早晨、卧室-暗     ║
║ ⏳ 镜头：6/8 完成                              ║
║   [缩略图 1] [缩略图 2] [缩略图 3] [⏳] [⏳]   ║
║   [缩略图 4] [缩略图 5] [缩略图 6]            ║
║ ⏳ 字幕生成中                                  ║
║ ⏳ TTS 配音 + BGM 选取                         ║
║                                              ║
║ 💡 [切换到标准模式查看细节] [取消]              ║
║                                              ║
╚══════════════════════════════════════════════╝
```

### 3.4 精修模式渲染

完整 React Flow 画布，所有节点可拖拽 + 自由连线：

```
╔════════════════════════════════════════════════════════════════════╗
║ [< 返回] 自律早起 - 辅食版本   [✨ 精修]   [总成本 ¥9.42]  [⋯]    ║
╠══════╦═════════════════════════════════════════════════════════════╣
║ 资产 ║          ┌────────┐                                       ║
║库    ║          │ 用户输入│                                       ║
║      ║          └───┬────┘                                       ║
║ 角色  ║              │                                            ║
║ 场景  ║          ┌───▼────┐    ┌─────────┐                       ║
║ 模板  ║          │ 剧本    ├───→│Trending │                       ║
║      ║          │ ✓       │    │ 溯源    │                       ║
║      ║          └───┬────┘    └─────────┘                       ║
║      ║              │                                            ║
║      ║      ┌───────┴────────┐                                   ║
║      ║      │                │                                   ║
║      ║   ┌──▼──┐         ┌───▼──┐                               ║
║      ║   │角色 │         │场景  │                               ║
║      ║   │锚点 │         │锚点  │                               ║
║      ║   │ x 2 │         │ x 2  │                               ║
║      ║   └──┬──┘         └──┬───┘                               ║
║      ║      │  ┌────────────┘                                    ║
║      ║      └──┤    ↓                                            ║
║      ║         ▼   合成宫格图                                     ║
║      ║   ┌──────────────┐                                        ║
║      ║   │ 镜头 1  ┌→ 视频生成 ┐                                  ║
║      ║   │        ├→ TTS 配音 ├→ 镜头 1 成片                      ║
║      ║   │        └→ 字幕      ┘                                  ║
║      ║   └──────────────┘                                        ║
║      ║   ┌──────────────┐                                        ║
║      ║   │ 镜头 2  ┌→ ...                                         ║
║      ║   └──────────────┘                                        ║
║      ║   ...（8 个镜头并行）                                       ║
║      ║                  │                                         ║
║      ║                  ▼                                         ║
║      ║             合成成片 + BGM                                  ║
║      ║                  │                                         ║
║      ║                  ▼                                         ║
║      ║             发布包                                          ║
╚══════╩═════════════════════════════════════════════════════════════╝
```

精修模式是给 MCN / 高级用户的"工作台"——每个节点都可以独立编辑、重生、删除、连线。

---

## 4. 锚点系统的具体形态（差异化锁点 — 重点）

### 4.1 锚点节点的视觉

锚点不是"上传参考图"那种隐藏字段，而是**带名字、带头像、带状态、带历史**的画布主体：

```
┌─────────────────────────────────────┐
│ 👤 小张妈妈                          │
│ ┌─────┐ ┌─────┐ ┌─────┐             │
│ │正面 │ │侧面 │ │背面 │             │
│ └─────┘ └─────┘ └─────┘             │
│                                      │
│ 28 岁宝妈 · 短发 · 笑容亲切          │
│                                      │
│ 风格：写实 · 暖色调                  │
│                                      │
│ ✓ 已确认  |  跨 run 复用 3 次        │
│ [编辑] [生成更多视图] [删除]          │
└─────────────────────────────────────┘
```

字段：
- **三视图**（front / side / back）—— Image gen 用 3 个不同 prompt 生成
- **描述**（28 岁宝妈 · 短发 · 笑容亲切）—— 用户编辑或 agent 推断
- **风格**（写实 / 动漫 / 赛博 / 油画）—— 整组锚点统一
- **跨 run 计数** —— "这角色已被你用了 3 次"
- **可编辑** —— 用户调整后所有引用同步

### 4.2 场景锚点

```
┌─────────────────────────────────────┐
│ 🏠 厨房-早晨                         │
│ ┌──────────────────────────────┐    │
│ │      [场景定稿板大图]          │    │
│ │   现代家庭厨房，早晨自然光      │    │
│ └──────────────────────────────┘    │
│                                      │
│ 关键元素：木质台面 · 窗外晨光         │
│ · 锅具 · 食材 · 小娃椅              │
│                                      │
│ 风格：写实 · 暖色调                  │
│                                      │
│ ✓ 已确认  |  跨 run 复用 1 次        │
│ [编辑] [生成变体] [删除]              │
└─────────────────────────────────────┘
```

### 4.3 锚点之间的关系

```
角色锚点                        场景锚点
小张妈妈   ─┐              ┌──── 厨房-早晨
小娃       ─┼─→ 宫格图 ←──┤
邻居阿姨   ─┘              └──── 卧室-暗

宫格图 = 角色 × 场景的组合定稿板
（用 image gen 把"小张妈妈在厨房早晨"这种组合提前固化）
```

宫格图的作用：**让后续 frame 生成有了视觉一致性的"种子图"**——每个镜头的 image-grounded video 都参考相应的宫格图。这是 Cascade 比"上传一张 character_reference"做得深的地方。

### 4.4 锚点 schema

```sql
CREATE TABLE anchors (
  id              UUID PRIMARY KEY,
  project_id      UUID NOT NULL REFERENCES projects(id),
  type            TEXT NOT NULL,    -- 'character' | 'scene' | 'grid'
  name            TEXT NOT NULL,    -- "小张妈妈" | "厨房-早晨"
  description     TEXT,             -- "28 岁宝妈 · 短发"
  style           TEXT,             -- 'realistic' | 'anime' | 'cyberpunk' | ...
  
  -- 视图（character）/ 关键元素（scene）/ 组合（grid）
  views_json      JSONB,            -- character: { front, side, back }
                                    -- scene: { master_image, key_elements }
                                    -- grid: { participants: [anchor_ids], image_url }
  
  -- 锚点状态
  status          TEXT DEFAULT 'reviewing',  -- 'reviewing' | 'confirmed' | 'failed'
  asset_status    TEXT DEFAULT 'idle',       -- 'idle' | 'generating' | 'done' | 'failed'
  
  -- 跨 run 复用
  usage_count     INT DEFAULT 0,
  last_used_at    TIMESTAMPTZ,
  
  -- 商业化 hook
  cost_fen        INT DEFAULT 0,
  provider        TEXT,             -- 'apimart' | 'google-gemini'
  
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  
  INDEX (project_id, type)
);

CREATE TABLE anchor_usage (
  -- 谁在哪条 run 用了哪个 anchor
  anchor_id       UUID REFERENCES anchors(id),
  run_id          UUID REFERENCES cascade_runs(id),
  shot_id         UUID REFERENCES shots(id),
  PRIMARY KEY (anchor_id, run_id, shot_id)
);
```

---

## 5. Agent UI：5 触发器 × 3 形态混合

### 5.1 5 个触发时机

| # | 时机 | 触发条件 | UI 形态 | 用户期望 |
|---|---|---|---|---|
| 1 | **初始问风格** | 用户提交一句话直发后 | bottom sheet | "我帮你定个调子" |
| 2 | **剧本闸门** | 剧本生成完成、未确认 | modal | "看一下剧本对不对" |
| 3 | **锚点闸门** | 全部锚点生成完成、未确认 | modal | "角色场景定好了，请审" |
| 4 | **成片闸门** | 合成完成、未确认 | modal | "成片好了，要发吗？" |
| 5 | **出错时** | 任何节点失败 | inline 卡片 | "这里出问题了，怎么办" |
| 6 | **完成后** | 发布包准备完毕 | bottom sheet | "导出 / 发布选哪个" |

### 5.2 三种 UI 形态

#### A · Modal（强阻塞、关键决策）

用于：剧本闸门 / 锚点闸门 / 成片闸门

```
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║   剧本闸门 · agent 等你确认                            ║
║                                                       ║
║   ┌─────────────────────────────────────────────┐    ║
║   │ # 早起人生 - 辅食妈妈版                       │    ║
║   │                                              │    ║
║   │ ## 剧本                                       │    ║
║   │ 5:30 am，闹钟响起... 小张妈妈轻轻起身...    │    ║
║   │                                              │    ║
║   │ ## 分镜表                                     │    ║
║   │ 镜头 1 · 卧室特写闹铃 · 3 秒                  │    ║
║   │ 镜头 2 · 主角起身侧脸 · 4 秒                  │    ║
║   │ ...                                          │    ║
║   │                                              │    ║
║   │ ## 资产清单                                    │    ║
║   │ - 角色：小张妈妈、小娃                        │    ║
║   │ - 场景：卧室-暗、厨房-早晨                    │    ║
║   └─────────────────────────────────────────────┘    ║
║                                                       ║
║   有什么要调整的？                                    ║
║                                                       ║
║   ┌─────────────────────────────────────────────┐    ║
║   │ [反馈框：请告诉 agent 哪里需要改]              │    ║
║   └─────────────────────────────────────────────┘    ║
║                                                       ║
║   [通过 ✓]    [让 agent 调整]   [取消，回前面]         ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

#### B · Bottom Sheet（半阻塞、软问事）

用于：初始问风格 / 完成后导出

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ↑↓ 拖拽 / 点击关闭收起                              ║
║                                                      ║
║   🤖 agent  ·  "我帮你查了一下"                       ║
║                                                      ║
║   抖音 #自律早起 现在排第 3，有 3 条爆款值得参考。     ║
║                                                      ║
║   你想：                                              ║
║                                                      ║
║   ┌────────────────────────────┐                     ║
║   │ 看一眼热点参考               │                     ║
║   └────────────────────────────┘                     ║
║   ┌────────────────────────────┐                     ║
║   │ 先做自己的版本              │                     ║
║   └────────────────────────────┘                     ║
║                                                      ║
║   或者直接告诉我你想怎么拍：                          ║
║   ┌────────────────────────────┐                     ║
║   │ ...                         │                     ║
║   └────────────────────────────┘                     ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

#### C · Inline 卡片（无阻塞、节点上下文）

用于：出错时

```
画布上某个镜头节点
┌────────────────────────┐
│ 镜头 5 (失败 ⚠)         │
│                        │
│ ┌─ 🤖 agent ─────────┐ │
│ │ 这个镜头被内容审核 │ │
│ │ 驳回了。试试：     │ │
│ │ • 换 prompt 重生   │ │
│ │ • 换风格重生       │ │
│ │ • 跳过这一镜       │ │
│ │ • 完整重做         │ │
│ └─────────────────────┘ │
└────────────────────────┘
```

### 5.3 Agent 状态机

```
[hidden]
    │ trigger
    ▼
[summoning]  ← 短动画，不打扰
    │
    ▼
[active] ─── modal / bottom_sheet / inline ──┐
    │                                         │
    │ user_response                           │
    ▼                                         │
[handling_response]                           │
    │                                         │
    ▼                                         │
[hidden] ◄────────────────────────────────────┘
```

实现：FastAPI 后端推送 `agent_trigger` WebSocket event → 前端状态机切换。

---

## 6. 失败处置 UX

当任何节点失败，agent 弹起 inline 卡片在该节点下方，提供 **4 选 1 + 反馈**：

```
┌──────────────────────────────────────────────┐
│ 镜头 5 · 失败 ⚠                               │
│                                              │
│ 失败原因：内容审核未通过                       │
│ 提示词："深夜独自一人在街头..."                │
│                                              │
│ ┌─ 🤖 agent 建议 ─────────────────────────┐  │
│ │                                          │  │
│ │ 试试这些方案：                            │  │
│ │                                          │  │
│ │ [换个 prompt 重生（agent 帮润色）]        │  │
│ │   预计 ¥0.7 / 2 分钟                     │  │
│ │                                          │  │
│ │ [换个风格重生（动漫 / 写实 / 赛博）]       │  │
│ │   预计 ¥0.7 / 2 分钟                     │  │
│ │                                          │  │
│ │ [跳过这一镜（成片少 1 个场景）]            │  │
│ │   ¥0                                     │  │
│ │                                          │  │
│ │ [完整重做整条 run（从选题重来）]          │  │
│ │   预计 ¥10+ / 25 分钟                    │  │
│ │                                          │  │
│ │ ──── 或者告诉 agent 你想怎么调 ────      │  │
│ │ [反馈框]                                  │  │
│ │                                          │  │
│ └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

**关键设计**：
- 每个选项**显式标价**（成本透明）
- "跳过这一镜"明确说"成片少 1 个场景"（透明告知后果）
- 反馈框是 escape hatch（agent 自由发挥）

---

## 7. 数据 Schema（DAG · day-1 含商业化字段）

### 7.1 核心表

```sql
-- 用户层
CREATE TABLE users (
  id                UUID PRIMARY KEY,
  email             TEXT UNIQUE NOT NULL,
  display_name      TEXT,
  -- 商业化
  plan_tier         TEXT DEFAULT 'free',  -- 'free' | 'pro' | 'team' | 'enterprise'
  plan_expires_at   TIMESTAMPTZ,
  quota_used        JSONB DEFAULT '{}',   -- { videos: 5, deepAnalysis: 2, ... }
  quota_total       JSONB DEFAULT '{}',   -- { videos: 3, deepAnalysis: 1, ... }
  -- 多租户预留
  tenant_id         UUID,                  -- MCN/品牌团队主帐户
  seat_id           UUID,                  -- 团队座位 ID
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- 项目层
CREATE TABLE projects (
  id                UUID PRIMARY KEY,
  user_id           UUID NOT NULL REFERENCES users(id),
  name              TEXT NOT NULL,
  is_default        BOOLEAN DEFAULT FALSE,  -- 个人账号的隐藏 default 项目
  -- 商业化
  tenant_id         UUID,                  -- 同 users.tenant_id
  brand_pack_json   JSONB,                  -- V2: 品牌 logo/字体/调色板/禁用词
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- run 层
CREATE TABLE cascade_runs (
  id                  UUID PRIMARY KEY,
  project_id          UUID NOT NULL REFERENCES projects(id),
  user_id             UUID NOT NULL REFERENCES users(id),
  
  -- 模式
  mode                TEXT NOT NULL,         -- 'lightning' | 'standard' | 'pro' | 'manual'
  
  -- 状态
  status              TEXT DEFAULT 'pending',  -- pending | running | done | failed | cancelled
  
  -- 元信息
  title               TEXT,
  topic               TEXT,
  niche               TEXT,
  
  -- Trending 溯源
  trending_source_meta JSONB,                  -- 见 TOPIC_TO_CREATION_PIPELINE.md §6
  
  -- 商业化字段
  plan_tier_snapshot  TEXT,                    -- 创建时的 plan tier 快照（计费用）
  tenant_id           UUID,
  seat_id             UUID,
  total_cost_fen      INT DEFAULT 0,
  cost_breakdown_json JSONB,                   -- 分项成本：image / video / tts / bgm / compose
  
  -- 模板溯源
  parent_template_id  UUID REFERENCES templates(id),  -- 从模板复制来的
  parent_run_id       UUID REFERENCES cascade_runs(id),  -- "拿同款" 复刻来的（V2）
  
  started_at          TIMESTAMPTZ,
  completed_at        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 节点层（DAG）
CREATE TABLE cascade_nodes (
  id                  UUID PRIMARY KEY,
  run_id              UUID NOT NULL REFERENCES cascade_runs(id) ON DELETE CASCADE,
  type                TEXT NOT NULL,       -- 'script' | 'character_anchor' | 'scene_anchor' | 'grid' | 'shot' | 'tts' | 'bgm' | 'compose' | 'export'
  parent_node_ids     UUID[],              -- DAG 关系
  
  -- 节点数据
  node_status         TEXT DEFAULT 'reviewing',  -- 'reviewing' | 'confirmed'
  asset_status        TEXT DEFAULT 'idle',       -- 'idle' | 'generating' | 'done' | 'failed' | 'timeout'
  
  -- 位置（精修模式画布坐标）
  position_x          REAL,
  position_y          REAL,
  
  -- 内容
  title               TEXT,
  description         TEXT,
  prompt              TEXT,
  result_json         JSONB,
  feedback            TEXT,                -- 用户在闸门反馈的内容
  
  -- 商业化
  cost_fen            INT DEFAULT 0,
  provider            TEXT,                -- 'apimart' | 'google-gemini' | 'kling' | 'seedance' | 'huoshan-tts' | ...
  usage_meter_id      UUID,                -- 关联 usage_meter 表（V2 用量审计）
  
  -- 链接到锚点（如果是 shot 节点）
  anchor_ids          UUID[],
  
  -- 失败溯源
  retry_count         INT DEFAULT 0,
  failed_reason       TEXT,
  
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  
  INDEX (run_id, type)
);

-- 锚点表
CREATE TABLE anchors (
  -- 见 §4.4
);

-- 锚点使用追踪
CREATE TABLE anchor_usage (
  -- 见 §4.4
);

-- 模板库
CREATE TABLE templates (
  id                  UUID PRIMARY KEY,
  origin              TEXT NOT NULL,       -- 'operation' | 'ugc' | 'platform_seed'
  author_user_id      UUID,                -- UGC 模板的作者
  name                TEXT NOT NULL,
  description         TEXT,
  cover_url           TEXT,
  
  -- 模板内容（JSON 结构 = 一个完整的 run 骨架）
  payload_json        JSONB NOT NULL,      -- { chapters, shots_skeleton, default_anchors, style_preset, ... }
  
  -- 分类
  category            TEXT,                -- '美妆' | '辅食' | '科技测评' | ...
  tags                TEXT[],
  
  -- 商业化
  price_tier          TEXT DEFAULT 'free', -- 'free' | 'pro_only' | 'paid'
  price_fen           INT DEFAULT 0,
  -- UGC 创作者分成
  rev_share_pct       INT DEFAULT 0,       -- 0-100
  
  -- 使用统计
  usage_count         INT DEFAULT 0,
  
  created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 7.2 hotspot 整合后的 schema 扩充（v1 新增）

**详细 schema 见 `TOPIC_TO_CREATION_PIPELINE.md` §7**。Cascade 选题情报中台沿用 hotspot 4 张表 + 新增 niche_indices 表：

```sql
-- 从 hotspot 整套搬过来（MySQL → Postgres）
hot_search_snapshot           -- 60s 热搜快照（定时入库 02/06/08:00 等）
rank_data                     -- 新榜视频元数据（4 平台）
ai_video_info                 -- AI 视频基础信息
ai_video_metrics              -- AI 视频指标（含时序）

-- v1 新增（去 ColorOS 化 + 赛道索引架构）
niche_indices                 -- 用户/账户的赛道索引（含三池过滤、场景映射、经验风格、品牌包）
hotspot_analysis_cache        -- hotspot 算法层结果缓存

-- cascade_runs 关联字段
ALTER TABLE cascade_runs ADD COLUMN active_niche_index_id UUID REFERENCES niche_indices(id);
ALTER TABLE projects ADD COLUMN default_niche_index_id UUID REFERENCES niche_indices(id);
```

### 7.2b 数据统计层 schema 扩充（v2 新增 · 详见 `DATA_DASHBOARD.md`）

Cascade 数据统计 3 层（A 运营后台 + B 创作者数据中心 + C B2B 报告）共享同一埋点底座：

```sql
-- 原始事件表（永久保留，全量）
events                        -- user_id, tenant_id, session_id, event_name, properties JSONB, occurred_at
                              -- 25 个核心事件（user_signup / run_created / hotspot_score_visible / paid_conversion 等）

-- 按天聚合（加速 admin 查询）
daily_metrics                 -- date + metric_name + dimension_key JSONB + value
                              -- 每日 02:30 cron 聚合（dau / mau / runs_created / run_success_rate / 等）

-- 用户漏斗状态
user_funnels                  -- user_id + funnel_stage（signup → activated → first_create → first_complete → repeat_d7 → retained_d14 → paid）
                              -- 每 10 分钟 cron 推进
```

**关键索引**：
- `events (user_id, occurred_at DESC)` — B 层 /me/dashboard 查询
- `events (event_name, occurred_at DESC)` — A 层聚合查询
- `events (tenant_id, occurred_at DESC) WHERE tenant_id IS NOT NULL` — B2B 客户隔离

**安全 day-1**：
- B 层 RLS：`CREATE POLICY user_own_events ON events FOR SELECT USING (user_id = current_user_id())`
- A 层 PII 脱敏视图：`vw_users_anonymized`（屏蔽 email/phone）
- Metabase 用 `cascade_readonly` 角色（无 INSERT/UPDATE/DELETE 权限）

`cascade_runs.trending_source_meta` JSONB 字段在 hotspot 整合后扩充含 `hotspot_snapshot`（5 维评分快照）和 `niche_index_snapshot`（用户激活赛道索引快照）—— 详见 `TOPIC_TO_CREATION_PIPELINE.md` §7.4。

### 7.3 商业化 hook 字段总览

day-1 schema 已经包含、MVP UI 不暴露的字段：

| 字段 | 表 | 用途 | 启用时机 |
|---|---|---|---|
| `plan_tier` | users, projects, runs (snapshot) | 套餐分层 | MVP 显式 |
| `quota_used` / `quota_total` | users | 配额追踪 | MVP 显式 |
| `tenant_id` | users, projects, runs | 多租户 | V2 团队功能 |
| `seat_id` | users, runs | 团队座位 | V2 |
| `cost_fen` / `cost_breakdown_json` | runs, nodes | 成本透明 | MVP 显式 |
| `provider` | nodes | provider 路由 | MVP 后端用 |
| `usage_meter_id` | nodes | 用量审计 | V2 |
| `parent_template_id` / `parent_run_id` | runs | 模板/复刻溯源 | MVP 备好，V2 启用分成 |
| `brand_pack_json` | projects | 品牌库 | V2 品牌方功能 |
| `price_tier` / `rev_share_pct` | templates | 模板市场 | V2 |
| `data_source_tier` | hot_search_snapshot, rank_data | 数据源分层 | MVP 备好（hotspot 整合） |
| `analysisDepth` | trending_analysis | 浅/算法/深分析计费 | MVP 显式 |
| `active_niche_index_id` | cascade_runs | 用户激活的赛道（v1 新增） | MVP 显式（freemium 限 1 个） |
| `visibility` / `price_fen` / `share_count` | niche_indices | 赛道索引商业化（v1 新增） | V2 marketplace 启用 |
| `hotspot_snapshot` | cascade_runs.trending_source_meta | 算法层快照（用于复盘） | V2 数据回流时启用 |

---

## 8. WebSocket 协议（继承 OpenRHTV，扩展）

### 8.1 客户端 → 服务端

```typescript
interface WSClientMessage {
  // 原 OpenRHTV 已有
  | { type: 'user_message';        thread_id: string; content: string }
  | { type: 'update_position';     thread_id: string; node_id: string; x: number; y: number }
  | { type: 'review_node';         thread_id: string; node_id: string; action: 'approve'|'reject'; feedback?: string }
  | { type: 'execute_node';        thread_id: string; node_id: string; node_type: NodeType; description: string }
  | { type: 'update_node_status';  thread_id: string; node_id: string; node_status: NodeStatus }
  | { type: 'optimize_prompt';     thread_id: string; node_id: string; prompt: string; feedback: string }
  | { type: 'get_session_state';   thread_id: string }
  
  // Cascade 新增
  | { type: 'search_trending';     keyword?: string; platform?: string; source?: 'realtime'|'deep'|'auto' }
  | { type: 'analyze_trending';    opus_id: string; platform: string; depth: 'shallow'|'deep'; niche?: string }
  | { type: 'seed_canvas';         analysis_id: number; mode: Mode }
  | { type: 'switch_mode';         thread_id: string; mode: Mode }
  | { type: 'apply_template';      thread_id: string; template_id: string }
  | { type: 'copy_publish_pack';   thread_id: string };
}
```

### 8.2 服务端 → 客户端

```typescript
interface WSServerMessage {
  // 原 OpenRHTV 已有
  | { type: 'agent_response';       thread_id: string; content: string; canvas: CanvasData | null }
  | { type: 'agent_stream';         thread_id: string; event: 'tool_call'|'text'; content?: string; name?: string; args?: string }
  | { type: 'canvas_updated';       thread_id: string; canvas: CanvasData | null }
  | { type: 'processing';           thread_id: string }
  | { type: 'session_state';        thread_id: string; messages: Message[]; canvas: CanvasData | null }
  | { type: 'prompt_optimized';     thread_id: string; node_id: string; optimized_prompt: string }
  
  // Cascade 新增
  | { type: 'agent_trigger';        thread_id: string; trigger: TriggerKind; ui: 'modal'|'bottom_sheet'|'inline'; payload: any }
  | { type: 'trending_result';      result: TrendingFetchResult }
  | { type: 'analysis_progress';    analysis_id: number; phase: 'downloading'|'llm_calling'|'parsing'; progress: number }
  | { type: 'analysis_done';        analysis_id: number; depth: 'shallow'|'deep'; payload: any; cost_fen: number; cache_hit: boolean }
  | { type: 'quota_warning';        kind: 'videos'|'deepAnalysis'; used: number; total: number }
  | { type: 'cost_update';          thread_id: string; total_cost_fen: number; breakdown: Record<string, number> };
}
```

---

## 9. 商业化 UI 位（MVP 显式，但低调）

### 9.1 顶栏总成本（实时）

```
[< 返回] 项目名 / 这条 run 标题  [⚡ 标准]  [总成本 ¥0.87 ⓘ]  [配额: 12/30 条]  [⋯]
                                              │
                                              ▼ hover 展开
                                          ┌──────────────────┐
                                          │ Image: ¥0.21      │
                                          │ Video: ¥0.55      │
                                          │ TTS:   ¥0.01      │
                                          │ BGM:   ¥0.05      │
                                          │ 合成: ¥0.05       │
                                          └──────────────────┘
```

### 9.2 节点上预估费用（生成前）

```
┌─ 镜头 3 ────────────┐
│ [预览图 placeholder] │
│                     │
│ 预估 ¥0.85 · 2 分钟 │
│ [生成]               │
└────────────────────┘
```

### 9.3 配额耗尽时的引导

```
╔══════════════════════════════════════════╗
║                                          ║
║   ⚠ 本月免费配额已用完                    ║
║                                          ║
║   你已经创作了 3/3 条免费视频。           ║
║   升级到 Pro 套餐解锁 30 条/月。          ║
║                                          ║
║   ┌──────────────────────────────────┐  ║
║   │ Pro 套餐 · ¥39/月                 │  ║
║   │ • 30 条视频                       │  ║
║   │ • 无限深度热点分析                 │  ║
║   │ • 跨 run 锚点复用                  │  ║
║   │ • 高级 TTS 音色                    │  ║
║   │ [升级] [先试试基础功能]            │  ║
║   └──────────────────────────────────┘  ║
║                                          ║
║   或：单条加购 ¥3 → [生成这一条]          ║
║                                          ║
╚══════════════════════════════════════════╝
```

---

## 10. 移动端预留（V2）

MVP 锁定桌面端。移动端 V2 设计原则：
- **闪电模式 + 标准模式可移动化**（精修和手动模式只在桌面）
- **画布折叠为竖向时间线**（移动端 React Flow 不友好）
- **锚点库变下拉抽屉**
- **agent 弹起统一变 bottom sheet**
- **iOS/Android 原生 share extension** 替代复制发布包

---

## 11. 与 OpenRHTV 现有代码的差异

| OpenRHTV 现状 | Cascade 改造 |
|---|---|
| `canvas_tools._current_thread_id` 全局变量 | 多租户化：`tenant_id` + `user_id` + `run_id` 三层路由 |
| SQLite | Postgres + 多租户 RLS |
| 单一 NodeType (script/image/video/audio) | DAG 扩展：character_anchor / scene_anchor / grid / shot / tts / bgm / compose / export |
| 节点状态：node_status + asset_status | 同（继承） |
| HIERARCHY 配置 dict | 同（搬到 `lib/anchor-rules.py`） |
| 5 个 agent 角色 prompts | 重写为单 Director agent + canvas-manager subagent |
| `set_thread_id()` 全局切 | 每个请求带 user_id + run_id 上下文 |
| 前端 4 个 NodeType React 组件 | 8+ 个节点类型（含锚点 / 章节 / 合成） |

---

## 12. 相关文档

- `PRODUCT_VISION.md` §3 产品形态 / §4 差异化锁点
- `TOPIC_TO_CREATION_PIPELINE.md` §3 入口形态 / §6 数据 schema
- `MVP_SCOPE.md` 必做/砍掉清单
- `ROADMAP_6M.md` M2 锚点 / M3 音频 / M4 Agent

---

*画布是 Cascade 的视觉核心，锚点是差异化的灵魂。UI 设计师入职后会基于本文档出 Figma 高保真原型。*
