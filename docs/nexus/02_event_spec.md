# Phase 1 Event Spec — Minimum-Viable Telemetry

**Status**: Draft v1 · 工作规格
**Date**: 2026-05-19
**Author**: Analytics Reporter (Nexus)
**Authoritative source**: `PHASED_PLAN.md` §4.4 (Gate) + §7 (H1-H8) · `01_reviewer_synthesis.md` §5 (silent risks)
**Scope**: 12 events, 1 table, 0 dashboards. Founder reads SQL directly.
**One-liner**: Smallest possible event surface that (a) lets the founder judge Phase 1 Gate empirically and (b) makes Phase 3's learning-loop thesis verifiable retroactively.

---

## 0. Operating Constraints (read first)

1. **Backend-only emission.** All events fire from the Python backend in `backend/src/agent/`. No frontend SDK, no `track()` calls in React, no analytics vendor. Frontend tags are unreliable (ad-blockers, browser quits mid-run, offline) — and we already control every meaningful state transition server-side.
2. **No analytics SDK.** Internal `POST /events/batch` endpoint that accepts an array of event rows and inserts. No PostHog / GA / Amplitude / Mixpanel.
3. **No dashboards in Phase 1.** Founder runs SQL against the `events` table. The Phase 2 / Phase 3 dashboards (`DATA_DASHBOARD.md`) inherit this same table — Phase 1 is the foundation, not a throwaway.
4. **SQLite-first, Postgres-portable DDL.** OpenRHTV is on SQLite today (`backend/src/agent/tools/canvas.py`). The DDL below is written in Postgres dialect because Phase 2+ migrates to Postgres; Phase 1 can run it under SQLite by substituting `INTEGER PRIMARY KEY AUTOINCREMENT` for `BIGSERIAL` and `TEXT` for `JSONB` (SQLite stores JSON as TEXT and exposes `json_extract`). All queries in §3 use the JSON extraction syntax that works in both engines.
5. **≤12 events total.** This document proposes exactly **11**. If a 12th is added later, it costs us one. No 13th.
6. **Every event traces to a Gate row or an H-assumption.** If it doesn't, it's not in Phase 1.

---

## 1. Events Table Schema

### 1.1 DDL (Postgres dialect, SQLite-compatible)

```sql
CREATE TABLE events (
  id              BIGSERIAL PRIMARY KEY,
  event_name      VARCHAR(64)  NOT NULL,
  user_id         VARCHAR(64)  NOT NULL,        -- hashed (see §8); Phase 1 = single-tenant, never null
  run_id          VARCHAR(64),                  -- nullable: lifecycle events have no run
  occurred_at     TIMESTAMPTZ  NOT NULL,        -- server time at emission
  payload         JSONB        NOT NULL DEFAULT '{}',
  schema_version  SMALLINT     NOT NULL DEFAULT 1
);

CREATE INDEX idx_events_user_time      ON events (user_id, occurred_at DESC);
CREATE INDEX idx_events_name_time      ON events (event_name, occurred_at DESC);
CREATE INDEX idx_events_run            ON events (run_id) WHERE run_id IS NOT NULL;
CREATE INDEX idx_events_user_name_time ON events (user_id, event_name, occurred_at DESC);
```

**Why these four indexes and no more**:
- `(user_id, occurred_at)` — every "did user X do Y after Z" question
- `(event_name, occurred_at)` — every Gate roll-up
- `(run_id)` partial — joining all events of one run for cost / funnel reconstruction
- `(user_id, event_name, occurred_at)` — the learning-loop query in §4 hits this hard; without it the H8 reconstruction is a sequential scan

### 1.2 What's intentionally absent vs `DATA_DASHBOARD.md` §2.1

| Field in DATA_DASHBOARD | Phase 1 status | Reason |
|---|---|---|
| `tenant_id` | ❌ dropped | Single-tenant in Phase 1 (PHASED_PLAN §4.3 禁列项: 多租户). Add in Phase 2. |
| `session_id` | ❌ dropped | We don't ship session analytics in Phase 1. `user_id + occurred_at` window is sufficient. |
| `client_ip`, `user_agent`, `referrer`, `utm_*` | ❌ dropped | No attribution model in Phase 1. Founder recruited the 10 users by hand. |
| `daily_metrics` aggregate table | ❌ dropped | 11 events × 10 users × 6 weeks = trivial row count. Raw scan is fast enough. |
| `user_funnels` denormalized table | ❌ dropped | Reconstruct funnels from raw events via SQL in §3. |

### 1.3 Retention

- Phase 1: **never delete**. The corpus is ~10 users over 6 weeks; the entire table will fit in <50 MB. Deleting destroys the audit trail Phase 3 needs.
- Backup: `pg_dump` (or `.dump` for SQLite) into the project's S3 bucket weekly. Single command, no infra.
- Phase 2+ revisits archival per `DATA_DASHBOARD.md` ≥13mo policy.

---

## 2. Phase 1 Event Catalog (11 events)

Naming: `snake_case`, verb at end (`url_pasted`, not `paste_url`), past tense. Each event is one immutable fact.

All payloads also implicitly carry the table columns (`user_id`, `run_id`, `occurred_at`) — fields below are JSONB-only additions.

| # | event_name | Trigger (backend) | JSONB payload fields | Serves |
|---|---|---|---|---|
| 1 | `run_started` | Backend creates a new run record (POST `/runs`) | `entry_kind` ∈ {`url_paste`, `system_pick`}; `system_pick_rank` (1-5, null if URL paste); `url_host` (`douyin.com`/`xiaohongshu.com`/etc, null if system_pick); `niche_text_len` (int chars, never the text itself in this event); `niche_text_hash` (sha256 of trimmed text — see §4 H8) | **G1, G6** (funnel entry); **H1, H2** (hotspot-driven start) |
| 2 | `analysis_returned` | `normalize_analysis_result()` returns successfully (Phase 0 contract) | `schema_version`; `confidence` (float 0-1); `missing_fields` (string[]); `used_fallback` (bool); `latency_ms` (int) | **G7** (UI warning correctness depends on these flags); **H2** (downstream uses analysis fidelity) |
| 3 | `script_rewritten` | Niche-rewrite LLM call completes and parser yields valid script | `shot_count` (int, expect 3-5); `script_char_len` (int); `parser_warnings` (string[]) | **G6** (funnel mid-point); **H2, H3** (rewrite quality precondition) |
| 4 | `shot_generated` | An image-gen call for a shot node finishes (success **or** failure) | `shot_index` (int); `provider` (`gemini`/`apimart`/…); `model` (string); `outcome` ∈ {`done`, `failed`, `timeout`}; `attempt` (int, 1 = first try, 2+ = regenerate); `latency_ms`; `anchor_refs` (string[] of anchor_ids attached to this shot, empty if none — **critical for H8**) | **G2, G6** (creation completion); **H4, H8** (anchor reuse at point of use) |
| 5 | `publish_pack_copied` | Backend serves `/runs/:id/publish_pack` and frontend ack arrives (or backend logs clipboard endpoint hit) | `shot_count_in_pack` (int); `has_title` (bool); `has_tags` (bool); `script_char_len` (int) | **G2** (definition of "completed first content"); **G6** (funnel terminal); **H5** |
| 6 | `anchor_created` | Anchor row inserted into anchors table | `anchor_id`; `anchor_type` ∈ {`character`, `scene`}; `source_run_id` (the run this anchor was extracted from) | **G8** (precondition); **H4, H8** |
| 7 | `anchor_reused` | An anchor is attached to a node in a run **whose `source_run_id` differs from current `run_id`** | `anchor_id`; `anchor_type`; `source_run_id`; `current_run_id`; `days_since_created` (int) | **G8** (the actual "began to accumulate" signal, per Q8 in 01_phase1_requirements §6); **H4, H8** (the learning-loop core) |
| 8 | `failure_emitted` | Any backend exception that maps to the failure taxonomy fires this **before** the recovery UI is sent | `failure_code` (one of the 8 in KARPATHY §3.9: `DOWNLOAD_FAILED`, `ANALYSIS_TIMEOUT`, `SCHEMA_INVALID`, `MISSING_DIALOGUE`, `MISSING_VISUAL_CONTENT`, `ANCHOR_EXTRACTION_FAILED`, `PROVIDER_REJECTED`, `COST_LIMIT_EXCEEDED`); `stage` ∈ {`analysis`, `rewrite`, `shot_gen`, `anchor_extract`, `publish`}; `recovery_path_id` (string, must be non-null — empty string = silent failure, which we forbid) | **G7** (100% next-step rate); **H7**; silent-risk **S6** (静默失败 = 0) |
| 9 | `failure_recovered` | User takes any one of: retry, regenerate, accept-degraded, manual-override — i.e. a UI action that the backend can attribute to a prior `failure_emitted` (correlate by `run_id` + last open failure within 30min) | `failure_code` (copied from the originating failure); `recovery_action` ∈ {`retry`, `regenerate`, `accept_degraded`, `manual_skip`, `abandon`}; `seconds_since_failure` (int) | **G7** (failure → next-step rate); **H7** (failure-recovered users don't churn); silent-risk **S7** (per-failure-type recovery) |
| 10 | `generation_cost` | Every LLM call **and** every image-gen call, success or failure | `run_id` (already in column, but reaffirmed for joins); `call_kind` ∈ {`analysis`, `rewrite`, `shot_image`, `anchor_image`}; `provider`; `model`; `cost_fen` (int — store in 分, never floats); `latency_ms`; `tokens_in` (int, null for image); `tokens_out` (int, null for image); `outcome` ∈ {`done`, `failed`} | **G5** (单条 < ¥15); **H6** (¥39/月 unit economics) |
| 11 | `interview_logged` | Founder runs a CLI/admin script after each of the 10 interviews | `value_statement_match` ∈ {`yes`, `partial`, `no`} (did the user say "it helped me turn hot content into mine"-equivalent?); `would_pay_39` ∈ {`yes`, `maybe`, `no`}; `notes_url` (S3 link to transcript, or empty); `niche` (string) | **G4** (≥2 say the value sentence — not measurable from product behavior); **H6** subjective check |

**That's 11.** Defense for not adding a 12th: every additional event is debt — code to write, payload schema to govern, queries to keep working. The founder can hold 11 in their head. They can't hold 25.

---

## 3. Phase 1 Gate Measurement Queries

Every query below has been written against the schema in §1. Each is a one-liner the founder can paste into `psql` (or `sqlite3 -cmd ".mode column"`). The JSON extraction syntax `payload->>'x'` is Postgres; for SQLite, substitute `json_extract(payload, '$.x')`.

### G1 — Real creators ≥ 10

```sql
SELECT COUNT(DISTINCT user_id) AS unique_users
FROM events
WHERE event_name = 'run_started';
-- Pass: unique_users >= 10
```

### G2 — Completed first content ≥ 5

```sql
SELECT COUNT(DISTINCT user_id) AS users_completed
FROM events
WHERE event_name = 'publish_pack_copied';
-- Pass: users_completed >= 5
```

### G3 — Returned within a week ≥ 3

```sql
WITH first_run AS (
  SELECT user_id, MIN(occurred_at) AS first_at
  FROM events WHERE event_name = 'run_started'
  GROUP BY user_id
),
later_run AS (
  SELECT e.user_id
  FROM events e
  JOIN first_run f ON e.user_id = f.user_id
  WHERE e.event_name = 'run_started'
    AND e.occurred_at > f.first_at
    AND e.occurred_at <= f.first_at + INTERVAL '7 days'
  GROUP BY e.user_id
)
SELECT COUNT(*) AS users_returned_within_7d FROM later_run;
-- Pass: >= 3
```

### G4 — ≥ 2 users say the value sentence

```sql
SELECT COUNT(*) AS users_match
FROM events
WHERE event_name = 'interview_logged'
  AND payload->>'value_statement_match' = 'yes';
-- Pass: >= 2
```

### G5 — Per-run cost < ¥15 (median + P95)

```sql
WITH per_run AS (
  SELECT run_id, SUM((payload->>'cost_fen')::INT) AS total_fen
  FROM events
  WHERE event_name = 'generation_cost' AND run_id IS NOT NULL
  GROUP BY run_id
)
SELECT
  COUNT(*)                                                    AS runs,
  ROUND(AVG(total_fen) / 100.0, 2)                            AS mean_yuan,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_fen) / 100.0, 2) AS median_yuan,
  ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_fen) / 100.0, 2) AS p95_yuan,
  ROUND(MAX(total_fen) / 100.0, 2)                            AS max_yuan
FROM per_run;
-- Pass: median_yuan < 15 AND p95_yuan < 22 (P95 headroom check, not in Gate but useful)
```

### G6 — Hotspot → creation conversion ≥ 15%

```sql
WITH starts AS (SELECT DISTINCT run_id FROM events WHERE event_name = 'run_started'),
     ends   AS (SELECT DISTINCT run_id FROM events WHERE event_name = 'publish_pack_copied')
SELECT
  (SELECT COUNT(*) FROM starts)                                   AS runs_started,
  (SELECT COUNT(*) FROM ends)                                     AS runs_published,
  ROUND(100.0 * (SELECT COUNT(*) FROM ends) / NULLIF((SELECT COUNT(*) FROM starts), 0), 1) AS conversion_pct;
-- Pass: conversion_pct >= 15.0
```

### G7 — Failure → next-step rate = 100%

```sql
-- Part A: silent failures must be zero (any failure_emitted with empty recovery_path_id)
SELECT COUNT(*) AS silent_failures
FROM events
WHERE event_name = 'failure_emitted'
  AND COALESCE(payload->>'recovery_path_id', '') = '';
-- Pass: silent_failures = 0

-- Part B: every failure has a corresponding failure_recovered OR abandon (recovery_action='abandon' is still a "next step" — the user chose to leave knowingly)
WITH f AS (
  SELECT id, run_id, occurred_at, payload->>'failure_code' AS code
  FROM events WHERE event_name = 'failure_emitted'
),
r AS (
  SELECT run_id, occurred_at, payload->>'failure_code' AS code
  FROM events WHERE event_name = 'failure_recovered'
)
SELECT
  COUNT(*) AS total_failures,
  SUM(CASE WHEN EXISTS (
    SELECT 1 FROM r
    WHERE r.run_id = f.run_id AND r.code = f.code
      AND r.occurred_at BETWEEN f.occurred_at AND f.occurred_at + INTERVAL '30 minutes'
  ) THEN 1 ELSE 0 END) AS failures_with_next_step,
  ROUND(100.0 * SUM(CASE WHEN EXISTS (
    SELECT 1 FROM r WHERE r.run_id = f.run_id AND r.code = f.code
      AND r.occurred_at BETWEEN f.occurred_at AND f.occurred_at + INTERVAL '30 minutes'
  ) THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS next_step_pct
FROM f;
-- Pass: silent_failures = 0 AND next_step_pct = 100.0
```

### G8 — ≥ 2 users actually reused an anchor across runs

Per `01_phase1_requirements §6 Q8` default: "creation alone doesn't count, cross-run reuse counts".

```sql
SELECT COUNT(DISTINCT user_id) AS users_with_cross_run_reuse
FROM events
WHERE event_name = 'anchor_reused'
  AND (payload->>'source_run_id') <> (payload->>'current_run_id');
-- Pass: >= 2
```

---

## 4. Learning-Loop Event Subset (the 5 events Phase 3 cannot live without)

This is the section the Reviewer Synthesis §5 (silent risk S3) flags as the single biggest gap. Phase 3 will try to answer H8: **does the system get smarter as the user uses it?** That question is only answerable if Phase 1 collects the right traces *now*. If we miss them, Phase 3 has no data to mine and the moat thesis dies silently.

The 5 events, ranked by "if we could only ship five, ship these":

| Rank | Event | Why H8 dies without it |
|---|---|---|
| 1 | `run_started` | Anchors the temporal series per user. Without it we cannot order a user's 1st vs Nth creation, and "did N improve over 1" is meaningless. The `niche_text_hash` field is the H8-critical addition — it lets Phase 3 ask "did this user's niche description converge / drift across runs?" without exposing free-text PII in queries (the raw text lives in the canvas tables but is fetched only when analyzing). |
| 2 | `anchor_created` | The numerator's denominator. We cannot measure reuse rate without knowing what existed to be reused, and when. The `source_run_id` field lets us reconstruct the creation lineage. |
| 3 | `anchor_reused` | The actual learning-loop signal. The `(source_run_id, current_run_id, days_since_created)` triple is what Phase 3 regresses to test H4 + H8: does asset reuse compound over time? Without this exact triple — not just "an anchor was used" — Phase 3 cannot distinguish "user picked their own old anchor" from "user picked a template anchor", which is the whole compounding question. |
| 4 | `shot_generated` (with `anchor_refs` field) | The use-at-point-of-use signal. `anchor_reused` says "user attached an anchor", but `shot_generated.anchor_refs` says "the anchor was actually consumed by a generation". The delta between these two is exactly the "did they use it for show or for real" question Phase 3 will want to answer. |
| 5 | `script_rewritten` (with `parser_warnings`) | The quality-over-time signal. Phase 3 will want to ask "did this user's rewrite-quality acceptance rate improve as they did more runs?" — we need the per-run rewrite trace, and `parser_warnings` is the cheapest proxy for "did the LLM start producing cleaner outputs for this user over time" (under the H8 hypothesis where prompt/anchor context accumulates). |

**Defense of each, in one sentence:**

1. `run_started` — without it, no temporal series exists; nothing else is interpretable.
2. `anchor_created` — without the creation timestamp + provenance, reuse is unattributable.
3. `anchor_reused` — the direct H8 signal; the only event that operationalizes "compounding asset reuse".
4. `shot_generated.anchor_refs` — distinguishes attachment from consumption; closes the gap between intent and behavior.
5. `script_rewritten.parser_warnings` — the cheapest quality-trend proxy that doesn't require human labeling.

**If only these 5 ship and the other 6 don't, Phase 1 Gate measurement degrades but the Phase 3 moat thesis stays alive.** This is the order of priority.

### Sample Phase-3-style query (do not run in Phase 1, but the data must be there):

```sql
-- For each user's Nth run, how many anchors did they reuse from any prior run?
WITH ordered_runs AS (
  SELECT user_id, run_id, occurred_at,
         ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY occurred_at) AS run_index
  FROM events WHERE event_name = 'run_started'
),
reuse_per_run AS (
  SELECT r.user_id, r.run_index, COUNT(*) AS reused_count
  FROM ordered_runs r
  JOIN events e ON e.run_id = r.run_id
              AND e.event_name = 'anchor_reused'
  GROUP BY r.user_id, r.run_index
)
SELECT run_index,
       AVG(reused_count)        AS avg_reuses,
       COUNT(DISTINCT user_id)  AS users_at_this_run_count
FROM reuse_per_run
GROUP BY run_index
ORDER BY run_index;
-- Phase 3 reads this. If avg_reuses trends up with run_index, H8 has a pulse.
```

---

## 5. Failure-Recovery Telemetry

Karpathy's hard requirement (KARPATHY §3.9 + Reviewer Synthesis §5 S6 / S7): **silent failures = 0** and **100% of failures have a UI-visible next-step**.

### 5.1 The pair

`failure_emitted` (event #8) and `failure_recovered` (event #9) form a paired protocol. Backend invariant:

> Every code path that returns an error to the user MUST emit `failure_emitted` with a non-empty `recovery_path_id` **before** the response is sent. Any code path that doesn't is a silent failure by definition.

This is enforceable as a backend middleware in `backend/src/agent/server.py`: a try/except wrapper around handlers that intercepts uncaught exceptions and emits a `failure_emitted` with `failure_code='UNCAUGHT'` and forces the response. Phase 0 P0-6 defines the 8 codes; the wrapper catches the 9th case.

### 5.2 The proof query

The G7 query (§3, Part A + Part B) is the proof. The founder runs it once a week. If `silent_failures > 0` ever, the offending row's `run_id` points at the broken handler. If `next_step_pct < 100`, the unrecovered failures' `failure_code` distribution tells the founder which class of failure is bleeding users.

### 5.3 Per-failure-type breakdown (silent-risk S7)

```sql
SELECT
  payload->>'failure_code' AS code,
  COUNT(*) AS total,
  SUM(CASE WHEN EXISTS (
    SELECT 1 FROM events r
    WHERE r.event_name = 'failure_recovered'
      AND r.run_id = events.run_id
      AND r.payload->>'failure_code' = events.payload->>'failure_code'
      AND r.occurred_at BETWEEN events.occurred_at AND events.occurred_at + INTERVAL '30 minutes'
  ) THEN 1 ELSE 0 END) AS recovered,
  ROUND(100.0 * SUM(CASE WHEN EXISTS (
    SELECT 1 FROM events r
    WHERE r.event_name = 'failure_recovered'
      AND r.run_id = events.run_id
      AND r.payload->>'failure_code' = events.payload->>'failure_code'
      AND r.occurred_at BETWEEN events.occurred_at AND events.occurred_at + INTERVAL '30 minutes'
  ) THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS recovery_pct
FROM events
WHERE event_name = 'failure_emitted'
GROUP BY payload->>'failure_code'
ORDER BY total DESC;
-- Founder reads: which failure class has the worst recovery rate? That's the next fix.
```

---

## 6. Cost Telemetry

Single event: `generation_cost` (event #10). Every LLM call, every image call, success or failure. Costs are stored as `cost_fen` (integer 分, never float ¥) to avoid float drift on aggregation.

### 6.1 Median + P95 ¥/run

Already shown as **G5** in §3. Repeating the median/P95 portion for convenience:

```sql
WITH per_run AS (
  SELECT run_id, SUM((payload->>'cost_fen')::INT) AS total_fen
  FROM events
  WHERE event_name = 'generation_cost' AND run_id IS NOT NULL
  GROUP BY run_id
)
SELECT
  ROUND(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY total_fen) / 100.0, 2) AS median_yuan,
  ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_fen) / 100.0, 2) AS p95_yuan
FROM per_run;
```

### 6.2 Cost-by-provider triage

```sql
SELECT
  payload->>'call_kind' AS kind,
  payload->>'provider'  AS provider,
  payload->>'model'     AS model,
  COUNT(*)                                       AS calls,
  ROUND(SUM((payload->>'cost_fen')::INT)/100.0, 2) AS total_yuan,
  ROUND(AVG((payload->>'cost_fen')::INT)/100.0, 4) AS avg_yuan_per_call
FROM events
WHERE event_name = 'generation_cost'
GROUP BY 1, 2, 3
ORDER BY total_yuan DESC;
-- Founder reads: which (kind, provider, model) is eating the budget?
```

### 6.3 Hard-cap enforcement is *not* an analytics concern

P1-9's ¥15 hard block is enforced at write-time in the backend (compare running sum to cap before issuing the call). The `generation_cost` event is the **post-hoc** record. If the cap was hit, a `failure_emitted` with `failure_code='COST_LIMIT_EXCEEDED'` fires immediately after. The events table is the audit trail of "what we charged the user", not the gate that prevents the charge.

---

## 7. Anti-Event List (what we deliberately do NOT instrument in Phase 1)

These are tempting and were proposed in `DATA_DASHBOARD.md`. They are **off the table for Phase 1**:

| Not-instrumented | Why |
|---|---|
| `user_signup` / `user_activated` / `user_session_start` / `user_session_end` | Phase 1 = 10 hand-recruited users, founder knows every name. No funnel-from-signup analysis. Adds noise. |
| `topic_card_view` / `hotspot_score_visible` | The 5 system-picked hotspots are static JSON (per Q2). Tracking views requires frontend instrumentation we explicitly forbid. |
| `enter_canvas_from_trending` | We don't have a `/trending` page in Phase 1. |
| `gate_review_completed` (per-node review) | Conflates with `shot_generated.outcome`; redundant. |
| `node_retry` (separate from `shot_generated.attempt`) | The `attempt` field on `shot_generated` already captures retries. A separate event is double-counting. |
| `run_cancelled` | "Abandonment" is inferrable: any run with `run_started` but no `publish_pack_copied` within 24h is abandoned. Don't pay for an explicit event when SQL gives it free. |
| `niche_index_activated` / `niche_index_edited` | No niche-index UI in Phase 1 (per PHASED_PLAN §4.3: 赛道索引 is Phase 3). The `niche_text_hash` on `run_started` is enough for H8 reconstruction. |
| `agent_triggered` / `agent_response_user` | No Agent UI 5 triggers in Phase 1 (PHASED_PLAN §4.3 red line). |
| `quota_warning` / `upgrade_clicked` / `paid_conversion` | No commercialization in Phase 1 (PHASED_PLAN §4.3 red line). `interview_logged.would_pay_39` is the Phase 1 substitute. |
| Rage-clicks / scroll-depth / heatmaps / session replay | Need product-mature UX hypotheses to interpret. Phase 1 has no such hypotheses. Frontend instrumentation we forbid anyway. |
| A/B framework events (`experiment_assigned`, `experiment_exposed`) | N=10 is statistically too small for A/B. No framework needed. |
| Funnel-stage events (`first_create`, `first_complete`, `repeat_create_d7`) | These are *derived* from raw events. The Phase 2 `user_funnels` table is the right home; Phase 1 reconstructs via SQL. |

**The discipline**: any new event proposal in Phase 1 must answer "which Gate row or H-assumption breaks without it?" If the answer is "none", it doesn't ship.

---

## 8. PII / Compliance Check (China context)

Phase 1 runs in the founder's account with ≤10 hand-recruited creators. PIPL applies but the data surface is small. Rules:

### 8.1 Hashed / pseudonymized
- `user_id` — **never store WeChat openid, phone, or real name in `user_id`.** Generate an opaque random ID (e.g. `usr_<8 hex>`) at first sign-in and store the mapping in a separate `users` table that is NEVER joined into queries that get shared. The `events` table itself is researcher-readable.
- `niche_text` — the raw free-text niche description **is not stored in events**. Only `niche_text_len` and `niche_text_hash` (sha256). The raw text lives in the canvas/run record under access control.
- `url_host` — store the host only (`douyin.com`), never the full URL. Full URLs can contain creator-identifying share tokens.

### 8.2 Plain stored
- Anchor IDs, run IDs, event timestamps, costs, latencies, failure codes, outcomes — all non-PII operational data.
- `interview_logged.notes_url` — S3 path; the transcripts themselves require user consent at interview time and are stored in an access-controlled bucket. Phase 1 founder is the only reader.

### 8.3 Don't store, ever
- IP address, user agent, exact location.
- Raw script content, raw analysis JSON, raw rewrite output — these live in the canvas SQLite, not in events.
- Phone, email, WeChat ID, real name.

### 8.4 Right-to-delete
- A single `DELETE FROM events WHERE user_id = ?` handles the PIPL right-to-erasure request. Because we only have hashed IDs, this is mechanically clean. The mapping in the separate `users` table is deleted in the same transaction.

---

## 9. Verdict — can the founder really judge Phase 1 Gate from 11 events?

**Yes, with one explicit caveat.**

| Gate | Measurable from 11 events alone? |
|---|---|
| G1 unique users ≥ 10 | ✅ `run_started` distinct user_id |
| G2 first content ≥ 5 | ✅ `publish_pack_copied` distinct user_id |
| G3 7-day return ≥ 3 | ✅ `run_started` temporal join |
| G4 value-statement ≥ 2 | ⚠ requires `interview_logged` — which is **not** product-emitted, it's founder-emitted. This is the caveat: G4 fundamentally cannot be measured from product telemetry alone. We logged the interview into the same table to keep the answer in one SQL surface, but the founder must do the interviews. No event design solves this. |
| G5 median cost < ¥15 | ✅ `generation_cost` aggregate |
| G6 ≥ 15% hotspot→pack | ✅ `run_started` ÷ `publish_pack_copied` |
| G7 100% next-step | ✅ `failure_emitted` + `failure_recovered` paired |
| G8 ≥ 2 anchor cross-run reuse | ✅ `anchor_reused` with source_run_id ≠ current_run_id |

7 of 8 Gates are fully product-measurable. G4 is fundamentally a human-judgment question and the spec acknowledges it (event #11 = founder script, not product code).

**Phase 3's H8 thesis is also defensible from this spec** — see §4. The 5 events identified are the irreducible core. Anything thinner kills the moat reconstruction; anything fatter is debt.

The 11 events fit on a single page. The founder can hold the entire telemetry surface in their head while reading code. That is the point.

---

## 10. Implementation note (single paragraph)

Backend adds one module: `backend/src/agent/events.py` exposing `emit(event_name: str, *, user_id: str, run_id: str | None, payload: dict) -> None`. It writes one row to the local SQLite `events.db`. A weekly cron `pg_dump`/`.dump` to S3 is the only ops. The `POST /events/batch` endpoint is for future frontend needs (Phase 2+); Phase 1 doesn't use it — all 11 events are emitted from server-side call sites already inside the Python backend. No new infra, no new vendor, no dashboards. The events table itself is the Phase 1 deliverable.

---

*Any 12th event proposal must (a) name the Gate row or H-assumption it serves, (b) name the existing event it cannot be derived from, (c) name what gets dropped to stay at 12. No exceptions.*
