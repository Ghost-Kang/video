# Cycle W5D3 — UX 审视后续 + Risk 全收 (2026-05-28)

## 背景

W5D2 末 Cascade 上线 `https://cascade.herwin.top`。Founder 实测撞 2 个 bug:
1. 同条 URL 仍 `S4_SCENES_LEN_OUT_OF_RANGE` (W18 pad 路径未覆盖 timestamp 异常)
2. 失败时进度条 + 错误消息**共存** (`failed` state 没触发)

UX Architect agent 做了 layout 整体审视, 产出 4 件:
- **A 布局**: 右 360px panel → 底部 dock chat (max-h-50vh) ✅
- **B failed state 真触发**: heuristic 检测 `/请求超时|处理出错|系统暂时繁忙/` → setFailure ✅
- **C URL 溢出**: user bubble `break-all overflow-hidden` ✅
- **D 95% pin escape**: 90s 卡 95% → 弹「换一条 / 继续等」 ✅

Claude 接 **Risk 1** (heuristic 太脆) — backend 加结构化 `analysis_failed` WS frame, 不依赖 keyword 匹配。已 deploy。

剩余两件 cycle 工作分给 Claude + Codex 并行做。

---

## Owner 分工

| Owner | Task | Effort | 优先级 | 依赖 |
|---|---|---|---|---|
| **Claude** | T1 真实分析进度 WS event (取代 fake percent) | M (3-4h) | 🟡 中 (UX 锦上添花) | 无 |
| **Codex** | T2 dock layout 收尾 + URL truncate UX + Risk 2 messages overlay | M (3-4h) | 🟡 中 (touch device 不阻塞 desktop cohort) | 无 |
| **Founder** | 决策点 ↓ | — | — | — |

## Founder 决策点

1. **真实 progress event 推送频率**: backend 在 cascade_analyze 内部 4 个阶段 (resolve_url / mediakit_storyline / ARK_overlay / transcribe) 各 emit 一次进度?  还是只 emit 起止两次? 取决于 UX 实际期望粒度
2. **Cohort 用 touch device 比例**: 若 ≥ 30%, Risk 2 升级到 P0; 若 < 10%, 可推迟到 30+ 用户 cohort 时
3. **URL bubble 显示策略**: 完整显示 break-all (现状) / 中段省略 (...) / hover 才显示完整

---

## 验收 (两家完工后)

- ✅ Founder 重测那条 7643989458156861038 URL (现在能跑通 W18 pad 路径)
- ✅ AnalysisProgress 显示**真实** 阶段 % (不再线性递增 80%)
- ✅ Touch device 上 dock 内 messages history scroll 不跟 CardStack scroll 争
- ✅ 长 URL bubble 显示美观 (founder pick 策略)
- ✅ backend 507 + frontend ≥175 + tsc clean

## Handoff docs

- [Claude T1: 真实 progress event](claude_W5D3_T1_progress_events.md)
- [Codex T2: dock 收尾 + Risk 2 + URL truncate](codex_W5D3_T2_dock_polish.md)
