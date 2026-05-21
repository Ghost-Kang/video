# Codex handoff — P2-1 `analysis_returned` double-emit fix

**Owner**: Codex session
**Source of truth**: `03_evidence_audit.md` (Reality Checker hazard #1) · `backend/src/agent/cascade/analysis_service.py` · `backend/src/agent/cascade/events.py`
**Status**: STUB · awaiting founder 30min 口述 on the exact reproduction path
**Time budget**: 1 day (estimated; will firm up after founder context)

---

## 0. What to fix (stub — to be refined)

Reality Checker §1 (hazard #1) flagged that `analysis_returned` can fire more than once for the same `analysis_id` under certain retry conditions. The exact trigger path is in `analysis_service.py:request_shallow_analysis` interacting with `storage.load_analysis_for_source` cache lookup vs `save_analysis` insert idempotency.

**Symptom observed by founder** (to be filled by PM after 口述):
> _TBD — 30min founder call captures the exact path that produced the double emit_

**Likely cause hypothesis** (PM pre-analysis):
- `request_shallow_analysis` checks `load_analysis_for_source` for cache; on cache hit returns existing contract WITHOUT emitting `analysis_returned`. Correct.
- On cache miss, calls upstream, normalizes, calls `set_analysis_context`, calls `save_analysis` (ON CONFLICT DO UPDATE), then emits `analysis_returned`. Correct on first call.
- **But** if a parallel call for the same `(user_id, source_url)` races between the cache lookup and the save, both branches miss cache → both call upstream → both call `save_analysis` (UPDATE collides on `analysis_id` PK; one wins) → both emit `analysis_returned`. **Two events for one logical analysis.**

**Fix candidates**:
1. Acquire an async lock keyed by `(user_id, source_url)` around the entire request_shallow_analysis body — serializes parallel calls for the same source
2. Move the cache check to be inside the same transaction as save (read-then-insert with ON CONFLICT) and only emit `analysis_returned` if the INSERT actually inserted (not on UPDATE)
3. Add a unique constraint on `(user_id, source_url)` in `analyses` table and treat conflict as cache hit

PM recommends **(2)** — minimal change, no new locking primitives, matches the existing INSERT/UPDATE pattern in storage.py.

---

## 1. Files

| Path | Change |
|---|---|
| `backend/src/agent/cascade/analysis_service.py` | gate `emit("analysis_returned", ...)` on whether the save was an INSERT vs UPDATE |
| `backend/src/agent/cascade/storage.py` | add return value to `save_analysis` indicating insert-or-update |
| `backend/tests/test_analysis_service.py` | add `test_concurrent_same_url_emits_once` |

---

## 2. Tests required

1. Sequential identical URL: 2 calls → 1 `analysis_returned` event (already implicitly covered by cache path)
2. Concurrent identical URL: `asyncio.gather` of 2 calls → exactly 1 `analysis_returned` event
3. Different URLs same user: 2 calls → 2 `analysis_returned` events (regression guard)
4. Different users same URL: 2 calls → 2 `analysis_returned` events (multi-user isolation regression)

---

## 3. Done-signal

- `find backend/src/agent/cascade/analysis_service.py backend/src/agent/cascade/storage.py | wc -l` = 2 (touched)
- New test `test_concurrent_same_url_emits_once` exists and passes
- `uv run pytest tests/test_analysis_service.py` all green
- `grep -c 'await emit("analysis_returned"' backend/src/agent/cascade/analysis_service.py` = 1 (single emit site, no duplication)

---

## 4. NOT in this ticket

- Generic concurrency lock framework (over-engineering for one event)
- Retry policy redesign (separate ticket)
- Frontend handling of "I see analysis_returned events" UI (no UI change)

---

## 5. PM notes

- This brief is a STUB. Section 0 "Symptom observed by founder" must be filled with the exact reproduction path from a 30min founder 口述 before Codex picks it up.
- If founder 口述 reveals the actual cause is NOT the race condition hypothesized above, replace §0-§2 with the real fix; the done-signal in §3 stays.
- Founder commitment: 2026-05-21 (W2D0) PM session — TBD slot.
