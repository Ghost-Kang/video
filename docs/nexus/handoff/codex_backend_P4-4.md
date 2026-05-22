# Codex handoff — P4-4 events 表索引优化

**Owner**: Codex session (backend)
**Source of truth**: `backend/src/agent/events.py` schema;P4-2 admin events 面板查询模式
**Status**: DRAFT · no upstream blocker
**Time budget**: 0.5 day
**Allocation**: `PM_W4_allocation.md §3.2`

---

## 0. 背景

`events` 表目前只有 PK 索引。Phase 1 内测开始后,admin events 面板 + P4-3 observability counters 会让该表行数迅速增长到 10k-100k 级。常见查询路径:

```sql
-- pattern 1: admin events firehose, 反向时间序
SELECT * FROM events ORDER BY ts DESC LIMIT 200;

-- pattern 2: by type filter
SELECT * FROM events WHERE event_type = ? ORDER BY ts DESC LIMIT 200;

-- pattern 3: by thread_id(cascade 调试)
SELECT * FROM events WHERE thread_id = ? ORDER BY ts DESC;
```

无索引下 pattern 2/3 全表扫;pattern 1 也要 ORDER BY 物化排序。P4-4 加两个 compound index 解决。

---

## 1. Done-signal

- 新增 2 个索引:
  - `idx_events_thread_ts` on `(thread_id, ts DESC)`
  - `idx_events_type_ts` on `(event_type, ts DESC)`
- migration 文件落地(若现有项目用 Alembic 则 Alembic;若是手写 SQL migration 则跟现有 pattern 走 — 先 grep `backend/` 找现有 migration 习惯)
- 新增 1 个 perf-shape 测试 `backend/tests/test_events_index.py`:
  - 准备 1000 条 events
  - `EXPLAIN QUERY PLAN SELECT * FROM events WHERE thread_id = ? ORDER BY ts DESC LIMIT 200`
  - 断言输出含 `USING INDEX idx_events_thread_ts` 或 `SEARCH events USING INDEX`
  - 同样对 `event_type` 查询做一次
- 现有 events 测试全绿不退化

---

## 2. 实现指引

- 用 `CREATE INDEX IF NOT EXISTS` — migration 可重入
- ts 字段已经是 ISO 8601 TEXT 或 INTEGER timestamp(grep 确认);SQLite DESC index 自 3.3 起 OK
- migration 文件命名跟现有最近一份对齐(grep `backend/` 找现有 migration 文件名 pattern)

---

## 3. 边界(不在此票)

- **不动** `events` 表 schema(列不增不减)
- **不做** 历史 events 数据迁移 / 重写
- **不做** retention policy(Phase 1 内测先无限存,等数据真的大了再说)
- **不做** PostgreSQL 切换(P5/P6 再议)

---

## 4. Upstream dep

无。可与 P4-2 / P4-3 并行。

---

## 5. 失败兜底

如果 `EXPLAIN QUERY PLAN` 在 CI 上行为不稳定(SQLite 版本差异) → 测试改为只断言 query 在 1000 行下 < 10ms(更宽松,但 deterministic 较差)。两个口径任选一,默认走 EXPLAIN 断言。

---

## 6. Output 清单

- `backend/migrations/<timestamp>_add_events_indexes.sql`(或 Alembic 对应文件)
- `backend/tests/test_events_index.py`(新)
- commit:`perf(P4-4): events table compound indexes for thread_id/event_type lookups`
