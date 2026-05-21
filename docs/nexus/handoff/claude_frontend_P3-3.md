# Claude handoff — P3-3 admin creator onboarding view

**Owner**: Claude session (backend + frontend; cross-stack)
**Source of truth**: `PM_W3_allocation.md §3.3` · `02_event_spec.md` (event names) · `01_phase1_requirements.md` (creator concierge flow)
**Status**: ships unblocked; **becomes load-bearing** only after creator #1 onboarded (founder action)
**Time budget**: 1.5 days (0.5 backend + 1 frontend)

---

## 0. What you build

A `/admin/creators` page that lists every distinct `user_id` that has produced cascade events, with status flags + aggregated counters. Lets the founder see at a glance: "creator A 注册了但 0 条 run / creator B 跑过 1 条但没拿 publish pack / creator C 已经在反复用 anchors". It's the operational view for concierge onboarding.

This is one admin view, not a sprawling dashboard. Read-only. No auth gate in v1 — protected by being at an unguessable URL until P3 auth ticket later.

---

## 1. Files

### Backend (P3-3a)

| Path | Purpose |
|---|---|
| `backend/src/agent/cascade/storage.py` | New `list_creators()` async function — aggregates from events + anchors |
| `backend/src/agent/server.py` | `GET /api/creators` route |
| `backend/tests/test_creators_endpoint.py` | Aggregation correctness tests |

### Frontend (P3-3b)

| Path | Purpose |
|---|---|
| `frontend/src/lib/creatorsApi.ts` | `listCreators()` + `Creator` type + mock fallback |
| `frontend/src/hooks/useCreators.ts` | Fetch wrapper + derived counters |
| `frontend/src/pages/AdminCreators.tsx` | Top-level page (table + filters) |
| `frontend/src/components/admin/CreatorRow.tsx` | One-row component (compact) |
| `frontend/src/components/admin/CreatorStatusBadge.tsx` | invited / runs<1 / runs≥1 / multi-run badges |
| `frontend/src/components/admin/__tests__/CreatorRow.test.tsx` | Render + status logic tests |
| `frontend/src/hooks/__tests__/useCreators.test.ts` | Aggregation tests (mocked fetch) |
| `frontend/src/main.tsx` (modified) | `/admin/creators` route |

---

## 2. Backend contract (`GET /api/creators`)

Response shape:

```json
{
  "creators": [
    {
      "user_id": "u_xxxxx",
      "first_seen": "2026-05-20T08:00:00Z",
      "last_seen": "2026-05-21T12:30:00Z",
      "runs_started": 3,
      "rewrites_completed": 2,
      "publish_packs_copied": 0,
      "anchors_count": 1,
      "anchors_total_reuse_count": 0,
      "interview_logged": false
    }
  ]
}
```

Aggregation queries (one transaction):
- `SELECT DISTINCT user_id, MIN(created_at), MAX(created_at) FROM events GROUP BY user_id` — basic identity + activity window
- `SELECT user_id, COUNT(*) FROM events WHERE event_name='run_started' GROUP BY user_id` — runs_started
- `SELECT user_id, COUNT(*) FROM events WHERE event_name='script_rewritten' GROUP BY user_id` — rewrites_completed
- `SELECT user_id, COUNT(*) FROM events WHERE event_name='publish_pack_copied' GROUP BY user_id` — publish_packs_copied
- `SELECT user_id, COUNT(*), SUM(reuse_count) FROM anchors GROUP BY user_id` — anchors_count + total reuse
- `SELECT DISTINCT user_id FROM events WHERE event_name='interview_logged'` — interview_logged boolean

Single pass: zip results in Python by user_id.

Sort by `last_seen DESC` so the most active creators come first.

**404 / error path**: empty list if DB doesn't exist or events table empty. No HardFailure mapping needed — read-only endpoint.

---

## 3. Status derivation (frontend, not backend)

`CreatorStatusBadge` computes from the aggregates:

| Badge | Condition |
|---|---|
| `已邀请` | first_seen exists, runs_started = 0 |
| `已注册` | runs_started ≥ 1, rewrites_completed = 0 |
| `已改写` | rewrites_completed ≥ 1, publish_packs_copied = 0 |
| `已发布` | publish_packs_copied ≥ 1, anchors_total_reuse_count = 0 |
| `循环复用` | anchors_total_reuse_count ≥ 1 (the H8 success state) |
| `已访谈` | interview_logged = true (orthogonal flag, shown alongside) |

Computed client-side so backend stays generic.

---

## 4. Page layout

Single-page table view:

1. **Header**: "Creator 看板 · 共 N 人" + 刷新按钮 + "导出 CSV" (P4, ghosted in v1)
2. **Filter row**: search by user_id + status filter pills (全部 / 已邀请 / 已改写 / 循环复用 etc.)
3. **Table** (sticky header):
   - user_id (monospace, truncated to first 12 chars + tooltip)
   - 最近活动 (relative time: "3 小时前" / "2 天前")
   - 已运行 (runs_started)
   - 已改写 (rewrites_completed)
   - 已发布 (publish_packs_copied)
   - 素材 (anchors_count · 总复用 X)
   - 状态 (status badge)
   - 操作 (→ link to /chat/<thread_id> — but we don't store thread mapping yet; v1 omits this column)
4. **Empty state**: "还没有 creator 数据 — 让首批 creator 体验后再回来"

---

## 5. Tests

### Backend `test_creators_endpoint.py`

1. Empty DB → empty list
2. Single user with 3 run_started events → runs_started=3, rewrites=0, anchors=0
3. Two users isolated (multi-user aggregation correctness)
4. Anchor with reuse_count > 0 surfaces in `anchors_total_reuse_count`
5. `interview_logged` event flips boolean true
6. Sort order: most recent `last_seen` first
7. Event payload tolerates malformed JSON (ignores; doesn't crash)

### Frontend `useCreators.test.ts`

1. Fetches and exposes 0-row state cleanly
2. Sorts by last_seen DESC
3. Filters by user_id substring
4. Status derivation correct for each ladder rung (邀请→注册→改写→发布→循环)

### Frontend `CreatorRow.test.tsx`

1. Renders all aggregate columns
2. Shows correct badge for each status
3. Truncates long user_ids with tooltip

---

## 6. Acceptance verification

Backend:
- `cd backend && uv run pytest tests/test_creators_endpoint.py -q` — all green
- `grep -c "/api/creators" backend/src/agent/server.py` ≥ 1

Frontend:
- `cd frontend && npm run build` clean
- `cd frontend && npm run test` all green (+ ≥ 8 new cases)
- `cd frontend && npm run lint` clean
- `npm run dev` → open `/admin/creators` → mock data renders rows

---

## 7. Done-signal

- `/api/creators` route registered + tested
- `/admin/creators` route registered + page renders
- 8+ new tests across backend + frontend
- Screenshot in PR

---

## 8. NOT in this ticket

- Auth gate (P4 if needed; admin URL is unguessable enough for v1)
- Drill-down to a creator's runs / threads (needs thread→user mapping; backend follow-up)
- CSV export (P4)
- Real-time updates / websocket
- Editing creator info — read-only only
- Concierge note-taking interface (separate ticket; founder log is fine for now)

---

## 9. PM notes

- Founder uses this page during concierge onboarding (creator #1-3 in W3-W5). The page becomes load-bearing exactly when creator #1 starts using the product.
- The status ladder (邀请→注册→改写→发布→循环) maps to the H8 moat thesis funnel. When founder sees the first `循环复用` badge, that's the first proof point.
- Future iteration: add a sparkline of run_started per day per user as a small 7-day chart in each row. Defer to a P4 polish ticket.
