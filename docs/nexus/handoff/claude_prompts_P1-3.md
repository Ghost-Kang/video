# Claude handoff — P1-3 赛道改写 prompts

**Owner**: Claude session (this one OR a future one with full repo access)
**Source of truth**: `01_phase1_requirements.md` §4 · `02_brand_guardrails.md` term table · `cascade.contract.CascadeAnalysisContract`
**Time budget**: 5 days (was 3 — bumped per Trend Researcher §3 niche-specific tuning)

---

## 0. What you produce

Three niche-specific rewrite prompt files + their smoke-test driver. NO chain wiring (that's Codex's P1-3 chain ticket). NO frontend.

The prompt takes a full `CascadeAnalysisContract` (Pydantic) + a niche tag (`baomam_fushi` | `yuer_richang` | `jiating_chufang`) + the creator's account profile (Phase 1 = just a niche string, no real profile) and produces:

```json
{
  "rewritten_script": "string ≤ 600 chars",
  "rewritten_shots": [
    {"scene_index": 1, "scene": "...", "dialogue": "...", "visual_content": "..."}
  ],
  "rewrite_notes": "string ≤ 200 chars - what was preserved, what was changed and why",
  "confidence": 0.0-1.0
}
```

5 shots max. Scene labels in plain Chinese.

---

## 1. Files

| Path | Purpose |
|---|---|
| `backend/src/agent/prompts/rewrite_baomam_fushi.md` | 宝妈辅食 niche prompt |
| `backend/src/agent/prompts/rewrite_yuer_richang.md` | 育儿日常 niche prompt |
| `backend/src/agent/prompts/rewrite_jiating_chufang.md` | 家庭厨房 niche prompt |
| `backend/src/agent/cascade/rewrite.py` | `rewrite_for_niche(contract, niche) -> RewriteResult` Pydantic type + invocation |
| `backend/tests/test_rewrite.py` | Smoke tests using synthetic fixtures |
| `backend/src/agent/cascade/fixtures/rewrite_smoke/<niche>/ref_<N>.json` | 5 reference URLs per niche (founder curates the URLs; Claude generates synthetic analysis JSONs for now) |

---

## 2. Prompt structure (all 3 niches share)

```markdown
你正在帮一位中文短视频创作者把别人的爆款改写成 ta 自己的版本。
赛道：{niche_label}
目标：保留"为什么火"的内核，但换成 ta 的人设、场景、台词。

输入：
- 原视频的 viral_analysis（hook / pacing / climax / replicable_formula 等）
- 原视频的 scenes[]（{N} 个镜头）

输出（严格 JSON，符合 schema）：
{
  "rewritten_script": "...",         // ≤ 600 字
  "rewritten_shots": [...],          // ≤ 5 个镜头
  "rewrite_notes": "...",            // ≤ 200 字 — 你保留了什么、改了什么、为什么
  "confidence": 0.0-1.0
}

赛道特定要求（{niche_label}）：
{NICHE_SPECIFIC_GUIDANCE_HERE}

硬约束：
- 改写后的角色必须是创作者本人 / 创作者孩子（不是原视频里的角色）。
- 场景必须是普通家庭厨房 / 客厅 / 餐桌（不是商业摄影棚）。
- 台词风格必须自然口语，不能像广告。
- 任何"AI / 智能 / 工具 / 平台 / 算法"字样禁止出现在 dialogue 里。
- replicable_formula 的本质必须保留，但语言要改成你的版本。

input contract:
{CONTRACT_JSON}
```

Niche-specific guidance differs in:
- 宝妈辅食: 痛点是"宝宝拒食 / 怎么样添辅食"；情绪是焦虑→惊喜；视觉是温暖 / 食材特写 / 宝宝反应
- 育儿日常: 痛点是"哄睡 / 育儿挫败 / 跟孩子的小事"；情绪是疲惫→治愈；视觉是夜灯 / 室内 / 自拍
- 家庭厨房: 痛点是"做出餐厅感 / 预算"；情绪是好奇→满足；视觉是台面 / 食材 / 拉丝结尾

---

## 3. Smoke test design

5 reference contracts per niche, total 15 contracts. For each:
1. Load the contract.
2. Run `rewrite_for_niche(contract, niche)`.
3. Output goes into `tests/output/<niche>/ref_<N>_rewrite.json` for human review.

Acceptance: 4 of 5 outputs per niche pass these mechanical checks:
- `rewritten_script` length in [80, 600]
- `rewritten_shots` has 3-5 items
- No forbidden terms (per `01_phase1_requirements.md` + `02_brand_guardrails.md`)
- `confidence` ≥ 0.5
- `rewrite_notes` mentions both "保留" and "改" (basic linguistic check)

Human review (founder, < 30min per niche) decides if remaining qualitative bar is met. If 4/5 pass mechanical AND founder says "I'd post this version", the prompt is done.

---

## 4. Iteration discipline

Per Sprint Plan: this is the moat ticket. Don't under-invest in iteration.
- v1 of each prompt → mechanical check
- v2 with niche-specific examples baked in (few-shot)
- v3 with founder-tweaked phrasing

Stop iterating when mechanical 4/5 + founder qualitative pass. Do NOT keep iterating after that (Naval — premature optimization).

---

## 5. Done-signal

- `find backend/src/agent/prompts -name "rewrite_*.md" | wc -l` ≥ 3
- `find backend/src/agent/cascade/fixtures/rewrite_smoke -name "*.json" | wc -l` ≥ 15
- `uv run pytest tests/test_rewrite.py` passes
- `docs/nexus/founder_log/p1-3_qualitative_signoff_<date>.md` exists with founder ticking each niche

---

## 6. NOT in this ticket

- HTTP endpoint wiring (Codex P1-3 chain brief)
- Cost cap (P1-9)
- Frontend rendering of rewrite output (P1-4)
- Anchor reuse in the rewrite prompt (P1-6 augments this AFTER it lands)
