# Codex handoff — P1-2 浅分析 endpoint + 卡片数据

**Target tool**: Codex (or Claude Code in CLI mode if Codex is unavailable)
**Owner accountability**: This brief is a contract. Any divergence requires PM sign-off in `docs/nexus/03_routing.md`.
**Source of truth**: `docs/TOPRADOR_SCHEMA.md` · `backend/src/agent/cascade/contract.py` · `docs/nexus/02_event_spec.md`

---

## 0. What you are building

A backend endpoint that:
1. Accepts a `source_url` (抖音 / 小红书 / other).
2. Either calls an upstream analyzer (toprador) OR loads a synthetic fixture for development.
3. Pipes the raw payload through `agent.cascade.adapter.normalize_analysis_result()`.
4. Persists the resulting `CascadeAnalysisContract` keyed by `analysis_id`.
5. Returns the contract to the caller.
6. Emits an `analysis_returned` event per `docs/nexus/02_event_spec.md`.

You **must not** write any frontend code. You **must not** modify `cascade/contract.py` or `cascade/failures.py` — those are owned by the contract author. If you discover a bug there, file an issue, don't patch.

---

## 1. Files you will create

| Path | Purpose |
|---|---|
| `backend/src/agent/cascade/analysis_service.py` | The service layer (this is the bulk of the work) |
| `backend/src/agent/cascade/events.py` | Single-source events emitter (per routing §3) |
| `backend/src/agent/cascade/storage.py` | SQLite persistence for analysis results + events |
| `backend/tests/test_analysis_service.py` | Service-level tests using synthetic fixtures |
| `backend/tests/test_events.py` | Event emission tests |

Hook into `backend/src/agent/server.py` to add the FastAPI route (or whatever framework `server.py` currently uses — read it first; do **not** introduce a new framework).

---

## 2. Function signatures (do not change)

```python
# backend/src/agent/cascade/analysis_service.py

from agent.cascade.contract import CascadeAnalysisContract

async def request_shallow_analysis(
    source_url: str,
    *,
    user_id: str,
    run_id: str | None = None,
) -> CascadeAnalysisContract:
    """Entry point. Calls upstream OR loads fixture, normalizes, persists, emits event.

    Raises:
        agent.cascade.failures.HardFailure: when the adapter cannot salvage the payload.
                                            Caller (route handler) converts to HTTP status from
                                            HardFailure.http_status with HardFailure.to_payload()
                                            as the JSON body. Pass include_debug=True only in
                                            dev / staging (env var CASCADE_DEBUG_ERRORS=1).
    """
```

```python
# backend/src/agent/cascade/events.py

from typing import Any

async def emit(
    event_name: str,
    *,
    user_id: str,
    run_id: str | None,
    payload: dict[str, Any],
) -> None:
    """Single write path for all 11 Phase 1 events.

    Validates event_name against ALLOWED_EVENTS (the 11 from event spec).
    Unknown event names raise ValueError — do NOT silently accept new names."""

ALLOWED_EVENTS: frozenset[str] = frozenset({
    "run_started",
    "analysis_returned",
    "script_rewritten",
    "shot_generated",
    "publish_pack_copied",
    "anchor_created",
    "anchor_reused",
    "failure_emitted",
    "failure_recovered",
    "generation_cost",
    "interview_logged",
})
```

```python
# backend/src/agent/cascade/storage.py

from agent.cascade.contract import CascadeAnalysisContract

async def save_analysis(contract: CascadeAnalysisContract) -> None: ...
async def load_analysis(analysis_id: str) -> CascadeAnalysisContract | None: ...
```

---

## 3. Schema for the SQLite tables

```sql
CREATE TABLE IF NOT EXISTS analyses (
  analysis_id TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL,
  run_id      TEXT,
  source_url  TEXT NOT NULL,
  platform    TEXT NOT NULL,
  cost_cny    REAL NOT NULL,
  confidence  REAL NOT NULL,
  contract_json TEXT NOT NULL,           -- full CascadeAnalysisContract JSON
  created_at  TEXT NOT NULL              -- RFC3339 UTC
);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS events (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  event_name   TEXT NOT NULL,
  user_id      TEXT NOT NULL,
  run_id       TEXT,
  payload_json TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_user_name_time ON events(user_id, event_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, created_at);
```

Reuse the existing SQLite database path pattern from `backend/src/agent/store.py` (it puts DBs under `backend/data/`).

---

## 4. The event payload for `analysis_returned`

```jsonc
{
  "analysis_id":   "ana_...",
  "source_url":    "https://...",
  "platform":      "douyin",
  "cost_cny":      0.42,
  "duration_s":    38,
  "scenes_count":  5,
  "warnings_count": 0,
  "confidence":    0.88,
  "had_fallback":  false,            // true if ANY W2_FALLBACK_USED warning present
  "model":         "doubao-seed-2-0-pro"
}
```

This payload is read by 4 of the 8 Phase 1 Gate SQL queries — get the field names exactly right.

---

## 5. Upstream switching (toprador vs fixture)

Read an env var `CASCADE_UPSTREAM` with values:
- `"toprador"` — call the real upstream (out of scope for this brief; stub a function `_call_toprador()` that raises NotImplementedError for now)
- `"fixture"` — load a fixture by hashing `source_url` modulo the 3 happy paths

Default to `"fixture"` when the env var is unset, so the service is dev-runnable without toprador.

Even in `fixture` mode, the raw fixture payload **must** still pass through `normalize_analysis_result()` — never bypass the adapter.

---

## 6. Tests

`backend/tests/test_analysis_service.py` must cover:
- Happy path: fixture mode returns a valid contract
- Persistence: after `request_shallow_analysis`, `load_analysis(returned_id)` round-trips
- Event emission: `analysis_returned` fires with the exact payload shape above
- HardFailure path: corrupted fixture (mock the fixture loader) raises and the event `failure_emitted` is recorded
- Idempotency: `analysis_id` is per-call (new ULID every analysis). Idempotency is by `(source_url, user_id, model)` — calling `request_shallow_analysis` twice with the same triple within a TTL window (default 24h) returns the **most recent existing** `analysis_id` instead of running a new analysis. Implement with a SELECT-then-INSERT inside a transaction; emit `analysis_returned` only on the new-analysis branch, not the cache-hit branch.

`backend/tests/test_events.py` must cover:
- Unknown event name raises ValueError
- Known event with missing required field raises ValueError
- Successful emit persists to `events` table
- Event ordering: created_at strictly monotonic within a run_id

---

## 7. What you must NOT do

- ❌ Add a new dependency (no `httpx`, no `pydantic-settings`, no celery). Use existing aiosqlite + stdlib.
- ❌ Modify `cascade/contract.py` or `cascade/failures.py` — call them, do not change them.
- ❌ Add fields to `CascadeAnalysisContract`. If a real-world need surfaces, escalate to PM.
- ❌ Catch `HardFailure` anywhere inside `analysis_service.py` — let it propagate to the route handler.
- ❌ Add frontend code.
- ❌ Build a generic "event bus". Build the simple `emit()` function. YAGNI.

---

## 8. Acceptance

When you are done:
1. `cd backend && uv run pytest tests/test_cascade_contract.py tests/test_analysis_service.py tests/test_events.py -v` passes 100%.
2. A request to `POST /api/analysis/shallow` with body `{"source_url": "https://example.com/x"}` returns a valid `CascadeAnalysisContract` JSON.
3. After 3 successful requests, `sqlite3 backend/data/messages.db "SELECT event_name, COUNT(*) FROM events GROUP BY event_name"` shows `analysis_returned` count = 3.
4. Forbidden-term lint passes (CI step; no Chinese strings containing 节点/锚点/DAG/agent/画布/AI/平台/工具/智能 — these belong on the frontend's banned list, not the backend, but the principle stands for any user-facing string).

---

## 9. Time budget

**2 days** if you stay focused. If you find yourself wanting to refactor `server.py`, stop and escalate. If you find yourself wanting to write a proper event bus, stop and use `emit()` directly.
