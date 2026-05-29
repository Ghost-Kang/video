# Architecture + Code Review — 2026-05-28 (Opus 4.8)

**Reviewer**: Claude Opus 4.8 · **Scope**: backend ~24K LOC + frontend ~13K LOC
**Baseline commit**: `877786b` → **fixes shipped in**: `20f34f1` (deployed to prod, verified live)

## Executive summary

The codebase is well cared-for for its stage (10-person 内测): the god-module
split has held, transport/cascade/workers/persistence are cleanly separated,
the WS contract is typed + codegen'd, there are 87 test files, a structured
failure taxonomy, graceful SIGTERM drain, WAL + busy_timeout, and an LRU agent
pool. The architecture call from the prior performance review ("not a rewrite
moment; pain is orchestration + IO, not framework fit") was correct.

There was **one structural P0**: the HTTP transport had **no authentication at
all** while being publicly exposed via `cascade.herwin.top`, even though the WS
transport was properly gated. This exposed admin data *and* allowed unbounded
upstream spend. It was verified exploitable from the open internet and has been
fixed. P1–P3 (event-loop blocking, DB/connection churn, telemetry/classification
accuracy) were also fixed in the same pass.

All findings below were fixed, tested (520 backend + 176 frontend pass), and
deployed.

## Method

Read the transport layer, cascade services, all three SQLite persistence
layers, the agent runner, config, cost guard, and the frontend WS store + API
libs. Verified the auth gap with live `curl` from an external machine (no
credentials). Verified the fix the same way + a browser walkthrough of the
admin token flow.

---

## P0 — HTTP API had no authentication (CRITICAL) — FIXED

### Finding

`nginx.conf` proxied `/api/*` straight through; `http_router.py` had no auth
check on any route. The WS gate (`INVITE_CODES` + fail-closed `config.py`) only
protected WebSocket traffic. Live evidence from an external machine, no creds:

```
GET https://cascade.herwin.top/api/creators       → 200  (all user_ids + behavior)
GET https://cascade.herwin.top/api/events?limit=2  → 200  (source URLs, analysis_ids, cost, model)
GET https://cascade.herwin.top/api/health/summary  → 200  (server CPU/mem/disk/uptime)
```

Worse than data exposure: `POST /api/analysis/shallow` and `POST /api/rewrite`
were public and each spends real upstream money (≈¥0.5–1.2/call). `cost_guard`
keys its caps on **client-supplied** `user_id`/`run_id` (`cost_guard.py:62`,
`http_router.py:162/194`), so caps were trivially bypassed by rotating those
fields → **unbounded cost / financial DoS**.

### Fix (`20f34f1`)

Three-tier gate in `http_router._check_auth`:
- **OPEN** — `GET /api/health` (liveness), `GET /api/stats/public`
  (aggregate-only), `POST /api/client_error`.
- **COHORT** — analysis/rewrite/anchors/events POST/cost: require
  `X-Invite-Code ∈ INVITE_CODES`, enforced only when `INVITE_CODES` is set
  (mirrors WS; dev/test stay open).
- **ADMIN** — `GET /api/events`, `/api/creators`, `/api/health/summary`:
  require `X-Admin-Token == config.ADMIN_TOKEN`; fail-closed 403 in prod if the
  token is unset.

Supporting changes:
- New `GET /api/stats/public` returns only `{runs, creators}` via
  `COUNT(DISTINCT)` so the landing page stops shipping 500 raw events to every
  anonymous visitor (a leak in its own right) and `GET /api/events` can become
  admin-only.
- New `GET /api/health` liveness endpoint; the backend container healthcheck
  was repointed here (it previously hit `/api/events`, which would now 401 and
  break the deploy).
- Frontend: all `/api` calls routed through `apiFetch()`
  (`frontend/src/lib/apiClient.ts`), which injects both headers from
  localStorage; `AdminTokenBar` (mounted in `PageShell`, self-guards on
  `/admin/*`) lets the founder set the admin token once.
- `docker-compose.yml`: `ENV=prod` so `config.IS_PROD_LIKE` is reliable (the
  container HOSTNAME is a hash, not "prod"), making the fail-closed backstop
  real; prod `.env` gained `CASCADE_ADMIN_TOKEN` (`openssl rand -hex 24`).

### Verification (live, post-deploy)

| Endpoint | Before | After |
|---|---|---|
| `GET /api/creators` (no creds) | 200 leak | **401** |
| `GET /api/events` (no creds) | 200 leak | **401** |
| `GET /api/health/summary` (no creds) | 200 leak | **401** |
| `POST /api/analysis/shallow` (no creds) | 200 (spends $) | **401** |
| `GET /api/health` | — | **200** |
| `GET /api/stats/public` | — | **200** `{runs, creators}` |
| `GET /api/creators` + `X-Admin-Token` | — | **200** |
| `GET /api/anchors` + `X-Invite-Code` | — | **200** |

Browser walkthrough confirmed the admin token flow end-to-end (empty → enter
token → reload → 15 events load).

### Residual (accepted for the 10-person cohort)

`cost_guard` still keys caps on client-supplied `user_id`/`run_id`, so a cohort
member with the shared invite code could rotate them to bypass per-user caps.
The public/unbounded vector — the actual P0 — is closed. Proper fix
(server-derived identity) tracked for when the cohort scales.

---

## P1 — Synchronous IO blocking the asyncio event loop — FIXED

- `optimize_prompt` used `model.invoke()` (a blocking LLM network call,
  seconds) on the loop thread, stalling all WS/HTTP handling → changed to
  `await model.ainvoke()` (`agent_runner.py`).
- `run_agent`, every WS handler, and the `ws_server` auth path called
  synchronous `sqlite3` (canvas snapshot, `save_message`, `list_sessions`, node/
  edge mutations) directly on the loop → now offloaded via `asyncio.to_thread`
  (ContextVars propagate into the worker thread, so the per-task `set_thread_id`
  isolation still holds).

---

## P2 — DB / memory / transport hardening — FIXED

- **DDL on every connection** across all three SQLite layers (cascade
  `_connect`, canvas `_db` with 13 exception-throwing ALTERs, store `_conn`) →
  schema DDL now runs once per path. `CREATE TABLE canvas_nodes` was made the
  complete source of truth (it previously omitted the `generation_*` columns,
  which only existed via ALTERs) so a recreated file is complete even with the
  ALTER migrations gated.
- **Unbounded module-level lock dicts** (`_THREAD_RUN_LOCKS`,
  `_source_analysis_locks`) → bounded with unlocked-entry eviction.
- **No read timeout** on the hand-rolled HTTP server → added an
  `asyncio.wait_for` slowloris guard on header/body reads.

---

## P3 — Correctness / telemetry — FIXED

- **Failure misclassification**: unexpected internal exceptions were labeled
  `S8_UPSTREAM_REFUSED` ("系统暂时繁忙"), masking our own bugs as upstream
  failures → new `S11_INTERNAL_ERROR` code (backend taxonomy + frontend
  `FailureCode` union + `wsStore` KNOWN_CODES + recovery hint). Timeouts still
  map to S7; connection/refused/rate strings still map to S8.
- **Telemetry accuracy**: `generation_cost` now records real `latency_ms`
  (was hardcoded `0`); `cascade_cache_hit` reports honest TTL (`null` for the
  permanent cross-user analysis reuse, not a fake `60.0`).
- **Healthcheck**: backend container healthcheck → dedicated `/api/health` on
  `127.0.0.1` (was `/api/events` on `localhost`, which had the same IPv6
  fragility as the frontend Dockerfile fixed earlier and would 401 under the
  new auth).

### Kept intentionally (not a miss)

The `wsStore.ts` regex that synthesizes a `FailurePayload` from Chinese error
keywords in an `agent_response` is still load-bearing: it catches HardFailures
the agent *swallows* into a normal assistant message (a path that doesn't go
through `run_agent`'s except block). Removing it would regress that path. The
structured `analysis_failed` frame remains the primary path.

---

## Strengths worth preserving

- Clean module decomposition after the god-module split; `server.py` is a thin
  serve loop.
- Typed WS contract + `ws_generated.ts` codegen + the HANDLERS/INBOUND_MODELS
  drift assertion.
- Correct concurrency reasoning: `set_thread_id`/`set_user_id` are ContextVars
  (per-task isolated, per-connection task) — not the global race they superficially
  resemble. Agent pool: composite key + connection close on evict + per-thread
  run serialization + per-source-URL analysis lock + cross-user cache reuse.
- Strong test culture (520 backend + 176 frontend), structured failure
  taxonomy, events.db observability, fail-closed prod auth config.
- Ops hygiene: log rotation, backend ports not published, index.html no-cache,
  secrets gitignored.

## Follow-ups (not blocking)

- `cost_guard` server-derived identity before scaling past the trusted cohort.
- The P2 plan (`architecture_transport_storage_P2_plan.md`) — FastAPI/Starlette
  migration would also retire the hand-rolled HTTP parser; the auth layer added
  here ports cleanly to typed route dependencies.
- Rotate `CASCADE_ADMIN_TOKEN` (its value appeared in the 2026-05-28 session
  transcript) — see the credential rotation list for the prod server.

## Verification summary

- Backend: `520 passed, 9 skipped` (deterministic — canvas isolation fixed with
  a per-test temp DB; ran twice green).
- Frontend: `176 passed`, `tsc --noEmit` clean, production build OK.
- Prod: both containers healthy; auth gap confirmed closed via external `curl` +
  browser admin walkthrough.
