# Cascade 热点选题深度化整合方案

**Document Status**: Proposal v0.2  
**Date**: 2026-05-20  
**Owner**: Product + Algorithm + Engineering  
**Related**: `TOPIC_TO_CREATION_PIPELINE.md` · `MVP_SCOPE.md` · `PHASED_PLAN.md` · `ELON_PERSPECTIVE_INVESTMENT_REVIEW.md` · `BUFFETT_PERSPECTIVE_INVESTMENT_REVIEW.md` · `NAVAL_PERSPECTIVE_INVESTMENT_REVIEW.md` · `STEVE_JOBS_PERSPECTIVE_INVESTMENT_REVIEW.md` · `ILYA_PERSPECTIVE_INVESTMENT_REVIEW.md` · `KARPATHY_ENGINEERING_RISK_REVIEW.md`

---

## 0. 一句话结论

当前 `hotspot` 已经能解决"哪些话题在火、哪条内容可复刻、哪个话题蓝海"的问题；下一步要把它升级成 **短视频选题决策系统**：

```text
热点发现
  -> 爆款机制拆解
  -> 推荐系统信号评分
  -> 账号/赛道匹配
  -> 未来 3-7 天方向预测
  -> 生成可执行脚本/分镜
  -> 发布后反馈回流校准
```

产品上不要只做"AI 爆款评分"，而要做：

> 给创作者和运营团队每天推荐最值得拍的方向，并说明为什么值得拍、怎么拍、风险是什么、发出去后如何复盘。

**投资判断**：这个新增方向值得投，因为它把 OpenRHTV 从"AI 视频生成工具"推向"短视频创作决策系统"；但只能按学习闭环投资，不能按大推荐系统投资。当前只建议投入 Phase 1-3：规则分 + 结构化机制 + 发布后反馈回流。LightGBM / XGBoost 等模型化推荐必须等真实样本积累后再启动，多模态 Transformer 不进入当前路线图。

---

## 1. 当前热点选题能力盘点

OpenRHTV 现有 `TOPIC_TO_CREATION_PIPELINE.md` 已经定义了较完整的热点到创作链路：

| 层级 | 当前能力 | 已有价值 | 主要缺口 |
|---|---|---|---|
| 数据源 | 60s 热搜、新榜、hotspot 时序、toprador 视频分析 | 有实时热点、榜单数据、深度视频解析 | 缺账号历史反馈、发布后表现曲线、竞品长期跟踪 |
| 算法层 | 双轨评分、五维评分、互动 DNA、可复刻性、飙升、竞争空位 | 能判断"值得看/能不能复刻" | 缺推荐系统信号、未来机会分、账号匹配分 |
| AI 翻译层 | whyItHit / howToAdapt | 能把数据翻译成人话 | 还不够结构化，难以训练模型 |
| 创作层 | 进画布、生成脚本/分镜/资产 | 已经形成"热点 -> 创作"闭环 | 缺"发布后复盘 -> 下次推荐"闭环 |

因此本方案采用 **增量增强**，不替换现有 hotspot，只新增一层 `Deep Topic Intelligence`。

### 1.1 抖音热点宝 / 官方热门榜作为新增数据源

`douhot.douyin.com`（抖音热点宝）和抖音开放平台热门视频榜对当前热点选题体系有直接增量价值。它们不替代 `hotspot`，而是作为 **官方趋势信号源** 接入，补强抖音侧的可信度、飙升判断、低粉爆款发现和官方活动机会。

可补充的数据维度：

| 维度 | 对 OpenRHTV 的价值 | 用途 |
|---|---|---|
| 实时热榜 | 高 | 发现当前抖音正在分发的话题 |
| 飙升热点 | 很高 | 判断未来 1-3 天仍有上升空间的方向 |
| 垂类榜单 | 很高 | 让选题从泛热点变成赛道化热点 |
| 城市榜 | 高 | 服务本地生活、到店、区域商家 |
| 低粉爆款榜 | 很高 | 判断"素人/小号也能复刻"的机会 |
| 热词趋势曲线 | 很高 | 判断热点处于上升、峰值还是衰退 |
| 关联视频数 | 高 | 估算内容饱和度和竞争密度 |
| 评论词频 | 高 | 提炼用户情绪、争议点、二创角度 |
| 高赞案例 | 高 | 作为爆款机制拆解样本 |
| 官方活动日历 | 很高 | 提前发现平台扶持方向 |
| 作品诊断 | 高 | 辅助发布后复盘，但仍需用户授权或截图 |

抖音开放平台热门视频榜可作为优先接入的官方 API。公开文档字段包括 `rank`、`title`、`author`、`digg_count`、`comment_count`、`hot_words`、`play_count`、`item_cover`、`hot_value`、`share_url`。这些字段可以直接映射到 `rank_data` 或新增 `douyin_hot_videos`。

边界也要明确：热点宝主要解决 **热点发现、趋势判断、官方活动、低粉爆款、垂类选题**；它通常不能完整提供 `3秒留存`、`完播率`、`平均观看时长`、`划走率`、`负反馈率` 这类推荐系统核心反馈。这些仍需要：

```text
抖音开放平台用户授权
创作者中心导出
后台截图 OCR
用户手动录入
自有发布/投放系统回传
```

因此推荐的数据源分工是：

```text
热点宝 / 官方榜单 = 官方趋势信号源
新榜 / 第三方数据 = 榜单、竞品、跨平台补充
toprador video-analysis = 爆款机制拆解
创作者后台 / 授权数据 = 发布后真实反馈
OpenRHTV 模型层 = 融合为机会分、创作建议和复盘闭环
```

### 1.2 小红书官方 / 第三方信号作为种草选题数据源

小红书没有一个完全等价于"抖音热点宝"的单一公开平台。它的数据能力分散在创作者后台、商业合作、广告投放、商家经营和第三方趋势平台里。对 OpenRHTV 来说，小红书不能直接套抖音的"爆发传播"逻辑，而要单独建模为 **种草价值预测**。

推荐数据源分工：

| 来源 | 角色 | 可用数据 | 对 OpenRHTV 的价值 |
|---|---|---|---|
| 小红书创作服务平台 / 创作者中心 | 创作者侧后台 | 笔记表现、粉丝增长、创作灵感、官方活动、数据复盘 | 适合账号自进化和创作复盘 |
| 蒲公英 | 品牌/达人合作 | 达人画像、粉丝画像、报价、合作笔记表现、商业转化 | 适合 MCN、品牌投放、达人商业价值评估 |
| 聚光平台 | 广告投放 / 商业创意 | 优质笔记、行业创意、投放效果、关键词、营销链路 | 适合品牌和商家做商业选题 |
| 千帆 | 商家经营 | 商品、订单、店铺、直播、带货笔记、热搜词 | 适合电商、本地生活和店铺内容转化 |
| 第三方数据平台 | 趋势 / 竞品 / 爆文库 | 热门笔记、话题热度、搜索词、达人榜、竞品账号、笔记生命周期 | 适合补齐热点发现和竞品监控 |

小红书侧优先采集的数据维度：

```text
热门笔记
热门搜索词
话题标签热度
收藏数 / 收藏率
评论数 / 评论率
点赞数 / 点赞率
分享数
笔记发布时间
封面图
标题
正文
评论关键词
达人粉丝数
账号垂类
蒲公英合作数据
商品 / 店铺转化数据
```

小红书的核心信号与抖音不同：

```text
抖音：停留、完播、播放增速、转发、强情绪传播
小红书：收藏、搜索、评论质量、封面点击、标题关键词、长尾流量、种草转化
```

因此新增 `xhs_seed_score`，用于衡量"这条选题是否值得在小红书做种草内容"：

```text
xhs_seed_score =
  0.30 * collect_rate
  + 0.20 * comment_quality
  + 0.15 * search_keyword_fit
  + 0.15 * long_tail_growth
  + 0.20 * commercial_conversion_potential
```

小红书数据源在系统里的定位：

```text
创作服务平台 = 账号表现和发布后反馈
蒲公英 = 商业合作与达人价值
聚光 = 商业创意和投放效果
千帆 = 商家经营和商品转化
第三方平台 = 热门笔记、趋势、竞品、爆文库
OpenRHTV 模型层 = 统一成 xhs_seed_score、账号匹配和选题建议
```

---

## 2. 目标用户与商业价值

### 2.1 优先用户

优先做高付费意愿用户，而不是泛娱乐散户：

1. **MCN / 代运营团队**
   - 需要批量选题、批量复盘、批量生成脚本。
   - 愿意为"每天少刷 2 小时、爆款率提升"付费。

2. **本地生活 / 短视频电商团队**
   - 目标明确：到店、私信、成交、线索。
   - 适合做赛道索引和账号匹配。

3. **知识付费 / 个人 IP 团队**
   - 需要稳定选题、标题、观点、脚本。
   - 更看重收藏、关注转化、评论质量。

### 2.2 商业化包装

| 版本 | 核心权益 | 建议价格 |
|---|---|---|
| Free | 每日 5 条热点浅分析、基础爆款库 | 获客 |
| Pro | 深度爆点拆解、账号适配、创作建议、选题报告 | 99-299 元/月 |
| Team | 多账号雷达、竞品监控、发布后复盘、周报/月报 | 999-4999 元/月 |
| Enterprise | 自定义赛道库、私有数据接入、API、模型校准 | 项目制 |

---

## 3. 新增产品能力

### 3.1 /topics 卡片升级

现有卡片已有综合分、DNA、可复刻、蓝海、飙升。新增 6 个决策信号：

```text
推荐系统信号
- 开头停留潜力
- 完播潜力
- 互动潜力
- 转发/收藏潜力
- 负反馈风险

商业信号
- 账号匹配度
- 赛道转化价值
- 竞争饱和度
- 未来 3-7 天机会分
```

卡片示例：

```text
┌──────────────────────────────────────────────┐
│ #演唱会第一视角情绪 Vlog              机会分 86 │
│                                              │
│ 综合 82 | 飙升 +42% | 蓝海-机会型 | 可复刻 78    │
│ DNA: 收藏主导 + 评论共鸣                       │
│                                              │
│ 推荐系统信号                                  │
│ 停留 88 | 完播 74 | 互动 81 | 负反馈风险 12      │
│                                              │
│ 账号匹配                                      │
│ 女性成长账号: 高 | 本地生活: 中 | 电商带货: 低     │
│                                              │
│ 为什么值得拍                                  │
│ 女性情绪共鸣 + 演唱会素材稀缺 + BGM 传播强        │
│                                              │
│ [深度拆解] [生成 3 个选题] [进入画布]             │
└──────────────────────────────────────────────┘
```

### 3.2 新增"方向雷达"

不是只列热点，而是把视频聚类成"内容方向"：

```text
方向 = 主题 + 情绪 + 钩子 + 场景 + 叙事结构 + BGM + 目标人群
```

输出：

```text
未来 3-7 天推荐方向
1. 演唱会第一视角情绪 vlog
2. 女性成长独白 + 旧照片转场
3. 本地生活探店避坑 + 价格反差
4. AI 工具实测 + 结果前置
```

每个方向展示：

- 热度水平
- 增速
- 内容饱和度
- 高质量互动率
- 推荐账号类型
- 可复刻素材要求
- 低成本拍法
- 可生成脚本模板

### 3.3 新增"爆款机制拆解"

把 toprador 分镜分析结果结构化到算法层，形成可训练特征：

| 维度 | 字段 |
|---|---|
| 开头 | first_1s_hook_type、first_3s_conflict、face_in_first_frame、onscreen_text_in_first_2s |
| 节奏 | shot_count、avg_shot_duration、pace_level、emotion_peak_second |
| 情绪 | emotion_tags、pain_point、desire_trigger、identity_resonance |
| 视觉 | scene_tags、person_count、camera_movement、brightness、saturation、warm_tone |
| 文本 | title_formula、subtitle_density、comment_trigger、cta_type |
| 音频 | bgm_type、bgm_trend_score、speech_rate、sound_energy |
| 商业 | conversion_intent、product_binding_strength、brand_safety_risk |

### 3.4 新增"账号匹配"

同一个热点不是所有账号都该拍。新增账号画像：

```text
account_profile = {
  niche_tags,
  audience_tags,
  historical_best_topics,
  historical_best_emotions,
  avg_engagement_baseline,
  avg_completion_baseline,
  content_embedding_centroid,
  commercial_goal
}
```

匹配分：

```text
account_fit =
  0.30 * 主题相似度
  + 0.20 * 受众匹配
  + 0.15 * 历史爆款相似度
  + 0.15 * 素材可获得性
  + 0.10 * 商业目标匹配
  + 0.10 * 风险适配
```

---

## 4. 算法设计

### 4.1 总体模型

参考 X For You、YouTube、TikTok 推荐系统的共性，不直接预测"会不会火"，而是做多目标预测：

```text
候选方向召回
  -> 多维补特征
  -> 风险过滤
  -> 多目标打分
  -> 账号个性化排序
  -> 创作方案生成
```

输出目标：

```text
P(top_10_percent_24h)        # 24h 进入同类 top 10% 概率
P(top_1_percent_72h)         # 72h 进入同类 top 1% 概率
pred_completion_rate         # 完播率预测
pred_avg_watch_time          # 平均观看时长预测
pred_like_rate
pred_comment_rate
pred_collect_rate
pred_share_rate
pred_follow_convert_rate
negative_feedback_risk
opportunity_score            # 最终用于选题排序
```

### 4.2 第一阶段：规则分 + LLM 结构化

在没有足够发布后数据前，先用规则模型：

```text
opportunity_score =
  0.18 * hotspot_total
  + 0.12 * trend_acceleration
  + 0.10 * competition_gap
  + 0.12 * replicability
  + 0.12 * account_fit
  + 0.10 * hook_strength
  + 0.08 * completion_potential
  + 0.08 * interaction_potential
  + 0.06 * commercial_value
  - 0.08 * saturation_risk
  - 0.06 * safety_risk
```

接入抖音热点宝 / 官方热门榜后，规则分增加 `official_signal`：

```text
opportunity_score =
  0.16 * hotspot_total
  + 0.14 * official_hotspot_score
  + 0.12 * rising_score
  + 0.10 * low_follower_replicability
  + 0.10 * account_fit
  + 0.09 * category_fit
  + 0.08 * competition_gap
  + 0.08 * content_mechanism_score
  + 0.06 * official_activity_bonus
  - 0.09 * saturation_risk
  - 0.06 * safety_risk
```

字段含义：

| 信号 | 来源 | 解释 |
|---|---|---|
| `official_hotspot_score` | 热点宝 / 官方热门榜 | 官方热度值、排名、趋势曲线综合 |
| `rising_score` | 飙升榜 / 增长曲线 | 是否仍处于上升期 |
| `low_follower_replicability` | 低粉爆款榜 | 小账号也能做起来，复刻价值更高 |
| `category_fit` | 垂类榜 / 用户赛道 | 是否命中用户激活赛道 |
| `official_activity_bonus` | 官方活动日历 | 是否有平台活动或流量扶持窗口 |

小红书单独增加种草机会分，不直接复用抖音完播/爆发逻辑：

```text
xhs_opportunity_score =
  0.18 * xhs_seed_score
  + 0.14 * search_trend_score
  + 0.12 * collect_rate_score
  + 0.12 * comment_quality_score
  + 0.10 * long_tail_growth_score
  + 0.10 * account_fit
  + 0.08 * commercial_conversion_score
  + 0.08 * cover_title_strength
  + 0.06 * low_follower_replicability
  - 0.08 * saturation_risk
  - 0.06 * compliance_risk
```

小红书字段解释：

| 信号 | 来源 | 解释 |
|---|---|---|
| `search_trend_score` | 搜索词 / 话题热度 | 小红书强搜索，搜索趋势比瞬时热榜更重要 |
| `collect_rate_score` | 笔记收藏 | 判断攻略、清单、测评、教程类价值 |
| `comment_quality_score` | 评论语义 | 咨询、求链接、求教程、求价格等商业意图 |
| `long_tail_growth_score` | 多日表现曲线 | 小红书内容常有长尾，不只看首日爆发 |
| `cover_title_strength` | 封面 + 标题 | 小红书点击和搜索强依赖封面标题 |
| `compliance_risk` | 平台规范 | 软广、医疗、金融、夸大功效等风险 |

LLM 只负责把视频/话题转成结构化字段，不直接当最终预测器：

```json
{
  "hook_type": "first_person_emotion",
  "pain_point": "女性成长与情绪告别",
  "emotion_tags": ["共鸣", "治愈", "期待"],
  "comment_trigger": "你也有一首歌替你告别过谁吗",
  "replication_requirements": ["演唱会素材", "人群合唱", "情绪字幕"],
  "risk_notes": ["素材版权", "过度煽情"]
}
```

### 4.3 第二阶段：LightGBM / XGBoost

当积累 1000-50000 条"视频特征 + 表现数据"后，用树模型替代部分规则分。

输入特征：

```text
hotspot_features:
  heat, trend, efficiency, gap, dna_distribution, recommended_duration

content_features:
  hook_type, shot_count, avg_shot_duration, emotion_tags, scene_tags,
  title_formula, subtitle_density, bgm_type, visual_style

account_features:
  account_baseline, niche_tags, historical_topic_embedding, historical_best_dna

trend_features:
  topic_growth_24h, topic_growth_7d, bgm_growth, saturation, competitor_density

early_feedback_features:
  views_5m, likes_5m, comments_5m, completion_rate_30m, avg_watch_time_30m
```

输出：

```text
top_10_prob
top_1_prob
pred_24h_views_quantile
pred_completion_rate
pred_interaction_rate
```

选择 LightGBM/XGBoost 的原因：

- 数据量不大时比深度模型稳。
- 可解释，适合给用户展示"为什么推荐"。
- 易做离线训练和线上推理。

### 4.4 第三阶段：多模态 Transformer

当有 5 万条以上样本后，再做多模态模型：

```text
视频帧序列 embedding
+ OCR/ASR 文本 embedding
+ 音频/BGM embedding
+ 账号 embedding
+ 趋势时序 embedding
-> Multi-task Transformer
-> 多目标预测
```

这一步不是 MVP 必需。它适合在数据闭环成熟后提升精度。

### 4.5 方向聚类与趋势预测

用于"未来方向雷达"：

1. 为每条视频生成 `content_embedding`。
2. 使用 HDBSCAN / KMeans 聚类成方向簇。
3. 对每个簇计算时间序列：

```text
video_count
median_interaction
high_quality_ratio
growth_rate
new_creator_count
saturation
```

4. 计算方向机会分：

```text
direction_opportunity =
  0.25 * growth_rate
  + 0.20 * high_quality_ratio
  + 0.15 * cross_platform_spread
  + 0.15 * account_fit
  + 0.10 * commercial_value
  + 0.10 * replicability
  - 0.15 * saturation
```

---

## 5. 数据采集与字段设计

### 5.1 新增表：视频内容特征

```sql
CREATE TABLE video_content_features (
  id BIGSERIAL PRIMARY KEY,
  platform TEXT NOT NULL,
  opus_id TEXT NOT NULL,
  source_url TEXT,
  extracted_at TIMESTAMPTZ DEFAULT NOW(),

  -- 文本
  title TEXT,
  ocr_text TEXT,
  asr_text TEXT,
  hashtags JSONB DEFAULT '[]',

  -- 结构化爆款机制
  theme_tags JSONB DEFAULT '[]',
  audience_tags JSONB DEFAULT '[]',
  emotion_tags JSONB DEFAULT '[]',
  pain_points JSONB DEFAULT '[]',
  hook_type TEXT,
  title_formula TEXT,
  comment_trigger TEXT,

  -- 分镜/节奏
  duration_sec INT,
  shot_count INT,
  avg_shot_duration_sec NUMERIC(8,2),
  pace_level TEXT,
  emotion_peak_second INT,

  -- 视觉/音频
  scene_tags JSONB DEFAULT '[]',
  visual_style JSONB DEFAULT '{}',
  bgm_type TEXT,
  bgm_id TEXT,
  bgm_trend_score NUMERIC(6,2),

  -- 风险和商业
  commercial_intent TEXT,
  brand_safety_risk NUMERIC(6,2),
  content_saturation_risk NUMERIC(6,2),

  -- 向量存储可放 pgvector
  content_embedding VECTOR(1536),

  UNIQUE(platform, opus_id)
);
```

### 5.2 新增表：账号画像

```sql
CREATE TABLE creator_account_profiles (
  id BIGSERIAL PRIMARY KEY,
  platform TEXT NOT NULL,
  account_id TEXT NOT NULL,
  nickname TEXT,
  niche_tags JSONB DEFAULT '[]',
  audience_tags JSONB DEFAULT '[]',
  commercial_goal TEXT,
  avg_interaction_baseline NUMERIC(12,2),
  avg_completion_baseline NUMERIC(8,4),
  best_topic_tags JSONB DEFAULT '[]',
  best_emotion_tags JSONB DEFAULT '[]',
  best_dna_types JSONB DEFAULT '[]',
  content_embedding_centroid VECTOR(1536),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(platform, account_id)
);
```

### 5.3 新增表：发布后表现追踪

```sql
CREATE TABLE video_performance_snapshots (
  id BIGSERIAL PRIMARY KEY,
  platform TEXT NOT NULL,
  opus_id TEXT NOT NULL,
  account_id TEXT,
  minutes_after_publish INT NOT NULL,
  captured_at TIMESTAMPTZ DEFAULT NOW(),

  views BIGINT,
  likes BIGINT,
  comments BIGINT,
  shares BIGINT,
  collects BIGINT,
  followers_gain BIGINT,

  completion_rate NUMERIC(8,4),
  avg_watch_time_sec NUMERIC(8,2),
  replay_rate NUMERIC(8,4),
  negative_feedback_rate NUMERIC(8,4),

  UNIQUE(platform, opus_id, minutes_after_publish)
);
```

### 5.4 新增表：方向簇

```sql
CREATE TABLE topic_direction_clusters (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  topic_tags JSONB DEFAULT '[]',
  emotion_tags JSONB DEFAULT '[]',
  hook_types JSONB DEFAULT '[]',
  scene_tags JSONB DEFAULT '[]',
  sample_opus_ids JSONB DEFAULT '[]',
  heat_score NUMERIC(6,2),
  growth_score NUMERIC(6,2),
  saturation_score NUMERIC(6,2),
  commercial_value_score NUMERIC(6,2),
  opportunity_score NUMERIC(6,2),
  cluster_embedding VECTOR(1536),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.5 新增表：预测结果

```sql
CREATE TABLE topic_predictions (
  id BIGSERIAL PRIMARY KEY,
  target_type TEXT NOT NULL,       -- topic | opus | direction
  target_id TEXT NOT NULL,
  account_profile_id BIGINT,
  model_version TEXT NOT NULL,
  predicted_at TIMESTAMPTZ DEFAULT NOW(),

  top_10_prob NUMERIC(8,4),
  top_1_prob NUMERIC(8,4),
  pred_24h_views_quantile NUMERIC(8,4),
  pred_completion_rate NUMERIC(8,4),
  pred_interaction_rate NUMERIC(8,4),
  negative_feedback_risk NUMERIC(8,4),
  opportunity_score NUMERIC(6,2),

  explanation JSONB DEFAULT '{}'
);
```

### 5.6 新增表：抖音官方热点信号

用于接入抖音热点宝、官方热门视频榜、官方活动日历等抖音侧信号。第一阶段允许半自动采集或人工导入，后续再替换为官方 API / 授权数据。

```sql
CREATE TABLE douyin_hotspot_signals (
  id BIGSERIAL PRIMARY KEY,
  source TEXT DEFAULT 'douyin_hotspot',
  platform TEXT DEFAULT 'douyin',
  captured_at TIMESTAMPTZ NOT NULL,

  hot_id TEXT,
  title TEXT NOT NULL,
  category TEXT,
  city TEXT,
  rank INT,
  hot_value BIGINT,
  growth_rate NUMERIC(8,4),

  related_video_count BIGINT,
  comment_keywords JSONB DEFAULT '[]',
  trend_points JSONB DEFAULT '[]',

  is_rising BOOLEAN DEFAULT FALSE,
  is_low_follower_hit BOOLEAN DEFAULT FALSE,
  is_official_activity BOOLEAN DEFAULT FALSE,

  activity_start_at TIMESTAMPTZ,
  activity_end_at TIMESTAMPTZ,
  activity_url TEXT,

  raw JSONB DEFAULT '{}'
);
```

### 5.7 新增表：抖音官方热门视频榜

用于接入抖音开放平台热门视频榜，补充官方热门视频样本。

```sql
CREATE TABLE douyin_hot_videos (
  id BIGSERIAL PRIMARY KEY,
  captured_at TIMESTAMPTZ NOT NULL,
  rank INT,
  title TEXT,
  author TEXT,
  digg_count BIGINT,
  comment_count BIGINT,
  play_count BIGINT,
  hot_words TEXT,
  hot_value BIGINT,
  item_cover TEXT,
  share_url TEXT,
  raw JSONB DEFAULT '{}'
);
```

字段映射建议：

| 抖音官方字段 | OpenRHTV 字段 | 用途 |
|---|---|---|
| `rank` | `rank` | 趋势排序 |
| `title` | `title` | 主题、标题公式、语义 embedding |
| `author` | `author / nickname` | 创作者雷达 |
| `digg_count` | `likes` | 互动 DNA |
| `comment_count` | `comments` | 评论潜力 |
| `play_count` | `views` | 热度与效率 |
| `hot_words` | `related_hashtags / hot_words` | 热词与方向聚类 |
| `hot_value` | `official_hotspot_score` | 官方热度信号 |
| `share_url` | `source_url` | 深分析入口 |

### 5.8 新增表：小红书趋势信号

用于接入小红书热门搜索词、热门笔记、话题趋势、第三方爆文库、创作者中心或商业平台导入数据。

```sql
CREATE TABLE xhs_trend_signals (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,                    -- creator_center / pugongying / spotlight / qianfan / third_party
  platform TEXT DEFAULT 'xhs',
  captured_at TIMESTAMPTZ NOT NULL,

  keyword TEXT,
  topic TEXT,
  category TEXT,
  rank INT,
  heat_value BIGINT,
  search_trend_score NUMERIC(6,2),
  note_count BIGINT,
  growth_rate NUMERIC(8,4),

  is_official_activity BOOLEAN DEFAULT FALSE,
  is_commercial BOOLEAN DEFAULT FALSE,
  activity_url TEXT,

  raw JSONB DEFAULT '{}'
);
```

### 5.9 新增表：小红书热门笔记

用于沉淀小红书爆文样本和后续种草模型训练。

```sql
CREATE TABLE xhs_hot_notes (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL,

  note_id TEXT,
  note_url TEXT,
  title TEXT,
  content TEXT,
  cover_url TEXT,
  author_id TEXT,
  author_name TEXT,
  fans_num BIGINT,
  publish_time TIMESTAMPTZ,

  like_count BIGINT,
  comment_count BIGINT,
  collect_count BIGINT,
  share_count BIGINT,
  view_count BIGINT,

  topics JSONB DEFAULT '[]',
  keywords JSONB DEFAULT '[]',
  comment_keywords JSONB DEFAULT '[]',

  collect_rate NUMERIC(8,4),
  comment_rate NUMERIC(8,4),
  xhs_seed_score NUMERIC(6,2),
  commercial_conversion_score NUMERIC(6,2),
  long_tail_growth_score NUMERIC(6,2),

  raw JSONB DEFAULT '{}',
  UNIQUE(source, note_id)
);
```

字段映射建议：

| 小红书字段 | OpenRHTV 字段 | 用途 |
|---|---|---|
| 标题 | `title` | 标题公式、搜索关键词 |
| 正文 | `content` | 痛点、教程、清单、测评结构 |
| 封面 | `cover_url` | 封面点击潜力与视觉分析 |
| 收藏 | `collect_count / collect_rate` | 种草价值核心指标 |
| 评论 | `comment_count / comment_keywords` | 咨询意图和商业信号 |
| 点赞 | `like_count` | 基础互动热度 |
| 发布时间 | `publish_time` | 长尾曲线和发布时间分析 |
| 话题 | `topics` | 方向聚类和搜索匹配 |
| 达人粉丝 | `fans_num` | 低粉爆文、可复刻性 |

---

## 6. Tool / API 增强

### 6.1 search_trending 返回增加 deep_intelligence

在现有 `search_trending` 返回结构里为每个 topic/card 增加：

```json
{
  "deep_intelligence": {
    "opportunity_score": 86.4,
    "recommendation_signals": {
      "hook_strength": 88,
      "completion_potential": 74,
      "interaction_potential": 81,
      "share_collect_potential": 79,
      "negative_feedback_risk": 12
    },
    "business_signals": {
      "account_fit": 83,
      "commercial_value": 68,
      "saturation_risk": 41,
      "brand_safety_risk": 18
    },
    "prediction": {
      "top_10_prob": 0.31,
      "top_1_prob": 0.06,
      "pred_24h_views_quantile": 0.82
    },
    "explain": [
      "近期同类内容增长快，但还未完全红海",
      "互动 DNA 偏收藏/评论，适合女性成长账号",
      "复刻素材要求中等，需要真实现场画面和情绪字幕"
    ]
  }
}
```

### 6.2 新增 analyze_viral_mechanism

```text
analyze_viral_mechanism(opus_id, platform, source_url?) -> dict
```

职责：

- 调用 toprador / video-analysis。
- 抽取分镜、OCR、ASR、视觉、音频。
- LLM 归纳成结构化爆款机制。
- 写入 `video_content_features`。

返回：

```json
{
  "opus_id": "...",
  "viral_mechanism": {
    "hook": {...},
    "emotion": {...},
    "structure": {...},
    "visual": {...},
    "audio": {...},
    "business": {...}
  },
  "replication_blueprint": {
    "required_materials": [],
    "script_formula": "",
    "shot_plan": []
  }
}
```

### 6.3 新增 recommend_topic_directions

```text
recommend_topic_directions(
  niche_index_id?,
  account_id?,
  horizon_days=7,
  goal='growth' | 'conversion' | 'engagement'
) -> list[Direction]
```

用于 `/topics` 新增"方向雷达"。

### 6.4 新增 log_video_performance

```text
log_video_performance(
  platform,
  opus_id,
  minutes_after_publish,
  metrics
) -> PerformanceSnapshot
```

用于发布后数据回流。第一阶段允许用户手动录入或上传后台截图 OCR。

### 6.5 新增 ingest_douyin_hotspot_signals

```text
ingest_douyin_hotspot_signals(
  source='douyin_hotspot' | 'douyin_open_hot_video',
  mode='api' | 'manual_import' | 'screenshot_ocr',
  payload
) -> IngestResult
```

职责：

- 接入抖音热点宝导出的热点、飙升、垂类、城市、低粉爆款、活动日历。
- 接入抖音开放平台热门视频榜。
- 标准化为 `douyin_hotspot_signals` / `douyin_hot_videos`。
- 将官方热度信号融合到 `search_trending` 的 `deep_intelligence.official_signals`。

`search_trending` 增强返回：

```json
{
  "official_signals": {
    "source": "douyin_hotspot",
    "official_hotspot_score": 84,
    "is_rising": true,
    "is_low_follower_hit": true,
    "is_official_activity": false,
    "related_video_count": 1280,
    "comment_keywords": ["共鸣", "泪目", "青春"],
    "trend_stage": "rising"
  }
}
```

### 6.6 新增 ingest_xhs_trend_signals

```text
ingest_xhs_trend_signals(
  source='creator_center' | 'pugongying' | 'spotlight' | 'qianfan' | 'third_party',
  mode='api' | 'manual_import' | 'screenshot_ocr' | 'csv',
  payload
) -> IngestResult
```

职责：

- 接入小红书创作者中心、蒲公英、聚光、千帆或第三方趋势平台数据。
- 标准化为 `xhs_trend_signals` / `xhs_hot_notes`。
- 计算 `xhs_seed_score`、`search_trend_score`、`comment_quality_score`、`long_tail_growth_score`。
- 将小红书信号融合到 `search_trending` 的 `deep_intelligence.xhs_signals`。

`search_trending` 增强返回：

```json
{
  "xhs_signals": {
    "source": "third_party",
    "xhs_seed_score": 82,
    "search_trend_score": 76,
    "collect_rate_score": 88,
    "comment_quality_score": 79,
    "long_tail_growth_score": 72,
    "commercial_conversion_score": 81,
    "note_format": "攻略清单",
    "recommended_cover_style": "大字标题+结果对比"
  }
}
```

---

## 7. 产品页面整合

### 7.1 /topics 单入口增强

保持当前简化策略，不急着做复杂 6 Tab。建议第一阶段只做 3 个区域：

```text
/topics
├── 今日值得拍
│   └── 已排序的热点/方向卡片，展示 opportunity_score
├── 为什么值得拍
│   └── 点开卡片后展示推荐系统信号 + 爆款机制
└── 直接生成
    └── 生成 3 个选题 + 脚本 + 分镜，进入画布
```

### 7.2 深度分析抽屉

卡片点开后分 4 层：

1. **一句话判断**
   - "适合女性成长账号，未来 3 天仍有机会，但需要真实素材。"

2. **推荐系统信号**
   - 停留、完播、互动、分享收藏、负反馈风险。

3. **爆款机制**
   - 开头、情绪、节奏、画面、音频、评论诱因。

4. **创作方案**
   - 标题、前 3 秒、分镜、字幕、BGM、拍摄清单。

### 7.3 进入画布时带入上下文

进入画布的 prompt 不再只带 `topic`，而是带完整 `TopicBrief`：

```json
{
  "topic": "演唱会第一视角情绪 vlog",
  "why_now": ["热度增长", "素材稀缺", "女性情绪共鸣"],
  "target_audience": ["18-30 女性", "演唱会粉丝", "情绪价值内容消费者"],
  "viral_mechanism": {...},
  "replication_blueprint": {...},
  "account_fit": {...},
  "constraints": {
    "duration": "30-60秒",
    "risk_notes": ["音乐版权", "低质搬运风险"]
  }
}
```

---

## 8. 工程实施路径

### Phase 1: 文档与结构化输出

目标：不训练模型，先把深度选题的数据结构跑通。

任务：

- 新增 `DeepTopicIntelligence` 类型。
- 在 `search_trending` 输出中预留 `deep_intelligence`。
- 新增 `analyze_viral_mechanism` 的 mock / rule-based 版本。
- 新增 `douyin_hotspot_signals` / `douyin_hot_videos` schema。
- 先用手工导入或截图 OCR 接入抖音热点宝关键字段。
- 新增 `xhs_trend_signals` / `xhs_hot_notes` schema。
- 先用第三方平台 CSV / 截图 OCR 接入小红书热门笔记与搜索词。
- 修改 `/topics` 卡片展示 opportunity_score、推荐系统信号。
- 进入画布时带入 `TopicBrief`。

验收：

- 任意热点卡片可展示"为什么值得拍"。
- 可生成 3 个更贴近热点机制的脚本/分镜。
- 不依赖真实训练模型即可跑通。

### Phase 2: 视频深度特征入库

目标：把 toprador 分析从"报告"变成"可训练特征"。

任务：

- 从 video-analysis 结果抽取结构化字段。
- 写入 `video_content_features`。
- 对已有 `rank_data.top_contents` 批量补特征。
- 对 `douyin_hot_videos.share_url` 批量触发深度分析，沉淀官方热门视频机制样本。
- 对 `xhs_hot_notes` 批量触发封面、标题、正文、评论关键词分析，沉淀种草机制样本。
- 新增人工校正入口：允许运营修正 hook/emotion/pain_point。

验收：

- 每条深分析视频都有结构化 JSON。
- `/topics` 可以基于真实视频机制生成选题。

### Phase 3: 发布后反馈闭环

目标：开始积累训练样本。

任务：

- 新增表现录入 UI。
- 支持后台截图 OCR 或手动填写。
- 固定采样点：30min / 2h / 6h / 24h / 72h。
- 生成账号复盘：预测 vs 实际。
- 区分 `official_trend_used=true/false`，评估抖音热点宝信号是否真的提升选题表现。
- 区分 `xhs_seed_signal_used=true/false`，评估小红书收藏/搜索/评论信号是否提升选题表现。

验收：

- 单账号可以看到哪些推荐真的有效。
- 形成 `video_content_features + performance_snapshots` 训练集。

### Phase 4: 轻量模型上线

目标：用 LightGBM/XGBoost 替代规则分的一部分。

任务：

- 离线训练 top_10/top_1/互动率/完播率模型。
- 增加模型版本与解释字段。
- 用 SHAP 或 feature importance 生成解释。
- A/B 测试规则分 vs 模型分。

验收：

- 推荐方向点击率提升。
- 从热点进画布转化提升。
- 用户采纳后的视频表现优于账号历史 baseline。

---

## 9. 指标体系

### 9.1 产品指标

| 指标 | 含义 | 目标 |
|---|---|---|
| topic_card_view -> deep_analysis_open | 用户是否愿意看深分析 | >= 20% |
| deep_analysis_open -> enter_canvas | 分析是否能推动创作 | >= 15% |
| enter_canvas -> export | 选题是否真的可落地 | >= 35% |
| topic_reuse_7d | 用户 7 天内是否复用热点功能 | >= 30% |
| paid_conversion | 选题功能付费转化 | Pro >= 3% |

### 9.2 模型指标

| 指标 | 含义 |
|---|---|
| AUC_top10 | 是否进入同类 top 10% 的排序能力 |
| Calibration error | 爆款概率是否可信 |
| Lift@10 | 推荐前 10 条方向相对随机的提升 |
| Baseline lift | 采纳推荐后是否超过账号历史均值 |
| Explanation helpfulness | 用户是否认为解释可执行 |
| Official signal lift | 接入热点宝/官方榜信号后，推荐方向表现提升 |
| XHS seed signal lift | 接入小红书种草信号后，收藏/评论/长尾表现提升 |

---

## 10. 与现有文档/代码的对应关系

| 新能力 | 复用现有位置 | 新增位置建议 |
|---|---|---|
| 热点召回 | `hotspot/existSkill/topic-pipeline/pipeline.py` | 增加 deep_intelligence 字段 |
| 五维评分/DNA | `hotspot/existSkill/newrank/topic_scorer.py` | 增加推荐系统信号映射 |
| 可复刻性 | `hotspot/existSkill/douhot/analyze_data.py` | 拆成素材需求/制作难度/账号难度 |
| 深度视频分析 | `toprador video-analysis` | 写入 `video_content_features` |
| 抖音官方热点信号 | `douhot.douyin.com` / 抖音开放平台热门视频榜 | 新增 `douyin_hotspot_signals` / `douyin_hot_videos` |
| 小红书种草信号 | 创作者中心 / 蒲公英 / 聚光 / 千帆 / 第三方趋势平台 | 新增 `xhs_trend_signals` / `xhs_hot_notes` |
| /topics UI | `OpenRHTV/frontend/src` | 新增方向雷达/深度抽屉 |
| Agent 上下文 | `TopicBrief` | 进入画布时传递完整热点 brief |
| 数据闭环 | 当前缺 | 新增 performance snapshots |

---

## 11. 风险与边界

1. **不要承诺"一定爆"**
   - 产品文案应是"机会分/适配度/方向建议"，而不是"爆款保证"。

2. **不要依赖黑盒 LLM 评分**
   - LLM 做结构化理解和创作建议，最终排序要有可解释分数。

3. **不要一开始做全平台全垂类**
   - 先选 1-2 个垂类，例如本地生活、女性成长、知识 IP。

4. **公开视频数据不等于真实推荐反馈**
   - 完播率、平均观看时长、负反馈需要创作者后台或用户录入。

5. **趋势预测必须带不确定性**
   - 输出"未来 3-7 天机会高/中/低"，不要伪装成精确预测。

---

## 12. 参考算法与资料

- X For You Feed Algorithm: https://github.com/xai-org/x-algorithm
- YouTube DNN Recommendation: https://research.google.com/pubs/archive/45530.pdf
- YouTube Multitask Ranking: https://research.google/pubs/recommending-what-video-to-watch-next-a-multitask-ranking-system/
- ByteDance Monolith: https://arxiv.org/abs/2209.07663
- Watch-time Short-video Recommendation: https://arxiv.org/abs/2306.17426
- Duration Bias in Micro-video Recommendation: https://arxiv.org/abs/2208.05190
- Video Popularity Prediction with RNN: https://arxiv.org/abs/1707.06807
- Micro-video Popularity Prediction MMVED: https://arxiv.org/abs/2003.12724

---

## 13. 推荐下一步

最建议的下一步不是训练模型，而是先做一个可上线的 `Phase 1`：

```text
1. 给 search_trending 增加 deep_intelligence mock/rule 输出。
2. /topics 卡片显示 opportunity_score 和推荐系统信号。
3. 点开卡片展示"为什么值得拍 + 怎么拍"。
4. 进入画布时传入 TopicBrief。
5. 发布后让用户手动录入表现，开始积累训练数据。
```

这一步能把热点选题从"数据看板"升级为"创作决策入口"，也是后续所有模型的地基。

---

## 14. 六视角投资评审

### 14.1 总判断

新增 `Deep Topic Intelligence` 值得投入，但投资边界要非常清楚：

```text
现在投：
Phase 1 文档 / 类型 / 规则分 / mock 输出
Phase 2 视频机制结构化入库
Phase 3 手动 / 截图 OCR 发布表现回流

暂缓：
Phase 4 LightGBM / XGBoost，等有 1000+ 有效样本

不做：
多模态 Transformer
全平台全垂类预测
复杂 6 Tab 决策中台
```

最小可投版本应该是：

```text
/topics 今日值得拍
  -> 一句话判断
  -> 为什么值得拍
  -> 怎么拍
  -> 生成 3 个选题 / 脚本 / 分镜
  -> TopicBrief 进入画布
  -> 发布后手动复盘
```

这不是对原有 MVP 的功能加法，而是对产品定位的收敛：

> **OpenRHTV 不和 AI 视频模型比生成质量，而是在上游帮助创作者决定今天最值得拍什么。**

### 14.2 Elon Musk 视角

**方向**：对。它攻击的是真瓶颈。创作者的瓶颈不是"视频生成按钮"，而是"选题决策"。

**价值**：`Deep Topic Intelligence` 把热点从"榜单"变成"生产指令"，比单纯热点卡片有更高杠杆，因为它直接进入创作链路。

**实现方案**：先删到最小闭环：

```text
热点 / 爆款
  -> opportunity_score 规则分
  -> 为什么值得拍
  -> 怎么拍
  -> TopicBrief 进画布
  -> 发布后手动录入表现
```

**投资判断**：投 Phase 1，谨慎投 Phase 2/3，不投 Phase 4。先证明它能让用户更快完成内容，而不是证明团队能造推荐系统。

### 14.3 Buffett 视角

**方向**：这是从"工具"走向"生意"的正确方向。单次生成工具没有护城河，选题数据、账号画像、复盘记录、角色 / 场景资产才可能形成长期价值。

**价值**：真正的好生意来自重复使用。新增方案里的 `account_profile`、`video_performance_snapshots`、`topic_direction_clusters` 是护城河种子。

**实现方案**：先看经营指标，不看故事。6 周内只验证：

```text
deep_analysis_open -> enter_canvas
enter_canvas -> export
topic_reuse_7d
用户是否愿意手动录入发布表现
是否有 3 个以上账号一周内重复使用
```

**投资判断**：买观察票，不买整家公司。值得小额投入新增功能，但不值得把它扩成 8 个月大系统。没有留存和复用前，模型预测只是漂亮报告。

### 14.4 Naval 视角

**方向**：好，因为它把创作者的特定知识产品化。优秀运营知道"这个热点适不适合我"，但这种判断通常藏在脑子里。OpenRHTV 可以把它变成代码和数据。

**价值**：这里有两种杠杆：

```text
代码杠杆：规则分、方向聚类、TopicBrief 自动生成
数据杠杆：账号画像、历史表现、赛道匹配、复盘反馈
```

如果做对，它不是帮用户"做一条视频"，而是帮用户建立一个持续工作的选题资产。

**实现方案**：不要做"AI 军师"，要做"账号选题操作系统"。输出应该沉淀为资产：

- 这个账号适合什么方向。
- 哪些情绪 / 钩子历史表现好。
- 哪些热点不适合拍。
- 下次怎么更接近自己的高表现内容。

**投资判断**：值得投，但前提是不要变成人工运营服务。凡是需要人肉分析才能交付的部分，都不是可复利资产。

### 14.5 Steve Jobs 视角

**方向**：方向非常好，页面会很危险。方案里有太多信号、分数、模型、表和预测。用户不想看仪表盘，用户想知道今天拍什么。

**价值**：最好的产品句子应该是：

> **每天告诉你最值得拍的 3 个方向，并一键变成你的脚本。**

**实现方案**：`/topics` 不要做复杂 6 Tab。第一阶段只保留：

```text
今日值得拍
为什么值得拍
直接生成
```

卡片上默认只给一句判断，展开后再看推荐系统信号、爆款机制和风险。

**投资判断**：值得投"方向雷达"和 `TopicBrief` 进画布。不值得投复杂后台式预测页面。产品必须像 iPod 一样简单，不要像运营后台。

### 14.6 Ilya Sutskever 视角

**方向**：这是从生成系统走向学习系统。重要的不是第一版评分多准，而是能否通过反馈不断压缩"什么内容会适合这个账号"。

**价值**：`video_content_features + performance_snapshots` 是关键。没有反馈，系统只是解释热点；有反馈，系统才开始学习。真正的智能来自预测和现实之间的误差。

**实现方案**：不要过早追求模型。先把数据表示做好：

```text
视频机制结构化
账号画像结构化
发布表现结构化
预测 vs 实际结构化
```

然后再训练轻量模型。LightGBM / XGBoost 是合理的第二阶段，因为样本少、可解释、上线成本低。多模态 Transformer 现在不该做。

**投资判断**：值得投数据闭环。不是为了马上提高爆款率，而是为了建立一个会学习的系统。没有真实反馈，所谓预测只是幻觉。

### 14.7 Karpathy 视角

**方向**：产品方向对，但工程风险最高。这个方案会把系统从"内容生成应用"推向"推荐 / 预测系统"。推荐系统 demo 容易，deployment reliability 很难。

**价值**：如果只是 mock 分数，没有价值；如果它能稳定产出 `TopicBrief` 并提升从热点到画布的转化，就有价值。

**实现方案**：先建 contract，不要先建模型。至少定义：

```text
DeepTopicIntelligence
TopicBrief
ViralMechanism
AccountFit
PerformanceSnapshot
```

所有字段必须有：

- 来源
- 置信度
- 缺失 fallback
- 是否可展示给用户
- 是否进入排序

最大风险是 LLM 输出漂移。LLM 可以做结构化理解，但最终排序必须是可解释规则或模型，不能是"LLM 觉得会火"。

**投资判断**：值得投 Phase 1，但要用工程验收卡死：

| 指标 | 通过线 |
|---|---:|
| 100 条热点卡片字段完整率 | >= 90% |
| `TopicBrief` 进入画布成功率 | >= 95% |
| deep_analysis_open -> enter_canvas | >= 15% |
| enter_canvas -> export | >= 35% |
| 用户反馈录入率 | 可被验证 |

### 14.8 最终投资边界

这个新增方向值得投，因为它增强的是 OpenRHTV 最重要的差异化：

> **不是生成视频，而是决定今天拍什么、为什么拍、怎么拍、拍完如何复盘。**

但不能按大推荐系统投资。当前路线应当是：

1. 先投规则分和 `TopicBrief`。
2. 再投视频机制结构化。
3. 再投发布后反馈回流。
4. 有真实样本后再投轻量模型。
5. 不在当前阶段投入多模态 Transformer。
