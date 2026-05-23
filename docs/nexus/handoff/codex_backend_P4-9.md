# Codex handoff — P4-9 Toprador 真实端到端 staging

**Status**: ⛔ **SUPERSEDED by P5-3 Doubao-lite 重写** @ 2026-05-23 W3D3
Founder 2026-05-23 W3D3 决定:toprador 上游路径全切 Doubao-lite 自建(`handoff/codex_backend_P5-3.md`)。本 brief **不再执行**,除非 P5-3 ship 失败或 founder 明示回滚到原 toprador。
当前状态:**dormant**;`scripts/p4-9_toprador_staging.py` scaffold 保留作 historical reference。

---

**Owner**: Codex session (backend) — **blocked on founder providing Toprador endpoint + key**
**Source of truth**: `backend/src/agent/cascade/analysis_service.py:_call_toprador`(P2-2 wiring + P3-7 hardening + P4-3 observability);`docs/TOPRADOR_SCHEMA.md`(上游契约)
**Status (original)**: DRAFT · blocked on `TOPRADOR_ENDPOINT` + `TOPRADOR_API_KEY` 配置
**Time budget**: 0.5 day
**Allocation**: PM_W4_allocation.md §3.2(W3D3 R6 mitigation)+ PM_risk_audit_2026-05-23.md §7

---

## 0. 背景

W1-W4 所有工程基于 `synthetic_v1` fixture。`CASCADE_UPSTREAM=toprador` 路径虽有 P2-2 wiring + P3-7 retry/breaker + P4-3 observability,**没有真实流量验证过**。

Phase 1 内测前必须做 1 次端到端 staging,验证:
1. Toprador 实际响应 schema 与 `contract.py` + `adapter.py` 是否对齐
2. 实际延迟 / 错误率 / 限流是否在 `circuit_breaker` 阈值合理范围
3. `cascade_*` 观察事件能否在真实流量下正确触发

P4-9 = 这次 staging exercise,产 staging 报告 + 任何发现的 adapter 漏洞修复。

---

## 1. Unblock 前置(founder action)

founder 在 `backend/.env` 加 2 行:
```
TOPRADOR_ENDPOINT=https://<toprador 实际 base url>/analyze
TOPRADOR_API_KEY=<token>
```

founder ping Codex "Toprador 已配,P4-9 可起跑" → Codex 开工。

---

## 2. Done-signal

- `docs/nexus/founder_log/p4-9_toprador_staging_<UTC>.md` 落地报告含:
  - 用 5 条 niche-相关真实 URL(从 `docs/nexus/founder_log/real_urls_for_p2-4.md` 挑出 1 条 baomam / 1 条 yuer / 1 条 jiating,加 2 条 founder 现场提供)
  - 每条调 `request_shallow_analysis(url, user_id="staging", run_id="p4-9-<n>")`
  - 报告每条:
    - 延迟 ms(`upstream_latency_ms`)
    - retry 次数(`upstream_attempts`)
    - 是否触发 cascade_retry / cascade_cache_miss / cascade_cache_hit(重复跑同 URL 看 cache 是否生效)
    - 是否触发 W1/W2/W9 warnings 或 hard failure
    - schema 字段对齐情况(若 adapter 抛 `S5_INVALID_PAYLOAD` 列出具体字段)
- staging 期间 admin `/admin/events` 看到对应事件,截图贴报告
- 任何发现的 adapter 漏洞 → 立即修(改 `adapter.py` + 加 test)
- 任何发现的 circuit_breaker 阈值不合理(例如 5 次失败窗口太严)→ 提出 W5 调整建议,不在本票动 P3-7 策略

---

## 3. 实现指引

### 3.1 Staging 脚本(新)

`scripts/p4-9_toprador_staging.py`:
```python
"""P4-9 Toprador 真实端到端 staging。

跑 5 条真实 URL 经 Toprador → contract,产报告。

使用:
    cd backend && uv run python ../scripts/p4-9_toprador_staging.py
"""
# 略 — Codex 按 §2 done-signal 自由设计
```

报告 markdown 自动生成,Codex 设计 schema。

### 3.2 真实 URL 选取

从 `docs/nexus/founder_log/real_urls_for_p2-4.md` 已存的 baomam_fushi / yuer_richang / jiating_chufang URL 中各挑 1 条 = 3 条;founder 现场加 2 条新的(staging 时间窗内的最新爆款)。

### 3.3 注意

- staging 用 user_id="staging" 隔离,**不污染** real creator 数据
- 跑前 + 跑后各看一眼 `/admin/cost`,记录 staging 净成本(放报告里)
- 若 Toprador 实际 schema 与 `contract.py` 偏移 ≥ 1 字段 → 立即 fix adapter + test,**不要 cherry-pick**(本就是 staging 目的)
- 若 5 条全过 + 0 hard failure + 0 schema 漂移 → 报告标 "✅ Phase 1 ready for real creator traffic"
- 若任一硬失败 → 报告标 "⚠️ <count> issues found, fix in commit hash <X>",列出 fix

---

## 4. 边界(不在此票)

- **不动** P3-7 retry / breaker 阈值(仅 W5 建议表)
- **不做** Toprador 自建 / 替换 / mock(就是去验证已部署的)
- **不做** 性能压测(< 100 req/min 的 Phase 1 体量不需要)
- **不引入** 负载测试工具
- **不做** P4-6 cache 持久化的真实流量验证(那是 P4-6 自己的票)

---

## 5. Upstream dep

- ⏳ **founder 配 `TOPRADOR_ENDPOINT` + `TOPRADOR_API_KEY`**
- ✅ P2-2 Toprador wiring(`eff6cd4` 等同期)
- ✅ P3-7 retry / breaker
- ✅ P4-3 cascade observability events

---

## 6. 失败兜底

- Toprador 不可达 / 5xx 持续 → 报告标 "blocked on upstream availability";founder 联系 Toprador 团队后再起;不要 fallback fixture 完成本票(那不算 staging)
- 限流(429)频繁 → 把跑 5 条改 1 条/min,共 5 min;报告说明限流口径

---

## 7. Output 清单

- `scripts/p4-9_toprador_staging.py`(新)
- `docs/nexus/founder_log/p4-9_toprador_staging_<UTC>.md`(报告)
- 若有 adapter 修复 → `backend/src/agent/cascade/adapter.py` + 对应 test
- commit:
  - 路径 a(无 fix):`docs(P4-9): Toprador real-traffic staging — N issues, ✅ Phase 1 ready`
  - 路径 b(有 fix):`feat(P4-9): Toprador staging + adapter fix — <issue>`
