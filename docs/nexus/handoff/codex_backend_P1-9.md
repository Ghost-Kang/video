# Codex handoff — P1-9 cost guard middleware

**Source of truth**: `cascade/failures.py` (S8_UPSTREAM_REFUSED) · `02_event_spec.md` event #10 (generation_cost)
**Time budget**: 1 day

---

## 0. What you build

Cost guard middleware. Sits in front of `/api/analysis/shallow`, `/api/rewrite`, and `/api/shot/generate`. Enforces:
- Per-run cap: ¥3 (configurable via env `CASCADE_RUN_CAP_CNY`)
- Per-user-day cap: ¥30 (configurable via env `CASCADE_USER_DAY_CAP_CNY`)
- 80% soft warning → warning banner (P1-8 surfaces)
- 100% hard block → `HardFailure(S8_UPSTREAM_REFUSED)` with hint "今天的额度用完了..."

Reads consumption directly from the `events` table (`generation_cost` events). No separate cost ledger.

---

## 1. Files

| Path | Purpose |
|---|---|
| `backend/src/agent/cascade/cost_guard.py` | The middleware function + caps |
| `backend/tests/test_cost_guard.py` | Unit tests for caps + edge cases |

Hook into `server.py` to wrap the 3 endpoints. Use the existing FastAPI dependency injection pattern.

---

## 2. Function

```python
async def cost_guard(user_id: str, run_id: str, predicted_cost_cny: float) -> None:
    """
    Raises HardFailure(S8_UPSTREAM_REFUSED) if either cap exceeded.
    Otherwise returns None and the call proceeds.

    DOES NOT emit `generation_cost` event — that's the caller's job AFTER the call succeeds.
    """
    run_consumed = await _run_cost(run_id)
    user_today_consumed = await _user_today_cost(user_id)

    run_cap = float(os.environ.get('CASCADE_RUN_CAP_CNY', '3.0'))
    user_day_cap = float(os.environ.get('CASCADE_USER_DAY_CAP_CNY', '30.0'))

    if run_consumed + predicted_cost_cny > run_cap:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"run {run_id} cost {run_consumed + predicted_cost_cny:.2f} > cap {run_cap}",
        )
    if user_today_consumed + predicted_cost_cny > user_day_cap:
        raise HardFailure(
            FailureCode.S8_UPSTREAM_REFUSED,
            f"user {user_id} day cost {user_today_consumed + predicted_cost_cny:.2f} > cap {user_day_cap}",
        )
    # 80% threshold: returns silently but UI uses this signal via a separate endpoint
```

`_run_cost` and `_user_today_cost` query the `events` table.

---

## 3. Optional companion: `/api/cost/status?user_id=&run_id=`

Returns:
```json
{
  "run_cost_cny": 1.42,
  "run_cap_cny": 3.00,
  "run_pct": 0.473,
  "user_today_cost_cny": 8.20,
  "user_day_cap_cny": 30.00,
  "user_pct": 0.273,
  "warn": false   // true if any pct >= 0.8
}
```

Frontend polls this lightly (once after each generation) to render the consumption bar / warning.

---

## 4. Tests

1. Below 80% on both caps: no exception, no warn
2. At 80% on run cap: no exception, warn=true (via the status endpoint)
3. Predicted cost would exceed run cap: HardFailure(S8) raised
4. Predicted cost would exceed user-day cap: HardFailure(S8) raised
5. Multiple users sharing same `events` table: counts isolated by `user_id`
6. Day boundary at UTC midnight: yesterday's cost doesn't count toward today (assuming day=UTC calendar day; document this)
7. Env vars CASCADE_RUN_CAP_CNY / CASCADE_USER_DAY_CAP_CNY override defaults
8. `generation_cost` event sums match what the guard reads back

---

## 5. Done-signal

- `uv run pytest tests/test_cost_guard.py` passes
- Hitting `/api/analysis/shallow` 4 times in same run (each ¥1) → 4th call returns 503 with S8
- `/api/cost/status` returns consumption matching `events` table aggregations

---

## 6. Day boundary clarification

"Per user day" = UTC calendar day. Document this in the response. If founder later wants Beijing time, that's a Phase 2 change (timezone has compliance implications).

---

## 7. NOT in this ticket

- Per-user MONTH cap (Phase 2)
- Differential caps by user tier (Phase 2 — there are no tiers yet)
- Stripe billing wiring (Phase 2)
- Cost prediction model (Phase 1 uses a flat ¥0.5 for analysis, ¥1.0 for rewrite, ¥1.5 for image gen — hardcoded constants documented in `cost_guard.py`)
- Cost forecasting / "you'll hit cap in 2 hours" (Phase 2)
