# Claude handoff — P2-4 LLM 改写真实模式

**Owner**: Claude session
**Source of truth**: `PM_W2_allocation.md §3.3` · `backend/src/agent/cascade/rewrite.py` · `backend/src/agent/prompts/rewrite_*.md` · `docs/nexus/founder_log/real_urls_for_p2-4.md`
**Status**: 待 founder 贴 15 条真实 URL 后启动
**Time budget**: 3 天(W2D2-W2D5)

---

## 0. What you build

把 `rewrite.py` 的 `CASCADE_REWRITE_UPSTREAM=llm` 路径从"能跑"升到"生产级"。fixture 模式保持现状(offline 回归基线)。LLM 模式针对 founder 在 `real_urls_for_p2-4.md` 贴的 15 条真实爆款 URL 跑通,每个 niche ≥ 4/5 机械检查 + ≥ 4/5 founder qualitative bar。

P2-4 不是"加一个 LLM call",是"把 LLM 输出从演示级带到产品级"。重点在容错、cost 控制、和回归基线。

---

## 1. Files

| Path | Change |
|---|---|
| `backend/src/agent/cascade/rewrite.py` | 强化 `_llm_rewrite`:JSON 解析容错 + 1 次 retry + 输出 schema 校验 + 后处理(剔除禁用词)+ confidence 校准 |
| `backend/src/agent/cascade/rewrite.py` | 新增 `_extract_json` 升级版:支持 ```json fence、多个候选 object 时选最大;支持流式 partial JSON 修复 |
| `backend/tests/test_rewrite_llm.py` | mocked-LLM 测试,覆盖 happy / malformed / retry / forbidden-term-leak / cost-tracking 路径 |
| `backend/src/agent/cascade/rewrite_service.py` | 已有 LLM dispatch;P2-4 不动这文件,只补 cost_cny 估算 |
| `docs/nexus/founder_log/p2-4_llm_outputs_<date>/` | 每次跑产出的 15 条改写文本(每个 niche 5 条),供 founder qualitative review |
| `docs/nexus/founder_log/p2-4_qualitative_signoff_<date>.md` | 第二轮 founder 签字模板(同 P1-3 模板结构) |

---

## 2. Behavior 要求

### 2.1 JSON 解析容错

LLM 输出可能:
- 包在 ```json fence 里 → 现有 `_JSON_PATTERN` 能处理
- 带 markdown 解释前缀("好的,我帮你改写,JSON 如下:...{...}")→ 现有 regex 能抓最外层 `{...}`
- 多个候选 `{...}`(model 在解释里嵌了示例 JSON)→ **当前版本会抓第一个,可能是错的**;P2-4 改成"抓最长的 `{...}` 块"
- 截断 / 损坏 JSON → 现有版本会抛 `json.JSONDecodeError`;P2-4 加 **1 次 retry**:把原始 prompt + 一句 "你刚才输出的不是合法 JSON,请只输出 JSON,不要解释" 再发一次

### 2.2 输出 schema 校验

`_llm_rewrite` 返回前用 `RewriteResult.model_validate(raw)` 自校验(目前依赖 service 层校验,P2-4 提前到模块内)。校验失败:
- 缺字段:补默认(rewrite_id 用 hash, parser_warnings 用 `[]`, etc.)
- shots 数量越界(< 3 或 > 5):截断到 5 或抛 `S5_INVALID_PAYLOAD`
- script_markdown 长度异常:不阻断,记 `parser_warnings`

### 2.3 后处理(forbidden terms 兜底)

prompt 已明确禁用词,但 LLM 可能漏。`_llm_rewrite` 在返回前对 `script_markdown` 和 shots 的 dialogue/visual 跑 `_clean()`(已有函数),自动替换禁用词。每次替换记一条 `parser_warnings`,founder 在 PR review 时能看到。

### 2.4 confidence 校准

- LLM 输出的 confidence 经常乐观。P2-4 加一个 ceiling:
  - 如果检测到任意硬约束违反(禁用词、长度异常、shot 数异常) → `confidence = min(confidence, 0.4)`
  - 否则用 LLM 给的值,但 clamp 到 `[0.0, 1.0]`

### 2.5 cost 估算

`cost_cny` 在 `_llm_rewrite` 返回值里目前是 hard-code 或 0。P2-4 加估算:
- 用 `len(prompt) / 4` 作为输入 token 近似(中文 token 比英文高)
- `len(output) / 4` 作为输出 token 近似
- 按 Gemini Flash 价格估算 RMB(具体单价由 `config.py` 暴露 `LLM_INPUT_PRICE_CNY_PER_1K` / `LLM_OUTPUT_PRICE_CNY_PER_1K`,默认值取 founder 在 `02_event_spec.md` 估算的成本上限)

### 2.6 retry policy

仅一种 retry:JSON 解析失败 → 1 次重发(prompt 后追加"请只输出 JSON")。其他失败不 retry。`rewrite_service.py` 已有 cost cap(>¥3/run 抛 S8),retry 走的 token 算到这个 cap 内。

---

## 3. Tests (`test_rewrite_llm.py`)

mocked-LLM 测试,patch `ChatGoogleGenerativeAI.invoke`:

1. **Happy path**: mock 返回合法 JSON → `RewriteResult` 校验通过,confidence 不被强降
2. **Markdown-fenced JSON**: mock 返回 ` ```json\n{...}\n``` ` → 正确抽取
3. **Multiple JSON candidates**: mock 返回 "示例 `{example_obj}` 实际 `{real_obj}`" → 抽到最长的(real_obj)
4. **Malformed JSON → retry**: mock 第一次返回坏的、第二次返回合法 → 测试 retry 触发、最终成功
5. **Malformed twice → raise**: mock 两次都坏 → 抛 `S5_INVALID_PAYLOAD`,不静默 fallback
6. **Forbidden term leak**: mock 返回包含"AI / 神器"的 JSON → `_clean` 替换后 `parser_warnings` 记录,confidence 降到 ≤ 0.4
7. **Shot count out of range**: mock 返回 7 个 shots → 截断到 5,`parser_warnings` 记录
8. **Cost estimation**: 验证 `cost_cny > 0` 且与 prompt 长度大致成比例

---

## 4. Real-URL acceptance (P2-4 真实交付门槛)

Founder 在 `real_urls_for_p2-4.md` 贴 15 条 URL 之后:

1. 写一个一次性脚本 `scripts/p2-4_run_real_urls.py`:
   - 读 `real_urls_for_p2-4.md`,parse 15 条 URL
   - 对每条调 `CASCADE_UPSTREAM=toprador` 拉真实 analysis(P2-2 必须先到位 — 这里依赖 Codex 的 P2-2)
   - 用拉到的 contract 调 `rewrite_for_niche(contract, niche)`(`CASCADE_REWRITE_UPSTREAM=llm`)
   - 把每条输出落到 `docs/nexus/founder_log/p2-4_llm_outputs_<date>/<niche>/url<N>_output.json` + 配套 `.md` 可读版
2. 自动跑机械检查(复用 `test_rewrite.py` 里的 5 条规则),输出每个 niche 的 pass/fail 统计
3. 把统计写到 `docs/nexus/founder_log/p2-4_mechanical_2026-05-XX.md`
4. 通知 founder 做 qualitative review:`p2-4_qualitative_signoff_<date>.md` 模板(同 P1-3 结构,15 条而不是 3 条)

**Done bar** (per `PM_W2_allocation.md`):
- 4/5 机械检查通过(每个 niche 5 条 URL 至少过 4 条)
- founder qualitative 4/5(每个 niche 至少 4 条标"我会发出去")
- 累计 cost ≤ ¥3/run(每条单独跑算 1 run)

---

## 5. Done-signal

- `grep -c '_llm_rewrite\|_extract_json\|confidence.*0\.4' backend/src/agent/cascade/rewrite.py` ≥ 3
- `uv run pytest tests/test_rewrite_llm.py -v` 全过
- `scripts/p2-4_run_real_urls.py` 存在且可执行
- `docs/nexus/founder_log/p2-4_llm_outputs_<date>/` 包含 15 个 niche/url<N>_output.json
- `docs/nexus/founder_log/p2-4_qualitative_signoff_<date>.md` founder 签字 4/5 per niche

---

## 6. NOT in this ticket

- Toprador 真实接入(P2-2 Codex)— P2-4 假设 P2-2 已 done
- Eval dashboard 自动化(P2-6,本工单后置)
- prompt 迭代(P2-4 只验证 prompt 在 LLM 路径下表现;真要改 prompt 单独开 P2-7 prompt-iteration 工单)
- multi-LLM provider 支持(只用 Gemini;后期切 provider 是 P3 工作)
- 缓存(rewrite_service 已有 24h 缓存,本工单不动)

---

## 7. PM notes

- **依赖 P2-2 完成**才能跑真实模式。P2-2 没到位之前,只能跑 mocked tests + 用 synthetic_v1 fixture 测 LLM 路径。
- founder 的 15 条 URL 是软依赖:测试可以用 synthetic_v1,但 done bar 必须用真实 URL。
- 这个工单是 W2 的"产品质量门" — cascade 能不能上车 creator,看 P2-4 真实模式过没过 qualitative bar。
