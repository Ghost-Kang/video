# Codex handoff — P2-2 S7 / S8 upstream wiring

**Owner**: Codex session
**Source of truth**: `03_evidence_audit.md` (Reality Checker hazard #2) · `backend/src/agent/cascade/analysis_service.py:_call_toprador` · `backend/src/agent/cascade/failures.py`
**Status**: STUB · awaiting founder 30min 口述 on Toprador endpoint shape + auth + observed failure modes
**Time budget**: 2 days

---

## 0. What to build (stub — to be refined)

Today `CASCADE_UPSTREAM=toprador` resolves to `analysis_service.py:_call_toprador` which raises `NotImplementedError`. Phase 1 ships with `CASCADE_UPSTREAM=fixture` only.

Reality Checker §2 (hazard #2) flagged that S7 (`UPSTREAM_TIMEOUT`) and S8 (`UPSTREAM_REFUSED`) are defined in `failures.py` but never actually raised — no real upstream means no real failure modes ever fire, so the recovery UI is untested.

**Founder 口述 needed**:
- Toprador endpoint URL + auth header shape
- Expected response shape (does it already conform to `CascadeAnalysisContract` or need adapter normalization?)
- Observed real failure modes:
  - Rate limit response code + body shape → maps to S8
  - Timeout threshold + retry-after header → maps to S7
  - Other failure shapes Reality Checker saw in the wild
- Auth refresh path if token expires

---

## 1. Files

| Path | Change |
|---|---|
| `backend/src/agent/cascade/analysis_service.py` | implement `_call_toprador` with real HTTP call + S7/S8 mapping |
| `backend/src/agent/cascade/adapter.py` | (maybe) handle Toprador-specific quirks if response differs from contract |
| `backend/tests/test_analysis_service.py` | add S7/S8 simulation tests using `respx` or `httpx_mock` |
| `backend/src/agent/config.py` | `TOPRADOR_ENDPOINT`, `TOPRADOR_API_KEY` env wiring |

---

## 2. Behavior

```python
async def _call_toprador(source_url: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                TOPRADOR_ENDPOINT,
                json={"url": source_url},
                headers={"Authorization": f"Bearer {TOPRADOR_API_KEY}"},
            )
        except httpx.TimeoutException as exc:
            raise HardFailure(FailureCode.S7_UPSTREAM_TIMEOUT, str(exc)) from exc
        if resp.status_code == 429:
            raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "rate_limit")
        if resp.status_code in (401, 403):
            raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "auth_refused")
        if resp.status_code >= 500:
            raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, f"upstream_5xx_{resp.status_code}")
        resp.raise_for_status()
        return resp.json()
```

Exact status code mapping subject to founder 口述 confirmation.

---

## 3. Tests required

1. Happy path: real `CASCADE_UPSTREAM=toprador` returns 200 with contract-shaped JSON → contract validates
2. Timeout: mock httpx to raise `TimeoutException` → `HardFailure(S7_UPSTREAM_TIMEOUT)` propagates; `failure_emitted` event with `failure_code=S7_...`
3. Rate limit: mock 429 → `HardFailure(S8_UPSTREAM_REFUSED, "rate_limit")`
4. Auth refused: mock 401 → `HardFailure(S8_UPSTREAM_REFUSED, "auth_refused")`
5. 5xx: mock 500 → `HardFailure(S8_UPSTREAM_REFUSED, "upstream_5xx_500")`
6. Malformed response: mock 200 with non-conforming JSON → contract adapter raises `S2_VERSION_MISMATCH` or `S5_INVALID_PAYLOAD`

---

## 4. Done-signal

- `grep -c "S7_UPSTREAM_TIMEOUT\|S8_UPSTREAM_REFUSED" backend/src/agent/cascade/analysis_service.py` ≥ 2
- All 6 tests above pass
- `CASCADE_UPSTREAM=toprador uv run python -c "import asyncio; from agent.cascade.analysis_service import request_shallow_analysis; asyncio.run(request_shallow_analysis('<real-url>', user_id='smoke', run_id='smoke'))"` returns contract WITHOUT NotImplementedError
- Cost guard (`P1-9`) sees real `generation_cost` events from this path

---

## 5. NOT in this ticket

- Retry policy / exponential backoff (separate ticket if needed)
- Caching of upstream responses beyond what `storage.load_analysis_for_source` already does
- New failure codes (S7/S8 already exist; we are wiring them, not inventing)
- Frontend banner changes (`RECOVERY_ACTIONS` already wired to S7/S8 in P1-8)

---

## 6. PM notes

- This brief is a STUB. Section 0 needs founder 口述 to fill auth + endpoint + observed failure shapes.
- Suggested founder slot: same 30min as P2-1 口述 — these two briefs share the analysis_service.py file and can be discussed together.
- Founder commitment: 2026-05-21 (W2D0) PM session — TBD slot.
