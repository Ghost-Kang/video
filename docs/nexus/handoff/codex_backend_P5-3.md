# Codex handoff — P5-3 MediaKit-driven 视频分析(替代 toprador 分析层)

**Owner**: Codex session (backend)
**Status**: ✅ **READY** (post 2026-05-23 W3D3 大重写;founder 提供 3 份完整 MediaKit API 文档后)
**Time budget**: **~3 工作日**(从原 7.5d 砍掉 ~60% — `analyze-video-storyline` 一 API 直接覆盖 scenes + dialogue + visual + score 四件套)
**Allocation**: PM_W5_allocation.md §3.2(W4D7 → W5D1 起跑)
**Partial-supersede**: `handoff/codex_backend_P4-9.md`(Toprador staging)— 分析层 deprecated;**老 toprador 的"页面 URL → 直接媒体 URL resolver 模块保留**(per Founder W3D3 决定)
**Sources of truth(API 文档,founder W3D3 提供)**:
1. **场景切分** API(`POST /api/v1/tools/segment-scenes`)— 异步,task_id 模式;返回 `result.segments[].{start_time, end_time, segment_video_url}`
2. **剧情故事线分析** API(`POST /api/v1/tools/analyze-video-storyline`)— **战略 jackpot**:一次调用拿到 clip_title / clip_summary(画面)/ clip_dialogue(口播)/ clip_score / clip_snapshot_url + source_video_summary + storyline_highlights
3. **视频理解 Chat API**(`POST https://amk-ark.cn-beijing.volces.com/api/v1/chat/completions`)— ARK Chat 兼容;**Authorization 两 key 斜杠拼接**:`Bearer <ARK_API_KEY>/<VOLC_MEDIAKIT_AK>`;支持 5GB URL 视频,自由 prompt + fps/max_frames/max_pixels 控帧

---

## 0. 关键架构转向(post W3D3)

原 brief(`3392938` + `528525f` + `d155b23`)基于 3 个错假设,全废:
- ❌ 假设 MediaKit 有"完整 3-tool 套" extract-audio + extract-frames + transcribe
- ❌ 假设需要自建 Doubao Vision + Doubao text LLM 聚合 4 步流水线
- ❌ 假设 MediaKit 工时 7.5d

实际(根据 founder 提供的 3 份完整文档):
- ✅ **`analyze-video-storyline` 一 API 一站式覆盖 P5-3 sub-phase A+B+C 的 80%**
- ✅ `segment-scenes` 仅用于场景物理切分(若 storyline 已含 clip_start_time/end_time 则可不用)
- ✅ ARK 视频理解 Chat API 仅用于补 viral_analysis 中 storyline 没明确字段对应的 hook / pacing / climax / emotional_arc
- ✅ 不需要 ffmpeg / 不需要 ASR / 不需要 Vision 单独调用

工时 7.5d → **~3d**(详见 §3 phase 拆解)。

---

## 1. 总 Done-signal(P5-3 全部 ship 后)

- `CASCADE_UPSTREAM=mediakit` 是新分支(`analysis_service.py:_load_upstream_payload`)— 命名从 doubao_lite 改为 mediakit 更准确反映来源
- `.env.example` 默认从 `fixture` 改为 `mediakit`;`fixture` 保留作 offline test
- 端到端跑通:粘一条 Douyin / 小红书 URL → toprador URL resolver 拿直链 .mp4 → `request_shallow_analysis(...)` → 返回 `CascadeAnalysisContract`,与 fixture mode 输出结构 100% 一致
- 5 条真实 niche URL(3 niche × 1-2 条)端到端验证 + staging 报告
- P3-7 retry / breaker + P4-3 cascade_* events + P4-6 cache 持久化沿用
- 60s 视频端到端 ≤ 8 分钟(MediaKit 平均 RTF 3-5,storyline ~4-6 min)
- 单视频成本 ≤ ¥0.50(MediaKit storyline + 可选 ARK Chat 补维)
- 25+ unit tests(累积 5 sub-phase)
- `handoff/codex_backend_P4-9.md` 顶部 SUPERSEDED 标记保留

---

## 2. MediaKit 关键 API 契约(已确认,真实文档)

### 2.1 `POST /api/v1/tools/analyze-video-storyline` ⭐ 核心

**Request**:
```json
{
  "video_urls": ["https://example.com/movie_part1.mp4"],
  "enable_snapshot": true
}
```

**Auth**: `Authorization: Bearer <VOLC_MEDIAKIT_AK>`

**Limits**:
- 单视频建议 ≤ 150 min(2.5h),累计 ≤ 210 min(3.5h)
- 单任务最多 30 个 video file
- 分辨率最高 1080p
- 单账号 20 并发,超出排队

**Response (sync)**:
```json
{"success": true, "task_id": "amk-tool-analyze-video-storyline-...", "request_id": "..."}
```

**Polling**: `GET /api/v1/tasks/{task_id}` → `status: completed` 时:
```jsonc
{
  "result": {
    "duration": 342.36,
    "source_video_info": [
      {
        "source_video_index": 0,
        "source_video_url": "...",
        "source_video_title": "AI 生成标题",
        "source_video_summary": "AI 生成 ~150 字摘要",
        "source_video_tag": ["tag1", "tag2", ...]  // 5 个
      }
    ],
    "storyline_clips": [
      {
        "clip_index": 0,
        "source_video_index": 0,
        "clip_start_time": 9.12,
        "clip_end_time": 43.28,
        "clip_title": "场景标题",
        "clip_summary": "AI 生成场景描述,含居家室内/书桌/人物等画面细节",
        "clip_dialogue": "完整口播文字 + 时序",
        "clip_score": 3.5,           // 精彩度 0-5
        "clip_snapshot_url": "..."   // enable_snapshot=true 才有
      }
    ],
    "storyline_highlights": [
      {
        "highlight_index": 0,
        "highlight_clips_index": [0, 1, 2],
        "highlight_title": "...",
        "highlight_summary": "..."
      }
    ]
  },
  "created_at": ..., "finished_at": ..., "expires_at": ...
}
```

**字段映射 Cascade contract(`docs/TOPRADOR_SCHEMA.md v1.0`)**:

| Cascade 字段 | MediaKit 来源 |
|---|---|
| `analysis_id` | 本地生成(sha256 of url+user_id) |
| `source_url` | input video_url(toprador resolver 解析后的直链)|
| `platform` | 从 input 原 Douyin/XHS URL 推断(adapter 层) |
| `duration_s` | `result.duration` |
| `model` | `"mediakit-storyline"`(固定串)|
| `cost_cny` | 本地估算(待 W5 cost calibration P4-8 跑后给) |
| `viral_analysis.replicable_formula` | **`source_video_summary` + storyline_highlights[].summary 拼接 + ARK Chat 补 prompt(详 §2.3)** |
| `viral_analysis.target_audience` | **`source_video_tag` 翻译** |
| `viral_analysis.hook / pacing / climax / emotional_arc / score_breakdown / niche_signals` | **ARK Chat API 补维**(详 §2.3),input = storyline clips 的 dialogue + summary |
| `scenes[i].timestamps` | `storyline_clips[i].{clip_start_time, clip_end_time}` |
| `scenes[i].visual_content` | `storyline_clips[i].clip_summary` |
| `scenes[i].dialogue_and_narration` | `storyline_clips[i].clip_dialogue` |
| `scenes[i].shot_type` | **ARK Chat 推断**或暂 default "medium" |
| `scenes[i].importance_score`(新)| `storyline_clips[i].clip_score` (若 contract 不含此字段,加进 schema v1.1) |
| `scenes[i].snapshot_url`(新)| `storyline_clips[i].clip_snapshot_url` |
| `warnings[]` | adapter 层根据 missing fields 补 |
| `confidence` | 本地算法:storyline clip 数 / duration ratio + avg clip_score |

### 2.2 `POST /api/v1/tools/segment-scenes`(可选,见 §3.0 决策)

如果 storyline 的 `clip_start_time/end_time` 边界质量不够(需要更细 / 更稳),用 segment-scenes 替代:

**Request**:
```json
{
  "video_url": "https://...",
  "segment_threshold": 10,      // 0-100,默认推荐 10
  "min_duration": 2.5,          // s,合并过短片段
  "max_duration": 30,           // s,强制切分长片段
  "enable_clip_fade": false
}
```

**Polling result**:
```json
{
  "result": {
    "duration": 185.5,
    "segments": [
      {"start_time": 0.0, "end_time": 15.2, "segment_video_url": "https://...clip_1.mp4"}
    ]
  }
}
```

**用法**(若启用):用 segment-scenes 拿物理 segment_video_url[],再把每段 segment_video_url 输入 analyze-video-storyline 拿语义解析。增加成本 + 延迟,但可控切分粒度。

**Codex 决策点**:**先不上 segment-scenes**;直接用 storyline 的 clip 边界 ship 第一版;首位 concierge creator first-run 后看 founder 评价是否需要更精细切分,再决定是否引入。

### 2.3 ARK 视频理解 Chat API(补 viral_analysis 8 维)

**Endpoint**: `POST https://amk-ark.cn-beijing.volces.com/api/v1/chat/completions`

**Auth**(注意!): `Authorization: Bearer <ARK_API_KEY>/<VOLC_MEDIAKIT_AK>` — **两 key 斜杠拼接成一个 string**

**Model**:沿用现有 `doubao-seed-1-6-250615`(或新 multimodal `doubao-seed-1-6-vision-*`,Codex 调研)

**Request schema**(标准 OpenAI Chat,但 content 含 video_url):
```json
{
  "model": "doubao-seed-1-6-250615",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "<viral_analysis 8 维专用 prompt>"},
        {
          "type": "video_url",
          "video_url": {
            "url": "https://...direct-mp4...",
            "fps": 1,
            "max_frames": 100,
            "max_pixels": 518400
          }
        }
      ]
    }
  ],
  "stream": false
}
```

**用法**:在 storyline 解析完成后,**用一次** ARK Chat API call 把视频 URL + storyline summary 一起喂给 doubao 视觉模型,问 8 维结构化 JSON:hook / pacing / climax / emotional_arc / replicable_formula 等。Codex 设计 prompt 在 `prompts/mediakit_viral_analysis_overlay.md`。

**Token 预算**:200k(MediaKit 内置抽帧 cost 控制),默认 fps=1 即可;Phase 1 内测 60s 视频成本 ~¥0.10。

---

## 3. Sub-phase 拆解(5 阶段,~3d 总)

### Sub-phase 0 — 预备(0.25d)

- **复用 toprador URL resolver**:与 founder 确认 toprador 的 URL resolver 接续方式(独立 endpoint / 嵌入 lib / 微服务)
- 新建 `backend/src/agent/cascade/mediakit/` 目录(替代原 doubao_lite/)
- `config.py` 加 `VOLC_MEDIAKIT_AK`(.env)
- `.env.example` 加 5 行 MediaKit 配置注释

### Sub-phase A — analyze-video-storyline client + task polling(1d)

- 新文件 `mediakit/storyline_client.py`:
  ```python
  async def submit_storyline_task(video_urls, *, enable_snapshot=True) -> str  # task_id
  async def poll_task(task_id, *, timeout_s=600, poll_interval_s=10) -> dict
  async def analyze_storyline(video_url, *, user_id, run_id) -> dict  # 高层 wrapper
  ```
- 异步 httpx + retry/breaker(沿用 P3-7 范式;新建 `_STORYLINE_BREAKER`)
- P4-3 emit:`cascade_retry / cascade_circuit_open / cascade_cache_hit / cascade_cache_miss`
- P4-6 cache:`save_toprador_cache` 复用,key prefix `f"mediakit_storyline::{url_hash}"`
- 7 unit tests:submit 200 + parse task_id / poll completed / poll failed → S8 / poll timeout → S7 / mid-poll retry / hash isolation / 24h cache hit

### Sub-phase B — adapter:storyline → CascadeAnalysisContract(0.75d)

- 新文件 `mediakit/storyline_adapter.py:storyline_to_contract(storyline_result, source_url, user_id) -> dict`
- 映射逻辑实现 §2.1 表格(map_field by map_field)
- **加 schema v1.1 兼容字段**:`scenes[i].importance_score` + `scenes[i].snapshot_url`(若 contract.py 不含,加 optional field + W14 warning)
- 6 unit tests:happy path mapping / missing snapshot field / niche tag fallback / multiple source_video_info / empty storyline_clips → S5 / clip ordering by start_time

### Sub-phase C — ARK Chat API for viral_analysis 8-dim overlay(0.5d)

- 新文件 `mediakit/viral_overlay.py:overlay_viral_dims(contract_dict, video_url) -> dict`
- 调用 `https://amk-ark.cn-beijing.volces.com/api/v1/chat/completions`
- prompt 放 `prompts/mediakit_viral_analysis_overlay.md`(基于 hook_taxonomy H1-H9 + 现有 niche)
- 失败 fallback:返回 storyline-only contract,viral_analysis 8 维字段以默认值或 storyline_highlights summary 兜底
- 4 unit tests:happy path / Chat API timeout → fallback to storyline-only / malformed JSON → S5 + warning / 200k token budget 截断

### Sub-phase D — analysis_service.py 接入(0.5d)

- 新分支:
  ```python
  elif upstream == "mediakit":
      direct_url = await resolve_to_direct_media(source_url)  # toprador URL resolver
      storyline = await analyze_storyline(direct_url, user_id=user_id, run_id=run_id)
      contract_dict = storyline_to_contract(storyline, source_url, user_id)
      contract_dict = await overlay_viral_dims(contract_dict, direct_url)
      return contract_dict
  ```
- retry / breaker / cache observability 沿用现有 `_call_toprador` 范式
- 8 unit tests:happy path / resolve fail → S8 / storyline timeout → S7 / overlay fail → degraded contract / 重入幂等性 / 不同 user 同 URL 隔离 / Adapter S5 / contract validate fail

### Sub-phase E — 默认切换 + cleanup(0.5d)

- `.env.example` `CASCADE_UPSTREAM=mediakit`
- `config.py` 默认值同步
- `docs/TOPRADOR_SCHEMA.md` 顶部加 v1.1 schema 更新注 + MediaKit 字段映射 reference
- `handoff/codex_backend_P4-9.md` SUPERSEDED 标记(原已有,确认仍生效)
- `scripts/check_progress.sh` 加 `p5_3 probe`:扫 `analysis_service.py` 含 `analyze_storyline` 即标 done
- 第一份真实 staging 报告 commit `founder_log/p5-3_mediakit_staging_<UTC>.md`(5 真实 niche URL 端到端跑通)

---

## 4. 边界(不在此 brief)

- ❌ 重建 toprador URL resolver(founder 决定保留;只是 P5-3 调用方)
- ❌ 视频生成 / Seedance(独立)
- ❌ TTS / 配乐 / 剪辑合成(MVP B5-B7,后期)
- ❌ MediaKit 其他工具(画质增强 / 字幕擦除 / 视频抠图等;后期按需引)
- ❌ ARK Chat API 高级用法(streaming / tool calling)— Phase 1 简单 non-stream 即可
- ❌ 5GB 大视频特殊处理(Phase 1 短视频均 < 100MB)

---

## 5. Upstream dep / Blocker

- ✅ `ARK_API_KEY`(已配,P4-1 已使用)
- ✅ `VOLC_MEDIAKIT_AK`(founder W3D3 已申请;临时 AKLT* 已用于本 brief 写作的 probe;长期 key 待发放,或临时 key 长期有效待确认)
- ⏳ **toprador URL resolver 接续方式**(founder W3D3 决定保留模块,但接续协议待:独立 endpoint / 嵌入 lib / 微服务三选一)— 这是 sub-phase 0 阻塞
- ✅ MediaKit 3 个 API 文档已就位(本 brief §2 嵌入完整契约)

**Sub-phase 0 起跑前 founder 必须给**:
1. 长期可用 `VOLC_MEDIAKIT_AK`
2. toprador URL resolver 接续协议(`POST /api/resolve-url` endpoint? 还是 python module import?)

其他 sub-phase A/B/C/D/E 可在 0 完成后顺序执行,不再需要 founder 介入。

---

## 6. 验收指标(W6D7 复盘看)

| 指标 | 目标 | 失败 → 动作 |
|---|---|---|
| 60s 视频端到端延迟 p95 | ≤ 8 min(MediaKit RTF 3-5)| W5 加 storyline 任务 prewarm / 并发提交 |
| 单视频成本 | **≤ ¥1.50**(2026-05-23 修正,基于 MediaKit 官方计费)| 关 enable_snapshot / 关 ARK overlay(degraded mode);见 §6.1 cost breakdown |
| 3 niche × 5 URL adapter pass rate(不抛 S5)| ≥ 80% | 改 adapter / 加 warning 兜底 |
| Founder qualitative("storyline 准不准") | ≥ 7/10 | 调 ARK overlay prompt / 启用 segment-scenes 精细切分 |
| viral_analysis hook_pattern_id 与 fixture 一致率 | ≥ 70% | 重写 ARK overlay prompt + 在 in-context exemplar 加更多 hook 例 |

### 6.1 Cost breakdown(per 60s 视频 = 1 分钟 input duration)

| 调用 | 单价 | 60s 成本 | 必要性 |
|---|---|---|---|
| **MediaKit 剧情故事线分析** | ¥1.00/min input | ¥1.00 | 必要(主分析)|
| ARK 视频理解 Chat overlay | Doubao seed-1.6 token(~3000 tokens × 0.002元/千)| ~¥0.06 | 必要(viral_analysis 8 维补维)|
| MediaKit 场景切分(若启用)| ¥0.02/min input | ¥0.02 | 可选(P5-3 默认不启用)|
| MediaKit ASR(若另调,Phase 2)| ¥0.03/min input | ¥0.03 | 不启用(storyline 已含 dialogue)|
| **小计** | — | **≈ ¥1.06-1.10** | — |
| **PREDICT_ANALYSIS_CNY** | — | **¥1.20**(¥0.14 buffer)| cost_guard `cost_guard.py` |

**Phase 1 内测整 cohort 估计**:3 人 × 5 次 first-run × 1.10 = ¥16.50 — 完全可控。

**长视频惩罚**:若 creator 输入 5min 视频(罕见,Phase 1 大都 ≤ 60s),storyline 成本 = ¥5.00,**超 PREDICT_ANALYSIS_CNY ¥1.20**;cost_guard 应拒绝。adapter / cascade UI 需把 "建议视频长度 ≤ 60s" 告知 creator。

### 6.2 PREDICT_ANALYSIS_CNY 历史

- W2 原始值:¥0.5(基于 toprador 估算,无真实数据)
- 2026-05-23 W3D3 修正:¥1.20(MediaKit 官方计费数据后)
- W5+ P4-8 cost 校准报告(`scripts/cost_calibration.py`)运行后,根据真实 p95 再调
- `CASCADE_RUN_CAP_CNY` 默认 ¥3.0 不变;若 first-run 真实账单出现 ¥2-3 单 run cost,founder 通过 env 调到 ¥5.0

---

## 7. 与 Phase 1 内测的关系

P5-3 ship 后 Phase 1 内测 first-run together 可用真实 video URL,不再走 fixture。即:

- W4D5-D7(per `concierge_onboarding_script §3`)concierge creator 体验时,若 P5-3 已 ship,creator 粘 Douyin URL → toprador resolver → MediaKit storyline → 改写 → 锚点 → 发布包,**全程真实数据**
- 若 P5-3 仍在跑,Phase 1 first-run 退回 fixture mode(`CASCADE_UPSTREAM=fixture`),不阻塞 concierge 体验,只是 viral_analysis 是 mock 数据(creator 仍能体验改写 + 锚点 + 发布包流程)

**P5-3 ship 时机最理想 = W4D5 之前(Phase 1 first-run 落地前)**;若推迟到 W4D7+,fixture mode 兜底,concierge 体验仍可继续。
