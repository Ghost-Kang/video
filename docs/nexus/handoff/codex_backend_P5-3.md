# Codex handoff — P5-3 Doubao-lite 视频分析(替代 toprador)

**Owner**: Codex session (backend)
**Status**: READY · no upstream blocker(`ARK_API_KEY` 已在 `.env`)
**Time budget**: 8 工作日(分 5 sub-phase,每 phase 独立可 ship)
**Allocation**: PM_W5_allocation.md §3.2(本 brief 写于 W3D3 晚,W5D1 开工)
**Supersedes**: `handoff/codex_backend_P4-9.md`(Toprador staging)— 该 brief 改为 deprecated;若 P5-3 ship 顺利,P4-9 永不执行
**Founder decision (2026-05-23 W3D3)**: "toprador 路径 = PM 开 P5-3 Doubao-lite 重写(推荐)"

---

## 0. 背景与决策

Toprador 是 founder 老项目的视频分析服务(Flask + MySQL),`MVP_SCOPE A1` 原计划 5 天脱敏 + Postgres 迁移 + 公网部署。**已废弃此路径**,改走 **火山 MediaKit(server-side 抽帧/抽音/转写)+ Doubao Vision(多模态) + Doubao text LLM(语义聚合)** 全境内自建。

**重要更新 2026-05-23 W3D3 22:55 PDT**(founder 提供 MediaKit curl 后):
- Sub-phase A 不再需要本地 ffmpeg + 火山 ASR 直调;统一走 **MediaKit `tools/extract-audio` + `extract-frames` + `transcribe`**(per founder 确认 3 tool 完整)
- Auth 简化为单 Bearer token(原 brief 假设的 ASR 三件套作废)
- Sub-phase A 工时 1d → **0.5d**(server-side 处理,代码大幅简化)
- 总工时 8d → **~7.5d**

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

### Sub-phase A — MediaKit 抽帧 + 转写接通(0.5 天)

**Founder 2026-05-23 决定**:用火山 **MediaKit** 服务(`mediakit.cn-beijing.volces.com/api/v1/tools/*`)做 server-side 抽帧 + 抽音 + 转写,**不再需要本地 ffmpeg + 文件下载**。

**已知 API 契约**(来自 founder 提供的 curl,2026-05-23):

```bash
# extract-audio (已验证)
curl -X POST 'https://mediakit.cn-beijing.volces.com/api/v1/tools/extract-audio' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <VOLC_MEDIAKIT_AK>' \
  -d '{"video_url": "https://example.com/my_video.mp4"}'

# MediaKit 还含(per founder 确认): extract-frames + transcribe
# 三个 endpoint 假设统一 base URL + auth + 类似输入(video_url 或 audio_url)
```

**Auth 方式**:**单 Bearer token**(`Authorization: Bearer <VOLC_MEDIAKIT_AK>`),不是 AK+SK HMAC。token 形态 `AKLT...`(Volc Access Key)。

**目标**:给一条视频 URL,产 `scenes[]` 的局部输出(timestamps + dialogue_and_narration + 占位 visual_content)。

**Done-signal**:
- 新文件 `backend/src/agent/cascade/doubao_lite/mediakit_client.py` — 三个方法:
  - `async extract_audio(video_url) -> dict`(返回结构待 Codex 第一次跑 staging 探测)
  - `async extract_frames(video_url, count=12) -> list[dict]`(假设响应有 frame_url + timestamp_s;**Codex 需用本 token 跑 1 次真实 curl 确认 schema**)
  - `async transcribe(video_or_audio_url) -> dict`(假设有 segments[] + word_timestamps;**同上待 Codex 探测**)
- 配置 1 行加 `config.py`:`VOLC_MEDIAKIT_AK = os.getenv("VOLC_MEDIAKIT_AK", "")`
- `.env.example` 加 1 行注释 + placeholder
- 因 SDK 不存在,直 httpx POST + 沿用 P3-7 retry/breaker 范式
- 端到端测试:1 条公开 video URL → 抽帧 + 转写 → 按 transcribe 的 segment 边界切 `scenes[]`(timestamps 字段 + dialogue_and_narration 字段填充)
- 5 unit tests:happy path mock / 401 auth refused / 5xx retry / 静音视频 → empty dialogue 但 scenes 仍生成 / 单 service 超时 fallback
- 1 个 staging script `scripts/p5-3a_mediakit_probe.py` 用 founder 提供的 dev key 跑一次真实 video URL,把 3 个 endpoint 返回的 raw JSON 落盘到 `founder_log/p5-3a_mediakit_schemas_<UTC>.md`(为后续 phase 提供 schema 真理来源)
- commit:`feat(P5-3a): MediaKit client (extract-audio/frames/transcribe) → partial scenes[]`

**⚠️ Pre-execution 待 founder 给 PM 确认 / 提供**:

1. **`VOLC_MEDIAKIT_AK`** 长期有效的 key(founder 之前给的 `AKLT...` 是临时测试,不入 git)
2. `extract-frames` 与 `transcribe` 的精确 endpoint path —— 假设是 `/api/v1/tools/extract-frames` 和 `/api/v1/tools/transcribe`,**Codex sub-phase A 第一步用临时 key probe 1 次确认**
3. 公开 docs 找不到 MediaKit;Codex 第一次 probe 时把 3 个 endpoint 的真实 request/response JSON 写到 `founder_log/p5-3a_mediakit_schemas_<UTC>.md`,后续 phase 当真理源

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

# 火山 MediaKit(server-side 抽帧 + 抽音 + 转写,2026-05-23 founder 决定路径)
# Endpoint base: https://mediakit.cn-beijing.volces.com/api/v1/tools/
# Auth: Authorization: Bearer <VOLC_MEDIAKIT_AK>
# 公开 docs 缺;开通 / 申请方式 founder 内部渠道
VOLC_MEDIAKIT_AK=
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
- ⏳ **founder 给长期 `VOLC_MEDIAKIT_AK`**:`AKLT...` 形态;2026-05-23 提供的临时测试 key 已用于本 brief 设计验证,**不要** 落进 git。Codex sub-phase A 起跑前需要长期 key 才能跑真实 staging。
- ⏳ founder 确认 `DOUBAO_VISION_MODEL` 在你 ARK 账户已开通(多模态推理点可能与 text 不同)
- ⏳ MediaKit `/tools/extract-frames` + `/tools/transcribe` endpoint path 仅为 PM 推测;Codex sub-phase A 第一步必须 probe 真实 API 落 schema(per sub-phase A §"Pre-execution 待 founder 给 PM 确认 / 提供" §2-§3)
- ✅ `docs/TOPRADOR_SCHEMA.md v1.0`(已 stable;MediaKit 真实 schema 探测后,adapter 兜底补齐)

**Sub-phase A 起跑前 founder 必须先给长期 `VOLC_MEDIAKIT_AK`**,否则 staging probe 跑不通。Sub-phase B/C 只需 ARK key 已有就行。

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
