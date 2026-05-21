# Claude handoff — P2-5 anchor sidebar visual polish

**Owner**: Claude session (re-routed from Cursor per `03_routing.md §0.1`, 2026-05-21)
**Source of truth**: `PM_W2_allocation.md §3.3` · existing W1 deliverable in `frontend/src/components/anchors/`
**Status**: ready when Claude picks it up; not blocked
**Time budget**: 1.5 days

---

## 0. What you build

W1 shipped a functional anchor sidebar (P1-6 frontend, Cursor's brief — see `handoff/cursor_frontend_P1-6.md`). It works but UX is rough: drag-drop occasionally lags, reuse_count is not visible per anchor card, and sort order is hard-coded. P2-5 polishes those three things without changing the underlying contract.

This is the **first frontend ticket Claude owns post-routing-change**. Treat the verification bar slightly higher than usual since Claude doesn't have Cursor's hot-reload muscle memory — run the dev server, click through the actual flow, and screenshot evidence in the PR.

---

## 1. Files

| Path | Change |
|---|---|
| `frontend/src/components/anchors/AnchorSidebar.tsx` | Add sort toggle (reuse_count DESC / created_at DESC), make container `position: sticky` per Brand Guardian sidebar pattern |
| `frontend/src/components/anchors/AnchorCard.tsx` | Surface `reuse_count` as a small pill in the top-right of each card; tooltip "已用 N 次" |
| `frontend/src/components/anchors/AnchorPickerModal.tsx` | (if applicable) inherit the sort selection |
| `frontend/src/hooks/useAnchors.ts` | Add `sortBy: "reuse" \| "recency"` argument; default `"reuse"` |
| `frontend/src/components/anchors/__tests__/AnchorCard.test.tsx` | Snapshot test that reuse pill renders only when `reuse_count > 0` |
| `frontend/src/components/anchors/__tests__/AnchorSidebar.test.tsx` | Test sort toggle flips order |

---

## 2. Behavior requirements

### 2.1 Drag-drop latency < 200ms (PM acceptance bar)

Measure with React DevTools Profiler:
- Click → first onDragStart fire: ≤ 50ms
- Drop → ShotCard `subject` populated: ≤ 200ms
- If above thresholds: profile, identify re-render bottleneck (likely zustand selector breadth), narrow selectors with `shallow`

Don't add throttling or debouncing — find the real cause.

### 2.2 reuse_count pill

Top-right corner of `AnchorCard`. Only renders if `reuse_count > 0` (zero = clutter for new anchors). Show as text only "已用 N",no number badge. Tooltip on hover: "已用 {N} 次,最近 {days_since_last_reuse} 天前"(days_since_last_reuse needs backend extension — see §6 NOT in this ticket).

For P2-5 the tooltip just says "已用 N 次" without the recency text. Recency requires `anchor_reuses` table aggregation that isn't currently surfaced through the anchors API — handled in a P3 follow-up.

### 2.3 Sort toggle

Above the anchor list, two pills:
- `按使用次数`(default, sorts `reuse_count DESC, created_at DESC`)
- `按时间`(sorts `created_at DESC`)

Pill state persists in `localStorage` under key `anchor_sort_preference`. On mount, hook reads it and passes to `useAnchors({ sortBy })`.

Backend already returns anchors in `reuse_count DESC, created_at DESC` order (per `anchors.py:list_anchors`). For "按时间", sort client-side after fetch — no new API.

---

## 3. Tests

`vitest` is configured. Run via `npm run test`.

1. `AnchorCard.test.tsx`:
   - `reuse_count = 0` → no pill
   - `reuse_count = 1` → pill renders "已用 1"
   - `reuse_count = 99` → pill renders "已用 99"
2. `AnchorSidebar.test.tsx`:
   - Initial sort = reuse_count DESC (default)
   - Click "按时间" → list re-orders by `created_at DESC`
   - localStorage key `anchor_sort_preference` is written on toggle
   - Reload component with `localStorage = "recency"` → defaults to recency
3. `useAnchors.test.tsx`:
   - sortBy=reuse passes through to backend query (verify URL params)
   - sortBy=recency triggers client-side resort

---

## 4. Acceptance verification (Claude's frontend skill bar)

Per `03_routing.md §0.1`:
1. `cd frontend && npm run build` — clean (zero tsc errors, zero vite warnings)
2. `cd frontend && npm run test` — all green
3. `cd frontend && npm run lint` — clean
4. Start dev server: `cd frontend && npm run dev`
5. Manual click-through:
   - Open anchor sidebar
   - Verify reuse pill on at least one anchor (use a seeded reuse via API or backend seed)
   - Toggle sort, verify order flips
   - Drag an anchor onto a ShotCard, verify subject populates within ~200ms (just feel; precise profile in PR if uncertain)
6. Take 2 screenshots:
   - Before (W1 state) — from git stash of pre-P2-5 main
   - After (P2-5) — current
   Embed both in PR description.

---

## 5. Done-signal

- `git diff --stat HEAD~1 frontend/` shows changes only in `components/anchors/` + `hooks/useAnchors.ts` + `__tests__/`
- `npm run build` exits 0, `tsc -b` 0 errors
- `npm run test` reports new tests green, total count ≥ previous + 5
- `npm run lint` clean
- PR description includes 2 screenshots (before/after) and a one-line note "drag-drop ≤ 200ms measured" or, if not measured, the React Profiler trace screenshot

---

## 6. NOT in this ticket

- `days_since_last_reuse` field — needs `anchor_reuses` API extension; defer to P3
- Anchor preview modal (large image on click) — separate UX ticket
- Anchor delete / rename — separate ticket; not in W2 scope
- Backend changes to `anchors.py` — out of scope; sidebar uses existing GET /api/anchors endpoint
- Animation on drag — keep it instant; animations come later in brand polish phase

---

## 7. PM notes

- This is Claude's first frontend ticket post-routing. Verification bar is intentionally explicit to compensate for Claude not having Cursor's hot-reload feel. Screenshots in PR are required.
- If anything reveals that Claude's frontend execution is materially worse than Cursor's was (slow visual iteration, missed CSS conventions, etc.), surface that in the W2 retro so PM can re-evaluate routing
- Founder's spot-check before merge is required — Claude opens PR but does NOT auto-merge even for green CI
