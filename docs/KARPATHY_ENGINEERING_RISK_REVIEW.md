# Cascade / OpenRHTV · Karpathy 工程风险评估

**Date**: 2026-05-19  
**Scope**: 基于 Cascade / OpenRHTV `docs/` 文档，聚焦最大工程风险与建议做法。  
**结论**: 最大风险不是“能不能生成视频”，而是上游分析 contract 不稳定，导致下游画布、字幕、prompt、锚点全部建立在不可靠字段上。

---

## 1. 最大工程风险

最大的工程风险是：

> **上游 `analysis_result` schema 不稳定，但下游画布、字幕、imagePrompt、锚点系统全部依赖它。**

`TOPRADOR_SCHEMA_INVESTIGATION.md` 已经明确指出：

- `viral_analysis` 的 8 维字段还没有权威枚举。
- `scenes[]` 的单镜结构还没有确认。
- `duration` / `timestamp_start` / `timestamp_end` 可能不存在。
- `subject` / `characters[]` 可能不存在。
- 字幕字段、旁白字段、视觉字段之间关系不清楚。
- Douyin 下载链路、临时文件、对象存储、副作用还没摸清。
- MySQL 到 Postgres 的结构化策略还没确定。

这意味着：

```text
toprador raw output
  -> seed_canvas
  -> script node
  -> scene anchors
  -> character anchors
  -> image prompts
  -> subtitles
  -> generated clips
```

这整条链路都可能因为一个字段缺失或漂移而失败。

Demo 里一条视频跑通，不代表产品可部署。

Deployment 里，100 条视频会暴露尾部问题：

- URL 下载失败
- 平台风控
- `scenes[]` 数量不稳定
- 字幕时码缺失
- 角色字段不存在
- 多模态分析成本漂移
- 生成 provider 内容审核失败
- 锚点一致性不稳定
- 用户不知道如何修复

这是典型的 **march of nines** 问题。

从 0 到 demo 很快。  
从 demo 到 95% 完成率很难。  
从 95% 到 99% 更难。

---

## 2. 原则

### 2.1 不要先写产品功能

先稳定 contract。

没有稳定 contract，下游功能都在沙地上盖楼。

### 2.2 不要让前端直接吃 LLM 原始输出

LLM 输出是梦。

产品需要的是可验证的工程 contract。

### 2.3 不要假装系统全知道

UI 必须展示不确定性、缺失字段和 fallback。

这是 Iron Man suit。

系统增强人，但不装神。

---

## 3. 建议做法

## 3.1 先产出 `TOPRADOR_SCHEMA.md`

按 `TOPRADOR_SCHEMA_INVESTIGATION.md` 的清单，先跑 20 条真实视频，产出权威字段表。

每个字段必须标清：

- 字段名
- 类型
- 是否必填
- 缺失率
- 示例值
- 哪个下游模块消费它
- 缺失时 fallback 是什么

建议表结构：

| Field | Type | Required | Missing Rate | Consumer | Fallback |
|---|---|---:|---:|---|---|
| `scenes[].scene` | string | yes | TBD | scene anchor | 从 `visual_content` 提取地点 |
| `scenes[].dialogue_and_narration` | string | yes | TBD | script / subtitle | 无字幕草稿 |
| `scenes[].visual_content` | string | yes | TBD | imagePrompt | `scene + subject + style` 拼接 |
| `scenes[].duration` | number | no | TBD | timeline | 平均分配 |
| `scenes[].characters[]` | array | no | TBD | character anchor | MVP 不自动建角色 |

`TOPRADOR_SCHEMA.md` 是 W1-W2 的第一交付物，不是附属文档。

---

## 3.2 给 `analysis_result` 加 `schema_version`

不要让裸 JSON 在系统里流动。

建议结构：

```json
{
  "schema_version": "toprador.analysis.v1",
  "source_url": "https://...",
  "platform": "douyin",
  "viral_analysis": {},
  "scenes": [],
  "quality": {
    "field_completeness": 0.92,
    "confidence": 0.78,
    "warnings": []
  }
}
```

后续 schema 变更时，显式 migrate。

不要默默兼容。

---

## 3.3 建 normalized contract

加一层 adapter：

```text
toprador raw output
  -> normalize_analysis_result()
  -> CascadeAnalysisContract
  -> seed_canvas / subtitles / prompts / anchors
```

所有下游只依赖 `CascadeAnalysisContract`。

不依赖 toprador 原始字段。

这是防火墙。

建议类型：

```ts
type CascadeAnalysisContract = {
  schemaVersion: "cascade.analysis.v1";
  source: {
    platform: "douyin" | "xhs" | "bilibili" | "kuaishou" | "unknown";
    url: string;
    title?: string;
    author?: string;
  };
  quality: {
    fieldCompleteness: number;
    confidence?: number;
    warnings: AnalysisWarning[];
  };
  viral: {
    hook?: string;
    pacing?: string;
    emotionalArc?: string;
    replicableFormula?: string;
    visualStyle?: string;
  };
  scenes: Array<{
    index: number;
    scene?: string;
    visualContent?: string;
    dialogueAndNarration?: string;
    durationSec?: number;
    timestampStartSec?: number;
    timestampEndSec?: number;
    characters?: string[];
    fallbackUsed?: string[];
  }>;
};
```

---

## 3.4 每个下游字段都要有 fallback

没有 fallback 的字段，不能进入 MVP 关键路径。

| 下游需求 | 主字段 | Fallback |
|---|---|---|
| scene 锚点 | `scene` | 从 `visual_content` 提取地点 |
| 字幕 | `dialogue_and_narration + timestamp` | 无时码字幕，后续人工调 |
| imagePrompt | `visual_content` | `scene + subject + style` 拼接 |
| character 锚点 | `characters[]` | MVP 不自动建角色，让用户选 |
| 镜头时长 | `duration` | 平均分配 3-5 秒 |
| 镜头排序 | `scene_index` | 数组顺序 |
| BGM cue | `bgm_cue` | 根据整体风格自动推荐 |

Fallback 不是异常路径。

Fallback 是产品路径的一部分。

---

## 3.5 建 20 条真实视频 fixture corpus

不要每次联调都调用真实 API。

保存 fixture：

```text
fixtures/toprador/
  douyin_001_raw.json
  douyin_001_normalized.json
  douyin_002_raw.json
  douyin_002_normalized.json
  xhs_001_raw.json
  xhs_001_normalized.json
```

覆盖类型：

- 口播视频
- Vlog
- 图文混剪
- 多人物剧情
- 无人场景
- 商品种草
- 字幕很多
- 字幕很少
- 下载失败
- 内容审核失败
- 长视频被截断
- 无明显角色
- 强音乐弱对白

这是项目的小 benchmark。

没有 benchmark，就没有工程判断。

---

## 3.6 做 contract tests

每次改 prompt、换模型、改 parser，都跑：

```text
raw
  -> normalize
  -> validate
  -> seed_canvas
```

测试重点不是“好不好看”。

测试重点是：

- 必填字段是否存在
- `scenes` 数量是否合理
- 文本长度是否超限
- 时间戳是否递增
- prompt 是否为空
- 成本是否记录
- warnings 是否正确
- fallback 是否被标记
- `seed_canvas` 是否能生成可用节点

建议测试命名：

```text
test_normalize_requires_scene_or_visual_content
test_subtitle_fallback_when_timestamp_missing
test_character_anchor_skipped_when_characters_missing
test_seed_canvas_handles_variable_scene_count
test_analysis_warning_surfaces_to_ui
```

---

## 3.7 UI 展示 warnings

不要假装系统全知道。

示例：

```text
这条视频分析完成，但有 2 个不确定点：

- 没有检测到明确角色，已跳过角色锚点
- 字幕时码缺失，字幕会按镜头平均分配
```

这会降低用户对“全自动”的错误期待。

也会让用户知道该在哪里介入。

---

## 3.8 MVP 降低自动化承诺

不要一开始做：

```text
URL -> 自动完整成片
```

先做：

```text
URL
  -> 分析
  -> 草稿
  -> 用户确认
  -> 生成
```

自动化越强，schema 风险越大。

先让人类在关键节点兜底。

---

## 3.9 把失败类型产品化

失败不要只是 exception。

定义 failure taxonomy：

```text
DOWNLOAD_FAILED
ANALYSIS_TIMEOUT
SCHEMA_INVALID
MISSING_DIALOGUE
MISSING_VISUAL_CONTENT
ANCHOR_EXTRACTION_FAILED
PROVIDER_REJECTED
COST_LIMIT_EXCEEDED
```

每种失败都要有用户可理解的恢复路径：

| Failure | 用户恢复路径 |
|---|---|
| `DOWNLOAD_FAILED` | 重试 / 手动上传视频 |
| `ANALYSIS_TIMEOUT` | 重试 / 降级为浅分析 |
| `SCHEMA_INVALID` | 重新分析 / 进入手动草稿 |
| `MISSING_DIALOGUE` | 手动补字幕 / 只生成画面草稿 |
| `MISSING_VISUAL_CONTENT` | 手动描述镜头 / 用脚本生成画面 |
| `ANCHOR_EXTRACTION_FAILED` | 手动选择角色 / 跳过角色锚点 |
| `PROVIDER_REJECTED` | 换 prompt / 换风格 / 换 provider |
| `COST_LIMIT_EXCEEDED` | 降低镜头数 / 只生成草稿 |

---

## 4. 第一阶段验证目标

先追求 80% boring reliability。

不要先追求惊艳 demo。

第一阶段目标：

```text
20 条真实视频
80% 能产出可读分析
70% 能进草稿画布
0 个静默失败
每个失败都有原因和下一步
```

建议 Gate：

| 指标 | 通过线 |
|---|---:|
| 深分析成功率 | >= 80% |
| 核心字段完整率 | >= 90% |
| 草稿画布生成成功率 | >= 70% |
| 静默失败 | 0 |
| 单条草稿成本 | < ¥5 |
| 完整成片预估成本 | < ¥15 |
| 每类失败都有恢复路径 | 100% |

---

## 5. 推荐实施顺序

### Week 1

1. 跑 20 条真实 URL。
2. 保存 raw JSON。
3. 统计字段完整率。
4. 起草 `TOPRADOR_SCHEMA.md`。
5. 定义 `CascadeAnalysisContract`。

### Week 2

1. 实现 `normalize_analysis_result()`。
2. 实现 validator。
3. 建 fixture corpus。
4. 写 contract tests。
5. 产出 `seed_canvas` 最小节点。

### Week 3

1. 加 UI warnings。
2. 接入失败 taxonomy。
3. 做草稿画布。
4. 验证 3-5 镜头草稿链路。
5. 跑 10 个用户样本。

### Week 4-6

1. 加最小视频 / 图片生成。
2. 验证一个角色 + 一个场景锚点复用。
3. 统计真实完成率。
4. 决定是否进入完整 MVP。

---

## 6. 最终建议

不要先做完整平台。

先证明：

1. 爆款分析稳定。
2. 赛道改写有用。
3. 锚点复用可感知。
4. 失败路径可恢复。

这四个成立，再扩。

不成立，画布再漂亮也只是 slop orchestration。

Demo 是 90%。  
产品是 march of nines。
