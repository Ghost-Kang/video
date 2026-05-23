# Codex handoff — P4-6 Toprador cache 跨进程持久化

**Owner**: Codex session (backend)
**Source of truth**: `backend/src/agent/cascade/analysis_service.py` (`_TOPRADOR_CACHE` in-memory 字典,P3-7 + P4-3 增强);`backend/src/agent/cascade/storage.py` (SQLite 持久化范式)
**Status**: READY · no upstream blocker
**Time budget**: 1 day
**Allocation**: PM_W4_allocation.md §3.2(W3D3 新加)

---

## 0. 背景

`_TOPRADOR_CACHE` 当前是 module-level dict,TTL 60s。**问题**:
1. 进程重启即清空 → 重启后真实流量第一次命中全是 cache_miss
2. 多 worker 部署时各 worker 独立 cache,命中率下降到 1/N
3. P4-3 加的 `cascade_cache_hit/miss` 事件无法反映"理论应命中但物理上不能命中"

P4-6 把 in-memory 字典升级为 SQLite 持久化层,沿用现有 storage.py 模式。**不引入 Redis / Memcached**,保持单进程 + SQLite 的 Phase 1 简洁度。

---

## 1. Done-signal

- 新增 `backend/src/agent/cascade/storage.py:save_toprador_cache(source_url_hash, payload, ttl_s)` + `load_toprador_cache(source_url_hash) → dict | None`
- 新增表 `toprador_cache`(`source_url_hash PK, payload_json, expires_at`)+ `CREATE INDEX IF NOT EXISTS idx_toprador_cache_expires ON toprador_cache(expires_at)` (用于清理)
- `analysis_service.py:_call_toprador` 入口处:先查 SQLite cache,命中且未过期则返回 + emit `cascade_cache_hit`;miss 则正常调用 + 调用成功后 `save_toprador_cache`
- 移除 `_TOPRADOR_CACHE` module-level 字典(纯 SQLite 后退)
- `cascade_cache_hit` payload 增加 `cache_layer: "sqlite"` 字段(为后续 Redis 升级留扩展位)
- 新增 `cleanup_expired_toprador_cache()` 函数,每次 hit/miss 时机会性清理 < 现在的 entry(避免长期堆积);可选 cron 路由
- 5 个 unit test:save 后 load 返回原 payload / 过期后 load 返回 None / 跨进程重启模拟(close db → reopen → load 仍命中)/ 清理过期 entry 不动未过期 / hash 不同的两条 entry 隔离

---

## 2. 实现指引

### 2.1 Schema

```sql
CREATE TABLE IF NOT EXISTS toprador_cache (
  source_url_hash TEXT PRIMARY KEY,
  payload_json    TEXT NOT NULL,
  expires_at      TEXT NOT NULL  -- ISO 8601 UTC,字符串排序与时间序一致
);
CREATE INDEX IF NOT EXISTS idx_toprador_cache_expires ON toprador_cache(expires_at);
```

### 2.2 storage.py 新增函数

```python
async def save_toprador_cache(
    source_url_hash: str, payload: dict[str, Any], ttl_s: float,
) -> None:
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_s)).isoformat()
    # INSERT OR REPLACE on PK → idempotent
    ...

async def load_toprador_cache(source_url_hash: str) -> dict[str, Any] | None:
    # SELECT WHERE hash = ? AND expires_at > now;返回 None 若 miss 或 expired
    ...

async def cleanup_expired_toprador_cache() -> int:
    # DELETE WHERE expires_at <= now;返回删除行数
    ...
```

### 2.3 analysis_service.py 改造

把现有 `_TOPRADOR_CACHE` 字典代码块替换为 await SQLite 查询。**P4-3 的 emit_cache_hit / emit_cache_miss 调用点保持不变**,只是数据来源变了。

### 2.4 PII 口径

`source_url_hash` 仍走 `_hash_source_url(url)` = `sha1[:12]`,保持与 P4-3 一致 + P3-R1 PII 脱敏口径。原 URL 仍不入库。

---

## 3. 边界(不在此票)

- **不引入** Redis / Memcached / 外部 KV
- **不做** distributed cache invalidation(单进程 OK)
- **不动** TTL 默认值(仍 60s,沿用 `_TOPRADOR_CACHE_TTL_S`)
- **不做** cache warmup / preloading
- **不动** P4-3 emit 路径(cache_hit/miss 事件 schema 仅加 cache_layer 字段)
- **不做** 自动 cron 清理任务(可选 cron 路由是后续,P4-6 只产函数)

---

## 4. Upstream dep

- ✅ P3-7 Toprador hardening(retry / breaker)
- ✅ P4-3 cascade observability events(emit hooks 已就位)

无 blocker。

---

## 5. 失败兜底

- 若 SQLite 在高并发 cache hit 下成为瓶颈(预期不会,Phase 1 体量 < 100 req/min)→ 切回 in-memory 字典 + 加 WAL mode
- 若 hash 碰撞(sha1[:12] 理论碰撞概率 ~2^-48,实际 Phase 1 url 集合 < 1000,可忽略)→ 改 hash 长度到 16

---

## 6. Output 清单

- `backend/src/agent/cascade/storage.py`(+ 3 函数 + 1 table)
- `backend/src/agent/cascade/analysis_service.py`(替换 _TOPRADOR_CACHE 字典代码块)
- `backend/tests/test_toprador_cache_persistence.py`(新文件,5 cases)
- commit:`feat(P4-6): persist Toprador cache to SQLite — survives restarts`
