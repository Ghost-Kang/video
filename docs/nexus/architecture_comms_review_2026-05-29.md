# Communication Architecture Review — 2026-05-29 (Opus 4.8)

**Reviewer**: Claude Opus 4.8 (Software Architect) · **Scope**: full WS/HTTP transport layer, frontend WS store + connection hook, run lifecycle
**Baseline commit**: `403ecb3` · **Trigger**: 3 days / 8 commits (`de32e22`→`d4a8240`) chasing one recurring class of 线上故障 — "卡 95% / 拆解空白 / 网络已恢复 toast 狂闪"
**Verdict (one line)**: **加固,不重构。** The transport substrate (self-written `websockets` + per-thread serialization + Pydantic contract) is sound for 5–10 人内测. The bug class is not a framework-fit problem — it is **two specific architectural defects** (frame routing bound to a captured-at-start ws object, and no single source of truth for run lifecycle/results). Fix those two surgically; do **not** migrate to SSE or pull in LangGraph stream-resume.

---

## Method

Read end-to-end, not skimmed:
- Backend transport: `ws_server.py`, `ws_handlers.py`, `agent_runner.py`, `notify.py`, `context.py`, `run_state.py`, `runtime_ctx.py`, `ws_messages.py`.
- Frame producers downstream of run start: `tools/cascade.py` (`_push_ws`, `_push_failure_frame`, `cascade_analyze`/`cascade_rewrite`), `cascade/analysis_service.py` (`_emit_progress`), all 5 `workers/*` (`notify_user`).
- Persistence: `session_results_repo.py`.
- Frontend: `hooks/useWebSocket.ts`, `store/wsStore.ts`, `lib/chatPanelState.ts`, `App.tsx`, `main.tsx`.

Traced each of the 8 commits to the exact line it patched and asked: *what general invariant was being violated, and does the patch restore the invariant or just paper over one instance of its violation?*

---

## 1. How the comms layer actually works (verified)

**Inbound** (browser → backend): one WS, first frame must be `auth` (`ws_server.py:62`). Auth registers `user_id→ws` in `notify._ws_registry` (`ws_server.py:77`), builds `WSCtx`, auto-pushes `session_list`. Subsequent frames are dispatched through `HANDLERS` (`ws_handlers.py:338`) after Pydantic validation. `user_message` spawns a detached task `_run_agent_serialized` guarded by a per-`thread_id` `asyncio.Lock` (`ws_handlers.py:62`).

**The run** (`agent_runner.run_agent`): captures `{user_id, thread_id, ws, run_id}` into the `RUN_CTX` ContextVar **once, at the top** (`agent_runner.py:64`). Marks `run_state.mark_running`. Streams LangGraph `astream` tokens out as `agent_stream` frames. Inner tools (`cascade_analyze`, etc.) read `RUN_CTX` and push their own frames (`analysis_progress`, `analysis_returned`, `rewrite_returned`, `analysis_failed`) via `_push_ws` (`tools/cascade.py:64`). On terminal: `mark_done`/`mark_failed` + a final `agent_response`/`canvas_updated`.

**Worker pushes** (image/video/composite pipelines): out-of-band; look up the *current* ws via `notify._ws_registry.get(user_id)` (`notify.py:31`) each time they push.

**Outbound serialization**: every send goes through `context.send_json`, which holds a per-ws `asyncio.Lock` keyed by `id(ws)` in a `WeakValueDictionary` + strong-pin dict (`context.py:44`). Correct — prevents interleaved frames.

**Reconnect**: `useWebSocket` exponential backoff (`useWebSocket.ts:150`). On reopen it re-sends `auth`, flushes the pending queue, and (if `wasReconnect`) re-sends `get_session_state` for the current thread (`useWebSocket.ts:90`). 4001/4003 are terminal — stop reconnecting, drop to invite gate (`useWebSocket.ts:116`).

**Resume**: `get_session_state` returns persisted messages + canvas + `run_status` (from `run_state`, falling back to chat-history inference) + `failure`, then `_replay_results` re-pushes the thread's stored `analysis_returned`/`rewrite_returned` from the `session_results` pointer table (`ws_handlers.py:116`).

**Frontend dispatch** (`wsStore.dispatch`): `session_list` unions backend + local ids (`wsStore.ts:188`). Then the thread guard at `wsStore.ts:217`:
```ts
const rid = "thread_id" in event ? event.thread_id : undefined;
if (rid && rid !== get().currentThreadId) return;   // ← silently drop
```
Then a per-type reducer. UI mode is derived by `deriveChatPanelState` (idle/running/failed/ready/refine) from 4 store fields + last-message role.

---

## 2. The 8 commits, and the common root-cause pattern

Your hypothesis is **correct and is the proximate cause** for ~half the commits. But it sits *downstream* of a deeper defect. Mapping each commit to the invariant it touched:

| Commit | Symptom | Proximate fix | Underlying invariant violated |
|--------|---------|---------------|-------------------------------|
| `de32e22` | 断线重连卡 95% | add `run_state` + `run_status` + ping tuning | **No authoritative run lifecycle** — terminal frame lost on disconnect, client spins forever |
| `50f37d8` | 重载误判 95% | `deriveChatPanelState` last-role fallback | **No authoritative lifecycle** — UI *infers* run state from message tail because the real state isn't transmitted |
| `c8c71d7` | 已完成会话重载空白 | `session_results` table + replay | **Results are fire-and-forget** — a delivered-once frame has no durable record tied to a thread |
| `4ecc124` | 重连后空白 | auto re-send `get_session_state` on reconnect | **Frames lost across a gap are never re-delivered by the channel** — client must manually re-pull |
| `5d2dfa2` | 新会话拆解空白 | `session_list` union (don't overwrite) | **`currentThreadId` drift** → thread guard drops live frames |
| `c6f8075` | 4003 无限重连 (真凶) | 4001/4003 terminal, stop reconnect | **Auth is in-band post-connect** → bad-cred connect/close/reconnect loop |
| `d4a8240` | 邀请码错挡门外 | invite-gate UX | same auth-model consequence, UX side |

**The common pattern, stated precisely:**

> A run's output frames are routed to **a connection identity captured at run-start** (the `ws` object in `RUN_CTX` for tool/stream pushes; `currentThreadId` for client-side acceptance). Any event that changes that identity *after* the run starts — a dropped socket, a reconnect on a new ws object, a redirect/session-switch, a `session_list` overwrite — **permanently severs the run's frames from their destination**, with no recovery mechanism in the channel itself. Every fix so far added an *out-of-band patch* (replay table, manual re-pull, state inference, drift guards) to compensate for the missing in-channel guarantee.

Your thread-guard observation is the **client-side half** of this. The **server-side half** — which your hypothesis #3 names but under-weights — is more damaging and harder to see:

- `agent_runner` captures `ws` into `RUN_CTX` at line 64 and never refreshes it. The run task lives 20–50s. If the socket dies at t+5s and the browser reconnects at t+8s with a **new** ws object, then `analysis_progress`/`analysis_returned`/`rewrite_returned` pushed at t+30s by the cascade tool go to the **dead** ws and are swallowed by `_push_ws`'s `except (ConnectionClosed, …): pass` (`tools/cascade.py:70`). The client never receives them. This is invisible — no error, no log beyond a generic close.
- Note the asymmetry the user's hypothesis blurs: the **worker** path (`notify_user`) re-reads `_ws_registry.get(user_id)` *per push*, so it self-heals on reconnect (the registry is overwritten at `ws_server.py:77`). The **run** path does **not** self-heal — it holds the stale ws object for the task's lifetime. So progress/analysis/rewrite frames are the fragile ones; worker canvas_updated frames are comparatively robust. This is exactly why "卡 95%" (a run-path progress/terminal frame) was the dominant symptom.

So: thread-guard drift is real but is one of *four* drift sources. The replay table + `get_session_state` re-pull is what *actually* saves the day today — but only because the client manually asks again. The channel itself still guarantees nothing.

---

## 3. Root architectural defects (assessed)

Validating your 5 observations:

1. **Fire-and-forget frames, no ack/seq/replay-by-channel** — ✅ confirmed, and this is the **#1 root defect**. `_push_ws` and `send_json` are unidirectional best-effort. There is no per-run sequence number, no client ack, no "give me everything since seq N". `session_results` replay is a *result-level* patch (only `analysis_returned`/`rewrite_returned`), not a *frame-level* guarantee — `analysis_progress` and `agent_stream` tokens are still lost forever on a gap.
2. **Run state scattered, no single source of truth** — ✅ confirmed. Authoritative-ish state lives in 4 places: frontend `loading`/`currentThreadId` (wsStore) + canvasStore `failure`, backend `run_state` (in-memory, lost on restart), and SQLite (`session_results` + chat messages). `_resolve_run_status` (`ws_handlers.py:99`) and `deriveChatPanelState` both *infer* lifecycle because no single component owns it.
3. **Frames pushed to the run-start-captured ws; `notify` single-value map** — ✅ confirmed and **under-weighted by you** (see §2). The single-value `user_id→ws` map is the *lesser* problem (it self-heals + a second tab is rare in 内测); the **captured-ws-in-RUN_CTX** is the *worse* one.
4. **Auth in-band, not at handshake** — ✅ confirmed (`ws_server.py:62`). A wrong invite code produces connect→4003→reconnect; `c6f8075`/`d4a8240` patched the *loop*, but the *model* still admits the connection before rejecting it.
5. **5-state derived UI, no explicit run lifecycle state machine** — ✅ confirmed. `deriveChatPanelState` is a clean pure function, but it's reconstructing a state machine that the system never explicitly maintains. "Has messages, no result" is repeatedly ambiguous (`50f37d8`).

**What is NOT broken** (resist the urge to "fix" these):
- Self-written `websockets` vs FastAPI — irrelevant to these bugs; switching is pure churn.
- Per-thread `asyncio.Lock` serialization — correct and necessary.
- `send_json` per-ws send lock — correct.
- Pydantic contract + codegen — a real asset; keep it as the single wire-truth.
- SQLite / single container — fine at this scale; not implicated.

---

## 4. Prioritized, directly-implementable plan

### P0-A — Route run frames through a live connection lookup, not a captured ws  *(root defect #3; the dominant "卡 95%" cause)*

**Solves**: progress/analysis/rewrite/terminal frames silently dying on the dead socket after a reconnect.

**Idea**: stop carrying the `ws` object through `RUN_CTX`/`run_agent`. Carry only `(user_id, thread_id)`. At each send, resolve the *current* ws from the registry — the same self-healing pattern `notify_user` already uses. Upgrade the registry from single-value to a set so multi-tab/overlapping-reconnect doesn't evict a live socket.

**Concrete changes:**
- `notify.py`: change `_ws_registry: dict[str, Any]` → `dict[str, set]`. 
  - `register(user_id, ws)` → `_ws_registry.setdefault(user_id, set()).add(ws)`
  - `unregister(user_id, ws)` → discard that ws; drop the key if the set empties. (Signature must take ws now — update the `ws_server.handle` finally block at `ws_server.py:122` to pass `websocket`.)
  - Add `async def send_to_user(user_id: str, payload: dict) -> int:` that iterates the set, calls `send_json(ws, **payload)` on each, drops any that raise `ConnectionClosed*`, and returns the count delivered.
- `runtime_ctx.py` / `RunCtx`: drop `ws`; keep `user_id`, `thread_id`, `run_id`. (Or keep `ws` as an unused fallback for one release to avoid a big-bang.)
- `tools/cascade.py` `_push_ws` and `_push_failure_frame`, and `analysis_service._emit_progress`: replace `ws = ctx.get("ws"); await ws.send(...)` with `await notify.send_to_user(ctx["user_id"], payload)`.
- `agent_runner.run_agent`: the parameter `ws` and the captured `RUN_CTX["ws"]` go away; its `agent_stream`/`agent_response`/`canvas_updated`/`analysis_failed` sends route via `send_to_user(user_id, ...)` too. (`run_agent`'s signature loses `ws`; caller `_run_agent_serialized` stops passing `ctx.ws`.)

**Function signatures (target):**
```python
# notify.py
def register(user_id: str, ws: Any) -> None
def unregister(user_id: str, ws: Any) -> None
async def send_to_user(user_id: str, payload: dict) -> int   # returns # delivered
```

- **Root cause addressed**: #3 (captured-ws) primarily; reduces reliance on #1's replay patch.
- **Files**: `notify.py`, `runtime_ctx.py`, `agent_runner.py`, `tools/cascade.py`, `analysis_service.py`, `ws_server.py` (unregister call). Workers already use `notify_user` — refactor `notify_user` to delegate to `send_to_user` so there's one path.
- **Risk**: medium. `send_json`'s per-ws lock must stay (still keyed by `id(ws)` — fine, each ws in the set has its own). Tests that pass a `FakeWebSocket` through `RUN_CTX["ws"]` must switch to registering it via `notify.register`. Concurrency: iterating a set while a connection closes — snapshot to a list before iterating.
- **WS contract**: unchanged (same frames, same shapes). ✅ no codegen change.
- **Data migration**: none.
- **Effort**: medium (touches ~6 files, mostly mechanical; the test fixture change is the fiddly part).

---

### P0-B — One authoritative, persisted run-lifecycle record per thread  *(root defects #2 + #5; kills "卡 95%" and "重载误判" for good)*

**Solves**: run state surviving restart; client never having to *infer* lifecycle; `get_session_state` returning truth instead of a history-tail heuristic.

**Idea**: promote `run_state` from an in-memory dict to a tiny SQLite-backed, append-on-transition record keyed by `thread_id`. It becomes the single source of truth `get_session_state` reads. Keep the in-memory map as a write-through cache for hot reads — but **persist every transition** so a restart mid-run yields `failed`/`stale` deterministically instead of `idle`-by-inference.

**Concrete schema** (new table; `db.py` migration alongside `session_results`):
```sql
CREATE TABLE IF NOT EXISTS run_lifecycle (
  thread_id   TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL,
  run_seq     INTEGER NOT NULL DEFAULT 0,   -- bumped on each mark_running (for P1-C)
  status      TEXT NOT NULL,                -- 'running' | 'done' | 'failed'
  failure     TEXT,                         -- JSON FailurePayload when failed
  started_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
```

**Function signatures (target — `run_state.py` keeps its API, gains persistence):**
```python
async def mark_running(user_id: str, thread_id: str) -> int   # returns new run_seq
async def mark_done(thread_id: str) -> None
async def mark_failed(thread_id: str, failure: dict | None) -> None
async def get(thread_id: str) -> RunState | None              # cache → DB fallback
```

**Startup reconciliation** (one call in server boot, before accepting connections): any row left `status='running'` is a run that died with the process → set to `failed` with a synthetic `S11_INTERNAL_ERROR`/"上次处理被中断,请重试" payload. This makes the post-restart answer *deterministic*, replacing the `_resolve_run_status` history-tail guess at `ws_handlers.py:99`.

- `_resolve_run_status` simplifies to: read the lifecycle row; if `running` and `updated_at` older than `RUN_TURN_TIMEOUT_S + slack` → treat as `failed`/stale (defends against a task that died without marking). No more "agent message at tail == done" inference.
- Frontend: `deriveChatPanelState` can stay, but now it's fed authoritative `run_status` from `session_state` rather than guessing; the `lastMessageRole` fallback (`chatPanelState.ts:43`) becomes a belt-and-suspenders, not load-bearing.

- **Root cause addressed**: #2 (no SSOT) + #5 (inferred state).
- **Files**: `run_state.py` (now async, DB-backed), `db.py` (migration), `ws_handlers.py` (`_resolve_run_status` + handler awaits), `agent_runner.py` (await the marks), server boot (reconciliation call).
- **Risk**: medium. `run_state.mark_*` becomes async — every caller in `agent_runner` is already in async context, so this is clean. The eviction/cap logic (`run_state.py:39`) is replaced by SQL.
- **WS contract**: unchanged. `SessionStateEvent.run_status` already exists (`ws_messages.py:178`); we just make its value trustworthy. Optionally add `"stale"` as a documented value of the existing `run_status: str` (no schema break — it's already typed `str`). ✅
- **Data migration**: one new table, additive. Safe.
- **Effort**: medium.

> **P0-A and P0-B together** retire the *mechanism* behind 5 of the 8 commits (`de32e22`, `50f37d8`, `c8c71d7`, `4ecc124` partially, `5d2dfa2` partially). They are the high-ROI core. Do these first.

---

### P0-C — Make the client thread-guard explicit, not silently lossy  *(your named landmine; `5d2dfa2` class)*

**Solves**: the `wsStore.ts:218` `return` that drops frames whenever `currentThreadId` drifts from the running run's thread.

**Idea**: do **not** keep accepting frames for non-current threads blindly (that re-opens cross-thread bleed), and do **not** silently drop them. Instead, **buffer per-thread** and replay on switch. The store already knows every thread frame's `thread_id`.

**Concrete change** (`wsStore.ts`):
- Add `pendingByThread: Record<string, WSEvent[]>` to the store.
- At the guard (`wsStore.ts:217`): if `rid && rid !== currentThreadId`, push the event into `pendingByThread[rid]` (cap each bucket to ~200, drop-oldest) and `return` — but now it's *buffered*, not lost.
- In `setCurrentThreadId` (and on the `get_session_state` round-trip in `App.tsx`'s tid effect): after switching, drain `pendingByThread[newTid]` through `dispatch` in order, then clear that bucket.
- This makes a mid-run redirect/switch survivable even without P0-A — they're complementary (P0-A keeps the server *sending*, P0-C keeps the client *keeping*).

- **Root cause addressed**: client-side half of §2 (currentThreadId drift).
- **Files**: `wsStore.ts` only (plus a 1-line drain call in `App.tsx` `switchSession`/tid effect).
- **Risk**: low. Pure frontend, bounded buffer.
- **WS contract**: unchanged. ✅
- **Data migration**: none.
- **Effort**: small.

---

### P1 — Move auth to the WS sub-protocol / first-frame-before-accept, kill the connect-then-reject loop *(root defect #4; `c6f8075`/`d4a8240` class)*

**Idea**: keep the in-band `auth` frame for back-compat, but treat a 4001/4003 as the *non-retryable terminal* it already is on the client (done in `c6f8075`) **and** stop the server from doing expensive setup before auth. Today auth is fine functionally; the remaining smell is that the *connection* is the unit of auth, so a bad code still costs a full TCP+WS handshake per retry. At 内测 scale this is cosmetic, not load-bearing — hence **P1, not P0**.

**Minimal hardening worth doing now:**
- Pass the invite code as a WS subprotocol or `Sec-WebSocket-Protocol` header so nginx/cloudflared could reject pre-upgrade later (don't build that now — just stop *requiring* a post-accept round trip to know the code is bad).
- Backend: validate invite code synchronously in the `auth` branch before `start_workers()`/`list_sessions` (it already does — `ws_server.py:71` is before the session push; this is already correct). The real P1 is purely the client UX already shipped.

- **Verdict**: the loop is *already broken* by `c6f8075`. P1 here is "don't regress + document the model"; only escalate to handshake-time auth if you later put the WS behind a shared edge. **Low ROI now.** Effort: small. Contract: would add an optional subprotocol — defer.

---

### P1 — Collapse the failure-classification duplication into one path

**Observation (not in your list, found while reading):** there are now **three** places that synthesize/normalize a failure:
- `agent_runner.run_agent` except block (`agent_runner.py:121`) classifies exceptions → `analysis_failed` + `run_state.mark_failed`.
- `tools/cascade._push_failure_frame` (`cascade.py:75`) pushes `analysis_failed` for tool-caught `HardFailure` (which `run_agent` never sees, because the tool returns an error dict to the LLM instead of raising).
- Frontend `synthesizeFailureFromContent` (`wsStore.ts:54`) regex-matches `agent_response` content to *fabricate* a failure the backend already knew about.

The frontend regex synth (`TIMEOUT_PATTERN`) is a genuine hazard: a legitimate agent answer containing "处理出错" flips a successful turn to `failed`. It exists only because tool-caught `HardFailure` → error dict → Director may relay it as plain chat text, losing the structured frame.

**Fix**: ensure **every** terminal failure (tool-caught included) results in exactly one `analysis_failed` frame **and** one `run_state.mark_failed`, so the frontend can delete `synthesizeFailureFromContent` and the `TIMEOUT_PATTERN` heuristic entirely. `_push_failure_frame` already pushes the frame; it just needs to also call `run_state.mark_failed` (and after P0-B, that's the persisted SSOT). Then `agent_response` is *always* a success and the client never guesses.

- **Root cause addressed**: #5 (inferred state) on the failure axis; removes a false-positive bug surface.
- **Files**: `tools/cascade.py` (`_push_failure_frame` also marks failed), `wsStore.ts` (delete synth path + `TIMEOUT_PATTERN`/`REFUSED_PATTERN`), `App.tsx` (`sendChatMessage` timeout currently calls `synthesizeFailureFromContent` — repoint to a plain client-timeout `FailurePayload` literal).
- **Risk**: low–medium (must confirm tool failure paths all reach `_push_failure_frame`; grep shows analyze + rewrite do).
- **WS contract**: unchanged. ✅
- **Effort**: small–medium.

---

### P2 — Per-run event sequence number + "since-seq" replay  *(the "real" fix for root defect #1)*

This is the textbook robust answer (each frame carries `run_seq` + monotonic `seq`; client tracks last-seen; on reconnect sends `resume{thread_id, last_seq}`; server replays buffered frames since). **It is over-engineering for 内测 right now** — *if* P0-A+P0-B+P0-C land, the only frames still lost on a gap are `agent_stream` tokens (cosmetic streaming text) and `analysis_progress` (decoration). The *results* are already durable (replay table) and *lifecycle* is authoritative (P0-B).

Implement P2 **only if** post-P0 telemetry shows users still hit lost-token/lost-progress confusion. If you do: the `run_seq` column from P0-B's schema is already there to anchor it, and you'd add an in-memory ring buffer per thread (last ~50 frames) + a `resume` inbound message. Keep the buffer in-memory (no DB) — it's recovery-window-scoped.

- **Verdict**: **deferred / likely YAGNI.** Don't build it now.

---

### Explicitly AVOID (over-engineering for this stage)

- ❌ **Migrate to SSE + HTTP POST.** Would discard the working bidirectional channel, the typed contract, and the serialization lock for zero gain on *these* bugs (which are routing/state, not transport-type).
- ❌ **LangGraph checkpoint stream-resume.** Heavy, couples recovery to the graph internals; P0-B's lifecycle row + replay table covers the actual need at a fraction of the complexity.
- ❌ **Redis / external pub-sub for the registry.** Single container, single process — an in-memory `dict[str, set]` is correct. Adding Redis adds an ops dependency and a new failure mode for 5–10 users.
- ❌ **Full event-sourcing / CQRS of the run.** P0-B is a single mutable row per thread; that is the right altitude.
- ❌ **Generic ack/retransmit on every frame (P2) before measuring need.**

---

## 5. Sequencing & ROI

| Order | Item | Solves | Effort | ROI |
|-------|------|--------|--------|-----|
| 1 | **P0-A** route via live registry | dead-ws frame loss (dominant 卡95%) | M | ★★★★★ |
| 2 | **P0-B** persisted run lifecycle SSOT | state survives restart, no inference | M | ★★★★★ |
| 3 | **P0-C** client per-thread buffer | currentThreadId drift frame loss | S | ★★★★☆ |
| 4 | **P1** unify failure path, drop regex synth | false-positive failures | S–M | ★★★☆☆ |
| 5 | **P1** auth model doc/harden | loop already fixed; cosmetic | S | ★★☆☆☆ |
| 6 | **P2** seq+resume | lost tokens/progress | L | ★☆☆☆☆ (defer) |

P0-A + P0-B + P0-C are one coherent landing: **server keeps sending to the right live socket, the run's truth is persisted, and the client stops discarding.** That trio dissolves the recurring bug class instead of patching its next instance.

---

## 6. Answers to the core questions

- **Refactor or harden?** **Harden.** The substrate is appropriate for the scale; the defects are two specific routing/state mistakes plus a lossy client guard. Three surgical P0s, no framework change, no contract break, one additive table.
- **Thread-guard frame loss — root fix?** **Per-thread client-side buffering + replay-on-switch (P0-C)**, paired with **live-registry server routing (P0-A)** so frames keep arriving in the first place. Not seq-numbers (overkill now).
- **Authoritative, persisted, recoverable run state machine?** **Yes — P0-B.** One `run_lifecycle` row per thread, write-through cached, reconciled on boot. It replaces the in-memory `run_state` + the `_resolve_run_status`/`deriveChatPanelState` inference as the source of truth.
- **Highest ROI?** P0-A and P0-B, in that order.
