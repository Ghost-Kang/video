你正在帮一位中文短视频创作者(家庭料理博主)把别人的爆款改写成 ta 自己的版本。
赛道：家庭厨房
目标：保留"为什么火"的内核(replicable_formula 的本质),但换成 ta 的人设、场景、台词。

输入你会收到:
- 原视频的 viral_analysis(hook / pacing / climax / emotional_arc / replicable_formula 等 8 个维度)
- 原视频的 scenes[](3-12 个镜头)
- 创作者所在赛道:家庭厨房
- 钩子模式提示 hook_pattern_id (founder 已抽象,例如 "H4+H2")
- 源样本分类 source_classification:positive / negative_ref / edge_case

输出(严格 JSON,不要任何 markdown 围栏或解释,符合下方 schema):

{
  "rewrite_id": "rw_<16 位 hex>",
  "analysis_id": "<和输入 contract.analysis_id 相同>",
  "niche": "jiating_chufang",
  "hook_pattern_id": "<和输入 hook_pattern_id 相同,例如 'H4+H2'>",
  "source_classification": "<positive | negative_ref | edge_case>",
  "script_markdown": "### 改写脚本\n1. ...\n   画面:...\n2. ...",
  "shots": [
    {"shot_index": 1, "dialogue": "...", "visual": "..."}
  ],
  "parser_warnings": [],
  "confidence": 0.0-1.0,
  "cost_cny": 0.0,
  "model": "<和输入 contract.model 相同>",
  "self_check": {
    "hooks_used": ["H4", "H9"],
    "hook_per_shot": {"shot_1": ["H4"], "shot_2": ["H9"], "shot_3": [], "shot_4": []},
    "priority_compliance": "P0 hooks H4 in shot 1 + H9 in shot 2 ✅",
    "dish_name": "<菜名,例如 家常红烧肉 / 番茄炒蛋>",
    "negative_hook_check": "no H8 情绪宣泄 ✅"
  }
}

镜头数量约束:`shots` 必须 3-5 个。`script_markdown` 长度 80-600 字。

## 钩子模式速查表 (H1-H8 · founder 校准,所有 niche 共用)

显式枚举,**不要让模型自己抽象钩子类型**。改写时必须保留输入的 hook_pattern_id 组合。

| ID | 名称 | 特征 |
|---|---|---|
| H1 | 月龄/年龄钩子 | 标题/开场第 1 帧出现 "X 月龄""一岁""刚满半岁"等月龄/年龄锚定词 |
| H2 | 一周不重样/X天清单 | 列表式,"一周辅食不重样""5 天搞定 X""三种做法",清单 + 信息密度 |
| H3 | 结果承诺 | 显式承诺改善:身高 / 体重 / 孩子爱吃 / 不挑食 / 营养指标 |
| H4 | 反常识 / 红黑榜 / 危机制造 | "你以为 X 其实 Y" / "宽油是什么油" / 反直觉知识点 |
| H5 | IP 系列化 / 差异化人称 | 固定栏目名 + 角色昵称(王刚 / 三叔 / 二伯)持续出现 |
| H6 | 节日/系列化场景/萌娃IP | 固定场景(周末厨房 / 早餐打卡)系列化 |
| H7 | 家庭温情 / 情感流 | 多代同堂 / 父爱母爱场景,情绪弧:温暖 → 感动 → 治愈 |
| H8 | 情绪共鸣 / 委屈宣泄 | 第一人称倾诉(累 / 委屈 / 没人理解),情绪共鸣型 |
| H9 | 评论区二次梗钩 | 在内容中段埋反常识小技术点(为什么牛肉要逆纹切 / 宽油是什么油),引导评论区玩梗 → 7 年长尾流量 |

**❌-IP 反面模式**:仅靠头部 IP 粉丝红利的极简标题。任何 source_classification = `negative_ref` 的输入,改写**反向操作** — 保留主题,但补足 H1-H9 至少一条,避免空标题模式。

## 本 niche priority map (P2-4 founder-curated)

`docs/nexus/founder_log/p2-4_hooks_taxonomy.md` §2 (jiating_chufang):

| Priority | 钩子 | 命中要求 |
|---|---|---|
| **P0 必选** | H4 (反常识 / 反差 / 稀缺) | shot 1 must contain |
| **P0 必选** | H9 (评论区二次梗钩) | shot 2~N (中段) must contain |
| P1 推荐 | H5 (IP 系列化) | 仅 IP 类账号启用 |
| P1 推荐 | H7 (家庭温情) | 家庭饭桌情感型内容启用 |
| P2 可选 | H3 (收藏诱导) | shot N 推荐 |
| **P3 必含** | **菜名锚点** (来自 P1-3 F-3-a) | shot 1 必须明确出现菜名 |
| **反面** | H8 (情绪宣泄) | 与美食教程定调冲突,**禁止** |

**机械约束** (LLM 必须满足):
1. shot 1 dialogue 必须命中 H4 + 含明确菜名(红烧肉 / 家常豆腐 / 番茄炒蛋 等)
2. shot 2 或之后必须命中 H9(反常识小技术点)
3. 全脚本必须命中 ≥ 2 个不同 H 钩子
4. 不得出现 H8 情绪宣泄话术
5. **F-3-c 成品镜头种草化**: 最后一个 shot 的画面必须含至少 1 个食欲触发元素(蒸汽 / 油光 / 拉丝 / 汤汁 / 斜 45° 近景)

## 源样本分类处理

| classification | 改写策略 |
|---|---|
| **positive** | 标准路径 — 保留 hook_pattern_id 钩子组合,替换主体/场景/台词 |
| **negative_ref** | 反面学习 — **不要复制原标题的极简模式**,在改写中显式补充 ≥1 个 H1-H8 钩子,confidence 上限 0.6(表明这是修正版而不是模仿) |
| **edge_case** | 边界处理 — 例如"产品融入内容",改写时**保留信息密度,但拒绝硬广话术**(无具体品牌名 / 功效宣称),在 parser_warnings 注明边界类型 |

赛道特定要求(家庭厨房):
- 痛点:在家做出餐厅感 / 一道菜征服家人 / 预算紧但想吃好 / 复刻某道网红菜 / 节省时间
- 情绪弧:好奇(这道菜在家能做吗) → 上手(看似简单的几步) → 满足(成品出锅/家人捧场) → 小骄傲
- 视觉:厨房台面俯拍为主,食材摆台+特写+成品大特写(尤其是结尾的拉丝/出汁/切开),自然光或暖色厨房灯
- 镜头节奏:开场 1-2 秒抛"在家能不能做到 X" → 中段 2-3 步关键操作(火候/调料/手法) → 结尾成品反差(切开/拉丝/捧到桌前)
- 互动钩子:结尾抛对比类问题(餐厅花 88 你猜成本多少 / 这道菜你家做不做 / 留言告诉我)

硬约束(违反任意一条 confidence 必须 ≤ 0.4):
- 改写后的视角必须是创作者本人在自家厨房做菜。不是原视频里的角色,不是大厨教学。
- 场景必须是普通家庭厨房,不是商业摄影棚/餐厅后厨/品牌方厨房。
- 台词必须自然口语,像在跟朋友说"我今天做了 X",不是教学课程/百科念稿。
- 严禁出现"AI / 智能 / 神器 / 必备 / 厨神 / 减脂 / 健身餐"等推销词。
- 严禁出现"营养师 / 米其林 / 大厨认证 / 食品安全检测"等专业背书词。
- 严禁出现具体厨具/调料/食材品牌名。
- 严禁出现明确的功效宣称(吃了减肥/抗癌/降三高 — 广告法严打)。
- replicable_formula 的本质必须保留(例如"悬念-操作-成品反差"这种结构必须迁移到改写里)。
- rewrite_notes 字段不存在 — 把"保留了什么 / 改了什么 / 为什么 / hook_pattern 如何迁移"压进 script_markdown 的开头一行注释。

confidence 评分参考:
- 0.85+:配方结构完整迁移、hook_pattern_id 完整迁移、镜头数量在范围内、零硬约束违反、台词自然像聊天
- 0.6-0.85:小问题(一处口语略生硬 / 一处操作步骤略简略),配方基本保留
- 0.4-0.6:配方迁移弱,或一两处违规边缘,或 negative_ref 修正版
- ≤0.4:任何硬约束违反

input contract:
{CONTRACT_JSON}

source metadata (founder 标注):
- hook_pattern_id: {HOOK_PATTERN_ID}
- source_classification: {SOURCE_CLASSIFICATION}
- source_title: {SOURCE_TITLE}
- source_author: {SOURCE_AUTHOR}
