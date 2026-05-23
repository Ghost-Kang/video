# Codex handoff — P4-8 cost_guard 预测 vs 实际校准报告

**Owner**: Codex session (backend)
**Source of truth**: `backend/src/agent/cascade/cost_guard.py`(PREDICT_ANALYSIS_CNY / PREDICT_REWRITE_CNY 常量);`backend/src/agent/cascade/events.py` (generation_cost event payload `cost_fen` 实际值)
**Status**: READY · no upstream blocker
**Time budget**: 0.5 day
**Allocation**: PM_W4_allocation.md §3.2(W3D3 新加)

---

## 0. 背景

`cost_guard.py` 用硬编码 PREDICT 常量在调用前做预算检查,防止某 user/run 失控烧钱。**但**:
- PREDICT 是 W1 估算,Doubao seed-1.6 + Apimart 真实价格可能已偏移
- generation_cost event 写入实际 cost_fen,**有真实数据**但目前没人对照
- Phase 1 内测 = 校准窗口;校准报告决定 W5+ 是否升 PREDICT

P4-8 不改 PREDICT,只**产报告**:对每种 call_kind,聚合实际 cost_fen 分布(p50/p95/max)+ PREDICT 值,输出对照表。Founder 看完后决定是否调 PREDICT。

---

## 1. Done-signal

- `scripts/cost_calibration.py`(新)从 events 表读所有 generation_cost,按 call_kind 聚合统计
- 输出 Markdown 报告到 `docs/nexus/founder_log/cost_calibration_<UTC>.md`,格式:

```
# cost_guard 校准报告 — <UTC>

samples_count: <N>

| call_kind | p50 (¥) | p95 (¥) | max (¥) | mean (¥) | n | PREDICT (¥) | drift |
|---|---|---|---|---|---|---|---|
| analysis | 0.012 | 0.045 | 0.080 | 0.018 | 124 | 0.05  | OK     |
| rewrite  | 0.080 | 0.180 | 0.220 | 0.105 |  87 | 0.10  | ⚠ p95>PREDICT |
| shot     | ...   | ...   | ...   | ...   | ... | 0.30  | OK     |

## 调整建议
- rewrite PREDICT 当前 0.10,p95 实际 0.18 → 建议 PREDICT 上调到 0.20(或保持 0.10 但提示"95% 调用 < 0.18,长尾不阻塞")
- (类似建议针对其他 call_kind)
```

- 4 个 unit test:
  1. 报告 markdown 文件落地
  2. 4 个 call_kind 都有行(analysis / rewrite / shot / 其他存在的)
  3. drift 列:p95 > PREDICT 标 ⚠;p95 ≤ PREDICT 标 OK;无样本标 — (n=0)
  4. samples_count 与 generation_cost events 总数一致

---

## 2. 实现指引

- 复用 `storage.list_events(event_name="generation_cost", limit=10000)`(P4-2 已就位)
- 拆 payload 的 `cost_fen` / 100 = cny
- numpy 不必引,纯 python list sort + len 索引算 p50/p95
- PREDICT 值从 `cost_guard.py` import,**不要** 硬编码副本

---

## 3. 边界(不在此票)

- **不动** PREDICT 常量;报告只给建议,不动代码
- **不做** 自动报警(P5/P6 才上)
- **不做** 分 user_id 聚合(全体 + 按 call_kind 就够);也不分时间窗口(就跑当下全部数据)
- **不做** 与 Doubao 官方定价对照(校准目标是经验值,不是理论值)

---

## 4. Upstream dep

- ✅ P4-2 `/api/events` / `storage.list_events`
- ✅ generation_cost event schema(W2 就稳定)

无 blocker。

---

## 5. 失败兜底

- 若 generation_cost events < 10 条 → 报告标 "样本不足,等数据" + samples_count + 不写 drift 列
- 若所有调用都来自单 user_id(Phase 1 内测早期常见)→ 不算异常,正常输出;P5 加 sample diversity 提示

---

## 6. Output 清单

- `scripts/cost_calibration.py`(新)
- `backend/tests/test_cost_calibration.py`(新,4 cases)
- 第一次跑 → `docs/nexus/founder_log/cost_calibration_<UTC>.md`(可选 commit 进去当 baseline)
- commit:`feat(P4-8): cost_guard calibration report — p50/p95/max vs PREDICT per call_kind`
