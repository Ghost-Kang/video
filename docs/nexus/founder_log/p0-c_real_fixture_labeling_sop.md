# P0-C 手动标注 ≥ 20 条真实 fixture SOP

**Date opened**: 2026-05-21
**Owner**: Founder(只能 founder 做,需要赛道 + 爆款判断)
**Time budget**: ≥ 3 个半天(W3D1 上午 / W3D1 下午 / W3D2 上午 minimum)
**Spec source**: `docs/nexus/03_routing.md §1` P0-1 · `docs/TOPRADOR_SCHEMA.md` · 现有 synthetic_v1 + rewrite_smoke fixture

---

## 0. 目标

把 `backend/src/agent/cascade/fixtures/real_v1/` 目录从空 → ≥ 20 个真实视频的 hand-labelled JSON。每个文件是一份 valid `CascadeAnalysisContract`(per `backend/src/agent/cascade/contract.py`)。

完成判定:`find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" | wc -l` ≥ 20

---

## 1. 为什么必须真手动

- 我们的 synthetic_v1 + rewrite_smoke 都是合成内容,**没有真实评论数据 / 真实点赞分布 / 真实拍摄环境**
- contract 测试现在跑的是合成数据 → 真实数据落地时 schema 是否仍 valid,**只有用真实数据测才知道**
- 这是 Phase 0 闸门 — 没有真 fixture 就不知道 cascade 在真实输入下是否 work

---

## 2. 数据源(已经在 `real_urls_for_p2-4.md` 里有 15 条 URL)

Founder 在 `docs/nexus/founder_log/real_urls_for_p2-4.md` 已提供 15 条爆款 URL(5 个 niche × 3 = 15 ... wait, 实际 15 = 3 niche × 5 URL)。
**P0-C 需要 ≥ 20 条**,所以再加 5 条最低:

- 2 条宝妈辅食(可以从 real_urls_for_p2-4.md 之外的爆款找,例如年糕妈妈 / 育学园早期视频)
- 2 条育儿日常(同上)
- 1 条家庭厨房(王刚 / 老饭骨 早期视频)

(或者每 niche 7-8 条达到 21+ 进一步增加 robustness)

---

## 3. 单条 fixture 的工作量(≈ 15-30 min / 条)

每条视频要产出一个 JSON,包含:

| 字段 | 怎么填 |
|---|---|
| `schema_version` | 固定 `"1.0"` |
| `analysis_id` | `ana_real_<niche>_<3 位序号>`,例如 `ana_real_baomam_001` |
| `source_url` | 真实 URL(从 URL 池粘) |
| `platform` | `douyin` / `xiaohongshu` / `other`(host sniff) |
| `created_at` | 当前 UTC 时间 ISO |
| `model` | 标 `"manual_label_v1"`(不是真分析,是 founder 手标) |
| `cost_cny` | `0.0` |
| `duration_s` | 看视频读出的秒数 |
| `confidence` | founder 对这条标注的信心(0.7-0.95 典型) |
| `viral_analysis.hook` | ≤ 80 字 — 视频第 1-3 秒的钩子描述 |
| `viral_analysis.pacing` | ≤ 80 字 — 镜头节奏(几秒切一次 / 越接近结尾越快) |
| `viral_analysis.climax` | ≤ 80 字 — 高潮在哪个镜头 |
| `viral_analysis.visual_style` | ≤ 80 字 — 视觉风格(暖色 / 自然光 / 俯拍...) |
| `viral_analysis.emotional_arc` | ≤ 80 字 — 情绪弧线 |
| `viral_analysis.target_audience` | ≤ 80 字 |
| `viral_analysis.engagement_levers` | ≤ 80 字 — 抛问题 / 抛对比 / 抛悬念 |
| `viral_analysis.replicable_formula` | ≤ 120 字 — **必填、非空** — 可复制的公式 |
| `scenes[]` | **3-12 个镜头**,逐个填 timestamp + 场景描述 + dialogue + visual_content + shot_type + camera_movement |
| `warnings[]` | 通常 `[]`,如果观察到反常态可以加 `{code, field, message, severity}` |

参考已有 fixture:`backend/src/agent/cascade/fixtures/synthetic_v1/baomam_fushi/001.json`(详细到位的标注模板)。

---

## 4. 落地建议工作流(每条 ~25 min)

1. **看视频两遍**(8-10 min) — 第一遍整体,第二遍记 scene timestamps
2. **复制 synthetic_v1 同 niche 的 001.json** → 改名 `real_v1/<niche>/001.json`
3. **填 viral_analysis 8 个维度**(7-10 min) — 一边看视频一边填
4. **逐 scene 填**(8-12 min,取决于镜头数) — 时间戳 + 镜头描述 + dialogue + visual
5. **跑校验**:`cd backend && uv run python -c "import json; from agent.cascade.contract import CascadeAnalysisContract; CascadeAnalysisContract.model_validate(json.load(open('src/agent/cascade/fixtures/real_v1/<niche>/<n>.json')))"`
6. **commit 单条**(或攒 5 条 commit 一次)

---

## 5. 完成 ≥ 20 后

```bash
# 一次性把 schema 验通所有 real_v1 fixture
cd backend && uv run pytest tests/test_cascade_contract.py -k real_v1 -v
```

如果不存在 `test_cascade_contract.py` 里的 `real_v1` 集合 tests,founder commit ≥ 20 后,**PM 立刻派 Codex** 加 `test_cascade_contract.py::test_validate_all_real_v1_fixtures` 让 contract 测试遍历整个 `real_v1/` 目录(这是 P0-T 的本质)。

---

## 6. 完成判定

- `find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" | wc -l` ≥ 20
- `bash scripts/check_progress.sh` → `Phase0 fixtures=20+`(probe 已在脚本里)
- P0-T 自动 unblock(contract test 真实 corpus 上跑通)

---

## 7. PM 注

- 这是 founder 唯一不能委派的 P0 工单(需要"看视频读出 hook / formula"的判断)
- ≥ 20 条门槛是 Reality Checker §3 "real-corpus completeness gate" 给出的最低值;Codex 已在 `03_evidence_audit.md` 中 honestly skip(有 fixture 才解禁)
- 起步建议:**先做 1 条完整跑通**(确认 schema valid 流程通畅),再批量做剩下 19+

## 8. PM 已 ship 的 stub 骨架(2026-05-22 W3D1 EOD)

PM 在 `real_v1/` 落了 15 个 stub,覆盖 `real_urls_for_p2-4.md` 里的全部 15 条 URL:

```
backend/src/agent/cascade/fixtures/real_v1/
├── baomam_fushi/{001..005}.json
├── yuer_richang/{001..005}.json
└── jiating_chufang/{001..005}.json
```

**Stub 状态**:每个 JSON 顶部带 `"_stub_status": "A_only_pending_founder_label_2026-05-22"` 标记。

**已预填的 A 档 8 字段**:
- `schema_version: "1.0"`
- `analysis_id: "ana_real_<niche>_<n>"` (唯一)
- `source_url` (从 URL 池)
- `platform: "douyin"` (15 条都是抖音)
- `created_at` (用 source 视频发布日 ISO)
- `model: "doubao-seed-2-0-pro"` (founder 如改纯手标可改 `"manual_label_v1"`)
- `cost_cny: 0.0` (占位,真分析后回填)
- `duration_s: 0` (占位,看视频后填实际秒数)

**Founder 需要填的 B+ 档**(每个 stub 头部 `_pending_for_founder` 列出):
1. `duration_s` 真值
2. `confidence` 0-1
3. `viral_analysis.*` 8 个字段 — **`replicable_formula` 必填**,空会触发 S3_NO_FORMULA HardFailure
4. `scenes` ≥3 ≤12 个 — 空 array 会触发 S4_SCENES_LEN_OUT_OF_RANGE

**Source 元数据已埋进 stub 顶部**(无需回查 `real_urls_for_p2-4.md`):
- `_source_creator` / `_source_posted_at` / `_source_hook_ids` / `_source_rating` / `_source_notes`

**单条填实流程**:
1. 打开视频(URL 在 `source_url` 里)
2. 看完后:填 `duration_s` 实际秒数 + 8 项 viral_analysis 人话描述 + 至少 3 scenes
3. 把 `_stub_status` 改为 `"labeled_2026-05-XX"`(或直接删掉);`_pending_for_founder` 字段也删
4. `cd backend && uv run pytest tests/test_cascade_contract.py -q` 跑一遍单条是否 valid
5. commit 单条 或 攒 5 条

**Gate G2 测试逻辑**(PM 同步调整):
- 之前:dir 存在就跑 → 15 stubs 会让 `assert len >= 20` hard-fail
- 现在:dir 存在 **AND** ≥20 条 **AND** 没有 `_stub_status` 还是 `A_only_pending_founder_label_*` 的才跑
- 任何 stub 仍带 status → test skip(safe,不破 CI)
- 全 20 条 labeled 后 status 自动清除 → test 跑 + Gate G2 自动校验 完整率 ≥ 90%

**剩余的 ≥5 条 加到 ≥20**:按 §2 来源(年糕妈妈 / 育学园 / 王刚老饭骨 早期视频),founder 自己捡。捡到后可直接复制 `001.json` 改 URL + niche + filename。
