# Codex handoff — W5D2 可观测性 backend infra 半边

**Owner**: Codex
**Source**: PM W5D2 cycle · founder 已上线 `https://cascade.herwin.top`
**Date**: 2026-05-28
**优先级**: 🔴 高(P0 部署完了用户开始用,日志会写满磁盘 + 没 health endpoint)
**Effort**: M (2-3h)
**Dependencies**: 无 — 跟 Claude lane (C/E backend) 文件不冲突,跟 Cursor lane (前端) 不冲突

---

## 0. 你做什么

3 件 backend infra 类工作,纯独立模块,跟其他 owner 不打架:

1. **A — docker-compose 日志切片**
2. **D — `/api/health/summary` HTTP endpoint**
3. **附赠 — SQLite vacuum cron** (events.db 长期增长,周末 vacuum)

---

## 1. 任务 A — Docker log rotation

### 目标
当前 `docker compose` 默认 json-file 日志驱动,**无 size cap**,几周后会写满 80G 磁盘。

### 实施
`docker-compose.yml` 给 backend + frontend service 各加 logging block:

```yaml
services:
  backend:
    # ...existing fields...
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
        compress: "true"

  frontend:
    # ...existing fields...
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        compress: "true"
```

### 部署
本机改完后还得 push 到 `/opt/cascade/docker-compose.yml`,然后 `docker compose up -d` (compose 检测到 logging 变更会 recreate container)。

注意:**Claude 同时在改 docker-compose.yml** 加 backup volume 或其他 — 你们俩用 git rebase 解决,或 Claude 先合,你 rebase 顶。

### 验收
- `docker inspect cascade-backend | grep -A4 LogConfig` 输出 max-size=10m max-file=5
- 跑 5min 后看 `/var/lib/docker/containers/<id>/*.log*` 文件数

---

## 2. 任务 D — `/api/health/summary` GET endpoint

### 目标
Frontend `/admin/health` 看板要靠这个 endpoint 拿数据。Cursor lane 在做前端,签好契约 ASAP。

### Spec (跟 Cursor 已经协调过的 shape)

```json
GET /api/health/summary
→ 200 OK
{
  "server": {
    "cpu_percent": 12.4,
    "mem_used_mb": 1230,
    "mem_total_mb": 3300,
    "disk_used_gb": 8.2,
    "disk_total_gb": 59,
    "uptime_seconds": 45623
  },
  "events_5min": {
    "total": 47,
    "by_type": {
      "analysis_returned": 12,
      "script_rewritten": 8,
      "failure_emitted": 1,
      "...": ...
    }
  },
  "upstream_success_rate": {
    "analysis_returned": 0.94,
    "script_rewritten": 1.0
  },
  "recent_failures": [
    {
      "id": 76,
      "ts": "2026-05-28T08:11:43Z",
      "event_name": "failure_emitted",
      "user_id": "anon-xxx",
      "payload": {"failure_code": "S5_INVALID_PAYLOAD", "stage": "analysis"}
    }
    // up to 10
  ]
}
```

### 实施细节

文件: `backend/src/agent/transport/http_router.py`(新 route)
- Add path `("GET", "/api/health/summary"): handle_health_summary`
- `handle_health_summary(qs, body)` 实现:
  - **server**: `psutil.cpu_percent(interval=0.5)`, `psutil.virtual_memory()`, `shutil.disk_usage("/")`, `time.monotonic() - SERVER_START_TIME`
  - 但 **psutil 未在 deps 里!** 你需要在 `pyproject.toml` 加 `psutil>=6.0` + `uv lock` + 重 build。或者用 `/proc/stat`、`/proc/meminfo`、`os.statvfs("/")` 纯 stdlib 实现 (推荐这条,不引依赖)。
  - **events_5min**: 直接 sqlite query `events` 表, `where ts > datetime('now', '-5 minutes')` group by event_name
  - **upstream_success_rate**: 过去 1h `analysis_requested` vs `analysis_returned` 比例; `rewrite_requested` vs `script_rewritten`
  - **recent_failures**: `select * from events where event_name='failure_emitted' order by id desc limit 10`

实现位置参考 `backend/src/agent/cascade/storage.py` 的现有 events query helper,复用 `_connect()` async sqlite cursor pattern。

### 测试
- `backend/tests/transport/test_health_summary.py` (新)
- 至少 3 个测试:
  - happy path: 表非空时返回所有 4 段
  - empty events table: events_5min.total = 0, upstream_success_rate 是 null 或 1.0
  - server section: 不 mock psutil/proc, 测真实返回的字段类型 (mem_total_mb > 0 等)

### 部署
跟 A 一起 push 到服务器, `docker compose build backend && up -d`。

### 验收
- `curl https://cascade.herwin.top/api/health/summary | jq .server` 返回 cpu_percent 等 6 个字段
- Cursor 的 AdminHealth 前端能渲染

---

## 3. 附赠 — SQLite vacuum cron (P1, 可选)

### 目标
events.db 几个月后会膨胀 (delete 不实际回收空间)。每周日 03:30 跑一次 VACUUM。

### 实施

新文件: `scripts/ops/vacuum_sqlite.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
DATA_DIR="${1:-/opt/cascade/data}"
for db in events.db canvas.db checkpoints.db messages.db; do
  src="$DATA_DIR/$db"
  [ -f "$src" ] || continue
  before=$(stat -c %s "$src")
  sqlite3 "$src" "VACUUM;"
  after=$(stat -c %s "$src")
  echo "[ok] $db: ${before} → ${after} bytes (saved $((before - after)))"
done
```

`chmod +x scripts/ops/vacuum_sqlite.sh`

### 部署 cron
```bash
ssh ubuntu@119.29.18.216 'crontab -l 2>/dev/null > /tmp/c; echo "30 3 * * 0 /opt/cascade/scripts/ops/vacuum_sqlite.sh /opt/cascade/data >> /var/log/cascade-vacuum.log 2>&1" >> /tmp/c; sort -u /tmp/c | crontab -; crontab -l | grep vacuum'
```

### 验收
- crontab -l 包含 vacuum 行
- 手动跑一次: `bash scripts/ops/vacuum_sqlite.sh /opt/cascade/data` 输出 saved bytes

---

## 4. 提交 + 部署

3 件事独立 commit,顺序提交:

```
git commit: "chore(deploy): docker-compose json-file log rotation (max 50MB/svc)"
git commit: "feat(backend): /api/health/summary endpoint for /admin/health"
git commit: "chore(ops): weekly sqlite VACUUM cron"
```

Push 到 `gk/main`。

部署到服务器:
```bash
# 1. 服务器 git pull / scp 改动文件
ssh ubuntu@119.29.18.216 'cd /opt/cascade && git pull gk main 2>/dev/null'
# 如果服务器没 git remote 配,改用 scp:
scp backend/src/agent/transport/http_router.py ubuntu@...:/opt/cascade/backend/src/...
scp docker-compose.yml ubuntu@...:/opt/cascade/
scp scripts/ops/vacuum_sqlite.sh ubuntu@...:/opt/cascade/scripts/ops/

# 2. backend 重 build (D 引入新代码)
ssh ubuntu@... 'cd /opt/cascade && sudo docker compose build backend && sudo docker compose up -d backend'

# 3. 验证
curl https://cascade.herwin.top/api/health/summary | jq .server
```

---

## 5. 边界 / 禁区

- **不动 `backend/src/agent/transport/agent_runner.py`** — Claude lane (C: uncaught_exception → events.db) 改这个
- **不动 `backend/src/agent/transport/ws_messages.py`** — Claude lane (E: ClientErrorMsg Pydantic 模型) 改这个
- **不动 `backend/src/agent/transport/http_router.py` 已有的 routes** — 你只**追加**新 `("GET", "/api/health/summary")` 路由项,不动 `/api/client_error` (Claude 会加,你只看注释跳过)
- **不动 frontend** — Cursor lane 全部
- **不引入 psutil** — 用 stdlib /proc 实现避免 deps 膨胀 + 镜像变大

---

## 6. 验收 checklist

- [ ] docker-compose.yml 加 logging block 两处
- [ ] `/api/health/summary` 返回完整 4 段 JSON
- [ ] backend pytest 全绿 (baseline 501 passed → ≥504)
- [ ] cron 加 vacuum 行
- [ ] 3 个 commit push 到 gk/main
- [ ] 服务器 `curl https://cascade.herwin.top/api/health/summary` 200 OK

---

**Owner sign-off**: Codex
**Estimated**: 2-3h
