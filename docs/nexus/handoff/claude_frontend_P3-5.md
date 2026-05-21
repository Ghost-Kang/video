# Claude handoff — P3-5 anchor reuse analytics page

**Owner**: Claude session (frontend)
**Source of truth**: `PM_W3_allocation.md §3.3` · existing `/api/anchors` from P1-6 · `01_reviewer_synthesis.md §5` (H8 moat measurement)
**Status**: unblocked — uses only the W1-shipped anchors API
**Time budget**: 1 day

---

## 0. What you build

A read-only analytics page at `/analytics/anchors` that visualizes the H8 learning-loop signal: how often each user's "你之前用过的" anchor actually gets dragged into a new run.

This is the founder's first data look at whether the cascade workstream's moat thesis (anchor reuse drives compounding value per creator) is actually holding up. The page must work today against the existing API surface — no backend changes.

---

## 1. Files

| Path | Purpose |
|---|---|
| `frontend/src/pages/AnchorAnalytics.tsx` | Top-level analytics page component |
| `frontend/src/hooks/useAnchorAnalytics.ts` | Fetches + aggregates anchors data |
| `frontend/src/components/analytics/StatCard.tsx` | Reusable big-number card |
| `frontend/src/components/analytics/AnchorBarChart.tsx` | CSS-only horizontal bar chart for top N anchors by reuse_count |
| `frontend/src/components/analytics/__tests__/AnchorBarChart.test.tsx` | Render + sort + truncate tests |
| `frontend/src/hooks/__tests__/useAnchorAnalytics.test.ts` | Aggregation math tests |
| `frontend/src/App.tsx` (modified) | Add `/analytics/anchors` route |

---

## 2. Behavior requirements

### 2.1 Data sources

Use the existing `/api/anchors?user_id=...` and `/api/anchors?user_id=...&kind=...` endpoints (W1-shipped). Concatenate character + scene results. No new backend endpoint required.

The hook fetches once on mount and exposes:

```ts
interface AnchorAnalytics {
  totalAnchors: number;
  totalReuses: number;          // sum of reuse_count across all
  avgReuseCount: number;        // mean
  maxReuseCount: number;
  ratioCharacterToScene: number;
  oldestAnchorDays: number;
  topByReuse: Anchor[];         // top 5 sorted reuse_count DESC
  distribution: Record<number, number>;  // {reuse_count: anchor_count} histogram
  byKind: { character: AnchorAggregate; scene: AnchorAggregate };
  isLoading: boolean;
  refresh: () => Promise<void>;
}
```

### 2.2 Layout

Single column, 6 sections:

1. **Page header** — "你的素材复用看板" + last-refreshed timestamp + refresh button
2. **Stat row** — 4 StatCards: total anchors / total reuses / avg reuses per anchor / max reuses on one anchor
3. **Bar chart** — top 5 anchors sorted by reuse_count, horizontal CSS bars (no chart library); each bar shows label + reuse_count + image thumbnail
4. **Histogram** — small vertical bars showing how many anchors have N reuses, N=0..max (binned if max > 10)
5. **By-kind breakdown** — character vs scene, counts + reuse rates side by side
6. **Empty state** — if `totalAnchors === 0`: friendly "还没有素材,先在画布里创建一些试试"

No charts library. Tailwind utility classes only.

### 2.3 Sort + filter

- Default: top 5 by reuse_count DESC
- Toggle pills "全部 / 角色 / 场景" filters the bar chart (not the headline stats)
- Sort is fixed (reuse_count DESC) — no toggle needed

### 2.4 Routing

`/analytics/anchors` requires no auth gate in this iteration (P3-3 admin gate is a separate ticket). Just add the route in `App.tsx` alongside Landing.

If you don't have user_id in URL or store, default to `"default"` (matches the backend default).

---

## 3. Tests (vitest)

### `useAnchorAnalytics.test.ts`

1. Empty `/api/anchors` response → `totalAnchors=0`, `totalReuses=0`, `topByReuse=[]`
2. 3 anchors with reuse_counts [5, 2, 0] → totalReuses=7, avgReuseCount≈2.33, maxReuseCount=5
3. Histogram correct for [0, 0, 1, 1, 3, 5]
4. By-kind split: 2 character + 1 scene → both buckets correctly populated
5. ratioCharacterToScene returns Infinity when no scenes, 0 when no characters

### `AnchorBarChart.test.tsx`

1. Renders top N bars
2. Bars sorted reuse_count DESC
3. Bars truncated to maxItems (default 5)
4. Empty list renders empty state
5. Image fallback when image_url empty

### Optional component test

- `AnchorAnalytics.test.tsx` — page renders with mock anchors, refresh button calls refresh, kind toggle filters bar chart

---

## 4. Acceptance verification (frontend bar per `03_routing.md §0.1`)

1. `cd frontend && npm run build` — clean, tsc 0 errors
2. `cd frontend && npm run test` — all green; new tests ≥ 8 cases
3. `cd frontend && npm run lint` — clean
4. `cd frontend && npm run dev` — open `/analytics/anchors`, verify mock data renders (mocked anchors are baked into `lib/anchorApi.ts`)
5. Screenshot in PR (page rendered with mock data)
6. Empty-state path verified by temporarily clearing mock list

---

## 5. Done-signal

- `find frontend/src/pages/AnchorAnalytics.tsx frontend/src/hooks/useAnchorAnalytics.ts | wc -l` = 2
- `npm run build` exit 0
- `npm run test` shows total + new cases pass
- `npm run lint` exit 0
- App.tsx contains route for `/analytics/anchors`

---

## 6. NOT in this ticket

- Backend `/api/anchors/stats` aggregation endpoint (P3 follow-up if performance demands)
- `days_since_last_reuse` per anchor (needs `/api/anchors/<id>/reuses` endpoint; P3 backend follow-up)
- Real-time updates / websocket subscription
- Per-creator drill-down (P3-3 admin view's job)
- Export / CSV download (P4 if founder asks)
- Authentication gate (P3-3)

---

## 7. PM notes

- This page is the founder's first numeric look at H8 reuse signal. Founder should review it after creator #1 onboarded to validate "reuse compounds value" thesis
- Visual quality is more important than depth — keep layout calm and confident, not noisy with 10 charts
- All cascade workstream pages should feel cohesive; reuse `AnchorCard.tsx` styling vocabulary (stone-200 borders, stone-50 hover, rounded-xl) where applicable
