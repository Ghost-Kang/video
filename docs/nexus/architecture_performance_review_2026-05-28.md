# Architecture + Performance Review - 2026-05-28

## Executive Summary

Current Cascade architecture is healthy for the 10-person cohort: transport,
cascade services, persistence, and frontend stores are now separated enough to
ship quickly. The next performance gains should come from avoiding duplicate
expensive work and preventing synchronous IO from degrading the realtime chat
experience. This is not a rewrite moment.

## P0 — Completed By Codex

1. Per-thread agent serialization
   - Problem: `user_message` spawned `run_agent` tasks directly. Double-send or
     autosend/reconnect could run two Director turns against one LangGraph
     checkpoint and duplicate upstream analysis.
   - Change: `backend/src/agent/transport/ws_handlers.py` now serializes
     `run_agent` per `thread_id` with an `asyncio.Lock`.
   - Expected impact: lower duplicate cost, fewer checkpoint races, clearer UX.

2. SQLite write contention hardening
   - Problem: hot SQLite paths mixed `sqlite3` and `aiosqlite`; lock waits could
     surface as slow WS/HTTP handling.
   - Change: core SQLite connections now set `journal_mode=WAL`,
     `synchronous=NORMAL`, and `busy_timeout=5000` across cascade persistence,
     message store, canvas persistence, and anchors.
   - Expected impact: better concurrent read/write behavior under cohort bursts.

3. Health summary SQL aggregation
   - Problem: `/api/health/summary` loaded up to 1000 events and aggregated in
     Python.
   - Change: event counts now use SQL `GROUP BY`; recent failures and failure
     stage parsing only fetch the minimal needed rows.
   - Expected impact: admin health remains cheap as `events` grows.

4. Same source URL cross-user analysis reuse
   - Problem: the same public Douyin URL analyzed by different creators caused
     duplicate upstream model calls.
   - Change: analysis service checks the latest stored analysis for the source
     URL globally, clones it to a user-scoped `analysis_id`, and emits a normal
     `analysis_returned` event without calling upstream again.
   - Expected impact: large cost/latency win when cohort users test the same
     trending videos.

## P1 - Completed By Codex

1. Frontend route-level code splitting
   - Problem: landing, chat, admin, analytics, and React Flow loaded in one
     large bundle.
   - Change: `App` chat route plus admin/analytics routes are lazy-loaded behind
     `Suspense`.
   - Expected impact: lighter first load for landing/invite users; chat/admin
     code is fetched only when needed.

2. Generation queue lease/backoff
   - Problem: generation workers recovered every submitted/polling task without
     a durable lease, so restart recovery and transient provider errors could
     cause tight retries or duplicate polling under multiple workers.
   - Change: canvas generation nodes now persist `attempt_count`, `lease_until`,
     and `next_retry_at`; claim/recover paths take a lease and transient worker
     exceptions schedule exponential-backoff retries.
   - Expected impact: more deterministic recovery and lower provider pressure
     during provider or network instability.

## P1 - Recommended Next Codex Follow-Up

These are not in the current patch because they touch longer-running behavior
and should ship with product-level soak:

1. Analysis staged contract
   - Return the core analysis as soon as `viral_analysis + scenes` are ready.
   - Push transcript/audio/production patches as follow-up WS frames.
   - Goal: reduce perceived analysis latency even when transcript is slow.

## P2 - Plan Prepared For Claude

Owner: Claude

Scope: transport and storage evolution, not product UI.

Tasks:

1. FastAPI/Starlette transport migration plan
   - Keep existing service functions intact.
   - Replace the hand-written HTTP router with typed route declarations,
     request logging, response compression, CORS policy, and OpenAPI docs.
   - WS can remain on `websockets` initially; propose whether to migrate it in
     the same phase or after HTTP stabilizes.

2. Durable datastore decision
   - Evaluate SQLite-with-WAL ceiling vs Postgres for 30/100/500 creator
     cohorts.
   - Include migration plan for `messages`, `events`, `analyses`, `rewrites`,
     `anchors`, and LangGraph checkpoints.
   - Include rollback story and local-dev story.

3. End-to-end tracing design
   - Introduce `trace_id`/`run_id` propagation across WS commands, agent turns,
     cascade tools, events, upstream calls, and frontend error reports.
   - Output should include schema changes, event payload updates, and sample
     admin query patterns.

Deliverables:

- `docs/nexus/architecture_transport_storage_P2_plan.md`
- Handoff docs for Codex/Cursor if implementation is split.
- No production code changes unless explicitly approved after review.

## Architecture Notes

- Do not replace LangGraph or DeepAgents right now. Current pain is
  orchestration and IO, not agent framework fit.
- Do not introduce Redis/Postgres just for 10 cohort users. Add clean seams now;
  migrate only when measured contention or operational risk justifies it.
- Keep event names typed and preserve WS codegen as the source of truth for
  frontend/server contract drift.

## Verification

Codex verification for this round:

- Backend targeted tests: health summary + analysis service.
- Backend full pytest.
- Frontend TypeScript check.
- Frontend unit test suite.
- Frontend production build.
