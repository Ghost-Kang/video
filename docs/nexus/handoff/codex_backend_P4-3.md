# Codex handoff — P4-3 cascade observability counters

**Owner**: Codex session (backend)
**Source of truth**: `codex_backend_P3-7.md` (Toprador hardening — retry / breaker / cache);`backend/src/agent/cascade/analysis_service.py`;`backend/src/agent/events.py`
**Status**: DRAFT · no upstream blocker
**Time budget**: 1 day
**Allocation**: `PM_W4_allocation.md §3.2`

---

## 0. 背景

P3-7 落地了 Toprador 的 retry / circuit breaker / in-memory cache,但**没有任何观察手段** — 失败一次只在日志看得到,founder 无法在 admin 面板看 "今天 circuit 跳了几次"。

P4-3 把 P3-7 已经有的内部状态以 events 形式 emit 到 `events` 表,**不引入 Prometheus / OTel**(过早 — Phase 1 内测体量不需要),只复用现有 events pipeline。P4-2 admin 面板会直接展示。

---

## 1. Done-signal

- 4 个新 event_type 写入 `events` 表:
  - `cascade_retry` — 每次重试触发,payload `{endpoint, attempt, reason, duration_ms}`
  - `cascade_circuit_open` — breaker 跳开,payload `{endpoint, consecutive_failures, cooldown_until}`
  - `cascade_cache_hit` — 命中 in-memory cache,payload `{source_url_hash, ttl_remaining_s}`
  - `cascade_cache_miss` — miss,payload `{source_url_hash}`
- 6 个 unit test:每种 event 至少 1 个触发用例 + retry 上限到达不再 emit + breaker 半开探测 emit 单条
- 现有 `analysis_returned` event 的 `upstream_latency_ms` + `upstream_attempts` 字段(P3-7 已加)保持兼容,不动
- `cascade_circuit_open` 在 60s 内同一 endpoint 最多 emit 1 次(避免风暴);用 `_last_circuit_emit_ts` 字典内存控

---

## 2. 实现指引

- emit 入口:`backend/src/agent/events.py:emit_event(event_type, payload, ...)` (已有);**不要**新开 channel
- 触发点:`analysis_service.py:_call_toprador` 内,在 retry / breaker / cache 已有的逻辑分支里加 emit 调用
- payload schema 用 `dataclass` 在 `analysis_service.py` 顶部声明,便于测试 import
- `source_url_hash` 用 `hashlib.sha1(url.encode()).hexdigest()[:12]` — 不要把原 URL 写入 events(PII 风险,与 P3-R1 `_strip_pii` 口径一致)

---

## 3. 边界(不在此票)

- **不引入** 任何外部 telemetry stack
- **不做** events 表 schema 改动(payload 都是 JSON blob 字段;已 P4-4 处理索引)
- **不做** 前端展示(P4-2 负责;两票独立可并行)
- 不动 P3-7 已有的 retry 策略 / breaker 阈值

---

## 4. Upstream dep

- ✅ P3-7 Toprador hardening
- ✅ P3-R1 `_strip_pii` 规约(用于 hash url 不泄敏)

P4-2 admin events 面板是 **downstream 消费方**(不阻塞,先后无关)。

---

## 5. 失败兜底

如果 events 表写入太频繁导致 cascade 主路径变慢(测试发现 `_call_toprador` p95 增加 > 10%) → 把 emit 改为 fire-and-forget(`asyncio.create_task(emit_event(...))`),避免阻塞主请求。

---

## 6. Output 清单

- `backend/src/agent/cascade/analysis_service.py`(emit 注入点)
- `backend/tests/test_cascade_observability.py`(新文件,6 cases)
- commit:`feat(P4-3): cascade observability events — retry/breaker/cache visibility`
