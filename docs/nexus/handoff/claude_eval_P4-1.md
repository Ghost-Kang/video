# Claude handoff — P4-1 LLM judge baseline (Doubao mode)

**Owner**: Claude session (LLM + eval line)
**Source of truth**: `claude_eval_P2-6.md` §3 (LLM mode plan, originally Gemini-only); `codex_backend_P3-R2.md`(Doubao provider switch,shipped in `eff6cd4`)
**Status**: DRAFT · awaiting founder `ARK_API_KEY` + `DOUBAO_MODEL` 写入 `.env`
**Time budget**: 0.5 day(运行 + 调通 + 写 baseline JSON)
**Allocation**: `PM_W4_allocation.md §3.1`

---

## 0. 背景

W3 期间 Codex 已把 LLM provider 抽象到 `agent/llm_factory.py`(P3-R2),`LLM_PROVIDER=doubao` 默认走豆包,`gemini` 仍可作 fallback。P3-1 原本被 `GOOGLE_API_KEY` 卡住,**现在改用 Doubao 后 unblock**。

P2-6 已有 `mode=fixture` baseline(`p2-6_baseline_20260521T163207Z.json`)。本票要产出 `mode=llm` baseline,并固化为 W4 起的 regression 锚点。

---

## 1. Done-signal

- `docs/nexus/founder_log/p2-6_baseline_<UTC>.json` 存在,且 JSON `metadata.mode == "llm"` + `judge_realism_avg > 0`(非 skipped)
- `docs/nexus/founder_log/p2-6_report_<UTC>.md` 与 baseline 配套(沿用 P2-6 现有报告器)
- 同期 `mode=fixture` baseline 仍保留作为对照(**不要覆盖** `20260521T163207Z`)
- `docs/nexus/founder_log/p2-6_llm_vs_fixture_diff_<UTC>.md` 写一份对比 — 含:`mechanical_pass_rate`、`judge_realism_avg`、`founder_pass_rate`(后者 LLM 下仍可能为 0,声明即可)三个指标 delta;每个 niche 各列一行

---

## 2. 执行步骤

1. 确认 `.env` 里 `LLM_PROVIDER=doubao`、`ARK_API_KEY=*`、`DOUBAO_MODEL=*` 都齐(若任一缺 → 阻塞并写到 `founder_log/PM_blocker_P4-1_<date>.md`)
2. 跑(在 `backend/` 下):
   ```
   uv run python ../scripts/p2-6_eval.py --niche all --mode llm
   ```
3. baseline JSON + report 落到 `docs/nexus/founder_log/`
4. 写 diff 报告

---

## 3. 边界(不在此票)

- **不做** prompt iteration(后续 P5 才动 prompt)
- **不做** Doubao SDK 升级 / model name 调整(Codex P3-R2 已固化)
- **不做** UI 展示(W5/W6 才会有 baseline diff 面板)
- 不预先评估 founder pass rate;LLM 下若仍为 0 是预期,因为 founder 还没在 LLM 输出上签字

---

## 4. Upstream dep

- ✅ Codex P3-R2 LLM provider switch(`eff6cd4`)
- ⏳ Founder 写 `ARK_API_KEY` + `DOUBAO_MODEL` 到 `.env`(W4D1)

---

## 5. 失败兜底

如果 Doubao 调用率太高 / cost 不可接受 → 在 baseline 跑完后立刻打开 `LLM_PROVIDER=gemini` 走 fallback(需要 founder 单独配 `GOOGLE_API_KEY`)。**P4-1 不负责 cost 优化**,只产 baseline。

---

## 6. Output 清单(W4D2 末)

- `p2-6_baseline_<UTC>.json`(mode=llm)
- `p2-6_report_<UTC>.md`
- `p2-6_llm_vs_fixture_diff_<UTC>.md`
- commit:`feat(P4-1): LLM-mode (Doubao) p2-6 baseline + fixture diff`
