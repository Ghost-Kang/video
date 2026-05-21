# Claude handoff — P2-6 LLM 改写 eval harness

**Owner**: Claude session
**Source of truth**: `PM_W2_allocation.md §3.3` · `claude_llm_P2-4.md` · `01_reviewer_synthesis.md` §5 (H8 measurement)
**Status**: 阻塞,等 P2-4 done
**Time budget**: 2 天(W2D6-W2D7)

---

## 0. What you build

P2-4 跑出 LLM 模式真实输出后,P2-6 给这套产出搭一套**自动化 eval harness**,让 prompt 迭代 / model 切换 / provider 切换有可重复的回归基线。不是产品功能,是工程基础设施。

核心:任何时候改了 prompt / 换了 LLM,跑一条命令就能拿到"这次比上次好还是坏"的结构化结论。

---

## 1. Files

| Path | Purpose |
|---|---|
| `backend/src/agent/cascade/eval/__init__.py` | eval 包 |
| `backend/src/agent/cascade/eval/runner.py` | 主入口:`run_eval(niches, mode, n_per_niche) -> EvalReport` |
| `backend/src/agent/cascade/eval/checks.py` | 机械检查函数集(复用 + 扩展 `test_rewrite.py` 里的 5 条) |
| `backend/src/agent/cascade/eval/report.py` | EvalReport Pydantic 类型 + markdown 渲染器 |
| `backend/src/agent/cascade/eval/baselines.py` | 历史 baseline 加载/比对 |
| `scripts/p2-6_eval.py` | CLI wrapper:`python scripts/p2-6_eval.py --niche all --mode llm --baseline last` |
| `backend/tests/test_eval_harness.py` | eval 系统自检 |
| `docs/nexus/founder_log/p2-6_baseline_<date>.json` | 落地的 baseline 快照 |

---

## 2. Eval 维度

### 2.1 机械检查(自动,无需人工)

复用 `test_rewrite.py` 里的 5 条,加 3 条:
1. script_markdown 长度 ∈ [80, 600]
2. shots 数 ∈ [3, 5]
3. 无禁用词(`FORBIDDEN_TERMS`)
4. confidence ≥ 0.5
5. script_markdown 含"保留" + "改" rationale marker
6. **新**: shot 之间 dialogue 不重复(diversity check)
7. **新**: shot 平均 dialogue 长度 ≥ 10 字(防止空壳输出)
8. **新**: 至少 1 个 shot 的 visual 包含家庭场景关键词(暖色 / 厨房 / 客厅 / 卧室 / 餐桌)

### 2.2 LLM-judge 检查(LLM 评 LLM,半自动)

调用一个独立 judge LLM(可以是同一 model 但不同 prompt),针对每条改写问:
1. "这条改写是否保留了原配方的本质?" → yes/no/partial + 简要理由
2. "这条改写读起来像不像 niche 目标用户会发的真实视频脚本?" → 1-5 评分
3. "这条有没有商业雷区(品牌名 / 功效宣称 / 误导)?" → yes/no + 命中片段

judge 输出 JSON,落到 report。

### 2.3 founder qualitative(人工,从 P2-4 签字文件读)

P2-4 已落地 `p2-4_qualitative_signoff_<date>.md`。P2-6 把每个 niche 的"通过/调整"勾选状态 parse 出来,作为基准线。

---

## 3. EvalReport 结构

```python
class CheckResult(BaseModel):
    name: str
    passed: bool
    detail: str = ""

class PerCaseReport(BaseModel):
    source_url: str
    niche: str
    rewrite_id: str
    mechanical: list[CheckResult]
    llm_judge: dict  # {kept_formula: yes/no, realism_1to5: int, ad_risk: yes/no}
    founder_qualitative: str  # pass/fail/not_reviewed

class PerNicheReport(BaseModel):
    niche: str
    cases: list[PerCaseReport]
    mechanical_pass_rate: float  # 0..1
    judge_realism_avg: float  # 1..5
    judge_ad_risk_count: int
    founder_pass_rate: float

class EvalReport(BaseModel):
    timestamp: str
    mode: str  # fixture | llm
    model: str  # gemini-2.0-flash / etc
    prompt_version_hash: str  # sha256 of all 3 prompt files
    niches: list[PerNicheReport]
    overall_mechanical: float
    delta_from_baseline: dict  # {"mechanical": +0.05, "realism": -0.2, ...} | None
```

`report.py` 把 EvalReport 渲染成 markdown 文件,落到 `docs/nexus/founder_log/p2-6_report_<date>.md`,founder 可读。

---

## 4. Baseline 比对

`baselines.py`:
- `save_baseline(report)`:把 EvalReport 落到 `docs/nexus/founder_log/p2-6_baseline_<date>.json`
- `load_latest_baseline() -> EvalReport | None`:读最近一个
- `diff(current, baseline) -> dict`:比较核心指标(mechanical_pass_rate / realism / ad_risk_count)

`run_eval(baseline="last")` 自动调 diff,把 delta 写进 report。

---

## 5. CLI 用法

```bash
# 跑完整 eval,baseline 比对最近一次
uv run python scripts/p2-6_eval.py --niche all --mode llm --baseline last

# 单 niche
uv run python scripts/p2-6_eval.py --niche baomam_fushi --mode llm

# fixture 模式(回归基线,不烧 LLM 费用)
uv run python scripts/p2-6_eval.py --niche all --mode fixture
```

输出:
1. stdout 打印每个 niche 的指标摘要 + delta
2. `docs/nexus/founder_log/p2-6_report_<YYYY-MM-DDTHHMMSS>.md`(人读版)
3. `docs/nexus/founder_log/p2-6_baseline_<YYYY-MM-DDTHHMMSS>.json`(机器读版)

---

## 6. Tests (`test_eval_harness.py`)

1. mechanical checks 都 fire 正确(给坏样例,触发对应 fail)
2. llm_judge mock 返回 → parse 正确
3. EvalReport 序列化 → 反序列化 round-trip 不丢字段
4. baseline diff 计算正确(当前 vs 历史)
5. report.py 渲染的 markdown 含所有 niche 摘要 + delta 段落

---

## 7. Done-signal

- `find backend/src/agent/cascade/eval -name "*.py" | wc -l` ≥ 4
- `scripts/p2-6_eval.py --niche all --mode fixture` 跑通,产出 baseline JSON + report MD
- `uv run pytest tests/test_eval_harness.py -v` 全过
- 第一次正式 eval(--mode llm)已经跑过 1 次,落地 `p2-6_baseline_<date>.json` 作为后续 prompt 迭代的起点

---

## 8. 怎么用 eval 做 prompt 迭代

这是工单交付后的使用流程,founder/Claude 改 prompt 时:

1. 改 `backend/src/agent/prompts/rewrite_<niche>.md`
2. `uv run python scripts/p2-6_eval.py --niche <niche> --mode llm --baseline last`
3. 看 delta:realism_avg ↑? mechanical_pass_rate 不降? ad_risk_count = 0?
4. 三项都 OK 才把 prompt 改动 merge 到 main

→ "改 prompt 不靠拍脑袋,靠 eval 数字"。

---

## 9. NOT in this ticket

- Real-time eval(每次 rewrite call 跑 eval 是 P3 性能/cost 工作)
- A/B test 框架(几个 prompt 版本同时上线分流) — 这是 P3 / Phase 2
- multi-judge ensembling(用多个不同 model 做 judge 取多数)— 简化版只用一个 judge
- 把 eval 接入 CI(自动每 PR 跑) — 等 cost 模型稳定后再说

---

## 10. PM notes

- 这个工单的最大价值不是当下,是**后续 6 周里每次想动 prompt**时都能用 — 一次性投资,长期复用
- founder qualitative 必须先有(P2-4 done)。没有 founder 锚点的 baseline 是无意义的
- judge LLM 成本不算到 cost guard 里(eval 是开发期,不算用户 run)
- baseline JSON 文件落 git;founder 能在 PR diff 里直接看指标变化
