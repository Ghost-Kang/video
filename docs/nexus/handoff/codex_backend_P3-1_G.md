# Codex handoff — Task G (P3-1 事件名 → StrEnum)

**Owner**: Codex
**Source**: `docs/nexus/architecture_review_2026-05-26.md` P3-1
**优先级**: 低(可放 cycle 末尾)
**Effort**: S (1-2 小时)
**Dependencies**: 建议在 **Codex-E 完成后做**(那时 events_repo 已分出,改起来更清晰)

---

## 0. 你做什么

事件名(`script_rewriten`, `publish_pack_generated`, `generation_cost`, …)现在
在三个地方重复写死:
- `backend/src/agent/cascade/events.py` 里的 `ALLOWED_EVENTS` 集合(canonical 源)
- `backend/src/agent/cascade/storage.py:335` 和 `:398-424` 里写死的 string literal(用作 SQL 查询过滤)
- `backend/src/agent/cascade/analysis_service.py` 里 `emit("script_rewriten", ...)` 调用

一个 typo (`script_rewriten` vs `script_rewritten`) → 数据静默丢失,没有任何编译/运行时报错。

你要:把事件名晋升到 `StrEnum`,所有 import,grep 后保证没有裸字符串。

---

## 1. 新文件

```python
# backend/src/agent/cascade/event_names.py
from enum import StrEnum


class EventName(StrEnum):
    """All canonical event names. Single source of truth.

    新增事件必须:
    1. 加到本 Enum
    2. (如有 schema)在 events.py ALLOWED_EVENTS 同步注册
    """

    SCRIPT_REWRITTEN = "script_rewriten"  # 保留历史拼写(已写入 DB,不要改);新事件请正确拼写
    PUBLISH_PACK_GENERATED = "publish_pack_generated"
    GENERATION_COST = "generation_cost"
    RUN_STARTED = "run_started"
    # ... 完整列表见 events.py ALLOWED_EVENTS
```

**关键**:**保留历史拼写错误**(`script_rewriten`)— 数据库里已经写了带拼错的事件,
改正会让历史数据失踪。Enum 名用正确拼写 (`SCRIPT_REWRITTEN`),value 保留 typo。
加个 comment 说明。

---

## 2. 替换调用点

`grep -rn 'event_name\s*==\s*['"'"'"]\|event_name=['"'"'"]\|emit(['"'"'"]' backend/src/agent/cascade backend/src/agent/transport backend/src/agent/workers`

把每处裸字符串改成 `EventName.XXX`(或 `EventName.XXX.value`,如果需要 str type)。

主要文件:
- `cascade/events.py` — `ALLOWED_EVENTS` 改用 Enum 构建
- `cascade/storage.py`(或 Codex-E 之后的 `persistence/events_repo.py`) — SQL 参数用 `EventName.X.value`
- `cascade/analysis_service.py` — `emit(EventName.SCRIPT_REWRITTEN, ...)`
- `cascade/rewrite_service.py` — 同上
- `transport/http_router.py` — `emit("generation_cost", ...)` 已经在 Claude-A 写进去
- `tools/canvas.py` 如果有 emit

不能改的地方:
- `tests/` 里硬编码事件名作为断言数据 — **保留字符串**,test 是验证 wire format 不变,
  不应该跟实现耦合

---

## 3. 验收

**必过**:
1. `cascade/event_names.py` 存在,EventName 包含所有 events.py `ALLOWED_EVENTS` 项
2. `grep -rn "event_name\s*=\s*['"'"'"]" backend/src/agent/cascade` ≤ 1 处(允许 events.py 内构建 Enum 的部分保留 string literal)
3. `grep -rn 'emit(['"'"'"]' backend/src/agent/{cascade,transport,workers}` = 0 处
4. backend pytest 全绿(256)
5. `EventName.SCRIPT_REWRITTEN.value == "script_rewriten"` 保留 typo(单测断言)

---

## 4. 不要碰

- DB 里已有的事件 row(不要做 migration 改 `script_rewriten` → `script_rewritten`)
- tests 内硬编码的事件名字符串(test 验 wire format,不应跟随实现迁移)

---

## 5. 提交规范

- 单 commit:`refactor(backend): Codex-G event names → StrEnum`
- 在 commit body 说明保留 `script_rewriten` typo 的原因
