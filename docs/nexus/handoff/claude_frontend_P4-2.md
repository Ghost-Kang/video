# Claude handoff — P4-2 admin events firehose 面板

**Owner**: Claude session (frontend line)
**Source of truth**: `claude_frontend_P3-3.md` (admin layout)、`backend/src/agent/events.py`
**Status**: DRAFT · no upstream blocker (可直接起跑)
**Time budget**: 1.5 days
**Allocation**: `PM_W4_allocation.md §3.1`

---

## 0. 背景

P3-3 已有 `/admin/creators` 页 + 后端 `/api/creators` 聚合。但 founder 现在调试 cascade、consent、Toprador 等组件时,没有一个统一的 "事件直播流" 入口 — 只能进 SQLite 看 raw 表。

P4-2 新增 `/admin/events` 页,以及配套 `/api/events` 端点,直出最近 200 条 events,前端按 `event_type` / `phase` / `user_id` 过滤。也是 P4-3 cascade observability counters 落地后的可视化承接面。

---

## 1. Done-signal

- 后端:`GET /api/events?limit=200&type=*&user_id=*&phase=*` 返回数组
- 前端:`/admin/events` 页存在;表格反向时间序展示 events,顶上 3 个 filter(type / phase / user_id);右上角 "refresh" 按钮(不强制做 SSE / WebSocket — 手动刷新 + 30s 自动 refresh 即可)
- 3 个 vitest 用例:filter 一项 / paging 第二页 / refresh 触发新数据
- 手动 smoke:在另一个 tab fire 一条 `consent_accepted` event(走 P3-R3 ConsentGate 点同意),`/admin/events` 上能在下次 refresh 看到该事件

---

## 2. 接口契约

```ts
// GET /api/events
{
  events: Array<{
    id: number,
    ts: string,             // ISO 8601
    event_type: string,
    phase: string | null,
    user_id: string | null,
    thread_id: string | null,
    payload: Record<string, unknown>
  }>,
  has_more: boolean,
  next_offset: number | null
}
```

QueryString:
- `limit`(default 200, max 1000)
- `offset`(default 0)
- `type`(可选,exact match)
- `phase`(可选,exact match)
- `user_id`(可选,exact match)
- `since_ts`(可选,ISO 8601,过滤 ts > since_ts)

---

## 3. 边界(不在此票)

- **不做** event 写入(只读)
- **不做** 实时推送(SSE / WS),只 30s polling
- **不做** event detail modal — 复杂 payload 用前端 `<pre>` JSON 展示就够了
- **不做** RBAC / auth gate(Phase 1 内测仍 admin-only,assume 已被 reverse-proxy 拦截)

---

## 4. Upstream dep

- P3-3 admin layout(✅ done)
- P3-R3 consent gate(✅ done)— 产出 smoke 的事件
- P4-3 cascade observability events(并行,不阻塞)
- P4-4 events 表索引(并行,不阻塞;若不上索引,200 条 LIMIT 内仍可接受)

---

## 5. 失败兜底

如果 SQLite `events` 表行数超过 100k 后 `/api/events` 不带 `since_ts` 慢于 500ms → 切到 P4-4 索引上线后再 ship。本票仍可在 dev/数据小情形下闭环。

---

## 6. Output 清单

- `backend/src/agent/api/events.py`(新文件)+ `routes.py` 注册
- `frontend/src/pages/admin/EventsPage.tsx`(新文件)
- `frontend/src/hooks/useEvents.ts`(新文件)
- `frontend/src/__tests__/EventsPage.test.tsx`(新)
- commit:`feat(P4-2): admin events firehose — /admin/events + /api/events`
