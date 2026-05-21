# Cascade · 热点 → 创作工坊 · 数据流与设计

**Document Status**: Pipeline v1（含 hotspot 整合）
**Date**: 2026-05-18
**Owner**: 工程 + 产品
**Related**: `PRODUCT_VISION.md` §3-5 · `CANVAS_DESIGN.md` §3 · `MVP_SCOPE.md`

---

## 0. 摘要

Cascade 把"发现热点 → 选具体爆款 → 学习它为什么火 → 在画布里复刻"作为**核心产品体验**。整合 hotspot 选题情报中台后，本文档定义：

- **四个数据源**（60s 实时 / 新榜 / **hotspot 持久化时序** / toprador 视频分析）的角色分工
- **hotspot 算法中台**（双轨/五维评分 + 互动 DNA + 可复刻性 + 飙升/竞争空位 + 创作者雷达 + 三池过滤）
- **赛道索引架构**（用户自定义"赛道词表 + 场景映射"，去 ColorOS 化的产品级亮点）
- 用户从首页到画布的完整旅程（三入口 × 渐进式**四层学习**）
- Agent 在这条 pipeline 上的工具规范（unified tool surface）
- 选题侧商业化扩展（数据源分层 + 赛道索引订阅 + 创作者雷达订阅 + 运营报告订阅）
- 与 Cascade 画布的集成接口

---

## 1. 为什么把热点和创作绑在一起

### 1.1 现状痛点

中文短视频创作者 90% 的时间花在两件事上：
1. **想"今天拍啥"**（选题枯竭）
2. **拍出来没人看**（不会蹭热点 + 不知道哪条能复刻 + 看不清竞争空位）

现有工具链是断的、能力是浅的：
- **新榜 / 飞瓜 / 卡思**：只看数据 → 看完不知道怎么做
- **即梦 / 可灵 / Sora**：只生成 → 不知道做什么
- **剪映 / CapCut**：只剪辑 → 在很后端
- **ACMM topic-analysis（3 句话浅分析）**：能告诉"为什么火"，但**不能告诉"得分多少 / DNA 是啥 / 复刻难不难 / 现在做是蓝海还是红海"**

### 1.2 Cascade 的合并形态（hotspot 整合后）

**把"发现"+"分析"+"创作"三件事合一**：

```
传统流程（割裂、浅）：
  刷抖音(1h) → 截图记 → 切到剪映(4h) → 自己脑补 → 发布

Cascade 工坊（一站、深）：
  /topics 雷达
    ↓
  四数据源融合候选池 + hotspot 算法层评分
  （客观：双轨/五维分 + DNA + 可复刻 + 蓝海/红海地图）
    ↓
  ACMM AI 翻译层
  （主观：为什么火 + 怎么改造为你的赛道）
    ↓
  toprador 深分析（可选）
  （分镜级蓝图）
    ↓
  自动入画布
    ↓
  用我的锚点重做 → 一键复制发布

节省：1h 选题 + 2h 模仿试错 = 3 小时
增强：客观评分 + 互动 DNA + 可复刻性 = 选题质量从盲猜跃升到工业级
```

价值不只是省时间，更是 **"把选题质量从盲猜提升到数据 + 算法双驱动"**，**这是同行没有的能力**。

---

## 2. 四个数据源的分工（hotspot 整合后）

### 2.1 数据源对比矩阵

| 维度 | 60s 热搜（toprador） | 新榜 API（ACMM newrank sidecar） | hotspot 持久化时序 | toprador video-analysis |
|---|---|---|---|---|
| **来源** | 开源 vikiboss/60s（toprador 已部署 :4399） | newrank.cn API（ACMM 已包） | hotspot 4 张表（自建定时入库） | 多模态 LLM（doubao-seed-2-0-pro） |
| **平台覆盖** | 8+（抖音/微博/知乎/百度/头条/B站/60s/AI资讯） | 4（dy/ks/xhs/bz） | 4（dy/ks/xhs/bz）+ 4 热搜（weibo/douyin/bilibili/rednote）+ AI 视频专项 | 任意（只要有 URL） |
| **数据形态** | 实时话题词条 | T-3 视频元数据 | **结构化时序**（4 张表互锁） | 分镜级（8 镜 × 多维度） |
| **数据深度** | 浅（仅热搜词） | 中（视频元数据） | **结构化中等 + 时序对比** | 深（视频内容真分析） |
| **是否含算法层** | ❌ 原始数据 | 🟡 LLM 3 句话浅分析 | ✅ **双轨/五维评分 + DNA + 可复刻 + 飙升 + 空位** | ❌ 单条分析 |
| **是否含视频 URL** | 否（仅话题） | 是（4 平台 url 字段） | 是（rank_data.url） | 输入即 URL |
| **实时性** | 准实时（5min 刷新） | T-3 | 自定义（默认 02/06/08:00 多时段） | on-demand 按次 |
| **成本** | 免费（自部署） | 按 API key 计费 | 自建（除新榜 API 外免费） | 多模态 LLM ~¥0.3-0.8/次 |
| **现有代码** | toprador 直接复用 | ACMM TypeScript 整套 | **hotspot 整套搬过来** | toprador 直接复用 |

### 2.2 数据源角色定位（产品层）

```
                    用户的认知路径
                    
"今天什么在火？"    "这话题下哪条爆款？"    "这条得分多少 / 啥 DNA / 好不好做？"    "为什么火 / 怎么改？"    "分镜级蓝图？"
       ↓                  ↓                          ↓                              ↓                      ↓
   60s 热搜          新榜 API                   hotspot 算法层                    ACMM AI 翻译         toprador
   (灵感库)          (/topics 雷达)              (评分/DNA/可复刻)                (whyItHit/howToAdapt)  深分析
                                                                                                       
   广 / 浅 / 实时    深 / 中 / T-3              全 / 客观 / 时序                  人话 / 主观             单条 / 深 / 慢
       ↓                  ↓                          ↓                              ↓                      ↓
   首页轮播          /topics 卡片                /topics 卡片下方"得分"             卡片顶部 LLM 总结      用户点"深入"触发
   横向滚动          网格 + 缩略图                展开看 5 维分 + DNA + 可复刻      "为什么/怎么改"        30s 后画布初始化
```

**整合后的产品层级**：
- **数据层** = 60s + 新榜 + hotspot 时序表（持久化结构化）
- **算法层** = hotspot 双轨/五维 + DNA + 可复刻 + 飙升 + 空位
- **AI 翻译层** = ACMM whyItHit/howToAdapt（把得分翻译成人话）
- **深分析层** = toprador 分镜级蓝图（按需）

### 2.3 四源协同的杀手锏场景（更新版）

**场景**：用户想拍 #自律早起

```
1. 用户进 Cascade 首页
   ↓
2. 看到 60s 抖音热搜轮播："#自律早起 排第 3，今日上升 +15"（实时）
   ↓
3. 点入 → 跳 /topics 雷达，筛选"自律早起"标签
   ↓
4. 看到新榜里这话题下的 5 个爆款卡片（hotspot 已预先打分入库）
   每个卡片自带：
   - 综合得分 87/100（hotspot 五维评分）
   - DNA 标签：收藏主导（hotspot 互动 DNA）
   - 可复刻性 78/100（hotspot 算法）
   - 蓝海标签（hotspot 竞争空位）
   - 推荐时长：30-60 秒（hotspot 数据驱动）
   - 上升趋势 +25%（hotspot 飙升检测）
   ↓
5. 选用户A "5 点起床实录" 那条（50w 赞）
   ↓
6. 点 "AI 分析"（3 秒）
   → ACMM 浅分析把上面的客观数据翻译成人话：
     "为什么火：a) 早起焦虑是普世痛点 b) 实录形式真实感强 c) hook 用'你信吗'抓人"
     "怎么改造（基于你的赛道：宝妈辅食）：a) ...b) ...c) ..."
   ↓
7. 用户觉得有意思 → 点 "想要更深入？"
   ↓
8. 触发 toprador 深分析（30 秒）
   → 拿到完整 analysis_result（分镜级）
   ↓
9. 用户决定进画布 → "用我的赛道（宝妈辅食）复刻"
   ↓
10. 画布初始化：
    - agent 拿着 hotspot 评分 + ACMM 翻译 + toprador 分镜
    - 自动建议 character 锚点（基于用户激活的"宝妈辅食"赛道索引中的角色）
    - 自动建议 scene 锚点（从 scenes[].scene 派生 + 赛道场景映射）
    - 自动生成剧本（基于原 dialogue_and_narration + 赛道经验风格）
    - 自动建议每个 scene 的 imagePrompt（基于 analysis 的 visual_content）
   ↓
11. 用户审核 3 个闸门 → 出片 → 复制发布包
```

**对比 v0**：v0 是"三源 + AI 浅分析"，v1 是 **"四源 + 算法层 + AI 翻译层 + 深分析层"**——选题客观性大幅跃升。

---

## 3. hotspot 算法中台详解

> 这部分是 v1 新增的核心——把 hotspot 已经在 OPPO 内部生产验证过的算法层完整接入 Cascade。

### 3.1 算法清单

| 算法 | 输入 | 输出 | 实现位置 |
|---|---|---|---|
| **双轨评分**（泛热点） | 60s 热搜记录 | 热度 × 0.4 + 排名 × 0.2 + 可玩法化 × 0.25 + 传播潜力 × 0.15 → 0-100 | hotspot `hotsearch/topic_scorer.py:score_general_topic` |
| **双轨评分**（品牌契合 / 赛道契合） | 60s 热搜 + 用户激活的赛道索引 | 热度 × 0.3 + 功能匹配 × 0.3 + 场景落地 × 0.25 + 品牌契合 × 0.15 → 0-100 | hotspot `hotsearch/topic_scorer.py:score_coloros_topic`（去 ColorOS 化后） |
| **五维评分** | 新榜话题数据 | 话题热度 × 0.3 + 趋势加速度 × 0.25 + 内容效率 × 0.2 + 品牌契合 × 0.15 + 竞争空位 × 0.1 → 0-100 | hotspot `newrank/topic_scorer.py:score_topic` |
| **互动 DNA 四格** | 视频互动数据（点赞/收藏/评论/分享） | 主导消费方式 + 分布百分比 | hotspot `newrank/topic_scorer.py:classify_topic_dna` |
| **可复刻性 0-100** | 视频标题 + 粉丝量 + 时长 | 0-100 分（标题关键词 +30、粉丝差距 +20、时长档 +0~+20）+ 复刻难度标签 | hotspot `douhot/analyze_data.py` + `topic-pipeline/pipeline.py:_calc_replicability` |
| **最佳时长推荐** | 话题下所有视频时长 + 互动 | 6 档桶聚合（≤15s / 15-30s / 30-60s / 60-120s / 2-5min / 5min+）+ 平均互动 → 最佳档 | hotspot `newrank/topic_scorer.py:recommend_duration` |
| **飙升话题检测** | 时序数据（前 N 天 vs 当前） | 增长率（5x = 100 分）→ 飙升话题列表 | hotspot `newrank/data_prepare_mysql.py:build_rising_topics` |
| **竞争空位** | 话题出现次数 | zone（蓝海 ≤5 / 机会型 5-20 / 常规 20-50 / 红海 >50） | hotspot `newrank/topic_scorer.py:build_competition_map` |
| **创作者雷达** | rank_data 多日聚合 | 常驻爆款 / 素人黑马（粉丝 <1w 但互动爆发） / 赛道专精（按一/二级分类聚合） | hotspot `ops-account-radar/data_prepare_mysql.py` |
| **三池过滤** | 热搜标题 | light_popular / hardcore / gossip / neutral | hotspot `hotsearch/topic_scorer.py:classify_hot_search` |
| **主题契合度** | 用户主题词 + 标题 | 0-100（命中数 × 40，上限 100） | hotspot `topic-pipeline/theme_utils.py:calc_theme_fit` |
| **主题驱动三轨流水线** | 用户主题 + 启用轨道 | 三轨数据交叉过滤打分 → 统一 JSON | hotspot `topic-pipeline/pipeline.py:run_pipeline` |

### 3.2 算法输出在产品里的呈现

每个 trending 卡片背后都有 hotspot 的算法层输出：

```
┌──────────────────────────────────────────────┐
│ #3  用户A · "5 点起床实录"              ↑+15  │ ← 来自新榜 rank
│                                              │
│ [视频缩略图]                                  │
│                                              │
│ 早起焦虑直击！主角凌晨 5 点起床的真实记录...   │
│                                              │
│ 50w ♥  3w 收藏  1.2w 评论  4.5k 分享           │ ← 来自 newrank rank_data
│                                              │
│ ── 综合得分 87/100 ──────────────────────── │
│   热度 92 | 趋势 88 | 效率 78 | 契合 90 | 空位 85 │ ← hotspot 五维
│                                              │
│ ── 互动 DNA ──                                │
│   ● 收藏主导（45%） ● 点赞 30% ● 评论 18%      │ ← hotspot DNA
│                                              │
│ ── 可复刻性 78/100 容易复刻 ──                │
│   关键词 +20 | 粉丝差 +15 | 时长档 +20         │ ← hotspot 可复刻
│                                              │
│ ── 推荐时长 30-60 秒（数据驱动） ──            │
│                                              │
│ 🟢 蓝海赛道（话题出现 4 次）                   │ ← hotspot 空位
│ ↑ 飙升 +25%                                   │ ← hotspot 飙升
│                                              │
│ [AI 分析 ▾]   [用这条 →]                       │
└──────────────────────────────────────────────┘
```

点 [AI 分析 ▾] 后 ACMM AI 翻译层加在顶部：

```
┌──────────────────────────────────────────────┐
│ 🤖 ACMM AI 总结                                │
│                                              │
│ 为什么火：                                    │
│ • 早起焦虑是普世痛点                          │
│ • 实录形式真实感强                            │
│ • hook 用"你信吗"抓人                         │
│                                              │
│ 怎么改造（你的赛道：宝妈辅食）：              │
│ • 用宝妈视角讲早起带娃日常                    │
│ • 把"5 点起床"改为"6 点起床备辅食"             │
│ • 用厨房特写代替卧室特写                      │
│                                              │
│ ── 客观数据 ──（hotspot 算法层在下方展开）     │
│ ┌──────────────────────────────┐             │
│ │ 综合得分 87/100              │             │
│ │ DNA: 收藏主导 (45%)          │             │
│ │ 可复刻性 78/100 容易          │             │
│ │ 蓝海赛道 / 飙升 +25%          │             │
│ └──────────────────────────────┘             │
└──────────────────────────────────────────────┘
```

**层级清晰：**
- 顶部 ACMM AI 给"人话叙事"
- 底部 hotspot 算法给"客观分数 + 维度"
- 两者互补，不重复

### 3.3 算法 vs LLM 的产品哲学

| 维度 | hotspot 算法层 | ACMM AI 翻译层 |
|---|---|---|
| **特性** | 确定性、可量化、稳定 | 创造性、个性化、有风格 |
| **优势** | 用户可信任、可对比、可筛选 | 用户能读懂、能行动 |
| **形态** | 数字 + 标签 + 分布图 | 完整段落 |
| **成本** | 低（一次算法，多次复用） | 高（每次 LLM 调用 ~¥0.05-0.5） |
| **场景** | 排序、筛选、分组、雷达图 | 总结、对话、推理 |
| **产品定位** | "基础设施层"（必须有） | "增值层"（freemium 限次） |

**配合方式（MVP）**：
- **卡片默认显示**：hotspot 算法层（得分 + DNA + 可复刻）—— 任何用户都能看
- **点 AI 分析展开**：ACMM AI 翻译层（whyItHit + howToAdapt）—— freemium 限次

---

## 4. 赛道索引架构（去 ColorOS 化的产品级亮点）

> hotspot 里大量针对 ColorOS（功能映射、葵花宝典、三池过滤）的代码，我们把它**重构为通用的"赛道索引"架构**。这是 hotspot 整合的最大产品级亮点。

### 4.1 概念定义

**赛道索引（Niche Index）** = 一个用户/账户的"内容创作领域字典"，包含：

```typescript
interface NicheIndex {
  id:                 UUID;
  owner_user_id:      UUID;
  
  // 基础元信息
  name:               string;          // "宝妈辅食" / "ColorOS 营销" / "3C 数码测评"
  description:        string;          // 一段话描述
  
  // 三池过滤词表（继承 hotspot 设计）
  light_popular_keywords: string[];    // 用户的"轻松泛大众优先池"
  hardcore_keywords:      string[];    // 用户的"硬核降权池"
  gossip_keywords:        string[];    // 用户的"八卦过滤池"
  
  // 场景 → 功能映射（继承 hotspot COLOROS_FEATURE_MAP 结构）
  scenario_map: Array<{
    trigger_keyword:  string;          // "穿搭"
    feature:          string;          // "AI 灵感成片"
    category:         string;          // "影像创作"
    path:             string;          // "相册 > 编辑 > AI 图像助手"
    scenario:         string;          // "穿搭照片 AI 自动调出最佳构图"
  }>;
  
  // 经验风格（继承 hotspot 葵花宝典）
  style_principles: {
    voice:            string;          // "生活化小剧场，不用工程术语"
    tone:             string;          // "暖、亲切、不油腻"
    avoid:            string[];        // 禁用词清单
    formula:          string[];        // 常用爆款公式
  };
  
  // 品牌包（B2B 专用，B2C 可空）
  brand_pack?: {
    logo_url:         string;
    color_palette:    string[];
    font_family:      string;
    tagline:          string;
  };
  
  // 商业化
  visibility:         'private' | 'shared' | 'marketplace';
  price_fen:          number;          // marketplace 上架时定价
  share_count:        number;
  
  created_at:         timestamp;
  updated_at:         timestamp;
}
```

### 4.2 三档用户对赛道索引的使用

| 用户档 | 赛道索引 |
|---|---|
| **个人创作者**（Free） | 1 个默认赛道（"我的赛道"）+ AI 自动从历史 run 推断 |
| **个人创作者**（Pro） | 最多 5 个赛道，可手动维护 |
| **MCN**（Team） | N 个赛道（按 IP / 客户分），团队共享 |
| **品牌**（Enterprise） | 品牌库（含 brand_pack + 完整 scenario_map），可上传企业内部"功能索引"文档 |

### 4.3 ColorOS 作为示例 / 演示

hotspot 现有的 ColorOS 功能映射（`COLOROS_FEATURE_MAP` + `SCENARIO_FEATURE_MAP`）**直接作为 Cascade 内置的"示例品牌库"**：

- 注册时引导用户："要不要看个示例？"
- 示例库 = "ColorOS 营销" 完整赛道索引（带 60+ 功能、20+ 场景、葵花宝典风格）
- 用户参考示例 → 编辑出自己的赛道索引

**对 hotspot 代码影响极小**：把 `COLOROS_FEATURE_MAP` 包装成"默认赛道索引种子" + 把硬编码的 `coloros_index_path` 改为 `niche_index_id` 参数。

### 4.4 赛道索引的商业化（v3 重点）

- **Free**：1 个赛道、AI 自动推断、不可分享
- **Pro**：5 个赛道、可手动维护、可保存为私有模板
- **Team**：N 个赛道、团队共享
- **Enterprise**：品牌库 + brand_pack + 上传 docx/pdf 解析为赛道索引
- **Marketplace**（V2）：用户可上架自己的赛道索引到市场，付费订阅或买断，平台 30% 抽成
  - 例："母婴博主的 30 个爆款选题模板" ¥39 买断
  - 例："3C 数码测评 niche-index" ¥99 / 月订阅

---

## 5. 入口形态：三段并存 × 渐进式四层学习

### 5.1 入口 1 · 首页热点轮播

**位置**：首页输入框下方、"我的项目"上方
**内容**：5–10 条 60s 实时热搜横向滚动 + **每条预先用 hotspot 算法层打分**（5 分钟缓存）
**形态**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔥 今日热点                                                  查看全部 →  │
│                                                                          │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│ │ 抖音 #1   │ │ 微博 #2   │ │ 知乎 #1   │ │ B 站 #5   │ │ AI 资讯  │       │
│ │ 自律早起  │ │ xx 事件   │ │ xx 知识   │ │ xx 番剧   │ │ Sora 3.0 │       │
│ │ 87/100    │ │ 65/100    │ │ 91/100    │ │ 78/100    │ │          │       │
│ │ 🟢 蓝海    │ │ ⚪ 常规    │ │ 🟢 蓝海    │ │ 🟡 机会型  │ │          │       │
│ │ [创作]    │ │ [创作]    │ │ [创作]    │ │ [创作]    │ │ [创作]    │       │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

**变化**：每张卡片自带 hotspot 综合得分 + 竞争空位标签——首页就能看到客观选题质量。

### 5.2 入口 2 · 输入框对话式

变化（基于 hotspot 整合）：
- agent 调用的 `search_trending` tool 现在**直接对应 hotspot topic-pipeline**
- 输出含完整 hotspot 算法层（评分 + DNA + 可复刻 + 空位）
- 不需要再单独写"unified trending"逻辑——hotspot pipeline 就是它

### 5.3 入口 3 · /topics 独立雷达页

**Tab 结构**（hotspot 整合后扩充）：

```
/topics 雷达
├── Tab: 实时热点（60s 实时数据）
├── Tab: 视频爆款（新榜深度卡片 + hotspot 五维评分）
├── Tab: 飙升话题（hotspot rising_topics）       ← 新
├── Tab: 创作者库（hotspot account-radar）        ← 新（合并自原 v0 §3.3）
├── Tab: 蓝海机会（hotspot 竞争空位 + 蓝海/机会型筛选）   ← 新
├── Tab: AI 视频专项（hotspot douhot 数据，数据源待确认）  ← 新（条件展示）
└── 顶部：NichePanel（用户赛道索引切换 / 编辑）    ← v1 重构
```

### 5.4 渐进式**四层**学习（v1 升级，从三层到四层）

```
STAGE 0 · 用户点击 trending 卡片
   │
   ▼ 卡片默认显示
STAGE 1 · hotspot 算法层（瞬时显示，预先入库的客观分数）
   │ 得分 87 / DNA 收藏主导 / 可复刻 78 / 蓝海 / 飙升 +25%
   │
   ▼ 点 "AI 分析 ▾"（3 秒）
STAGE 2 · ACMM AI 翻译层（基于 hotspot 数据 + 用户 niche 生成人话）
   │ "为什么火：..." + "怎么改造（基于你的赛道）：..."
   │
   ▼ 点 "想要更深入？深度分析 →"（30 秒，¥0.5）
STAGE 3 · toprador 深分析（分镜级蓝图）
   │ viral_analysis + scenes[] × 8
   │
   ▼ 点 "进画布"
STAGE 4 · Cascade 画布初始化
   agent 拿着所有层的数据 + 用户激活的赛道索引
   → 自动初始化 script + character + scene + shots + imagePrompts
```

**变化点**：
- v0 是三层（浅 → 深 → 画布）
- v1 是 **四层**（**hotspot 算法层** → ACMM AI 翻译 → toprador 深 → 画布）
- hotspot 算法层是**零成本预先入库**的，不消耗用户配额
- ACMM AI 翻译是**主动 LLM 调用**，消耗 freemium 配额
- toprador 深分析是**最贵的多模态调用**，深度内容创作时再用

### 5.5 关键 UX 原则（v1 更新）

1. **每层都可单独存在**——只看 hotspot 算法层（不点 AI 分析）就够做"快速筛选"
2. **成本透明**——hotspot 标"免费"，AI 分析标 "免费 N 次/天 / ¥0.05/次"，toprador 标 "30s / ¥0.5"
3. **用户可任意层进画布**——hotspot 层直接进 = "我自己读懂数据"；AI 层 / toprador 层进画布 = 越深越自动化
4. **赛道索引激活影响所有层**：
   - hotspot 算法层：影响"主题契合"和"品牌契合"打分
   - AI 翻译层：影响 howToAdapt 的"基于你赛道"个性化
   - toprador 层：影响后续画布锚点的自动建议

---

## 6. Agent Tool 规范（v1 升级）

### 6.1 Unified Trending Tool（直接对应 hotspot topic-pipeline）

**Tool name**: `search_trending`
**实现**：直接调 hotspot `topic-pipeline/pipeline.py:run_pipeline`

```
search_trending(
  theme?: str,                                    # 主题词，逗号分隔
  tracks?: ['hotsearch', 'newrank', 'replicate'], # 启用的数据轨道
  audience?: 'editor' | 'kos' | 'koc',            # 视角
  niche_index_id?: UUID,                          # 激活的赛道索引（v1 新增）
  crawl_time?: str,                               # 热搜批次
  start_date?: str, end_date?: str,               # 新榜日期范围
) -> dict

返回（来自 hotspot pipeline 的统一 JSON）:
{
  meta: { theme, keywords, audience, generated_at, tracks_enabled },
  tracks: {
    hotsearch: {
      data_source: { type, crawl_time, total_loaded },
      general_topics: [{ title, platform, rank, hot_value, link, theme_fit, scores: {total, hot, rank, playability, spread} }],
      coloros_topics: [...]                       # 改名为 niche_topics
    },
    newrank: {
      data_source: { type, date_range },
      scored_topics: [{ topic, platforms, count, avg_interact, dominant_dna, recommended_duration, theme_fit, scores: {total, heat, trend, efficiency, brand_fit, gap}, top_contents }],
      rising_topics: [...]
    },
    replicate: {
      data_source: { type, crawl_time },
      top_replicable: [{ title, author, replicability_score, duration_level, theme_fit }],
      directions: [{ tag, count }]
    }
  }
}
```

### 6.2 Analyze Trending Tool（v1 增强）

```
analyze_trending_item(opus_id, platform, depth, niche_index_id?) -> dict

depth='shallow': ACMM topic-analysis（3 秒，3+3 句 LLM）
depth='deep':    toprador video-analysis（30 秒，分镜级 analysis_result）
depth='algo':    hotspot 算法层（瞬时，已入库无需调用）  ← v1 新增
```

### 6.3 Niche Index Tools（v1 新增）

```
list_niche_indices(user_id) -> list[NicheIndex]
get_active_niche_index(user_id) -> NicheIndex
update_niche_index(niche_id, updates) -> NicheIndex
create_niche_index_from_template(template='coloros_marketing' | ...) -> NicheIndex
ai_infer_niche_from_runs(user_id) -> NicheIndex   # 从用户历史 run 自动推断
```

### 6.4 Creator Radar Tools（v1 新增）

```
search_creators(niche_index_id?, category?) -> list[Creator]
  → 调 hotspot ops-account-radar
  → 返回 常驻爆款 + 素人黑马 + 赛道专精 三组创作者

get_creator_profile(uid, platform) -> CreatorProfile
```

### 6.5 Operations Report Tools（v1.5 新增）

```
generate_topic_report(date_range, niche_index_id?, format='html') -> ReportLink
  → 调 hotspot ops-insight + ops-topic-pick
  → 生成 HTML 暗色主题报告 + 上传 → 返回 URL

generate_account_report(date_range, niche_index_id?) -> ReportLink
  → 调 hotspot ops-account-radar
```

### 6.6 Tool 拓扑（v1 更新）

```
                   ┌────────────────────────┐
                   │  LangGraph Agent       │
                   │  (Director)            │
                   └───────┬────────────────┘
                           │
        ┌──────────────────┼─────────────────────┐
        │                  │                     │
        ▼                  ▼                     ▼
  search_trending  analyze_trending_item  niche / creator / report tools
        │                  │                     │
        ▼                  ▼                     ▼
  ┌──────────────────────────────────────────────────┐
  │ hotspot sidecar (Python)  ← v1 新增的核心        │
  │ - 4 张数据表 + 定时任务                          │
  │ - 9 个 Skills 算法（评分/DNA/可复刻/...）         │
  │ - topic-pipeline 主题驱动流水线                  │
  │ - ops-* 报告生成                                 │
  └──────┬─────────────┬───────────────┬────────────┘
         │             │               │
         ▼             ▼               ▼
   ┌──────────┐ ┌──────────────┐ ┌──────────┐
   │ 60s      │ │ Newrank      │ │ toprador │
   │ Sidecar  │ │ Sidecar      │ │ Analysis │
   │ :4399    │ │ :3000        │ │ :8080    │
   └──────────┘ └──────────────┘ └──────────┘
```

---

## 7. 数据 schema（v1 增加 hotspot 4 张表 + niche_index 表）

### 7.1 hotspot 直接搬过来的 4 张表（MySQL → Postgres）

```sql
-- 1. 热搜快照表（hotspot 原 hot_search_snapshot）
CREATE TABLE hot_search_snapshot (
  id              BIGSERIAL PRIMARY KEY,
  platform        VARCHAR(20) NOT NULL,   -- weibo / douyin / bilibili / rednote
  rank            INT NOT NULL,
  title           VARCHAR(500) NOT NULL,
  hot_value       VARCHAR(100),
  link            VARCHAR(1000),
  cover           VARCHAR(1000),
  crawl_time      TIMESTAMPTZ NOT NULL,   -- 抓取时间（定时 02/06/08:00 等）
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  -- 商业化 hook
  data_source_tier TEXT DEFAULT 'free',
  INDEX (platform, crawl_time DESC, rank)
);

-- 2. 榜单数据表（hotspot 原 rank_data）
CREATE TABLE rank_data (
  id              BIGSERIAL PRIMARY KEY,
  record_date     DATE NOT NULL,
  platform        VARCHAR(10) NOT NULL,   -- dy/ks/bz/xhs
  rank            INT NOT NULL,
  uid             VARCHAR(100),
  nickname        VARCHAR(255),
  account         VARCHAR(255),
  avatar          TEXT,
  fans_num        BIGINT,
  like_num        BIGINT,
  comment_num     BIGINT,
  share_num       BIGINT,
  collect_num     BIGINT,
  interact_num    BIGINT,
  opus_id         VARCHAR(100),
  title           VARCHAR(255),
  url             TEXT,
  type            VARCHAR(50),
  cover           TEXT,
  description     TEXT,
  duration        INT,
  first_category  VARCHAR(100),
  second_category VARCHAR(100),
  publish_time    TIMESTAMPTZ,
  update_time     TIMESTAMPTZ,
  platform_extra  TEXT,                   -- JSON 含 topics 字段
  -- 商业化 hook
  data_source_tier TEXT DEFAULT 'pro',
  UNIQUE (platform, record_date, rank)
);

-- 3. AI 视频基础信息表（hotspot 原 ai_video_info）
CREATE TABLE ai_video_info (
  item_id         VARCHAR(64) PRIMARY KEY,
  item_url        VARCHAR(512),
  item_title      TEXT,
  nick_name       VARCHAR(128),
  publish_time    TIMESTAMPTZ,
  item_cover_url  VARCHAR(1024),
  item_duration   INT,                    -- ms
  on_list_count   INT DEFAULT 0,
  first_seen_time TIMESTAMPTZ,
  last_seen_time  TIMESTAMPTZ
);

-- 4. AI 视频指标信息表（hotspot 原 ai_video_metrics）
CREATE TABLE ai_video_metrics (
  id              BIGSERIAL PRIMARY KEY,
  item_id         VARCHAR(64) REFERENCES ai_video_info(item_id),
  rank            INT,
  play_cnt        BIGINT,
  like_cnt        BIGINT,
  score           BIGINT,
  like_rate       DECIMAL(10,6),
  fans_cnt        BIGINT,
  trend_share_cnt  BIGINT,
  trend_like_cnt   BIGINT,
  trend_comment_cnt BIGINT,
  trend_new_fans_cnt BIGINT,
  date_window     INT,                    -- 小时
  crawl_time      TIMESTAMPTZ NOT NULL,
  UNIQUE (item_id, crawl_time)
);
```

### 7.2 v1 新增：赛道索引表

```sql
CREATE TABLE niche_indices (
  id                    UUID PRIMARY KEY,
  owner_user_id         UUID NOT NULL REFERENCES users(id),
  owner_tenant_id       UUID,             -- MCN/品牌共享
  
  -- 基础信息
  name                  VARCHAR(100) NOT NULL,
  description           TEXT,
  is_default            BOOLEAN DEFAULT FALSE,
  is_template           BOOLEAN DEFAULT FALSE,  -- 系统种子（如 coloros_marketing）
  
  -- 三池过滤词表（JSONB）
  light_popular_keywords  JSONB DEFAULT '[]',
  hardcore_keywords       JSONB DEFAULT '[]',
  gossip_keywords         JSONB DEFAULT '[]',
  
  -- 场景 → 功能映射
  scenario_map            JSONB DEFAULT '[]',
  
  -- 经验风格
  style_principles        JSONB DEFAULT '{}',
  
  -- 品牌包（B2B）
  brand_pack              JSONB,
  
  -- 商业化
  visibility              TEXT DEFAULT 'private',  -- private / shared / marketplace
  price_fen               INT DEFAULT 0,
  share_count             INT DEFAULT 0,
  
  created_at              TIMESTAMPTZ DEFAULT NOW(),
  updated_at              TIMESTAMPTZ DEFAULT NOW(),
  
  INDEX (owner_user_id, owner_tenant_id),
  INDEX (visibility, is_template)
);

-- 用户激活的赛道（每个 run 可关联一个）
ALTER TABLE cascade_runs ADD COLUMN active_niche_index_id UUID REFERENCES niche_indices(id);
ALTER TABLE projects ADD COLUMN default_niche_index_id UUID REFERENCES niche_indices(id);
```

### 7.3 v1 新增：hotspot 分析结果缓存

```sql
-- hotspot 算法层结果缓存（避免重复算）
CREATE TABLE hotspot_analysis_cache (
  id                 BIGSERIAL PRIMARY KEY,
  source_type        VARCHAR(20),         -- 'general' | 'niche' | 'newrank' | 'replicate'
  source_ref         VARCHAR(200),        -- title + platform + crawl_time hash
  niche_index_id     UUID REFERENCES niche_indices(id),
  
  scores_json        JSONB NOT NULL,      -- 5 维评分 / 双轨评分
  dna_json           JSONB,               -- 互动 DNA
  replicability      INT,                 -- 0-100
  recommended_duration VARCHAR(50),
  zone               VARCHAR(20),         -- 蓝海/机会型/常规/红海
  trend_change       DECIMAL(5,2),        -- 飙升 %
  
  computed_at        TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE (source_type, source_ref, niche_index_id)
);
```

### 7.4 cascade_runs trending_source_meta 字段扩充（v1）

```sql
-- 已有：
-- trending_source_meta JSONB
-- 内容扩充示例：
{
  "source_type": "trending_deep",
  "platform": "dy",
  "opus_id": "xxxxx",
  "rank": 3,
  "source_url": "https://...",
  "analysis_id": 12345,
  "depth_used": "deep",
  
  // v1 新增：hotspot 算法层快照（用于复盘）
  "hotspot_snapshot": {
    "scores": { total: 87, heat: 92, trend: 88, efficiency: 78, brand_fit: 90, gap: 85 },
    "dna": { dominant: "collect", distribution: { like: 30, collect: 45, comment: 18, share: 7 } },
    "replicability": 78,
    "zone": "蓝海",
    "trend_change": 25,
    "computed_at": "2026-05-18T08:00:00Z"
  },
  
  // v1 新增：用户激活的赛道索引
  "niche_index_snapshot": {
    "id": "uuid",
    "name": "宝妈辅食",
    "theme_fit_at_time": 85
  }
}
```

---

## 8. 商业化扩展点（v1 大幅扩充 · hotspot 整合带来的新 surface）

### 8.1 数据源分层（v0 已有）

不变。

### 8.2 AI 分析按次（v0 已有）

不变。

### 8.3 v1 新增：赛道索引商业化（hotspot 整合关键）

```
Free:    1 个赛道（AI 自动推断 + ColorOS 示例可参考）
Pro:     5 个赛道，可手动维护
Team:    N 个赛道（团队共享 + 跨成员可见）
Enterprise: 品牌库 + brand_pack + 上传 docx/pdf 解析为赛道索引
Marketplace (V2): 创作者上架自己的赛道索引到市场，付费订阅或买断（30% 平台抽成）
```

**实施 hook**：
- `niche_indices.visibility`、`price_fen`、`share_count` day-1 备好
- MVP UI 只暴露"私有赛道"管理；marketplace V2 加 UI

### 8.4 v1 新增：创作者雷达订阅

```
Free:    看 Top 10 创作者 / 月（hotspot account-radar 入口）
Pro:     看 Top 50 / 月
Team:    自定义对标列表（5 个）+ 自动监控变化
Enterprise: 自定义对标列表（无限）+ 创作者动态推送
```

### 8.5 v1 新增：运营报告订阅

利用 hotspot 已有的 HTML 报告生成能力：

```
Free:    画布卡片视图（无独立报告）
Pro:     按需生成"单次选题报告"（1 次/月免费、超额 ¥9/次）
Team:    周报 / 月报订阅（含创作者雷达 + 深度洞察 + 选题推荐）
Enterprise: 月度行业舆情 PDF + 自定义维度报告
```

每个报告对应 hotspot Skills：
- 选题推荐报告 = `ops-topic-pick`
- 深度洞察报告 = `ops-insight`
- 账号雷达报告 = `ops-account-radar`
- 主题三轨报告 = `topic-pipeline`

### 8.6 V2-V3 长期扩展（v0 已有 + v1 调整）

| Feature | 描述 | 价格 | 时机 |
|---|---|---|---|
| 关键词订阅 / 推送 | 上热搜推送邮件 / 微信 | ¥99/月 加包 | V2 |
| 品牌词监控 | 品牌 + 竞品提及监控 | ¥5w/年起 | V2.5 |
| 舆情周报 / 月报 | 行业舆情 PDF（基于 hotspot 报告） | ¥2w/年 加包 | V2.5 |
| 关键词广告位 | 品牌付费让内容关联出现（标"赞助"） | CPC | V3 |
| trending-as-a-service API | 给开发者 / BI 工具 | ¥0.5/call | V2 |
| 行业垂类雷达 | 美妆/3C/母婴专属流（hotspot 三池过滤改造） | ¥299/月 加包 | V2 |
| 赛道索引市场 | UGC 上架 + 抽成 | 30% 抽成 | V2 |

### 8.7 与创作侧的联动变现（核心数据）

```
TopicRadar → hotspot 算法层 → 浅分析 → 深分析 → 创作 → 复制发布 → 用户感觉"赚到了"
                                                                ↓
                                                             续费率提升
```

跟踪指标（埋点详见 `DATA_DASHBOARD.md` §2.2）：
- `topic_card_view → hotspot_score_visible → shallow_analysis_triggered → deep_analysis_triggered → enter_canvas_from_trending → run_completed` 的转化漏斗
- 不同 hotspot 综合得分段（70-80 / 80-90 / 90+）的"复刻成片率"
- 用户激活赛道索引前后的"AI 分析采纳率"
- 复刻视频的发布后留存 vs 自由创作的留存（V2 数据回流后）

**关键埋点事件**（DATA_DASHBOARD §2.2 完整事件目录的子集）：
- `topic_card_view` — trending 卡片露出
- `hotspot_score_visible` — 算法层数据呈现（含 total_score / dna / zone / replicability）
- `shallow_analysis_triggered` — ACMM 浅分析触发
- `deep_analysis_triggered` — toprador 深分析触发
- `enter_canvas_from_trending` — 从热点进画布
- `niche_index_activated` — 激活赛道索引
- `niche_index_edited` — 编辑赛道索引

---

## 9. 实施工时（v1 更新）

| 任务 | 工时 |
|---|---|
| 60s 服务接入（toprador 直接部署） | 0.5d |
| Newrank Node sidecar 化 | 2d |
| toprador video-analysis 模块脱敏 + 公网部署 | 5d |
| **hotspot 整套脱敏 + Postgres 迁移** | **5d**（新） |
| **hotspot 4 张表 schema 迁 Postgres + 定时任务** | **2d**（新） |
| **hotspot 9 个 Skills 算法整套整合到 Cascade sidecar** | **3d**（新） |
| **去 ColorOS 化 + 赛道索引架构重构** | **5d**（新） |
| **niche_indices 表 + ColorOS 示例种子** | **2d**（新） |
| Cascade 后端 `search_trending` / `analyze_trending_item` / niche / creator tools | 2d |
| 渐进式四段 UX 前端（卡片 hotspot 层 + 浅 + 深 + 进画布过渡） | 5d |
| `/topics` 雷达页（6 个 Tab：实时 + 视频爆款 + 飙升 + 创作者 + 蓝海 + AI 专项） | 4d |
| 首页热点轮播（带 hotspot 评分） | 2d |
| 对话式入口（输入框 agent 接管） | 2d |
| 商业化 hook + 中间件 | 1.5d |
| Trending 溯源 + hotspot_snapshot 字段 | 0.5d |
| `seed_canvas_from_analysis` tool（含 niche_index 上下文） | 2d |
| 测试 + 联调 | 4d |
| **合计** | **~47d ≈ 9 周** |

**对比 v0**（~26d）：+ 21d。但**节省的工时在算法层**：
- v0 是从零写 ACMM topic-analysis（已有 TS）
- v1 hotspot 直接提供 9 个 Skills 算法（如果不用 hotspot，重写这套算法 = +10-15 周）

**净节省 ≈ 5-10 周**（同时算法层从 MVP 级跃升到工业级）。

---

## 10. 相关文档

- `PRODUCT_VISION.md` §3 入口形态 / §4.3-4.4 差异化 / §5.2 商业化 / §6.4 hotspot 关系 / §12.5 hotspot 决策
- `CANVAS_DESIGN.md` §7 数据 schema（含 hotspot 4 表 + niche_indices）
- `DATA_DASHBOARD.md` §2 埋点底座 / §5 C 层 B2B 报告
- `MVP_SCOPE.md` §1.E "hotspot 整合"块 / §1.F 数据统计块
- `ROADMAP_6M.md` M1 hotspot 脱敏 + 埋点底座 / M4 topic-pipeline 接入 / M5 /admin + /me/dashboard

---

*v1（hotspot 整合）相比 v0（三数据源）：算法层 + 4 张表 + 赛道索引 + 创作者雷达 + 运营报告全部到位。这是 Cascade 选题侧的"工业级跃迁"。*
