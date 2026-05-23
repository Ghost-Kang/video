# Codex handoff — P5-3 Doubao-lite 视频分析(替代 toprador)

**Owner**: Codex session (backend)
**Status**: READY · no upstream blocker(`ARK_API_KEY` 已在 `.env`)
**Time budget**: 8 工作日(分 5 sub-phase,每 phase 独立可 ship)
**Allocation**: PM_W5_allocation.md §3.2(本 brief 写于 W3D3 晚,W5D1 开工)
**Supersedes**: `handoff/codex_backend_P4-9.md`(Toprador staging)— 该 brief 改为 deprecated;若 P5-3 ship 顺利,P4-9 永不执行
**Founder decision (2026-05-23 W3D3)**: "toprador 路径 = PM 开 P5-3 Doubao-lite 重写(推荐)"

---

## 0. 背景与决策

Toprador 是 founder 老项目的视频分析服务(Flask + MySQL),`MVP_SCOPE A1` 原计划 5 天脱敏 + Postgres 迁移 + 公网部署。**已废弃此路径**,改走全 Doubao(火山方舟 ARK)多模态 + ASR + text LLM 三件套自建。

理由(per founder W3D3 decision):
1. **Provider 一致性**:Cascade 链路 LLM 改写(P3-R2) + judge(P4-1) + 视频生成(Seedance)已统一在 ARK;视频分析也走 ARK = 全境内单 provider
2. **PIPL §38 合规**:全境内,不出境,与 `privacy_v0.md §4.2` 口径一致
3. **工时节省**:跳过 MVP_SCOPE A1 的 5 天部署 + 后续运维成本
4. **架构简洁**:嵌入 `analysis_service.py` 作为新 upstream 分支,不引入 Flask / MySQL / 公网服务

---

## 1. 总 Done-signal(P5-3 全部 ship 后)

- `CASCADE_UPSTREAM=doubao_lite` 是新分支(`analysis_service.py:_load_upstream_payload`)
- `CASCADE_UPSTREAM=doubao_lite` 设为 `.env.example` 新默认(取代 fixture);`fixture` 模式保留用于 offline test
- 端到端跑通:粘 1 条 Douyin / 小红书 URL → `request_shallow_analysis(url, ...)` → 返回 `CascadeAnalysisContract`,**与现有 fixture mode 输出结构 100% 一致**(per `docs/TOPRADOR_SCHEMA.md v1.0` §1-§3)
- 5 条真实 niche URL(3 个 niche × 1-2 条)端到端验证 + staging 报告落 `founder_log/p5-3_doubao_lite_staging_<UTC>.md`
- `P3-7 retry / breaker` + `P4-3 cascade_*` events + `P4-6 cache 持久化` 全部沿用(emit 路径不动,只换 upstream provider)
- 单视频成本 ≤ ¥0.50;p95 延迟 ≤ 90s
- 30+ unit tests(分 sub-phase 累积)
- `handoff/codex_backend_P4-9.md` 标 deprecated/superseded

---

## 2. Sub-phase 拆解(5 阶段,每阶段独立 commit)

### Sub-phase A — ffmpeg 抽帧 + 火山 ASR 接通(1 天)

**目标**:给一条视频 URL,产 `scenes[]` 的局部输出(timestamps + dialogue_and_narration + 占位 visual_content)。

**Done-signal**:
- 新文件 `backend/src/agent/cascade/doubao_lite/frame_extractor.py`(ffmpeg subprocess + key frame 抽取)
- 新文件 `backend/src/agent/cascade/doubao_lite/asr_client.py`(火山 ASR HTTP client;不引入 SDK,直 POST)
- ASR 配置 3 行加 `config.py`:`VOLC_ASR_APP_ID` / `VOLC_ASR_ACCESS_TOKEN` / `VOLC_ASR_CLUSTER`(对应 `volcengineapi.com` ASR endpoint;`.env.example` 同步注释如何获取)
- 端到端测试:1 条本地 .mp4 → 抽 8-12 关键帧到 tmp dir + ASR 返回带 word_timestamps 的 transcript → 按 5-15s 边界切 `scenes[]`(timestamps 字段 + dialogue_and_narration 字段填充)
- 5 unit tests:frame extraction count 在 8-16 范围;ASR client mock 返回 → scene 切片正确;edge case 静音视频 → empty dialogue 但 scenes 仍生成;超时 fallback;采样率不一致兼容
- commit:`feat(P5-3a): ffmpeg frame extraction + 火山 ASR client → partial scenes[]`

**边界**(不在 sub-phase A):
- 不调 Doubao Vision(下一 phase)
- 不写 viral_analysis(sub-phase C)
- 不接入 analysis_service.py(sub-phase D)

---

### Sub-phase B — Doubao Vision 出 visual_content + shot_type(2 天)

**目标**:每帧调 Doubao 多模态,出 `scenes[i].visual_content` + `shot_type`(close_up / medium / wide / aerial / pov)。

**Done-signal**:
- 新文件 `backend/src/agent/cascade/doubao_lite/vision_client.py`
- 使用模型 `doubao-1-5-vision-pro-32k`(或当时最新可用 vision-pro 系列;在 `config.py` 加 `DOUBAO_VISION_MODEL`)
- 单 prompt 出 JSON 结构:
  ```json
  {
    "visual_content": "厨房,母亲背影,正在切菜",
    "shot_type": "medium",
    "subject_count": 1,
    "lighting": "自然光"
  }
  ```
- prompt 设计放在 `prompts/doubao_lite_vision.md`(新),要求严格 JSON 不带 markdown 围栏
- 单帧调用成本 ≤ ¥0.02;p95 延迟 ≤ 8s
- 6 unit tests:happy path mock / malformed JSON fallback / shot_type enum coerce / 多人场景 / 文字遮挡场景 / 黑屏帧(应返回 "transition / black_frame")
- 端到端:把 sub-phase A 的 partial scenes 喂进来,每个 scene 取该段最具代表性 1 帧 → vision 调用 → 填 visual_content + shot_type
- commit:`feat(P5-3b): Doubao Vision client → scenes[].visual_content + shot_type`

**边界**:
- 不做帧级 OCR(那是 P6-x 范围)
- 不做 character recognition(那是 anchor 系统的事)
- 不做"光影分析" subjective field — 只填 enum 化的客观字段

---

### Sub-phase C — Doubao text LLM 聚合产 viral_analysis 8 维(2 天)

**目标**:把完整 scenes[](sub-phase A+B 产出)+ 视频元数据(duration, platform, source_url)喂给 Doubao text LLM,出 `viral_analysis` 8 维 JSON,对齐 `docs/TOPRADOR_SCHEMA.md §2`。

**Done-signal**:
- 新文件 `backend/src/agent/cascade/doubao_lite/viral_analyzer.py`
- 使用 `doubao-seed-1-6-250615`(已配,P4-1 用同款)
- 单 prompt 出 viral_analysis JSON:hook / pacing / climax / emotional_arc / replicable_formula / target_audience / niche_signals / score_breakdown
- prompt 放在 `prompts/doubao_lite_viral_analysis.md`
- 调用成本 ≤ ¥0.15;p95 延迟 ≤ 30s
- 8 unit tests:8 维度字段全填 / replicable_formula 长度 < 600 字 / score_breakdown 数值 in [0,1] / hook_pattern_id 与 hook_taxonomy.HOOK_PATTERNS 兼容 / emotional_arc enum 校验 / 文字暴力/敏感内容跳过(返回 W14 warning)
- commit:`feat(P5-3c): Doubao text LLM → viral_analysis 8 dims (replaces toprador analysis_result)`

**边界**:
- 不动 `adapter.py` / `contract.py`(下一 phase)
- 不做 "为什么 score 是 0.83" 的可解释性输出 — 那是 P6-x

---

### Sub-phase D — analysis_service.py 接 doubao_lite 分支(2 天)

**目标**:让 `request_shallow_analysis(url, ...)` 在 `CASCADE_UPSTREAM=doubao_lite` 时调上面 3 个 sub-phase 的客户端,组装成与 toprador / fixture **一模一样** 的 dict 结构,经 `adapter.normalize_analysis_result()` → `CascadeAnalysisContract`。

**Done-signal**:
- `analysis_service.py:_load_upstream_payload` 新增分支:
  ```python
  if upstream == "doubao_lite":
      return await _call_doubao_lite(source_url, user_id=user_id, run_id=run_id)
  ```
- 新函数 `_call_doubao_lite()` 编排 sub-phase A + B + C(并发抽帧 + vision + ASR;最后串行 viral_analyzer)
- **P3-7 retry / breaker + P4-3 emit 路径完全复用**:对 Doubao 调用包装相同的 retry / circuit_breaker / cascade_retry / cascade_circuit_open emits(像现在的 `_call_toprador`)
- **P4-6 cache 复用**:同 URL 命中同 cache,SQLite 持久化
- 8 unit tests:happy path / ASR 失败 fallback / vision 失败 fallback / viral_analyzer 失败 → S5 / 部分 scenes 不完整 / 整体超时 → S7 / 24h cache 命中 / 不同 user 同 URL 共享 cache
- 端到端 staging:跑 3 niche × 1 URL,落 `founder_log/p5-3_doubao_lite_staging_<UTC>.md`
- commit:`feat(P5-3d): analysis_service doubao_lite branch with retry/cache/observability`

**边界**:
- 不动 fixture mode(保留 offline test 用)
- 不删 `_call_toprador()` 函数(保留作 P4-9 fallback;只在配置层设默认改 doubao_lite)

---

### Sub-phase E — 默认切换 + 老 toprador 标 deprecated + cleanup(1 天)

**目标**:Phase 1 内测正式使用 Doubao-lite 作为分析上游。

**Done-signal**:
- `.env.example` 默认 `CASCADE_UPSTREAM=doubao_lite`(原 `fixture`)
- `config.py` 默认值同步
- `docs/TOPRADOR_SCHEMA.md` 顶部加 deprecation 注:"原 toprador 上游路径自 P5-3 起 deprecated,Doubao-lite 复用此 schema 作为产物契约;字段语义不变"
- `handoff/codex_backend_P4-9.md` 顶部加:"**SUPERSEDED by P5-3** @ 2026-05-23 W3D3 — 不再执行,除非 founder 主动 ARK 不可用 fallback"
- `PM_W5_allocation.md §"engineering done"` 标 P5-3 全 5 phase done
- `scripts/check_progress.sh` 加 `p5_3` probe:扫 `analysis_service.py` 含 `_call_doubao_lite` 即标 done
- 第一份真实 staging 报告 commit 进 `founder_log/`
- commit:`feat(P5-3e): default Cascade upstream to doubao_lite; deprecate toprador path`

---

## 3. 全 brief 共享的实现指引

### 3.1 Schema 不动

输出最终必须满足 `docs/TOPRADOR_SCHEMA.md v1.0`(`schema_version: "1.0"` + §1-§3 字段)。所有下游(`adapter.py` / `contract.py` / `rewrite.py` / `events.py` / `anchors.py`)**零改动**。如果 sub-phase 输出某字段不全,**adapter 兜底加 warning**(P0-4 范式),不要往 schema 加字段。

### 3.2 复用 Cascade 现有基础

- retry / breaker:沿用 `circuit_breaker.py` 的 `_TOPRADOR_BREAKER` 范式,新建 `_DOUBAO_VISION_BREAKER` + `_VOLC_ASR_BREAKER` + `_DOUBAO_TEXT_BREAKER`,每个独立熔断
- cache:沿用 `storage.save_toprador_cache` 范式,可加 `save_doubao_lite_cache`(或复用同一 table,namespace 字段区分)— **简单做法是直接复用 toprador_cache table**,key 用 `f"doubao_lite::{source_url_hash}"` 前缀避免冲突
- observability events:沿用 `cascade_retry / cascade_circuit_open / cascade_cache_hit / cascade_cache_miss`,只是 `endpoint` 字段值变成 doubao endpoint URL

### 3.3 配置项汇总(`.env.example` 同步加)

```
# Doubao-lite 视频分析(P5-3,2026-05-23 默认上游)
CASCADE_UPSTREAM=doubao_lite

# Doubao Vision(多模态)
DOUBAO_VISION_MODEL=doubao-1-5-vision-pro-32k

# 火山 ASR
VOLC_ASR_APP_ID=
VOLC_ASR_ACCESS_TOKEN=
VOLC_ASR_CLUSTER=volcengine_streaming_common
# (或非流式 endpoint,见火山引擎 ASR 文档)
```

### 3.4 PII 不写入 events

任何 emit 携带的 source_url 一律 hash(per `_hash_source_url`,P3-R1 + P4-3 已建立的口径)。ASR transcript / vision content 在生产 db 落地受 P4-7 retention 策略管(business 永久保留,因 anchor 复用刚需)。

---

## 4. 不在此 brief 范围

- ❌ 重建 toprador 自身(不需要 — 整个被替换)
- ❌ MVP_SCOPE B5(BGM 选取)/ B6(字幕渲染)/ B7(剪辑合成)— 这些是后期工作,与 P5-3 无关
- ❌ 多模态 Transformer 自训(per `TOPIC_INTELLIGENCE_DEEPENING_PLAN §4.4`,5万样本后才进路线图)
- ❌ Kling / Seedance 视频生成(已独立配置 `ARK_VIDEO_MODEL=doubao-seedance-2-0-260128`)
- ❌ ffmpeg server-side 端到端合成

---

## 5. Upstream dep / Blocker

- ✅ `ARK_API_KEY`(已配)
- ⏳ **founder 申请 `VOLC_ASR_APP_ID` + `VOLC_ASR_ACCESS_TOKEN`**:这是火山 ASR 独立 product,不在 ARK 范围内 — founder 需要在火山引擎控制台 https://console.volcengine.com/asr 创建 app + 拿 access token
- ⏳ founder 确认 `DOUBAO_VISION_MODEL` 在你 ARK 账户已开通(多模态推理点可能与 text 不同)
- ✅ `docs/TOPRADOR_SCHEMA.md v1.0`(已 stable)

**Sub-phase A 起跑前 founder 必须先配 VOLC_ASR_* 三件**,否则 ASR client 启动即抛 RuntimeError。Sub-phase B/C 只需 ARK key 已有就行。

---

## 6. 验收指标(W6D7 复盘看)

| 指标 | 目标 | 失败 → 动作 |
|---|---|---|
| 60s 视频端到端延迟 p95 | ≤ 90s | 拆帧降 to 6-8 / 并发 vision call / W7 加 cache pre-warm |
| 单视频成本 | ≤ ¥0.50 | 拆帧降 / 改用 `doubao-1-5-vision-lite`(更便宜)/ 或降频 |
| 3 niche × 5 URL pass rate(adapter 不抛) | ≥ 80% | 适配层修 schema 偏移 |
| Founder qualitative 信号("和 fixture mode 比 viral_analysis 准不准") | ≥ 7/10 | prompt 调 viral_analyzer §2 + 加 in-context exemplar |

---

## 7. P4-9 处理

P5-3e 同步在 `handoff/codex_backend_P4-9.md` 顶部加:

```
**SUPERSEDED by P5-3** @ 2026-05-23 W3D3
理由:founder 2026-05-23 决定 toprador 路径走 Doubao-lite 自建(P5-3),
不再要求老 toprador 脱敏部署。本 brief 仅在 P5-3 ship 后 staging 失败
或 founder 明示要求回滚时才执行。当前状态:dormant。
```

P5-3 sub-phase E 包含这个动作,P4-9 brief 文件 **保留**(不删 — git history 完整)。
