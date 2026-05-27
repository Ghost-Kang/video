# Codex handoff — Task E (P1-1 cascade/storage.py 拆 repo/service)

**Owner**: Codex
**Source**: `docs/nexus/architecture_review_2026-05-26.md` P1-1
**优先级**: 高(独立,可与 C 并行)
**Effort**: M (1-2 天,可分多 commit 渐进)
**Dependencies**: 无

---

## 0. 你做什么

`backend/src/agent/cascade/storage.py` 现在 528 LOC,塞了 5 个不相关的 DAO:
analyses / events / rewrites / toprador_cache / creators-aggregate。

问题(Architect P1-1):
1. 每个 entity 加新方法都翻 528 行
2. 每个调用都 "open conn + 1 query + commit + close",13×
3. `list_creators`(`storage.py:364-435`)做 cross-table 域逻辑,本不该住 DAO
4. retention policy(`_FAILURE_RETENTION_EVENTS`,`:286-326`)业务规则塞 DAO 里

你要**增量拆**:repo 按 entity 分,service 按域分,storage.py 收敛成 re-export shim
保向后兼容。

---

## 1. 目标文件树

```
backend/src/agent/cascade/
  persistence/
    __init__.py
    db.py                    # _connect, session context manager, schema bootstrap
    events_repo.py           # save_event, list_events, sum_generation_cost
    analyses_repo.py         # save_analysis, load_analysis, load_for_source
    rewrites_repo.py         # rewrite-related DAO
    toprador_cache_repo.py   # toprador_cache DAO
  services/
    __init__.py
    creators_service.py      # list_creators (composes events_repo + anchors_repo)
    retention.py             # retention_sweep + _FAILURE_RETENTION_EVENTS policy
  storage.py                 # ← 收敛成 re-export shim, ~30 LOC
```

---

## 2. 拆分顺序(必须严格按这个顺序,降低 blast radius)

### Step 1 · 抽出 `persistence/db.py`(0.5 commit)

把 `storage.py` 顶部的:
- `_connect()`
- schema 创建语句(`_init_schema` 之类)
- retention 表注册表

挪到 `persistence/db.py`。提供:
```python
@asynccontextmanager
async def session():
    """yield aiosqlite connection, 自动 commit + close。"""
    ...

async def bootstrap_schema():
    """startup 一次性建所有表 + index。"""
    ...
```

`storage.py` 顶部改为 `from .persistence.db import session, bootstrap_schema`。

**关键**:`bootstrap_schema()` 在 startup 调用一次,而不是每次 `_connect()` 内反复
执行 CREATE TABLE IF NOT EXISTS。把建表逻辑集中。

在 `agent/server.py` 的 `main()` 里加 `await bootstrap_schema()`(或在每个 repo 第一次
import 时 lazy bootstrap — 后者更兼容现有调用约定)。

### Step 2 · 抽 `events_repo.py`(调用点最多,先做这个验流程)

`storage.py` 里 `save_event`, `list_events`, `sum_generation_cost` 三个函数搬到
`persistence/events_repo.py`。

`storage.py` 加 re-export:
```python
from .persistence.events_repo import save_event, list_events, sum_generation_cost
```

确认全部 6 处调用点不需要改(import path 仍是 `from agent.cascade.storage import ...`)。

`tests/test_events_endpoint.py`, `test_events.py`, `test_events_index.py`, `test_events_retention.py` 全绿 → Step 2 done。

### Step 3 · 抽 `analyses_repo.py` + `rewrites_repo.py` + `toprador_cache_repo.py`

按同样模式,一个 commit 一个 entity。每个 repo 完成后 `pytest tests/test_analysis_service.py tests/test_rewrite.py tests/test_toprador_cache_persistence.py` 验证。

### Step 4 · 抽 `services/creators_service.py`

`list_creators`(`storage.py:364-435`)搬出。它现在写死了 4 个 event_name(`script_rewriten`,
`publish_pack_generated` 等);**保留写死**,Codex-G 任务统一改 StrEnum。

`services/creators_service.py` 内部 import `events_repo` + `anchors_repo`(后者已经在
`cascade/anchors.py`,需要 import path 调整或直接复用)。

`storage.py` re-export `list_creators` 兼容。

### Step 5 · 抽 `services/retention.py`

`_FAILURE_RETENTION_EVENTS` 常量 + retention_sweep 函数搬出。

### Step 6 · 收尾 `storage.py`

最终 `storage.py` 只剩 re-export:
```python
"""Back-compat re-exports. New code should import from persistence/ or services/."""
from .persistence.events_repo import save_event, list_events, sum_generation_cost
from .persistence.analyses_repo import save_analysis, load_analysis
from .persistence.rewrites_repo import ...
from .persistence.toprador_cache_repo import ...
from .services.creators_service import list_creators
from .services.retention import retention_sweep
```

目标:**≤ 50 LOC**。

---

## 3. 验收

**必过**:
1. `backend/src/agent/cascade/storage.py` ≤ 50 LOC
2. 全 backend pytest 通过(256 当前数,新拆分后不变):`uv run pytest`
3. 无导入循环(`uv run python -c "import agent.cascade.storage; import agent.cascade.persistence.events_repo; ..." ` 通过)
4. 现有所有调用点(`grep -rn "from agent.cascade.storage import" backend/src` 应该都不需要改)

**优秀**:
- 每个 entity 拆成独立 commit(reviewer 容易看)
- 给 `persistence/__init__.py` 加 docstring 说明这是 DAO 层、不要写业务逻辑

---

## 4. 不要碰

- **`backend/src/agent/cascade/contract.py`** — Architect 标了红线:cascade ACL 核心,不许动
- **`backend/src/agent/cascade/failures.py`** — 同上
- **`backend/src/agent/cascade/events.py`** — 单写路径,不要把验证逻辑挪到 repo 层(repo 只持久化,不验证)
- **事件名字符串** — Codex-G 任务负责换 StrEnum,你这里保持写死

---

## 5. 坑 / 决策

- **同步 sqlite3 vs aiosqlite**:`storage.py` 现在用 `aiosqlite`,`tools/canvas.py` 用 sync `sqlite3`。**只动 storage.py 这条线**(aiosqlite),不要触碰 canvas.py(Architect followup,不在你 scope)
- **schema bootstrap 时机**:如果选 lazy(每个 repo 首次 import 时 ensure),要小心 race。最干净是 startup 一次性。Founder 决策:**startup 一次,在 `server.main()` 里加 await**。
- **测试 fixtures**:如果某个 test 直接 `_connect()` 拼 SQL,改成用 `session()` context manager。`tests/test_events_retention.py` 可能有这种 case,谨慎。

---

## 6. 提交规范

- 5+ commits 渐进(每个 Step 一个,Step 1 单独一个 commit)
- Commit msg 前缀:`refactor(backend): Codex-E.${step} ...`
