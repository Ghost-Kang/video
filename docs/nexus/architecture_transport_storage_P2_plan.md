# P2 Transport, Storage, and Tracing Plan - 2026-05-28

Owner: Claude

Status: implementation plan ready. Do not change production transport/storage
without founder approval because this touches deployment shape and local-dev
workflow.

## Decision Summary

Move in three phases:

1. Keep SQLite WAL for the 10-person staging cohort.
2. Introduce typed FastAPI HTTP routes while keeping the current service
   functions and websocket server stable.
3. Add trace propagation before any datastore migration, so performance and
   failure data can justify whether Postgres is needed.

Do not migrate LangGraph, DeepAgents, or the websocket protocol in the same
change as HTTP routing.

## Phase A - FastAPI HTTP Shell

Goal: replace the handwritten HTTP router surface without changing business
logic.

Implementation shape:

- Add `backend/src/agent/transport/fastapi_app.py`.
- Register typed routes for existing HTTP endpoints.
- Reuse existing handlers/services first; extract request parsing only after
  parity tests pass.
- Keep websocket handling on the current `websockets` server for one release.
- Add request logging middleware with `method`, `path`, `status_code`,
  `duration_ms`, `user_id`, `run_id`, and `trace_id`.
- Add gzip/br compression where supported by the selected ASGI server.
- Generate OpenAPI docs but keep it internal-only in staging.

Acceptance criteria:

- Existing HTTP endpoint tests pass unchanged or with minimal transport harness
  updates.
- Existing websocket tests are untouched.
- `GET /api/health/summary` remains cheap and does not load full event lists.
- Admin frontend calls do not change URL or payload shape.

Rollback:

- Keep the old router entrypoint for one release behind an env flag:
  `HTTP_TRANSPORT=legacy|fastapi`.
- Default staging to `fastapi` only after smoke tests pass.

## Phase B - Durable Storage Decision

Current decision: SQLite WAL is acceptable for the 10-person cohort after P0/P1.
Revisit Postgres only when measured contention or operational risk appears.

Decision thresholds:

- Stay on SQLite for <= 30 creators if p95 health/admin reads stay under 150 ms,
  websocket user-message acceptance stays under 250 ms, and DB locked incidents
  are below 1 per 1000 requests.
- Prepare Postgres for 100 creators if event volume grows beyond 500k rows,
  generation workers run in more than one process, or checkpoint write
  contention appears in logs.
- Require Postgres for 500 creators or any multi-instance deployment.

Migration scope:

- `messages`
- `events`
- `analyses`
- `rewrites`
- `anchors`
- `canvas_nodes`
- `canvas_edges`
- LangGraph checkpoints

Migration order:

1. Introduce repository interfaces with SQLite implementations retained.
2. Add Postgres implementations behind `APP_DB_URL`.
3. Build one-way copy command: SQLite to Postgres.
4. Run shadow-read verification for events/analyses/rewrites.
5. Switch writes to Postgres in staging.
6. Keep SQLite file read-only for rollback during one release window.

Rollback:

- For the first release, no destructive migration.
- If Postgres write path fails, revert `APP_DB_URL` and restart into SQLite.
- Any writes made only to Postgres during the failed window require export back
  to SQLite before rollback is considered complete.

Local dev:

- Default remains SQLite.
- Add optional `docker compose up postgres` path only when Postgres work begins.
- Test matrix should include SQLite always; Postgres only for storage-layer
  integration tests.

## Phase C - End-to-End Trace Propagation

Goal: make one creator action traceable across frontend, websocket, agent,
cascade services, upstream model calls, events, and admin queries.

Trace fields:

- `trace_id`: generated at frontend action start if absent.
- `run_id`: existing run/thread-scoped id.
- `request_id`: per HTTP request.
- `span_id`: optional for future nested spans.

Backend propagation:

- Accept `trace_id` in HTTP headers: `X-Trace-Id`.
- Accept `trace_id` in websocket command payloads.
- Store trace context in a ContextVar for agent/cascade calls.
- Add `trace_id` column to `events`.
- Include `trace_id` in failure payloads during transition for backwards
  compatibility with existing admin views.

Frontend propagation:

- Add a trace id to websocket user-message commands.
- Add `X-Trace-Id` to admin/analytics HTTP calls.
- Include trace id in frontend error reports.

Admin query examples:

```sql
SELECT created_at, event_name, user_id, run_id, payload_json
FROM events
WHERE trace_id = ?
ORDER BY created_at, id;
```

```sql
SELECT event_name, COUNT(*)
FROM events
WHERE created_at > datetime('now', '-1 hour')
GROUP BY event_name;
```

Acceptance criteria:

- One pasted URL can be followed from frontend action to `analysis_returned` or
  `failure_emitted`.
- Health/admin pages can show trace id for support without exposing provider
  secrets.
- No user-visible copy displays raw provider errors.

## Claude Implementation Checklist

- Draft FastAPI route map and parity tests.
- Add trace schema migration proposal.
- Produce Postgres readiness matrix for 30/100/500 creators.
- Identify all raw SQLite connection sites that must move behind repository
  interfaces before Postgres.
- Return with implementation PR plan before coding production transport.
