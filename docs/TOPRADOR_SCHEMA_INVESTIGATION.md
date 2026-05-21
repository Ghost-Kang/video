# toprador video-analysis · 维度调研清单

**Status**: Draft
**Date**: 2026-05-18
**Owner**: 工程
**Related**: `TOPIC_TO_CREATION_PIPELINE.md` §6.2 · `ROADMAP_6M.md` W1-W2 · `MVP_SCOPE.md` A1 · `CANVAS_DESIGN.md` §7-8

---

## 0. 目的

`TOPIC_TO_CREATION_PIPELINE.md` 把 toprador `analysis_result` 描述为 `viral_analysis + scenes[] × 8`，但**实际 8 维 / 单镜字段的 schema 未在本仓库文档里 enumerate**。在 W1-W2 toprador 脱敏迁移启动前，必须先摸清完整 schema，避免：

- 画布 `seed_canvas` 消费字段缺失
- 字幕模块（`subtitle_watermark` 扩展）从 `dialogue_and_narration` 生成 SRT 找不到字段
- imagePrompt 生成器引用 `visual_content` 时字段名漂移
- MySQL → Postgres 迁移期间 JSONB 折叠策略错位

本清单 = 调研问题表 + 验收交付物列表。

---

## 1. viral_analysis 顶层（"8 维"）

文档里只有 `PRODUCT_VISION.md:233`"8 维 viral_analysis JSON"一句概括，**需要回源**。

### 1.1 待确认
- [ ] 实际维度数是 8 还是 N？穷举字段名
- [ ] 每个维度的类型：`string` / structured object / `enum` / score (0-100)
- [ ] 是否可空？默认值？
- [ ] 输出语言：中文 / 英文 / 双语
- [ ] 是否带置信度（confidence）

### 1.2 基于现有文档语境推断的候选维度
> 来源 `PRODUCT_VISION.md:236`、`TOPIC_TO_CREATION_PIPELINE.md:132,218`、`docs/TOPIC_TO_CREATION_PIPELINE.md:147` —— **推断，非权威**

| 候选维度 | 在 Cascade 哪里被消费 |
|---|---|
| `hook`（开场抓人） | ACMM whyItHit 翻译 / 画布开场镜头建议 |
| `pacing` / `rhythm`（节奏节拍） | 画布节奏建议 |
| `climax` / `peak`（爆点） | 画布章节"高潮"节点 |
| `visual_style`（视觉风格） | imagePrompt 风格基线 |
| `emotional_arc`（情绪曲线） | 画布章节情绪标签 |
| `target_audience`（目标人群） | 与赛道索引做匹配度 |
| `engagement_levers`（互动钩子） | DNA 互动消费引用 |
| `replicable_formula`（可复刻公式） | howToAdapt + agent 重做依据 |

调研产出需要把上面这张表"是 / 否 / 实际名称"对一遍。

---

## 2. scenes[] 单镜结构

### 2.1 已知被消费的字段（文档显式引用）
| 字段 | 消费方 | 出处 |
|---|---|---|
| `scene` | 画布 scene 锚点自动建议 | `TOPIC_TO_CREATION_PIPELINE.md:145` |
| `dialogue_and_narration` | 剧本生成 + SRT 字幕 | `TOPIC_TO_CREATION_PIPELINE.md:146` / `ROADMAP_6M.md:163` / `MVP_SCOPE.md:44` |
| `visual_content` | imagePrompt 生成 | `TOPIC_TO_CREATION_PIPELINE.md:147` |
| `hook` | 开场判断（视频级 or 单镜？需确认） | `TOPIC_TO_CREATION_PIPELINE.md:132,218` |

### 2.2 待确认字段
- [ ] `duration`（镜头时长，秒）
- [ ] `shot_type`（特写 / 中景 / 全景 / 鸟瞰）
- [ ] `camera_movement`（推 / 拉 / 摇 / 移 / 固定）
- [ ] `transition`（转场类型）
- [ ] `bgm_cue` / `sfx`（音乐/音效提示）
- [ ] `subject` / `characters[]`（主体人物）
- [ ] `first_frame_url` / `keyframe_url`（截帧 URL）
- [ ] `subtitle_text` 是否独立于 `dialogue_and_narration`
- [ ] `narration_speaker`（旁白 vs 角色对话）
- [ ] `scene_index` / `timestamp_start` / `timestamp_end`

### 2.3 结构性问题
- [ ] 数组长度是恒等 8 吗？变长边界？最少 / 最多？
- [ ] 8 镜不足时如何处理（合并 / padding）
- [ ] 超长视频（>3 分钟）是否会被截断

---

## 3. 调用接口 / 入参

参考 `ROADMAP_6M.md:80`"`analyze_single_video_task` 跑通一条抖音 URL"。

- [ ] 入参 schema：`url` only？还是 `url + platform + user_metadata`?
- [ ] 支持平台清单：仅抖音 / 含 B 站 / 含 YouTube？
- [ ] 同步 vs 异步：直接返 result 还是返 `task_id` + 轮询
- [ ] 超时 / 重试策略
- [ ] 并发上限（多模态 LLM 速率限制）
- [ ] 失败模式：部分场景失败时返回什么

---

## 4. 模型 / 成本

文档已确认：多模态 LLM 是 `doubao-seed-2-0-pro`（`TOPIC_TO_CREATION_PIPELINE.md:76`），单次 ~¥0.3-0.8（`PRODUCT_VISION.md:296`）。

- [ ] 实测成本分布（按视频时长档：≤30s / 30-60s / 60-180s）
- [ ] token 换算公式（如有）
- [ ] 模型切换支持：豆包 / 通义 / 智谱 / Gemini 多模态
- [ ] 是否需要先转写（ASR）再分析，还是直接喂视频

---

## 5. 依赖 / 副作用

### 5.1 上游依赖
- [ ] `Douyin_Download`（`ROADMAP_6M.md:311`）是否是前置必跑？
- [ ] 其他平台下载器是否存在
- [ ] 视频中间文件落地：本地 / S3 / 临时 tmpfs
- [ ] 中间产物（截帧、转写、音频）是否保留 / 大小

### 5.2 需要替换的 OPPO 内网依赖（`ROADMAP_6M.md:77`、`PRODUCT_VISION.md:364`）
- [ ] OPPO SSO → Clerk-style 鉴权
- [ ] OPPO 内部 LLM 网关 → 公网豆包/通义/智谱
- [ ] `wanyol.com` 域名引用
- [ ] OPPO 内部对象存储 → S3-compatible（项目已有，见 `backend/src/agent/tools/s3_upload.py`）
- [ ] 是否依赖任何 OPPO 内部 npm / pip 包

---

## 6. 数据库 schema

### 6.1 现有 MySQL 表
- [ ] 表清单：`video_analysis_task` / `viral_analysis` / `scenes` 还是单表 JSON 字段？
- [ ] 主键策略（自增 id / UUID）
- [ ] 索引：URL 去重 / opus_id / created_at
- [ ] 外键关系

### 6.2 Postgres 迁移决策
- [ ] 哪些字段保持列结构、哪些折叠为 `JSONB`
- [ ] `viral_analysis` 维度建议：单 `JSONB` 还是 8 列（影响后续按维度排序/筛选）
- [ ] `scenes[]` 建议：副表 `scene` + `analysis_id` 外键，还是 `JSONB[]`
- [ ] 全文检索需求（`dialogue_and_narration` 是否要 GIN 索引）

---

## 7. Cascade 消费方契约

### 7.1 画布 `seed_canvas` event（`CANVAS_DESIGN.md:811`）
- [ ] payload 形态：传完整 `analysis_result` 还是只传 `analysis_id`?
- [ ] agent 在 `seed_canvas` 后自动初始化哪些节点（script / character / scene / shots / imagePrompts）—— 与 `TOPIC_TO_CREATION_PIPELINE.md:411` 对齐

### 7.2 字幕模块（`subtitle_watermark` 扩展，`MVP_SCOPE.md:44`）
- [ ] SRT 时码从哪个字段来：`timestamp_start/end` / 推算 / LLM 二次生成
- [ ] 多语言字幕支持

### 7.3 imagePrompt 生成器
- [ ] prompt 模板引用的字段（除 `visual_content` 外还有 `scene` / `subject` / `visual_style` ?）
- [ ] 与赛道索引 `style_principles` 的拼接策略

### 7.4 锚点自动建议
- [ ] character 锚点从 `subject` / `characters[]` 推断 —— 字段是否存在
- [ ] scene 锚点从 `scene` 字段去重

---

## 8. 版本兼容 / 演进

- [ ] 是否需要在 `analysis_result` 加 `schema_version` 字段
- [ ] toprador 老数据是否有迁移诉求（还是 Cascade 从空库重新跑）
- [ ] 8 维变更（增/减一维）时的兼容策略

---

## 9. 法律 / 合规

`MVP_SCOPE.md:237` 已硬约束：用户输入 URL 的视频分析仅作"学习公式"，**原视频不存储 > 24h**。

- [ ] 哪些字段含视频原文 / 截帧 → 是否进 24h 清理
- [ ] `analysis_result` 是否含可识别的原作者 PII（昵称 / 头像 URL / UID）
- [ ] 跨境数据（如分析对象在境外平台）合规边界
- [ ] 用户协议条款草稿位置

---

## 10. 对接动作（调研执行步骤）

按顺序产出，每步 ≤ 1 天：

1. **clone toprador** → 在仓库内 grep `viral_analysis` / `scenes` / `analyze_single_video_task` 字段写入位置
2. **跑一条样本**（用"5 点起床实录"风格的抖音 URL）→ `pg_dump` / `json.dumps` 完整 `analysis_result`
3. **对照本清单填空** → 输出 `docs/TOPRADOR_SCHEMA.md`（权威 schema 文档）
4. **三方对齐**：画布（`CANVAS_DESIGN.md`）/ 字幕（`subtitle_watermark`）/ imagePrompt 生成器各自的最小字段需求
5. **锁定 MVP 范围**：哪些字段 W1-W2 必须迁、哪些 V1.5 再补
6. **回填本仓库**：把 `TOPIC_TO_CREATION_PIPELINE.md` 里的"scenes[] × 8 多维度"展开为权威字段表

---

## 11. 风险与回退

| 风险 | 触发条件 | 回退 |
|---|---|---|
| viral_analysis 实际是非结构化文本（不是 8 维 JSON） | grep 后发现是 prompt 输出纯文本 | LLM 二次结构化（成本 + 一次调用） |
| scenes 数量不是 8 而是变长 | 样本数据显示 5-12 镜 | 画布章节节点改为变长 |
| `subject` / `characters` 字段不存在 | 单镜里没人物维度 | character 锚点延后 V1.5，MVP 仅 scene 锚点自动建议 |
| 视频下载链路依赖灰色 API | Douyin_Download 风控被封 | 用户端浏览器插件上传 + 直接喂视频字节流 |

---

## 12. 验收

调研完成的判据：
- [ ] `TOPRADOR_SCHEMA.md` 字段表 100% 来自代码 / 样本，**无推断**
- [ ] 3 个消费方（画布 / 字幕 / imagePrompt）各自的字段依赖被明确标注
- [ ] OPPO 内网依赖替换清单完成且每项有公网对应方案
- [ ] Postgres DDL 草稿可提交
- [ ] W1-W2 工时估算精度 ±20% 之内（vs `ROADMAP_6M.md` 的 5d）
