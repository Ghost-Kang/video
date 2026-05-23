# Claude handoff — P4-1 LLM judge baseline (Doubao mode)

**Owner**: Claude session (LLM + eval line)
**Source of truth**: `claude_eval_P2-6.md` §3 (LLM mode plan, originally Gemini-only);`codex_backend_P3-R2.md`(Doubao provider switch,shipped in `eff6cd4`)
**Status**: **READY** · 结构性 audit 已完成 2026-05-22 (see §7);仅等 founder 在 `.env` 写 `ARK_API_KEY` + `DOUBAO_MODEL`
**Time budget**: 0.5 day(运行 + 调通 + 写 baseline JSON;audit 工作 0 day,已完成)
**Allocation**: `PM_W4_allocation.md §3.1`

---

## 0. 背景

W3 期间 Codex 已把 LLM provider 抽象到 `agent/llm_factory.py`(P3-R2),`LLM_PROVIDER=doubao` 默认走豆包,`gemini` 仍可作 fallback。P3-1 原本被 `GOOGLE_API_KEY` 卡住,**现在改用 Doubao 后 unblock**。

P2-6 已有 `mode=fixture` baseline(`p2-6_baseline_20260521T163207Z.json`)。本票要产出 `mode=llm` baseline,并固化为 W4 起的 regression 锚点。

---

## 1. Done-signal

- `docs/nexus/founder_log/p2-6_baseline_<UTC>.json` 存在,且 JSON `mode == "llm"` + `overall_judge_realism_avg > 0`(非全 skipped)
- `docs/nexus/founder_log/p2-6_report_<UTC>.md` 与 baseline 配套(沿用 P2-6 现有报告器,**已包含 §"Delta from baseline" 章节** — 自动与 fixture baseline 对比)
- 同期 `mode=fixture` baseline(`20260521T163207Z`)保留作为对照(**不要覆盖**;每次 run 产生 UTC 时间戳新文件,不会冲突)

> **brief 原先要求的独立 `p2-6_llm_vs_fixture_diff_<UTC>.md` 已不必要** — 现有 `render_markdown()` 已经在 report.md 顶部输出 `Delta from baseline` 段(`backend/src/agent/cascade/eval/report.py:141-146`)。harness 输出即满足 diff 需求。

---

## 2. 执行步骤

1. 确认 `.env` 里(在 `backend/.env`,被 `agent/config.py` 加载):
   - `LLM_PROVIDER=doubao`
   - `ARK_API_KEY=<…>`(火山引擎方舟控制台拿)
   - `DOUBAO_MODEL=<…>`(如 `doubao-pro-32k-241115` 或最新)
   - `ARK_BASE_URL` 已有默认值在 `config.py`,通常不用改

2. 验证 key 可用(0 cost 探测):
   ```
   cd backend && uv run python -c "from agent.llm_factory import get_chat_model; m = get_chat_model(); print(m.invoke('ping').content[:50])"
   ```

3. 跑全 niche LLM mode baseline:
   ```
   cd backend && uv run python ../scripts/p2-6_eval.py --niche all --mode llm
   ```

4. 验证产物:
   - `docs/nexus/founder_log/p2-6_baseline_<新 UTC>.json` 存在
   - `docs/nexus/founder_log/p2-6_report_<新 UTC>.md` 存在,顶部含 "Delta from baseline" 段
   - `jq .mode <baseline.json>` 输出 `"llm"`
   - `jq .overall_judge_realism_avg <baseline.json>` 非 0

5. commit:`feat(P4-1): LLM-mode (Doubao) p2-6 baseline + fixture delta`

---

## 3. 边界(不在此票)

- **不做** prompt iteration(后续 P5 才动 prompt)
- **不做** Doubao SDK 升级 / model name 调整(Codex P3-R2 已固化)
- **不做** UI 展示(W5/W6 才会有 baseline diff 面板)
- 不预先评估 founder pass rate;LLM 下若仍为 0 是预期,因为 founder 还没在 LLM 输出上签字
- **不做** `load_latest_baseline` 的 mode-filter 改造(见 §7 watch-out)— 首次 LLM run 与 fixture baseline 对比是有意义的 "mode-shift delta",后续 LLM-to-LLM 比较 W5 再说

---

## 4. Upstream dep

- ✅ Codex P3-R2 LLM provider switch(`eff6cd4`)
- ✅ `agent/cascade/eval/judge.py` 已通过 `agent.llm_factory.get_chat_model()` 路由 — provider 抽象到位
- ⏳ Founder 写 `ARK_API_KEY` + `DOUBAO_MODEL` 到 `backend/.env`(W4D1)

---

## 5. 失败兜底

- 如果 Doubao 调用率 / cost 不可接受 → run 完 baseline 后立刻切 `LLM_PROVIDER=gemini` 做 fallback(需要 founder 单独配 `GOOGLE_API_KEY`)
- 如果 Doubao 返回的 JSON parser 失败 → `_extract_first_json()` 已经做了正则兜底,返回 skipped sentinel,不阻塞整体 baseline 产出
- 如果某条 niche 全部 case judge 都 skipped → report.md 仍生成,只是 niche 那段 realism_avg=0;不视为失败

**P4-1 不负责 cost 优化**,只产 baseline。

---

## 6. Output 清单(W4D2 末)

- `p2-6_baseline_<UTC>.json`(mode=llm)
- `p2-6_report_<UTC>.md`(顶部 Delta from baseline 段自动写入)
- 1 个 commit:`feat(P4-1): LLM-mode (Doubao) p2-6 baseline + fixture delta`
- 无 code 改动(harness 已就绪)

---

## 7. 结构性 audit 记录(2026-05-22 W3D2 完成 by Claude pre-execution)

**Audit 触发**:P4-1 标 "blocked on env",但工程线 idle;Claude 主动检查 harness 是否真的"上 key 就跑";结果是 **完全就绪**。

**Pre-flight checks**:

| 检查项 | 状态 | 验证 |
|---|---|---|
| `agent.llm_factory.get_chat_model()` 处理 `LLM_PROVIDER=doubao` 分支 | ✅ | `backend/src/agent/llm_factory.py:11-19` |
| `eval/judge.py:judge_one()` 通过 `get_chat_model()` 抽象,不绑死 provider | ✅ | `backend/src/agent/cascade/eval/judge.py:64-69` |
| `judge.py` 在 provider 未配置时返回 `{skipped: True}` 而不抛 | ✅ | 同上 line 68-69 |
| `p2-6_eval.py --mode llm` 传到 `run_eval(mode=...)` | ✅ | `scripts/p2-6_eval.py:39-44` |
| `save_baseline()` 用 timestamp,不覆盖现有 fixture baseline | ✅ | `eval/baselines.py:22-26` — `p2-6_baseline_<ts>.json` |
| `render_markdown()` 自动写入 "Delta from baseline" 段 | ✅ | `eval/report.py:141-146` |
| 离线 smoke(`--mode fixture --skip-judge --niche baomam_fushi`)端到端跑通 | ✅ | 2026-05-22 16:16 UTC 验证;artifact 已清理避免污染 baseline pool |

**Watch-out**(不在 P4-1 范围内,W5 再处理):
- `load_latest_baseline()` 用 timestamp glob,**不区分 mode**。首次跑 `--mode llm` 时会拿 `20260521T163207Z` (mode=fixture) 作为 baseline → delta 是 "fixture → LLM" 的跨模式 delta(这次预期且 OK,本来就是 P4-1 想要的 "LLM vs fixture" 对比)。但 W5 起若想跑 `--mode llm` 二次 baseline,会拿 P4-1 LLM baseline 作 base(正确)— 此机制在 W5 起即正确工作,P4-1 不需要预先改。
- `p2-6_eval.py:42` 有个无效逻辑:`baseline_dir=None if args.baseline == "last" else None`(两边都是 None),`--baseline` 参数实际无效。这是 pre-existing bug,与 P4-1 无关,P5 再扫。

**结论**:harness 已就绪,P4-1 真正阻塞只剩 founder 在 `backend/.env` 写 key。W4D1 founder 一旦写入,Claude 即可在 5 分钟内 produce baseline + report,不需要任何代码改动。

---

## 8. Founder action ETA

请在 `backend/.env` 里加 3 行:
```
LLM_PROVIDER=doubao
ARK_API_KEY=<火山方舟 key>
DOUBAO_MODEL=<选定的 doubao 模型 id>
```

加完通知 Claude(在对话里直接说 "P4-1 unblock"),Claude 起跑。
