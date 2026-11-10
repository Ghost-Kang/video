# Upstream sync state

**Upstream**: https://github.com/waHhhHao/OpenRHTV
**This repo**: github.com/Ghost-Kang/video (cascade workstream)
**Routine**: `upstream-sync-watch` (trig_01AZqceZ6NDTocTUHGq3EEFd) — daily 02:00 UTC

---

last_evaluated_sha: 9bea52c (origin/main tip at time of manual sync — 2026-05-21 13:49 +0800)
last_evaluation_timestamp: 2026-05-22T14:00:00+08:00
last_merge_commit: e0c0aff (Merge origin/main into pm/upstream-sync-20260522)

Status: ⚠️ **upstream fetch blocked — session not authorized for waHhhHao/OpenRHTV**
last_run_attempt: 2026-11-10T03:07Z

---

## Sync log (newest first)

### 2026-11-10T03:07Z — FETCH FAILED: upstream repo not accessible

- `git fetch upstream main` failed: "could not read Username for 'https://github.com': terminal prompts disabled"
- `gh api /repos/waHhhHao/OpenRHTV/commits` failed: GitHub session scope limited to ghost-kang/video only
- No commits evaluated; last_evaluated_sha unchanged at `9bea52c`
- **Action required**: founder must attach `waHhhHao/OpenRHTV` read access to the upstream-sync session
  (see https://code.claude.com/docs — add the upstream repo to the session's GitHub access scope),
  OR trigger the routine manually from a session that has cross-repo read access.


### 2026-05-22T14:00:00+08:00 — manual sync of 28 commit backfill

- Routine `upstream-sync-watch` did not fire / did not produce PR by W3D1 morning;
  PM took over manually per founder direction.
- Created branch `pm/upstream-sync-20260522`, ran `git merge origin/main`,
  resolved 7 hard conflict files manually:
  - `backend/src/agent/server.py` (combined cascade routes + video provider + worker startup)
  - `frontend/src/main.tsx` (combined Phase 1 public routes + upstream AuthGate)
  - `frontend/src/App.tsx` (combined ProView toggle + multi-user + edge CRUD)
  - `frontend/src/components/Header.tsx` (combined ProViewToggle + logout)
  - `frontend/src/components/NodeDetail.tsx` (kept upstream MediaPanel + NodeType)
  - `frontend/src/components/Canvas.tsx` (accepted upstream)
  - `frontend/vite.config.ts` (kept Tailwind + vitest config + added server block)
- Auto-merged: `.env.example`, `backend/pyproject.toml`, `backend/src/agent/config.py`, `backend/uv.lock`
- Tests: frontend 70/70 ✅, backend Phase 1 subset 74/74 ✅, full suite 181/200 (19 fails
  are integration tests requiring missing API keys, not regressions)
- FF-merged `pm/upstream-sync-20260522` → `main` at `e0c0aff`
- Branch deleted post-merge

### 2026-05-22 — semantic flags raised for founder review

1. Image gen default switched apimart → google gemini (upstream `3c948d9`).
   Conflicts with `privacy_v0.md §4.3` ("default Apimart, 二次同意 for gemini").
   Action: founder picks: revert default to apimart OR update privacy_v0
   to reflect google default.
2. Login required for /chat/* (upstream `66758bd`). Anon ConsentGate flow
   on Landing now redirects to /login. Action: founder picks anon-style
   "creator_N" usernames OR introduces special anon path.

### 2026-05-21T14:05:00Z — state file seeded for backfill

- Anchor SHA set to `3aa7f90` (divergence point: "fix: remove S3 credentials from config defaults")
- Backfill window: the 28 upstream commits up to `9bea52c` (head at seed time)
- Routine was supposed to produce ONE PR on next run — never fired
