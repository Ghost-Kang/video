# Claude handoff — P3-R3 landing consent click-through

**Owner**: Claude session (frontend)
**Source of truth**: `docs/legal/user_agreement_v0.md §11` + `docs/legal/privacy_v0.md §10.1` + `compliance_done_2026-05-21.md §1` (partial tick — UI half pending)
**Status**: ready to execute; **hard prerequisite for first DM going out** (currently `recruitment.md dms=0`, so window is still open)
**Time budget**: 0.5 day (1 frontend component + 1 hook + 1 server event + 5 tests)

---

## 0. Why this exists

The legal docs landed (commit `d294754`) and reference a click-through consent mechanism in `user_agreement_v0.md §11.1`:

> 您在邀请页**勾选**"我已阅读并同意《用户协议(v0 试用版)》与《隐私政策(v0)》"且**点击进入产品**时,即视为您已阅读、理解并接受本协议全部条款。

But Landing.tsx today has no checkbox. Users can hit `/chat/...` without ever seeing the legal docs. **If a creator opts in tomorrow under the current state, our consent claim is structurally false** — they'd be using the product without seeing or accepting the协议.

P3-R3 closes this gap. It is the last frontend dependency between the legal docs and DM Day-1 (currently scheduled 2026-05-22 per pre-registration).

---

## 1. Functional spec

### 1.1 What the user sees on Landing

A consent block **above the fold**, between the H1 and `<HotCardGrid>`:

```
┌──────────────────────────────────────────────────────────┐
│ ☐  我已阅读并同意 《用户协议 v0》 与 《隐私政策 v0》       │
│                                                          │
│   (链接打开新标签;文档为 v0 试用版,Phase 2 公测前重写)   │
└──────────────────────────────────────────────────────────┘
```

Until the box is ticked:
- `<HotCardGrid>` cards are **non-clickable** (visually dimmed, `pointer-events: none`)
- `<UrlFallback>` submit button is **disabled**
- A small hint appears above the checkbox: `"先勾选同意才能开始"`

After tick:
- All interaction restored
- `localStorage.setItem("openrhtv_consent_v0", JSON.stringify({version: "v0", acceptedAt: ISO8601, sha256: <doc fingerprint>}))` writes the consent record
- A `consent_accepted` event is POSTed to `/api/events` for the server-side audit log

### 1.2 Persistence behavior

- Consent persists across sessions via `localStorage`
- Returning users with valid `openrhtv_consent_v0` record skip the gate — checkbox renders pre-checked + locked + smaller
- If the doc version changes (v0 → v1 someday), the localStorage key change forces re-consent

### 1.3 Doc fingerprint (`sha256`)

To prove which exact text was accepted, the consent record stores a sha256 of the **concatenated `user_agreement_v0.md + privacy_v0.md` content** as a build-time constant. If founder edits either doc post-build, the fingerprint mismatch forces re-consent on next page load.

Implementation: a Vite plugin OR a static export at build time. Cheapest path: a generated `frontend/src/lib/consentFingerprint.ts` produced by a small script in `package.json` `prebuild` step. If too much yak-shaving, ship without sha256 in v0 — just store version string + timestamp.

**Decision (default for v0)**: skip sha256; trust the version string `"v0"`. Note in code with `// TODO P3-R3.1: add sha256 fingerprint if doc revisions happen mid-Phase-1`.

---

## 2. Files

| Path | Action |
|---|---|
| `frontend/src/components/landing/ConsentGate.tsx` | **new** — checkbox component with links to docs |
| `frontend/src/hooks/useConsent.ts` | **new** — read/write localStorage + POST event |
| `frontend/src/pages/Landing.tsx` | modify — wrap `<HotCardGrid>` + `<UrlFallback>` in consent gate; render `<ConsentGate>` above |
| `frontend/src/components/landing/__tests__/ConsentGate.test.tsx` | **new** — 3 cases (initial state, tick → unlock, persisted across mount) |
| `frontend/src/hooks/__tests__/useConsent.test.ts` | **new** — 2 cases (read existing, write new) |
| `frontend/public/legal/user_agreement_v0.md` | **new symlink or copy** from `docs/legal/user_agreement_v0.md` (or serve via API) |
| `frontend/public/legal/privacy_v0.md` | **new symlink or copy** |
| `backend/src/agent/server.py` | extend `/api/events` to accept `consent_accepted` event (event name allowlist; no new route) |
| `backend/src/agent/cascade/events.py` | add `"consent_accepted"` to event name set; `_REQUIRED_FIELDS["consent_accepted"] = ["version", "accepted_at"]` |
| `backend/tests/test_events_endpoint.py` | add 1 case — POST `consent_accepted` event lands in `events` table |

---

## 3. Serving legal docs from frontend

The docs live in `docs/legal/` which is not in the frontend serve path. Three options:

| Option | Cost | Pros / cons |
|---|---|---|
| **A. Copy at build** (`prebuild` script copies `docs/legal/*.md` → `frontend/public/legal/`) | 5 lines in `package.json` | Simple, but two copies of truth — risk of drift |
| **B. Symlink** `frontend/public/legal -> ../../docs/legal` | 1 command | Vite serves from public/ — symlinks usually work but check Vite docs |
| **C. Backend route** `GET /api/legal/:doc` reads from `docs/legal/*.md` | 10 lines new route | Single source, but adds backend dep |

**Recommended: A** (build-time copy) — least magic, most explicit. The `prebuild` script in `frontend/package.json`:

```json
"scripts": {
  "prebuild": "mkdir -p public/legal && cp ../docs/legal/*.md public/legal/",
  "predev": "mkdir -p public/legal && cp ../docs/legal/*.md public/legal/",
  ...
}
```

Add `public/legal/` to `frontend/.gitignore` so the copies aren't double-tracked.

Render markdown in browser via existing markdown component (likely already used elsewhere; if not, `react-markdown` already in deps based on chat/script rendering).

**Open**: should the docs render in-app (modal/route `/legal/user-agreement`) or open in a new browser tab as plain `.md`? Cleaner UX = in-app route with rendered markdown. Cheaper = new tab to raw `.md`. **Default: in-app route** at `/legal/user-agreement` + `/legal/privacy` rendering the file content via `react-markdown`.

---

## 4. UX details

### 4.1 Layout

```tsx
// Landing.tsx (sketch)
<main className="...">
  <div className="mx-auto max-w-[720px]">
    <h1>看到刷屏的视频,想做一条自己的?挑一张开始 ↓</h1>

    <ConsentGate>
      <HotCardGrid onPick={pick} />
      <UrlFallback onSubmit={...} />
    </ConsentGate>
  </div>
  <WaitlistCta />
</main>
```

`<ConsentGate>` is a wrapper:
- If consent accepted → renders children + a tiny `已同意 v0 协议` badge in corner
- If not → renders the checkbox + dims/disables children via `pointer-events: none` + `opacity-50`

### 4.2 Copy (final)

```
[ ] 我已阅读并同意 [《用户协议 v0》] 和 [《隐私政策 v0》]
    本服务为 Phase 1 内测,公测前协议将完整重写
```

Links open in **new tab** (per common pattern) routes `/legal/user-agreement` and `/legal/privacy` inside the app.

### 4.3 Failure modes

- Backend unreachable when POSTing `consent_accepted` event → still write localStorage, queue the event POST in localStorage retry queue (existing pattern in `PublishPackCard.tsx:42-44` — reuse `publish_pack_events` style)
- User clears localStorage → consent gate re-appears next visit (acceptable; matches `privacy_v0.md §10.2`)

---

## 5. Backend `consent_accepted` event

### 5.1 Event payload

```json
{
  "event_name": "consent_accepted",
  "user_id": "anon-<hash>",
  "ts": "2026-05-22T14:30:00Z",
  "payload_json": {
    "version": "v0",
    "accepted_at": "2026-05-22T14:30:00Z",
    "user_agent": "<truncated to first 80 chars>",
    "documents": ["user_agreement_v0", "privacy_v0"]
  }
}
```

### 5.2 What NOT to store

Per `privacy_v0.md §2.3` and `02_event_spec.md §8.3`:
- ❌ IP address
- ❌ Full user agent (truncate to first 80 chars so we know browser family without device fingerprint)
- ❌ Anything that could re-identify the visitor

### 5.3 Done-signal for the audit value

```bash
sqlite3 backend/data/messages.db \
  "SELECT user_id, json_extract(payload_json, '\$.accepted_at') \
   FROM events WHERE event_name='consent_accepted' ORDER BY ts DESC LIMIT 5"
```

Founder can re-run this any time to prove "user X accepted on date Y" — backs up the localStorage record with a server-side timestamp the client can't forge.

---

## 6. Tests

### 6.1 Frontend (`ConsentGate.test.tsx`)
1. Initial render → checkbox unchecked, children disabled (pointer-events check via `style` assertion)
2. Tick checkbox → children enabled + localStorage written + POST fired (mock fetch)
3. Mount with pre-existing valid localStorage → consent gate auto-passes (child interactive immediately)

### 6.2 Frontend (`useConsent.test.ts`)
1. `useConsent()` returns `{accepted: false}` on empty localStorage
2. After calling `accept()` → localStorage written + returns `{accepted: true, acceptedAt: ISO}`

### 6.3 Backend (`test_events_endpoint.py`)
1. POST `consent_accepted` with valid payload → 200 + row in events table with `event_name='consent_accepted'`

---

## 7. Done-signal

- `frontend/src/components/landing/ConsentGate.tsx` exists; Landing wraps interactive children
- `frontend/src/hooks/useConsent.ts` exists with `useConsent()` hook
- `/legal/user-agreement` + `/legal/privacy` routes render the v0 docs (route entries in `main.tsx`)
- `npm test` in frontend passes the new 5 cases + zero regressions
- `uv run pytest backend/tests/test_events_endpoint.py -k consent -v` passes
- Manual smoke: open Landing, see disabled grid + checkbox; tick → grid clickable + localStorage shows `openrhtv_consent_v0` + sqlite shows new `consent_accepted` row
- `compliance_done_2026-05-21.md §1` "邀请页 click-through 同意机制" evidence line updated from `partial` to `✅ ConsentGate.tsx + /legal/* routes`

---

## 8. NOT in this ticket

- Doc version migration UI (v0 → v1 will come with Phase 2; out of scope)
- Multi-language (English / 繁體) versions of consent doc — Phase 1 is Chinese mainland only
- A formal "withdraw consent" UI button — `privacy_v0.md §7.4` says撤回 via email; no in-app button needed for 10-user trial
- sha256 doc fingerprint — explicit `// TODO` left in code; ship without
- Cookie banner / GDPR-style choice modal — not applicable (Chinese law, no EU users)
- Backend user identity / auth — anonymous `user_id` is fine for v0

---

## 9. PM notes

- This is the **last frontend dep** before DM batch can begin
- Closes `compliance_done #1` evidence row from partial → ✅
- Belongs in W3D1 — same day as DM batch start
- After merge, **founder visually verifies** the gate by opening Landing in incognito + checking localStorage entry exists post-tick

**Sequence**: Claude ships this → founder smoke-tests in browser → founder sends first DM(s) with link to invite page → first creator clicks → consent recorded → onboarding begins.
