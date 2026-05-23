# Codex handoff — P4-7 events 表 retention 策略

**Owner**: Codex session (backend)
**Source of truth**: `backend/src/agent/cascade/events.py` + `storage.py` events 表
**Status**: READY · no upstream blocker
**Time budget**: 0.5 day
**Allocation**: PM_W4_allocation.md §3.2(W3D3 新加)

---

## 0. 背景

events 表自 W1 起累积,Phase 1 内测进入后 P4-3 加的 cascade_retry/circuit_open/cache_hit/cache_miss 4 个新类型会让写入速率明显上升(estimated ~30-50 events/day per active user × 10 users × 6 weeks ≈ 12k-20k rows).

短期不是问题(P4-4 已加索引),长期需要 retention policy 防止表无限膨胀。**这不是性能优化,是数据治理**:Phase 1 数据 6 周后还有保留价值吗?分类决定保留 / 删除策略。

---

## 1. Done-signal

- `backend/src/agent/cascade/storage.py:retention_sweep(now: datetime | None = None) → dict[str, int]` 返回 `{event_name: rows_deleted}` 给观察用
- Retention 策略(硬编码在函数内,W5 起可改 config):

| 事件类型 | 保留期 | 理由 |
|---|---|---|
| `run_started / analysis_returned / script_rewritten / publish_pack_copied / shot_generated / anchor_created / anchor_reused / interview_logged / consent_accepted / generation_cost` | **永久**(business 关键)| funnel + cost + 合规审计 |
| `failure_emitted / failure_recovered` | 180 天 | debug 价值衰减,但 incident postmortem 6 个月内可能用到 |
| `cascade_retry / cascade_circuit_open / cascade_cache_hit / cascade_cache_miss` | **90 天** | 纯 infra 观察,旧数据无用 |

- 新增 1 个 CLI:`scripts/retention_sweep.py`,跑一次 + 打印汇总 + exit 0
- 新增 `pyproject.toml` 中 `[project.scripts]` 不动(避免 setup 改动);从 backend/ 跑 `uv run python ../scripts/retention_sweep.py`
- 4 个 unit test:
  1. 永久保留类不会被删
  2. failure_emitted 旧于 180 天被删,新于不删
  3. cascade_* 旧于 90 天被删
  4. 返回的 dict 准确反映删除行数

---

## 2. 实现指引

- 用 `created_at < ?` 跟字符串 ISO 8601 比较(SQLite TEXT 排序对 ISO 8601 是正序),不需要 strftime
- 单事务批量删 — 4 个事件类型一个 transaction,避免半完成状态
- **不要** VACUUM(WAL 模式下 VACUUM 会冲突;表大小回收交给 SQLite 自动 free pages)
- retention_sweep 是同步对 events 表的 DELETE,在 Phase 1 体量(< 50k rows)下 < 100ms;不需要分批

---

## 3. 边界(不在此票)

- **不做** 自动定时调度(cron / scheduler 不在 Phase 1 范围)— retention_sweep.py 当前只能手动跑
- **不做** archive(数据归档到 cold storage)— Phase 1 体量不需要
- **不做** config 化的 retention(W5 起再做,Phase 1 硬编码 OK)
- **不动** 永久保留类的事件 schema 或写路径
- **不做** events 表分区(SQLite 不原生支持,体量不够大不值)

---

## 4. Upstream dep

- ✅ events 表 schema(P3-3 起就稳定)
- ✅ P4-3 新事件类型(retention 策略表 §1 已含)

无 blocker。

---

## 5. 失败兜底

- 若运行时发现某事件 retention 期太短(founder 投诉"我想看一周前的某条 retry")→ 临时改回函数内 days 数值再跑;W5 配置化
- 若 sweep 删除过多行(测试错配置)→ 数据已删,需要从 SQLite 备份恢复;**所以加测试覆盖关键边界**

---

## 6. Output 清单

- `backend/src/agent/cascade/storage.py`(+ 1 函数)
- `scripts/retention_sweep.py`(新)
- `backend/tests/test_events_retention.py`(新,4 cases)
- commit:`feat(P4-7): events retention sweep — 90d for infra, 180d for failures, perm for business`
