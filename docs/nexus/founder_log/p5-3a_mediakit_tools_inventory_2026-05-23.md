# P5-3a 火山 MediaKit tools inventory — 2026-05-23 W3D3

**Source**: founder 截图 from 火山控制台 amk(2026-05-23 W3D3 晚)+ PM probe 40 候选 slug 全 fail
**Purpose**: list the **canonical tool slugs** Codex sub-phase A needs;blocked on founder filling §"endpoint slug" column from console API docs
**Status**: ⛔ **BLOCKED · 待 founder 在控制台点进每 tool 看接口文档拿 slug**

---

## 1. Inventory(per 截图)

### 1.1 视频工具 / Video Tools

| 显示名 | Cascade 相关性 | 已确认 slug | 候选(已 probe fail)| Codex 用法 |
|---|---|---|---|---|
| 画质增强 | 低(分析不需要)| — | — | n/a |
| 画质增强–大模型 | 低 | — | — | n/a |
| 字幕擦除 | 低(分析不需要)| — | — | n/a |
| **场景切分** | **核心**(scenes[] 边界)| ❓ | scene-segment/scene-split/video-segment/video-scene-segment/extract-scene/extract-scenes — 全 fail | 给 scenes[i].timestamps |
| **语音转字幕(ASR)** | **核心**(scenes[].dialogue_and_narration)| ❓ | asr/speech-to-subtitle/voice-to-subtitle/voice-to-text/extract-subtitle/extract-transcript/video-asr/voice-extract/voice-subtitle/speech-extract — 全 fail | 给口播文字 + word_timestamps |
| 视频识别字幕(OCR)| 中(burnt-in 字幕可补漏)| ❓ | subtitle-ocr/ocr — fail | 备用 fallback for ASR;在视频已有字幕时拉文本 |
| 高光智剪–短剧 | 低 | — | — | n/a |
| 高光智剪–小游戏 | 低 | — | — | n/a |
| **高光片段提取** | 中(可用于 frame 关键抽取)| ❓ | highlight-extract/extract-highlight/extract-highlight-segment — fail | 候选 frame 抽取来源 |
| 视频抠图 | 低(锚点 anchor 系统可能用到)| ❓ | video-matting/matting/remove-background — fail | 未来 anchor 抠图自动化 |
| **剧情故事线分析** | **战略 critical**(可能直接产 viral_analysis 8 维) | ❓ | storyline-analysis/story-analysis/plot-analysis/extract-story/extract-storyline/analyze-story — fail | **可能替代 sub-phase C 全部**(待证 schema 对齐) |

### 1.2 剪辑工具 / Editing Tools(P5-3 几乎不用,for reference)

| 显示名 | 备注 |
|---|---|
| 音视频拼接 / 裁剪 / 调速 | post-processing,Phase 1 不用 |
| **音频提取** | **疑似 = `/tools/extract-audio`(已 200 OK 确认)**;但显示名归在剪辑工具,不是视频工具 — 命名 vs 显示位置不一致;Codex sub-phase A 已用 |
| 音视频合成 / 音频混合 / 音量调节 / 图片转视频 / 视频翻转 / 加字幕 / 加图片 / 加滤镜 | post,Phase 1 不用 |

### 1.3 音频工具 / Audio Tools

| 显示名 | Cascade 相关性 | 候选 | 用法 |
|---|---|---|---|
| 人声背景音分离 | 中(ASR 干声预处理可能用到)| ❓ | 在 ASR 质量差时降噪 |

### 1.4 图像工具 / Image Tools

| 显示名 | Cascade 相关性 |
|---|---|
| 图像画质增强 / 评估 / 擦除修复 / 背景移除(智能抠图) / 文字识别(OCR) | 低 — 当前 P5-3 处理视频,图像工具走 Apimart |

### 1.5 视频理解拓展工具(⚠️ 截图未展开 — 待 founder 截更全 / 截图)

**关键未知**:右下角的"视频理解拓展工具"是另一个 category,**截图被截断未展开**。Possibility 此类下:
- 含 frame-level vision understanding(替代我假设的 Doubao Vision 直调)
- 含 multi-modal video Q&A
- 含 timestamp + content 综合输出 endpoint

**待 founder**:展开该 category 截全图,贴回 PM。

---

## 2. Cascade 实际需要的 4 个 tool slug + endpoint

P5-3 sub-phase A 真正阻塞在以下 4 个 slug 确认:

| Cascade 需求 | MediaKit 候选 tool | 验收 |
|---|---|---|
| **scenes[].timestamps + boundaries** | 场景切分 | sample call 返回 segments[] with start_ms / end_ms |
| **scenes[].dialogue_and_narration** | 语音转字幕(ASR)| sample call 返回 transcript + word/sentence timestamps |
| **scenes[].visual_content + shot_type** | 视频理解拓展工具内某项(待展开)/ 高光片段提取 / 或外部 Doubao Vision 直调 | sample call 返回每帧/每段 visual 描述 |
| **viral_analysis 8 维** | **剧情故事线分析**(若 schema 含 hook / pacing / climax 等;否则用 Doubao text LLM 聚合自建) | sample call 返回结构化 plot 字段;**最有战略价值的待证项** |

---

## 3. Founder 行动栏(W3D4 / W4D1 任意时刻)

在火山控制台 amk 产品页:

1. 点击"**场景切分**"tool → 找"API 调用 / 接口文档 / 调用示例"按钮 → 截图/复制 endpoint slug 和 request body 样例
2. 点击"**语音转字幕(ASR)**"tool → 同上
3. 点击"**剧情故事线分析**"tool → 同上(**最优先**,可能省 sub-phase C)
4. 点击"**视频理解拓展工具**"category → 展开看 children,截图整张
5. 全部贴回 PM(本文件 §1 的 "已确认 slug" 列就能填上)

**预期结果**:每 tool 有 1 行精确 `/api/v1/tools/<slug>` 名 + request schema + response schema(异步 task_id 还是同步 result)。

---

## 4. PM 已 probe 但全 fail 的 40 候选(避免重复浪费)

```
asr, speech-to-subtitle, voice-to-subtitle, voice-to-text,
extract-subtitle, extract-transcript, extract-keyframe,
extract-keyframes, extract-scene, extract-scenes,
scene-segment, scene-split, video-segment, video-scene-segment,
extract-story, extract-storyline, storyline-analysis,
story-analysis, plot-analysis, analyze-story, analyze-video,
analyze-scene, extract-highlight, highlight-extract,
extract-highlight-segment, extract-frames, extract-image,
video-matting, matting, remove-background, remove-subtitle,
subtitle-ocr, ocr, enhance-quality, video-quality-enhance,
video-asr, voice-extract, voice-subtitle, speech-extract,
audio-extract
```

**确认存在(唯一)**:`extract-audio`(POST /api/v1/tools/extract-audio,异步 task_id 模式)

**Routing 规律**:`POST /api/v1/tools/<X>` 任何 X 都返 HTTP 200;tool 未注册时 `success:false, error.code=InvalidParameter, error.type=NotFound, error.message="tool(<X>) not found"`。所以 200 不等于"endpoint 在",必须看 success 字段。

**Task polling**:`GET /api/v1/tasks/<task_id>` → 200 + 完整 task 状态(`status: pending / failed / done?` 待证 done 状态枚举);失败时 `error.code/type/message` 含 upstream stderr。

---

## 5. 此 doc 生命周期

- **open** @ 2026-05-23 W3D3
- founder 填回 §1 "已确认 slug" 列 → 状态 `partial-resolved`
- 4 个 critical slug(场景切分 / ASR / 剧情故事线 / 视频理解拓展)全部确认 → 状态 `resolved` + 触发 P5-3 brief 重写
- 若 founder 反馈"视频理解拓展工具不存在 children"→ 路径回归 Doubao Vision 直调 + Doubao text LLM 聚合(原 brief 方案 minus extract-audio 走 MediaKit)
