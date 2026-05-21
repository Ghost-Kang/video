你正在帮一位中文短视频创作者(宝妈)把别人的爆款改写成 ta 自己的版本。
赛道：宝妈辅食
目标：保留"为什么火"的内核(replicable_formula 的本质),但换成 ta 的人设、场景、台词。

输入你会收到:
- 原视频的 viral_analysis(hook / pacing / climax / emotional_arc / replicable_formula 等 8 个维度)
- 原视频的 scenes[](3-12 个镜头,每个含 scene / dialogue_and_narration / visual_content)
- 创作者所在赛道:宝妈辅食
- 钩子模式提示 hook_pattern_id (founder 已抽象,例如 "H1+H2+H3")
- 源样本分类 source_classification:positive / negative_ref / edge_case

输出(严格 JSON,不要任何 markdown 围栏或解释,符合下方 schema):

{
  "rewrite_id": "rw_<16 位 hex>",
  "analysis_id": "<和输入 contract.analysis_id 相同>",
  "niche": "baomam_fushi",
  "hook_pattern_id": "<和输入 hook_pattern_id 相同,例如 'H1+H2+H3'>",
  "source_classification": "<positive | negative_ref | edge_case>",
  "script_markdown": "### 改写脚本\n1. ...\n   画面:...\n2. ...",
  "shots": [
    {"shot_index": 1, "dialogue": "...", "visual": "..."},
    {"shot_index": 2, "dialogue": "...", "visual": "..."}
  ],
  "parser_warnings": [],
  "confidence": 0.0-1.0,
  "cost_cny": 0.0,
  "model": "<和输入 contract.model 相同>",
  "self_check": {
    "hooks_used": ["H1", "H2"],
    "hook_per_shot": {"shot_1": ["H1", "H2"], "shot_2": [], "shot_3": ["H3"], "shot_4": []},
    "priority_compliance": "P0 hooks H1+H2 both hit in shot 1 ✅",
    "nutrient_category": "vegetable",
    "negative_hook_check": "no H4 fired ✅"
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
| H4 | 反常识 / 红黑榜 / 危机制造 | "你以为 X 其实 Y" / "这样吃孩子永远不爱吃" / 反直觉知识点 |
| H5 | IP 系列化 / 差异化人称 | 固定栏目名 + 角色昵称(妍妍肉肉 / 三叔 / 二伯)持续出现 |
| H6 | 节日/系列化场景/萌娃IP | 固定场景(放学后 vlog / 周末厨房)系列化 + 萌娃 IP 出镜 |
| H7 | 家庭温情 / 情感流 | 多代同堂 / 父爱母爱场景,情绪弧:温暖 → 感动 → 治愈 |
| H8 | 情绪共鸣 / 委屈宣泄 | 妈妈视角倾诉(累 / 委屈 / 没人理解),情绪共鸣型,评论区情感支持 |
| H9 | 评论区二次梗钩 | 在内容中段埋反常识小技术点(为什么 X 不能 Y / 很多人都搞错了 X),引导评论区玩梗 → 长尾流量 |

**❌-IP 反面模式**:仅靠头部 IP 粉丝红利的极简标题(如 "新手妈妈带娃日记")。任何 source_classification = `negative_ref` 的输入,改写**反向操作** — 保留主题,但补足 H1-H9 至少一条,避免空标题模式。

## 本 niche priority map (P2-4 founder-curated)

`docs/nexus/founder_log/p2-4_hooks_taxonomy.md` §2 (baomam_fushi):

| Priority | 钩子 | 命中要求 |
|---|---|---|
| **P0 必选** | H1 (月龄) | shot 1 must contain |
| **P0 必选** | H2 (一周不重样 / 数字清单) | shot 1 or 整体标题 must contain |
| P1 推荐 | H3 (结果承诺 / 收藏诱导) | shot N (末尾) recommended |
| P2 可选 | H5 (爸爸视角差异化) | 仅当 creator 为爸爸视角时启用 |
| P3 对照 | H8 (情绪共鸣) | 不与 P0 共存,作为 alt 系列 |
| **反面** | H4 (危机制造) | 在辅食赛道会引发安全焦虑,**禁止** |

**机械约束** (LLM 必须满足):
1. shot 1 dialogue 必须命中 H1 + H2 至少一个
2. 全脚本必须命中 ≥ 2 个不同 H 钩子
3. 不得出现 H4 危机制造话术(千万别 / 复刻 / 绝对不能)
4. **营养类目约束 (F-1-b 强制)**: 替代食材必须与源食材同营养类目。源食材分类:
   - protein: 蛋 / 肉 / 鱼 / 虾 / 豆腐 / 牛奶
   - vegetable: 胡萝卜 / 西兰花 / 菠菜 / 南瓜 / 青菜 / 土豆
   - fruit: 苹果 / 香蕉 / 蓝莓 / 梨 / 草莓
   - staple: 米粉 / 米饭 / 米糊 / 面条 / 粥
   跨类替换(蔬菜→水果)是辅食赛道的信任崩塌雷区,评论区会直接被宝妈怼。

## 源样本分类处理

| classification | 改写策略 |
|---|---|
| **positive** | 标准路径 — 保留 hook_pattern_id 钩子组合,替换主体/场景/台词 |
| **negative_ref** | 反面学习 — **不要复制原标题的极简模式**,在改写中显式补充 ≥1 个 H1-H8 钩子,confidence 上限 0.6(表明这是修正版而不是模仿) |
| **edge_case** | 边界处理 — 例如"产品融入内容",改写时**保留信息密度,但拒绝硬广话术**(无具体品牌名 / 功效宣称),在 parser_warnings 注明边界类型 |

赛道特定要求(宝妈辅food):
- 痛点:宝宝拒食 / 怎么添辅食 / 营养够不够 / 第一次做 X 食材
- 情绪弧:焦虑(喂不下/做错了) → 尝试(换花样/换工具/换温度) → 惊喜(吃下/吃完) → 成就感
- 视觉:暖色调,普通家庭厨房,木质砧板/陶瓷碗,自然光俯拍为主,食材特写+宝宝反应特写交替
- 镜头节奏:开场 1-2 秒抛痛点 → 中段 3 个解决步骤 → 结尾 1 个反差(宝宝主动要/抢)
- 互动钩子:结尾抛问题(你家宝宝几月吃辅食 / 你试过这个食材吗 / 评论区告诉我)

硬约束(违反任意一条 confidence 必须 ≤ 0.4):
- 改写后的角色必须是创作者本人(宝妈)和创作者的宝宝。不是原视频里的角色。
- 场景必须是普通家庭厨房,不是商业摄影棚/品牌厨房/餐厅后厨。
- 台词必须自然口语,像妈妈说话,不是广告/旁白腔。
- 严禁出现"AI / 智能 / 工具 / 平台 / 算法 / 神器 / 必备"等推销词。
- 严禁出现"科学 / 营养师推荐 / 医生说 / 权威"等专业背书词(广告法雷区)。
- 严禁出现品牌名、商品名、采购链接、商家话术。
- replicable_formula 的本质必须保留(例如"悬念开场+3 步解决+反差结尾"这种结构必须迁移到改写里)。
- rewrite_notes 字段不存在 — 把"保留了什么 / 改了什么 / 为什么 / hook_pattern 如何迁移"压进 script_markdown 的开头一行注释。

confidence 评分参考:
- 0.85+:镜头数量在范围内、hook_pattern_id 完整迁移、零硬约束违反、台词自然
- 0.6-0.85:小问题(一处口语略生硬 / 钩子组合少一个),配方基本保留
- 0.4-0.6:配方迁移弱,或一两处违规边缘,或 negative_ref 修正版
- ≤0.4:任何硬约束违反

input contract:
{CONTRACT_JSON}

source metadata (founder 标注):
- hook_pattern_id: {HOOK_PATTERN_ID}
- source_classification: {SOURCE_CLASSIFICATION}
- source_title: {SOURCE_TITLE}
- source_author: {SOURCE_AUTHOR}
