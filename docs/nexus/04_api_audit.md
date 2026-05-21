# Cascade API Surface Audit (Phase 0 → Phase 1 transition)

**Auditor**: API Tester (contract-surface review only)
**Date**: 2026-05-19
**Scope**: `agent.cascade.contract`, `agent.cascade.failures` (error envelope), `codex_backend_P1-2.md` brief, `frontend/src/types/cascade.ts`.
**Out of scope**: implementation correctness of `analysis_service.py` (already partly built — its current test suite is acknowledged but not graded).

---

## Verdict: **NEEDS SPEC PATCH** before P1-2 lands

The contract types are clean and the adapter is rigorous. **Three contract-surface gaps will block Codex on day 1** of P1-2 implementation and **two more will silently break the frontend** the first time a 422 hits the wire. None require code changes to `contract.py` or `failures.py` — they require spec text in the brief and one shared lookup table. Patches are listed in §B below.

The **single biggest spec gap** Codex hits on day 1: the brief says "Caller (route handler) converts to HTTP 422 with `HardFailure.to_payload()` as the JSON body" but **does not specify the HTTP status code for any failure code, the response shape for non-HardFailure errors (network, validator, unknown), or whether `detail` is safe to render**. Codex will either invent a mapping (and the frontend will mirror that invention) or stall. See Finding F1 and patch P1.

---

## A. Findings (numbered)

### F1. [BLOCKING] No `FailureCode → HTTP status` map exists anywhere

**Where it bites**: `analysis_service.py` route handler — line "Caller … converts to HTTP 422" in the brief.

**Evidence**:
- `failures.py` defines 8 `S*` codes (S1–S8).
- `to_payload()` is HTTP-shape but emits no status.
- `codex_backend_P1-2.md` §2 docstring says "HTTP 422" for all of them — but S7 (`UPSTREAM_TIMEOUT`) and S8 (`UPSTREAM_REFUSED`) are NOT user-input errors; they are gateway/upstream failures that conventionally map to **504 / 502 / 503**, never 422.
- Mixing user-input (422) and upstream-availability (5xx) under one status code:
  - Breaks default browser/proxy/CDN retry behavior (CDNs cache 4xx, retry 5xx).
  - Makes uptime SLOs un-measurable (a 422 spike no longer distinguishes "users sending bad URLs" from "doubao is down").
  - Misleads APM tools (Sentry, Datadog) about ownership — 422 = client team, 5xx = platform team.

**Mapping I recommend the contract author publish** (NOT my invention — this is the spec gap I'm naming):

| FailureCode | HTTP status | Rationale category |
|---|---|---|
| S1_NO_SOURCE_URL | 400 | malformed request body |
| S2_VERSION_MISMATCH | 422 | semantically invalid (upgrade required) |
| S3_NO_FORMULA | 422 | unprocessable content |
| S4_SCENES_LEN_OUT_OF_RANGE | 422 | unprocessable content |
| S5_INVALID_PAYLOAD | 422 | unprocessable content |
| S6_NEGATIVE_COST | 500 | internal accounting bug — never user-caused |
| S7_UPSTREAM_TIMEOUT | 504 | gateway timeout |
| S8_UPSTREAM_REFUSED | 503 | upstream unavailable / rate-limited |

This table must live in either `failures.py` (as a `HTTP_STATUS: dict[str, int]`) or the handoff brief §2. Don't ask Codex to invent it.

### F2. [BLOCKING] `actions` is an array of opaque strings with no documented catalog

**Where it bites**: every frontend banner that needs to render recovery buttons.

**Evidence**:
- `failures.py` `RECOVERY_ACTIONS` enumerates 7 distinct opaque string tokens: `RETRY_WITH_NEW_URL`, `PICK_FROM_FEATURED`, `REPORT`, `RELOAD`, `RETRY_SAME_URL`, `RETRY_SAME_URL_AFTER_30S`, `RETRY_SAME_URL_AFTER_60S`.
- `cascade.ts` does not define a `RecoveryAction` union type at all — it imports the error envelope through nothing.
- `TOPRADOR_SCHEMA.md` documents warning codes but never documents action codes.
- Brand Guardian §4 says "no English jargon visible to user" — but these enum *values* are English. So they must be intermediate: the frontend maps token → button label + onClick handler. **Where is that mapping defined?** Today: nowhere.

**Concrete consequences if not fixed**:
- Frontend developer guesses `RETRY_WITH_NEW_URL` means "show a URL input" — backend author meant "open the URL-paste modal already in App.tsx". Drift.
- New action added in failures.py (e.g., `WAIT_AND_REPORT`) — frontend renders a button with no handler. Silent UX regression.

**What's missing**: A single shared enum (typed in both languages) + label/handler contract. See patch P2.

### F3. [BLOCKING] `detail` field leakage risk into UI

**Where it bites**: `HardFailure.to_payload()` line `"detail": self.detail`.

**Evidence in adapter.py**:
- Line 95: `raise HardFailure(FailureCode.S5_INVALID_PAYLOAD, str(e)) from e` — `str(e)` is the raw Pydantic ValidationError. That string contains JSON paths like `viral_analysis.replicable_formula → ValueError("must not be blank")`, internal field names, and sometimes user-supplied payload values quoted back.
- Line 219, 277, 540: same pattern — Pydantic `ValidationError` text propagates verbatim into `detail`.
- The frontend has no documented rule "do not render `detail` to end-users". `cascade.ts` doesn't even mark `detail` as internal.

**Consequences**:
- Field-name exposure violates the *Brand Guardian §4 "never expose field names"* rule.
- A maliciously crafted source_url that hits `S5_INVALID_PAYLOAD` could put attacker-controlled text into the banner (XSS surface — depends on frontend escaping, but the *contract* gives no warning).
- Internal model identifiers, stack-trace-flavored strings, and Python `repr()` output reach the UI today.

**What's missing**: explicit spec rule on `detail` — "debug-only, never user-visible; UI uses `hint` for display." Plus a `request_id` / `trace_id` field so support can correlate without showing detail. See patch P3.

### F4. [SHOULD FIX] TypeScript mirror drift — no CI check

**Where it bites**: every time `contract.py` or `failures.py` changes.

**Evidence**:
- `cascade.ts` is hand-written and marked "Keep in sync with backend/src/agent/cascade/contract.py".
- No script in `package.json` or CI workflow checks drift.
- `cascade.ts` is **already drifted** — it does not include any error-envelope type. It mirrors the success contract only.
- `failures.py` has 12 warning codes; `cascade.ts` has zero typed warning codes (only `code: string`).

**Minimum check** (see patch P5): one Python script that emits JSON Schema from `CascadeAnalysisContract` + the enum lists, diffs against a checked-in `cascade.schema.json`, fails CI on diff. Frontend then runs `quicktype` (or hand-mirrors) and the same script lints `cascade.ts`'s enum literals against the JSON.

### F5. [SHOULD FIX] `analysis_id` vs `source_url+user_id` idempotency contradiction

**Where it bites**: persistence layer, every retry, every "did I already analyze this" check.

**Evidence**:
- `TOPRADOR_SCHEMA.md` §1: `analysis_id` is a ULID, *"lexicographically sortable"*, generated per analysis.
- `codex_backend_P1-2.md` §3 SQL: `analysis_id TEXT PRIMARY KEY` → unique per row.
- `codex_backend_P1-2.md` §6: "Idempotency: calling twice with the same `source_url + user_id` does NOT create two analyses" — but ULIDs are time-monotonic, so a second call would naturally produce a *different* analysis_id.
- The existing implementation (`test_idempotency_same_user_and_url`) resolves this by returning the *first* call's contract on the second call — which means the API contract semantic is **"`source_url+user_id` is the logical key; `analysis_id` is opaque storage key"**. But this is nowhere in the spec.

**Open contract question** (I'm naming it, not answering it):
- Does `POST /api/analysis/shallow` always return the **same `analysis_id`** for the same `(source_url, user_id)` pair? (Today: yes, by current impl. Spec: silent.)
- What if the *model* changed between the two calls? Is that a new analysis or a cached return of the stale one?
- What if `cost_cny` matters for billing — second call should it count as 0 (cache hit) or full cost (re-run)?
- What HTTP status: 200 (re-returning), 201 (created), or 200 with `X-Cache: HIT`?

The contract author needs to pick one. Codex can implement whatever is picked.

### F6. [SHOULD FIX] `warnings[]` includes `severity: info` items meant for audit, not UI

**Where it bites**: every banner / card that iterates `warnings` and shows them.

**Evidence**:
- `failures.py` `W10_AUTHOR_PII_STRIPPED` has `RECOVERY_HINTS[...] = ""` (deliberately blank, "silent; never shown").
- `W1_AUTO_ID`, `W5_TIMESTAMPS_SORTED`, `W7_CONFIDENCE_COMPUTED`, `W9_CROSS_BORDER_SOURCE`, `W11_CONFIDENCE_CLAMPED`, `W12_TIMESTAMP_CLAMPED` all carry `severity: info` and are intended for logs.
- `cascade.ts` exposes the full `warnings` array with no filter hint.
- If frontend naively renders `warnings.map(...)`, every `info` warning becomes a UI element. Worst case: 6+ "silent" warnings clutter the card.

**Open contract question**: should the HTTP response wire-shape *strip* `severity: info` warnings before sending? Or send all and trust the client to filter? Today: nowhere stated. Frontend will guess.

### F7. [NICE TO HAVE] No pagination or list-endpoint shape decided

**Where it bites**: when /api/analyses (list) is added in P1-4+.

**Evidence**:
- `codex_backend_P1-2.md` only specifies the single-item POST endpoint.
- SQL schema has `idx_analyses_user(user_id, created_at DESC)` — implies a list endpoint is planned.
- No cursor / page-size contract exists.

**Not blocking P1-2.** Flag now because the contract type returned by list is presumably `CascadeAnalysisContract[]` — and full payloads in a list view are wasteful (each is ~30 KB JSON with all scenes). A list-summary type is missing from `cascade.ts`. Specify before P1-4.

### F8. [NICE TO HAVE] No deprecation/migration story for `schema_version` 1.0 → 1.1

**Evidence**:
- `TOPRADOR_SCHEMA.md` §10: "Future field additions: bump to `1.x` (minor). Adapter must accept all `1.x` versions."
- `contract.py` regex: `pattern=r"^1\.[0-9]+$"` — accepts 1.0, 1.1, …, 1.99.
- But: persisted contracts in SQLite are stored as `contract_json TEXT` (per brief §3). When schema becomes 1.1 and contract.py adds a required field, what happens to the existing 1.0 rows on read? `load_analysis()` will re-validate via Pydantic → existing rows fail.

**Open contract question**: read-side leniency for old rows. Today: undefined. Should be a stored `schema_version` filter or a one-time backfill script. Specify before any 1.x bump.

### F9. [NICE TO HAVE] Event shape for `analysis_returned` is duplicated, not derived

**Evidence**:
- The payload shape in brief §4 (10 fields) is hand-listed.
- Nothing prevents drift between brief §4 and `events.py` ALLOWED_EVENTS.
- There's no `class AnalysisReturnedPayload(BaseModel)` — so Codex must hand-validate.

Mild; can wait. Spec the event payload as a Pydantic type next time around so the test asserts via Pydantic, not `set(payload) ==`.

---

## B. API contract patches required before P1-2 starts

Each patch is a concrete change. Author of `contract.py` / `failures.py` / `codex_backend_P1-2.md` should land these before Codex picks the brief up.

### P1. Add `FailureCode → HTTP status` map [unblocks F1]

**Where**: append to `backend/src/agent/cascade/failures.py`:

```python
HTTP_STATUS: dict[str, int] = {
    FailureCode.S1_NO_SOURCE_URL.value: 400,
    FailureCode.S2_VERSION_MISMATCH.value: 422,
    FailureCode.S3_NO_FORMULA.value: 422,
    FailureCode.S4_SCENES_LEN_OUT_OF_RANGE.value: 422,
    FailureCode.S5_INVALID_PAYLOAD.value: 422,
    FailureCode.S6_NEGATIVE_COST.value: 500,
    FailureCode.S7_UPSTREAM_TIMEOUT.value: 504,
    FailureCode.S8_UPSTREAM_REFUSED.value: 503,
}
```

And add to `HardFailure`:
```python
@property
def http_status(self) -> int:
    return HTTP_STATUS.get(self.code.value, 500)
```

**Then**: edit `codex_backend_P1-2.md` §2 to say *"Caller converts to HTTP `HardFailure.http_status` with `HardFailure.to_payload()` as JSON body. Default 500 for any unmapped code."*

### P2. Promote `actions` to a typed catalog [unblocks F2]

**Where**: add to `failures.py`:

```python
class RecoveryAction(str, Enum):
    RETRY_WITH_NEW_URL = "RETRY_WITH_NEW_URL"
    PICK_FROM_FEATURED = "PICK_FROM_FEATURED"
    REPORT = "REPORT"
    RELOAD = "RELOAD"
    RETRY_SAME_URL = "RETRY_SAME_URL"
    RETRY_SAME_URL_AFTER_30S = "RETRY_SAME_URL_AFTER_30S"
    RETRY_SAME_URL_AFTER_60S = "RETRY_SAME_URL_AFTER_60S"

# Update RECOVERY_ACTIONS to use RecoveryAction enum values, then
ACTION_LABELS: dict[str, str] = {
    RecoveryAction.RETRY_WITH_NEW_URL.value: "换一条链接试试",
    RecoveryAction.PICK_FROM_FEATURED.value: "看看今日精选",
    RecoveryAction.REPORT.value: "告诉我们这条不行",
    RecoveryAction.RELOAD.value: "刷新一下",
    RecoveryAction.RETRY_SAME_URL.value: "再试一次",
    RecoveryAction.RETRY_SAME_URL_AFTER_30S.value: "30 秒后再试",
    RecoveryAction.RETRY_SAME_URL_AFTER_60S.value: "1 分钟后再试",
}
```

**And mirror in `cascade.ts`**:
```typescript
export type RecoveryAction =
  | 'RETRY_WITH_NEW_URL' | 'PICK_FROM_FEATURED' | 'REPORT'
  | 'RELOAD' | 'RETRY_SAME_URL'
  | 'RETRY_SAME_URL_AFTER_30S' | 'RETRY_SAME_URL_AFTER_60S';

export interface ErrorEnvelope {
  code: string;        // FailureCode
  hint: string;        // user-facing
  actions: RecoveryAction[];
  detail: string;      // DEBUG ONLY — do NOT render to user
  request_id?: string; // optional, for support
}
```

### P3. Mark `detail` as debug-only; add `request_id` [unblocks F3]

**Where**: edit `failures.py` `to_payload()`:

```python
def to_payload(self, *, request_id: str | None = None) -> dict:
    """Frontend-ready dict.

    `detail` is for debugging/logs only — UI must render `hint` instead.
    The route handler MUST attach a `request_id` for support correlation.
    """
    return {
        "code": self.code.value,
        "hint": self.hint,
        "actions": self.actions,
        "detail": self.detail,         # DEBUG ONLY
        "request_id": request_id,
    }
```

And edit `codex_backend_P1-2.md` §2 docstring:
- Route handler MUST generate a `request_id` (uuid4 hex), pass it to `to_payload(request_id=...)`, AND log it alongside the original `HardFailure.detail`.
- Frontend MUST NOT render `detail` — it is preserved only so support can ask the user for the `request_id` and correlate.

### P4. Resolve `analysis_id` vs `source_url+user_id` idempotency in spec [unblocks F5]

**Where**: edit `codex_backend_P1-2.md` §6 "Idempotency" bullet to read:

> Idempotency contract: `POST /api/analysis/shallow` is logically keyed by `(source_url, user_id)`. A second call within 24h returns the **same `analysis_id`** as the first, no new analysis is performed, no `analysis_returned` event is re-emitted, no new cost is incurred, and the HTTP response is `200 OK` with header `X-Cache: HIT` (vs `MISS` on first call). After 24h or when `model` changes, the (source_url, user_id) key is considered stale — a new ULID is minted and a new `analysis_returned` event fires.

This is one interpretation. The contract author may pick another — but the spec MUST commit to one before Codex implements.

### P5. TypeScript drift CI gate [unblocks F4]

**Where**: add `backend/scripts/emit_contract_schema.py`:

```python
"""Emits JSON Schema for the public Cascade contract surface."""
import json
from pathlib import Path
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.failures import FailureCode, WarningCode  # add RecoveryAction after P2

OUT = Path(__file__).resolve().parents[2] / "shared" / "cascade.schema.json"

doc = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "contract": CascadeAnalysisContract.model_json_schema(),
    "failure_codes": [c.value for c in FailureCode],
    "warning_codes": [c.value for c in WarningCode],
    # "recovery_actions": [a.value for a in RecoveryAction],  # after P2
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False))
```

**CI step** (one job, ~3 lines):
```yaml
- run: uv run python backend/scripts/emit_contract_schema.py
- run: git diff --exit-code shared/cascade.schema.json
```

When the diff fails, the PR author either (a) intentionally bumped the contract → commits the new schema → frontend reviewer is forced to update `cascade.ts` in the same PR, or (b) unintentionally drifted → fixes contract.py.

This gates drift at the smallest reasonable cost (one script, one CI step). No codegen, no `quicktype`, no monorepo build system.

### P6. Strip `severity: info` warnings before HTTP serialization [unblocks F6]

**Where**: in the eventual route handler:
```python
def _wire_serialize(contract: CascadeAnalysisContract) -> dict:
    d = contract.model_dump(mode="json")
    d["warnings"] = [w for w in d["warnings"] if w["severity"] != "info"]
    for s in d["scenes"]:
        s["warnings"] = [w for w in s["warnings"] if w["severity"] != "info"]
    return d
```

OR — preferred — bake into the contract layer with a `to_wire()` method. Either way, **spec the rule**: the HTTP wire form excludes `severity=info` warnings. Storage and event payloads keep all severities; only the wire form filters.

---

## C. Test plan for P1-2 (≥10 cases)

The existing `tests/test_analysis_service.py` covers 5 of these. The 10 listed below are the **minimum** the route handler + service need before sign-off. Numbered by criticality.

| # | Name | Input shape | Expected output / status |
|---|---|---|---|
| T1 | `test_happy_post_returns_full_contract_200` | `POST /api/analysis/shallow` body `{"source_url":"https://www.douyin.com/video/123"}` header `X-User-Id: u1` | 200; JSON validates against `CascadeAnalysisContract`; `analysis_id` starts with `ana_`; `Content-Type: application/json` |
| T2 | `test_missing_source_url_returns_400_S1` | body `{}` | 400; body `{code:"S1_NO_SOURCE_URL", hint, actions:["RETRY_WITH_NEW_URL","PICK_FROM_FEATURED","REPORT"], detail, request_id}` |
| T3 | `test_blank_source_url_returns_400_S1` | body `{"source_url":"   "}` | 400; S1 envelope |
| T4 | `test_non_http_source_url_returns_400_S1` | body `{"source_url":"ftp://x.com/v"}` | 400; S1 envelope |
| T5 | `test_no_formula_fixture_returns_422_S3` | force fixture loader to return `edge_no_formula.json` | 422; `code:"S3_NO_FORMULA"`; `actions` includes `PICK_FROM_FEATURED`; envelope contains `request_id` |
| T6 | `test_scenes_too_short_returns_422_S4` | force fixture loader → `edge_scenes_too_short.json` | 422; `code:"S4_SCENES_LEN_OUT_OF_RANGE"` |
| T7 | `test_idempotent_replay_returns_same_analysis_id` | call T1 twice with identical `(source_url, X-User-Id)` | both 200; identical `analysis_id`; only 1 row in `analyses`; only 1 `analysis_returned` event; second response has `X-Cache: HIT` (per patch P4) |
| T8 | `test_different_users_same_url_get_different_analyses` | T1 with `X-User-Id: u1` then `X-User-Id: u2` | both 200; different `analysis_id`s; 2 rows in `analyses`; 2 `analysis_returned` events |
| T9 | `test_info_severity_warnings_stripped_from_response` | force a fixture that triggers `W10_AUTHOR_PII_STRIPPED` + `W5_TIMESTAMPS_SORTED` | 200; response `warnings[]` contains **no** `severity:"info"` entries; persisted `contract_json` in SQLite still contains them |
| T10 | `test_response_contains_request_id_and_no_detail_in_hint` | T5 again | 422 body: `request_id` is a 32-hex string; `hint` does NOT contain the substring of `detail`; `detail` is a non-empty string (debug-only) |
| T11 | `test_oversized_request_body_returns_413` | body 11 MB of garbage JSON | 413 (or framework default); never reaches adapter; no event emitted |
| T12 | `test_unsupported_method_returns_405` | `GET /api/analysis/shallow` | 405; no event emitted |

T1–T10 are mandatory for sign-off. T11, T12 are routing-layer sanity.

---

## D. Failure-injection plan (5 scenarios)

The brief does NOT spec what happens when the *upstream analyzer* itself misbehaves. Codex needs this matrix or they will invent it.

| # | Injection point | Failure mode | Spec'd outcome |
|---|---|---|---|
| FI1 | `_call_toprador()` | raises `asyncio.TimeoutError` after configured timeout (default: 60s for P1-2) | route returns **504**; body code=`S7_UPSTREAM_TIMEOUT`, actions=`[RETRY_SAME_URL_AFTER_30S, RETRY_WITH_NEW_URL, REPORT]`; event `failure_emitted` with `failure_code:S7_UPSTREAM_TIMEOUT, stage:analysis`; NO `analysis_returned` event |
| FI2 | `_call_toprador()` | returns HTTP 500 from upstream / raises `UpstreamHTTPError` | route returns **503**; body code=`S8_UPSTREAM_REFUSED`; event `failure_emitted` with `S8`; NO retry inside service (the *client* retries via the action button) |
| FI3 | `_call_toprador()` | returns HTTP 200 with body `b"not json {{"` | route returns **422**; body code=`S5_INVALID_PAYLOAD`; `detail` contains parser error (NOT shown to user); event `failure_emitted` with `S5` |
| FI4 | `_call_toprador()` | returns HTTP 200 with valid JSON but missing `viral_analysis.replicable_formula` | route returns **422**; body code=`S3_NO_FORMULA`; event `failure_emitted` with `S3` |
| FI5 | `_call_toprador()` | returns HTTP 200 with valid JSON but `scenes: []` | route returns **422**; body code=`S4_SCENES_LEN_OUT_OF_RANGE` |

**Spec ambiguities FI exposes**:
- Does the service retry the upstream call internally before giving up? **Decision needed.** Recommend: no internal retry — the action-button protocol IS the retry. Predictable cost, no hidden tail-latency.
- Is `_call_toprador()`'s timeout configurable per-request? **Decision needed.** Recommend: env var `CASCADE_UPSTREAM_TIMEOUT_S=60`, no per-request override in Phase 1.
- Does `failure_emitted` count toward the user's cost? **Decision needed.** Recommend: no — cost guard (P1-9) ignores failed analyses.

These three decisions belong in `codex_backend_P1-2.md` §5 / §7 before Codex implements.

---

## E. TypeScript drift prevention (1 concrete proposal)

The proposal lives in patch P5 above. Re-stated as a one-liner:

> Add `backend/scripts/emit_contract_schema.py` that dumps `CascadeAnalysisContract.model_json_schema()` plus the enum lists to `shared/cascade.schema.json`. Add a single CI step that runs the script and `git diff --exit-code`s the output. Any contract drift now produces a red CI build until either (a) the schema file is regenerated and the frontend `cascade.ts` updated in the same PR, or (b) the python change is reverted.

This is the **minimum** check — it does not auto-generate TS types, it just guarantees that drift is **visible and gated**. Auto-generation via `quicktype` or `json-schema-to-typescript` is a future enhancement; today, a forced human diff in the PR is enough friction to prevent silent drift.

---

## Summary

**Verdict**: NEEDS SPEC PATCH (6 patches: P1–P6).

**Blockers** (must land before Codex starts P1-2): P1 (HTTP status map), P2 (action enum), P3 (detail-vs-hint), P4 (idempotency semantics).

**Should-land-soon** (before P1-2 PRs are reviewed): P5 (TS drift CI), P6 (info-warning wire filter).

**Single biggest day-1 spec gap**: F1 — no `FailureCode → HTTP status` map. Codex will route every failure to 422 (per current brief docstring) and the resulting API will be impossible to monitor, retry, or cache correctly. **Fix P1 first.**
