# Cursor handoff — P1-8 warnings + failure banners

**Source of truth**: `cascade/failures.py` (RECOVERY_HINTS, RECOVERY_ACTIONS, HTTP_STATUS) · `02_brand_guardrails.md` failure state copy rules
**Time budget**: 2 days

---

## 0. What you build

Three visual states on top of the card stack:
1. **Confidence banner** when `analysis.confidence < 0.5` — soft top-of-stack notice
2. **Warning chips** per warning code on the card whose field is affected
3. **Failure banner** when an API call returns 4xx/5xx with a `FailurePayload` — full-card replacement with 1-3 recovery action buttons

All copy comes from the backend `RECOVERY_HINTS` / `ACTION_LABELS` (mirrored in `frontend/src/types/cascade.ts`). NEVER hand-write user-facing failure text.

---

## 1. Files

| Path | Purpose |
|---|---|
| `frontend/src/components/feedback/ConfidenceBanner.tsx` | Top-of-stack low-confidence notice |
| `frontend/src/components/feedback/WarningChip.tsx` | Inline chip on a card |
| `frontend/src/components/feedback/FailureBanner.tsx` | Full-card failure with recovery buttons |
| `frontend/src/hooks/useApiError.ts` | Centralized error-handling hook for API calls |

Modify the existing card components to:
- ScriptCard: render `WarningChip` for each warning whose `field` starts with `viral_analysis.`
- ShotCard: render `WarningChip` for each warning whose `field` starts with `scenes[<this index>].`
- CardStack (parent): render `ConfidenceBanner` at top if applicable; render `FailureBanner` instead of card stack when fetch fails

---

## 2. ConfidenceBanner

Triggers: `analysis.confidence < 0.5` (constant `LOW_CONFIDENCE_THRESHOLD` exported from cascade.ts).

```
┌─────────────────────────────────────────┐
│ ℹ️ 系统对这条分析的把握一般，仅供参考       │
└─────────────────────────────────────────┘
```

Style: `bg-stone-100 border-l-4 border-stone-400 px-4 py-2 text-sm text-stone-700`. NOT orange (saves orange for primary action).

Dismissible: clicking ✕ collapses the banner for this session. Re-shows on page reload (it's an info signal, not a setting).

---

## 3. WarningChip

Renders inline on the affected card. Style: `inline-flex items-center gap-1 px-2 py-1 rounded-full bg-amber-50 text-amber-800 text-xs`.

Content: `RECOVERY_HINTS[warning.code]` — the human-language hint from failures.py. NEVER the field path. NEVER the code itself.

Severity rules:
- `severity: 'info'` → DO NOT render (the API audit P6 says these should be filtered server-side, but defensive code on client too)
- `severity: 'warn'` → render normally
- `severity: 'error'` → render with red tint (`bg-red-50 text-red-800`)

If a card has > 2 warnings, collapse extras under a "+N more" chip that expands on click.

---

## 4. FailureBanner

Replaces the entire card stack (or the affected card if it's a per-card failure).

```
┌──────────────────────────────────────────────────┐
│                                                  │
│   {RECOVERY_HINTS[code]}                          │
│                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌─────┐    │
│   │ {action 1}   │  │ {action 2}   │  │告诉我们│    │
│   └──────────────┘  └──────────────┘  └─────┘    │
│                                                  │
│   错误代码: {code} · 请求 ID: {request_id}          │
│                                                  │
└──────────────────────────────────────────────────┘
```

Action buttons:
- Up to 3 buttons sourced from `RECOVERY_ACTIONS[code]`
- Each button label = `ACTION_LABELS[action]`
- The last button is always "告诉我们" (REPORT) and opens a feedback form (stub for Phase 1; logs to `failure_recovered` event with `action='REPORT'`)
- Click any button → `/api/events` POST with `failure_recovered` event including which action was selected

For RETRY_SAME_URL_AFTER_30S / 60S: the button is initially disabled with a countdown; enables after the delay.

---

## 5. useApiError hook

```ts
const { wrappedFetch } = useApiError();
const res = await wrappedFetch('/api/analysis/shallow', { method: 'POST', body });
// On 4xx/5xx, automatically sets failure state in Zustand store
// CardStack reads failure state and renders FailureBanner instead of cards
```

The hook reads `response.headers.get('content-type')` — if JSON, parses `FailurePayload`. If not, falls back to `S5_INVALID_PAYLOAD`-shaped synthetic payload.

---

## 6. Tests

- `__tests__/FailureBanner.test.tsx`: for each of 8 FailureCodes, render the banner and verify the hint + correct number of action buttons + correct labels
- `__tests__/WarningChip.test.tsx`: severity=info filtered; severity=warn rendered; severity=error styled differently
- `__tests__/ConfidenceBanner.test.tsx`: shows when confidence < 0.5; hidden when ≥ 0.5
- `__tests__/useApiError.test.ts`: 4xx response sets failure state with parsed FailurePayload; non-JSON response falls back

---

## 7. Done-signal

- `npm run build` clean
- `grep -rn "RECOVERY_HINTS\|ACTION_LABELS" frontend/src/components/feedback/` ≥ 2 hits (proving the components consume backend-defined copy, not hand-written strings)
- All 8 FailureCodes have a working banner (visual smoke test)
- Manual: trigger S1 / S3 / S7 via mock backend → correct banners with correct buttons appear

---

## 8. NOT in this ticket

- Feedback form for REPORT action (Phase 2; stub it as `alert('收到，谢谢') + event log`)
- Auto-retry logic for transient failures (Phase 2)
- Cross-tab failure sync (Phase 2)
- Server-side info-warning filtering (Codex P1-2 brief covers this)
