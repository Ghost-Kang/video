# Signoff 文档状态汇总 — 2026-05-21

**Date**: 2026-05-21
**Purpose**: 记录 P1-3 和 P2-4 两份 founder qualitative signoff 当前的**实际打勾状态**,以及它们对工程下一步的影响。
**Triggered by**: PM 4-owner allocation rule — 需要把"founder 已表态但磁盘上没体现"的差距显式记下来。

---

## 1. `p1-3_qualitative_signoff_2026-05-21.md`

**磁盘状态**:
- 三个 niche 实际**已打勾** ✅ — founder 在 W2 改动中已写明 `- [x] 我会把这个版本发出去 — 通过 (fixture baseline 级)`
- 同时附了 10 条调整诉求(F-1-a/b/c, F-2-a/b/c, F-3-a/b/c/d)→ **全部已吸收进 P2-4 + hook_taxonomy**(见 `ca3dc9b` commit)
- §5 "最终签字与下一步"已经标 ✅ Acceptance bar reached 并 dated 2026-05-21

**结论**: P1-3 已完整签字闭环。无后续 founder action。

---

## 2. `p2-4_qualitative_signoff_2026-05-21.md`

**磁盘状态**: 0 / 15 ticks(所有 `- [ ]` 仍空白)

**Founder 口头确认**: 2026-05-21 conversation "上面触发条件已经完成" 涵盖 P2-4 signoff。已记录在 `W2_closed_2026-05-21.md`。

**当前 mismatch**: 文档里实际没勾。后续 PM session 或 routine 跑 `runner.parse_founder_qualitative()` 会读到全部 `not_reviewed` 状态。

---

## 3. 解决方案(三选一,founder 决定)

### Option A — Founder 在 IDE 里实打勾(推荐,~5 分钟)

打开 `docs/nexus/founder_log/p2-4_qualitative_signoff_2026-05-21.md`,把 15 个 `- [ ] 我会把这个版本发出去` 改为 `- [x] 我会把这个版本发出去`,commit。

完成后 P2-6 eval 的 `founder_pass_rate` 会从 0% 升到正常值。

### Option B — 增量"接受所有 fixture baseline"批注

在 signoff doc 顶部加一行:

> Founder 2026-05-21 verbal approval: 所有 15 条 fixture baseline 通过(等效 [x] × 15)。仅作 LLM 模式启动前的离线门槛,真实 founder bar 由后续 LLM 模式 + 真实 URL 出真品后再签。

这种方式保留"等真正跑过 LLM 模式才签真签字"的语义,但 P2-4 状态正式 done。

### Option C — Founder 改为针对真实 LLM 输出签字(推迟)

如果 founder 觉得 fixture baseline 不值得签字,跳过 P2-4 fixture signoff,等 `GOOGLE_API_KEY` 配好后跑 LLM 模式产出真输出,再做唯一一次正式签字。

期间 P2-6 eval 报告 founder_pass_rate=0% 是预期状态,只在文档里说明即可。

---

## 4. PM 推荐

**Option B** — 在 signoff doc 顶部加一行 verbal-approval 批注。理由:

- Founder 已经表过态,不应该让磁盘和实际状态长期不一致(下一个 PM session / routine 会困惑)
- Fixture baseline 本来就不是真 founder bar,B 保留这层语义
- 5 分钟搞定,不阻塞 W3 工程线

要 PM 自动写这一行吗?(需要 founder 在这里回 "yes" 我才会动 signoff doc)

---

## 5. 完成判定

- 选定 A / B / C 之一并执行
- `p2-4_qualitative_signoff_2026-05-21.md` 顶部或 checkbox 状态清晰
- 此文件标 `Resolved: <option> @ <timestamp>`
