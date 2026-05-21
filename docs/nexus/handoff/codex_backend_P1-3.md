# Codex handoff — P1-3 赛道改写 chain (backend wiring)

**Source of truth**: `claude_prompts_P1-3.md` (Claude writes the prompts; you wire the chain)
**Time budget**: 2 days

---

## 0. What you build

The HTTP + LangGraph wiring that takes an `analysis_id`, looks up the contract, picks the niche, calls the prompt (Claude's output from `claude_prompts_P1-3.md`), emits the `script_rewritten` event, and returns the rewrite result.

You do **not** write the prompts. You do **not** modify `cascade/contract.py`.

---

## 1. Files

| Path | Purpose |
|---|---|
| `backend/src/agent/cascade/rewrite_service.py` | The service layer; calls into `rewrite.py` from Claude's brief |
| `backend/src/agent/cascade/cost_cap.py` | (shared with P1-9) pre-call cost prediction |
| `backend/tests/test_rewrite_service.py` | Endpoint + chain + event-emission tests |

Hook into `server.py` to add `POST /api/rewrite`. Read it first; don't introduce a new web framework.

---

## 2. Function signatures

```python
async def request_rewrite(
    *,
    analysis_id: str,
    niche: Literal["baomam_fushi", "yuer_richang", "jiating_chufang"],
    user_id: str,
    run_id: str | None = None,
) -> RewriteResult:
    """
    1. Load analysis via storage.load_analysis(analysis_id)
    2. Pre-check cost via cost_cap.predict_rewrite_cost(contract, niche)
    3. If predicted cost > ¥3 → raise HardFailure(S8_UPSTREAM_REFUSED, "cost cap")
    4. Call agent.cascade.rewrite.rewrite_for_niche(contract, niche)
    5. Persist rewrite result keyed by (analysis_id, niche, user_id, attempt_n)
    6. Emit `script_rewritten` event (payload below)
    7. Return RewriteResult

    Idempotency: if (analysis_id, niche, user_id) already has a rewrite within 24h,
    return the existing one and emit `script_rewritten_cache_hit` event (not in the 11-event spec —
    log only, do not emit user-facing).
    """
```

---

## 3. Event payload (`script_rewritten`)

```json
{
  "analysis_id": "ana_...",
  "rewrite_id": "rw_...",
  "niche": "baomam_fushi",
  "parser_warnings": 0,
  "shots_count": 5,
  "confidence": 0.82,
  "cost_cny": 0.47,
  "model": "doubao-seed-2-0-pro",
  "had_anchor_reference": false
}
```

`had_anchor_reference` is hardcoded `false` for now (P1-6 will add anchor references).

---

## 4. Tests

12 cases — minimum:

1. Happy path: known niche + valid analysis → returns valid RewriteResult, event fires
2. Unknown analysis_id → 404
3. Unsupported niche → 400 with `S5_INVALID_PAYLOAD` (use existing failure code)
4. Cost cap exceeded → `HardFailure(S8_UPSTREAM_REFUSED)` raised, no event
5. Upstream prompt timeout → `HardFailure(S7_UPSTREAM_TIMEOUT)` raised
6. Idempotency: 2nd call within 24h returns same `rewrite_id`, NO new `script_rewritten` event
7. Idempotency timeout: 2nd call after 24h returns new `rewrite_id`, new event fires
8. Multi-user isolation: same analysis_id, different user_id → two distinct rewrites
9. `script_rewritten` payload schema matches §3 above
10. `info` severity warnings filtered from HTTP response (per API audit P6)
11. `debug_detail` only in response when `CASCADE_DEBUG_ERRORS=1`
12. `request_id` present on every error response

---

## 5. Done-signal

- `uv run pytest tests/test_rewrite_service.py` passes
- `POST /api/rewrite -d '{"analysis_id":"ana_syn_baomam_001","niche":"baomam_fushi"}'` returns 200 with `RewriteResult` shape
- `sqlite3 backend/data/messages.db "SELECT COUNT(*) FROM events WHERE event_name='script_rewritten'"` increments by 1 per successful new rewrite

---

## 6. NOT in this ticket

- The prompts themselves (Claude P1-3 brief)
- Image generation triggered from the rewrite (P1-5 — reuse existing `generation.py`)
- Anchor referencing inside the rewrite (P1-6)
- Frontend rendering (Cursor P1-4)
- Cost guard middleware (P1-9 — this brief only does PRE-call prediction; per-request enforcement is P1-9)
