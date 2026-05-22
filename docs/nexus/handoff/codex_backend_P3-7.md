# Codex handoff — P3-7 Toprador production hardening

**Owner**: Codex session
**Source of truth**: `codex_backend_P2-2.md` (Toprador wiring, shipped W2) · `backend/src/agent/cascade/analysis_service.py:_call_toprador`
**Status**: **STUB** · awaiting founder priority confirmation (this ticket pre-emptively hardens an endpoint that hasn't yet been load-tested under real traffic). Optional for W3 — execute only if founder green-lights.
**Time budget**: 2 days

---

## 0. What you build

`_call_toprador` (shipped in W2 via P2-2) does the basic happy path: single httpx POST, maps 429/401/403/5xx/timeout → S7/S8. Production-grade behavior demands more:

1. **Retry policy** — exponential backoff (3 attempts, 1s/2s/4s base, jitter) for transient failures (5xx, network errors). Not for auth refusals or rate limits beyond initial 429.
2. **Circuit breaker** — open the breaker after N consecutive S8s in a 60s window; fail fast (immediate S8 with `circuit_open` detail) while breaker is open. Half-open after cooldown, single probe to close.
3. **Timeout metrics on `analysis_returned`** — extend the event payload with `upstream_latency_ms` and `upstream_attempts`. Founder can see "this analysis took 12s and 2 retries" in the events table.
4. **In-memory cache layer** — short TTL (60s) cache keyed by `source_url`. Defends against accidental rapid re-submission of the same URL. Distinct from the existing `load_analysis_for_source` long-term cache (which is DB-backed and per-user).

---

## 1. STUB — to be filled before execution

This brief is intentionally light because:
- We don't yet know real Toprador failure rate (Toprador endpoint not wired in production env)
- Without traffic data, retry / circuit threshold values are guesses
- Founder hasn't confirmed P3-7 fits the W3 schedule (it may belong in W4)

**Before Codex executes**, founder + PM should fill:
- §2 specific retry / breaker thresholds (defaults below are placeholders)
- §3 SLO target the hardening should meet
- §6 explicit "NOT in this ticket" boundaries

---

## 2. Behavior placeholders

(To be confirmed)

| Knob | Placeholder | Source-of-truth |
|---|---|---|
| Retry attempts (transient) | 3 | (founder TBD) |
| Backoff base | 1s, jittered ±25% | (founder TBD) |
| Circuit threshold | 5 consecutive S8 in 60s | (founder TBD) |
| Cooldown | 30s | (founder TBD) |
| In-memory cache TTL | 60s | (founder TBD) |
| HTTP timeout per attempt | 30s | (founder TBD; currently 30s in code) |

---

## 3. SLO target placeholders

- `analysis_returned` p95 latency ≤ ?s
- S7 / S8 rate ≤ ?% of total analysis calls
- Cache hit rate (60s window) ≥ ?% during burst load

Without real traffic baseline, these are aspirational. Recommend: ship monitoring first (P3-9 candidate ticket), gather 1-2 weeks of data, then set real SLOs.

---

## 4. Files (anticipated, subject to refinement)

| Path | Change |
|---|---|
| `backend/src/agent/cascade/analysis_service.py` | wrap `_call_toprador` with retry + cache layer |
| `backend/src/agent/cascade/circuit_breaker.py` | new minimal module — in-memory breaker state |
| `backend/src/agent/cascade/storage.py` | possibly extend `analysis_returned` event spec to add `upstream_latency_ms` + `upstream_attempts` |
| `backend/src/agent/cascade/events.py` | add `upstream_latency_ms` / `upstream_attempts` to `_REQUIRED_FIELDS["analysis_returned"]` |
| `backend/tests/test_analysis_service.py` | extend with retry / breaker / cache cases |

---

## 5. Test surface

(to be expanded based on §2 final values)

- Transient 503 once → retry succeeds (1 attempt logged + final success)
- Transient 503 thrice → all retries exhausted → S8
- 5 consecutive S8 trips breaker → 6th call fails fast with `circuit_open`
- Cooldown elapses → half-open probe → success → breaker closes
- Cache hit on same source_url within TTL → 0 upstream calls
- `analysis_returned` event payload includes `upstream_latency_ms` non-zero

---

## 6. Done-signal placeholders

(To be defined when §2/§3 finalize)

---

## 7. NOT in this ticket

- Persistent circuit breaker state across process restarts (in-memory only for v1)
- Distributed cache (Redis) — single-process in-memory only
- Adaptive retry / dynamic backoff based on real-time success rate
- Toprador endpoint side scaling / infrastructure work (separate ops ticket)
- Cross-user cache (cache is per-URL, ignores user)

---

## 8. PM notes

- This is pre-emptive engineering for a path that may not see real traffic for weeks. Recommend deferring to W4 unless founder has specific Toprador reliability concern.
- If executed in W3, sequence after P3-6 (smaller, immediate value) and after P3-9 (observability — would give SLO baseline numbers).
- If deferred to W4, leave this STUB in place as the planning seed.

**Recommended decision (PM)**: defer to W4. Execute P3-6 in W3 first.
