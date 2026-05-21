# Stage 3 · Senior PM Routing Plan

**Date**: 2026-05-19
**Owner**: Senior PM (this session)
**Source of truth**: `docs/nexus/02_sprint_plan.md` (week-by-week tickets)
**Mode**: Claude executes Phase 0 directly; Phase 1 tickets routed to Codex / Cursor / Claude based on what each tool does best.

---

## 0. Routing philosophy

Each tool's strength dictates ownership:

| Tool | Strength | Owns |
|---|---|---|
| **Claude** (this session) | Long-horizon spec, contract design, code where correctness > velocity; **and frontend** as of 2026-05-21 | Phase 0 entirely; Phase 1+ contract code, prompt engineering, learning-loop instrumentation, **AND all frontend** (re-routed from Cursor — see §0.1) |
| **Codex** (offline) | Test-heavy, refactor-focused, structured backend changes with full context | P1-2 浅分析 endpoint, P1-9 cost guard middleware, P1-3 prompt-chain backend, P2-1 double-emit fix, P2-2 S7/S8 upstream wiring |
| **Cursor** (interactive) | (Deprecated for new tickets as of 2026-05-21.) Past Phase 1 frontend deliverables (P1-1 / P1-4 / P1-6 sidebar / P1-7 / P1-8) remain Cursor history | Maintenance-only for Cursor's W1 deliverables if regressions surface |
| **Founder** (manual) | Real-creator interviews, hand-labeling fixtures, niche prompt-tuning iteration | P0-1 real fixture upgrade, P1-10 creator interviews, recruitment, brand voice spot-check |

**Rule**: any ticket touching Cascade contract types (`contract.py` / `cascade.ts` / `topic_intelligence.py` / `topic_intelligence.ts`) routes through Claude to prevent type drift.

**Canvas-entry contract**: When users enter the canvas from a /topics card, the payload is a `TopicBrief` (per `topic_intelligence.py`), NOT a raw topic string. The Cursor P1-4 brief assumes this — frontend reads `TopicBrief.deep_intelligence.explain` to render the 3 one-liners on the card; the canvas reads `TopicBrief.viral_mechanism` + `replication_blueprint` to seed the script + shot cards.

## 0.1. Frontend re-routing (2026-05-21)

**Founder decision**: All new frontend tickets route to Claude going forward. Cursor's W1 deliverables stay as-is; the change applies to W2+ scope.

**Why**: Mode-switching between Claude (backend / spec / prompts) and Cursor (frontend) was higher-friction than expected. Consolidating frontend to Claude trades slightly slower visual iteration cycles for fewer handoffs and one cohesive coding voice across the stack.

**Implications for handoff briefs**:
- New frontend briefs in `handoff/` use the prefix `claude_frontend_*.md` instead of `cursor_frontend_*.md`
- Existing `cursor_frontend_*.md` briefs remain historical — they describe what Cursor shipped in W1
- Allocation docs (`PM_W{N}_allocation.md`) list "Claude" as owner for frontend tickets from W2 onward

**Implications for the skill stack**:
- Claude must run frontend smoke tests (`npm run build`, `npm run test:unit` if present, `tsc -b`) before declaring a frontend ticket done — same bar as backend `uv run pytest`
- Visual / UX iteration that previously benefited from Cursor's hot-reload now happens via running `npm run dev` and manual browser spot-check; founder must spot-check before merge if a flow involves user interaction
- For pure visual polish (CSS-only diffs), Claude uses screenshots/diffs rather than guessing at hex values

**P2-5 anchor sidebar polish** (the only W2 frontend ticket) is re-owned by Claude per this rule. PM updates `PM_W2_allocation.md §3.3` to reflect this.

---

## 1. Phase 0 — completed by Claude this session

| # | Status | File(s) |
|---|---|---|
| P0-2 | ✅ done | `docs/TOPRADOR_SCHEMA.md` |
| P0-3 | ✅ done | `backend/src/agent/cascade/contract.py`, `frontend/src/types/cascade.ts` |
| P0-6 | ✅ done | `backend/src/agent/cascade/failures.py` |
| P0-4 | ✅ done | `backend/src/agent/cascade/adapter.py` |
| P0-5 | ✅ done | `backend/tests/test_cascade_contract.py` |
| P0-1 | ✅ synthetic-v1 done; awaits hand-label upgrade | `backend/src/agent/cascade/fixtures/synthetic_v1/*` |

**Open before Phase 0 Gate can close**: founder + helper hand-label **≥ 20 real samples** across 3 pinned niches, replace synthetic_v1 fixtures, re-run `test_cascade_contract.py` against the real corpus. Contract is allowed to evolve in **minor** ways (1.0 → 1.1) if real samples surface missing fields — but only with new fixture + new test.

---

## 2. Phase 1 ticket routing

### P1-1 · Landing page · **Cursor**

- Card stack as hero, NOT URL field as hero (UX Researcher F1)
- Hero copy locked by Brand Guardian: **"看到刷屏的视频，想做一条自己的？挑一张开始 ↓"**
- 3-5 hand-picked hot cards visible above fold (3 cards per niche, see brand guardrails §5 for visual)
- URL input degrades to small text "或者粘贴你看到的爆款链接 →" below cards
- Forbidden terms in any UI string: `节点`, `锚点`, `DAG`, `agent`, `画布`, `AI`, `平台`, `工具`, `智能`
- Lighthouse-style perf: hero < 1s on 4G
- **Acceptance**: 5 internal testers (not the founder) can identify the primary action within 3 seconds

### P1-2 · 浅分析 endpoint + card · **Codex backend / Cursor frontend**

- Backend (Codex):
  - `POST /api/analysis/shallow` accepts `{ source_url }`, returns `CascadeAnalysisContract`
  - Calls upstream analyzer (toprador if available, else stub returning a synthetic_v1 fixture for dev)
  - Always pipes raw payload through `normalize_analysis_result()` — never bypass
  - Emits `analysis_returned` event (per `02_event_spec.md` event #2)
- Frontend (Cursor):
  - 三段式人话模板: "开头怎么抓人 / 中间为什么不快进 / 结尾为什么忍不住点赞" (UX §F3)
  - Maps to `viral_analysis.hook`, `viral_analysis.pacing`, `viral_analysis.climax` — never display field names
  - Streaming text effect (chunked rendering) per UX recommendation
  - Confidence banner if `contract.confidence < 0.5`
  - Warning chips if any `W*` codes present (use `RECOVERY_HINTS`)
- **Acceptance**: shows analysis for `baomam_fushi/001.json` fixture in human-readable form with zero schema terms visible

### P1-3 · 赛道改写 prompt chain · **Claude (prompt) + Codex (chain)**

- Claude writes:
  - 3 niche-specific prompts (`prompts/rewrite_baomam_fushi.md`, `_yuer_richang.md`, `_jiating_chufang.md`)
  - Each prompt consumes the full `CascadeAnalysisContract` and emits `{ script: string, shots: {scene, dialogue, visual_content}[] }`
  - Each prompt run is logged + replayable (deterministic seed where available)
  - Target: 4/5 usable scripts on 5 reference URLs per niche before declaring P1-3 done
- Codex writes:
  - `POST /api/rewrite` chain wiring (LangGraph node taking `analysis_id`, returning script + shots)
  - Cost-cap check: refuses to run if predicted cost > ¥3 per rewrite
  - Emits `script_rewritten` event with `parser_warnings` payload for learning-loop §4 of event spec
- **Sprint Plan §1 bumped P1-3 to 5 days** — do not under-invest in prompt iteration. This is the moat-thesis ticket.

### P1-4 · Card-stack UI (formerly minimal canvas) · **Cursor**

- Renders DAG data model but as vertical card stack — single column, mobile-friendly even on desktop
- Card types: `ScriptCard`, `ShotCard` (×3-5), `PublishPackCard`
- Uses existing Zustand store + WebSocket plumbing in `frontend/src/store/canvasStore.ts` — do not introduce new state systems
- "Pro view" toggle in header reveals existing `Canvas.tsx` React Flow layout for MCN seeds only
- Persona-facing strings come from `brand_guardrails.md §4` term table
- **Acceptance**: persona test (5 non-creator testers ≥ 1 宝妈) can identify next action on each card within 5s

### P1-5 · Image generation (existing) · **No new code**

- Reuse `backend/src/agent/tools/generation.py` (Apimart + Gemini) verbatim
- Wire `ShotCard` to call existing image gen with `prompt = visual_content + niche_style` injection
- Owner: Cursor for frontend wiring; no backend changes

### P1-6 · 跨 run 锚点列表 · **Claude + Cursor**

- Claude writes backend:
  - New table `anchors`: `(id, user_id, kind, label, image_url, source_run_id, created_at)`
  - `GET /api/anchors` returns user's anchors grouped by kind (`character` | `scene`)
  - `POST /api/anchors` from a shot card → emits `anchor_created` event
  - Reused-in event emitted from `/api/rewrite` when a shot ref's `image_url` matches a prior anchor
- Cursor writes frontend:
  - Sidebar tab "你之前用过的" (Brand Guardian §4 — never says "锚点")
  - Drag a previous anchor onto a `ShotCard` → fills `subject` field + records `anchor_reused` event
- **Critical**: this is the load-bearing event for Phase 3 H8 moat thesis. Don't ship P1-6 without `anchor_reused` event firing correctly.

### P1-7 · 发布包导出 · **Cursor**

- Single button on `PublishPackCard`: "复制到剪贴板"
- Clipboard payload (text):
  - 标题候选 (3 个) — derived from analysis hook + niche-specific template
  - 标签 (5-8 个) — from `target_audience` + trending tags from niche dictionary
  - 脚本 — concatenated dialogue from shot cards
  - 镜头图 URL 列表 (signed S3 URLs, 24h TTL)
- Emits `publish_pack_copied` event
- No OAuth, no direct platform publish (PHASED_PLAN §4.3)

### P1-8 · UI warnings + confidence · **Cursor**

- Top-of-card banner if `contract.confidence < 0.5`
- Inline chips for each warning code (using `RECOVERY_HINTS` from failures.py)
- Failure banner on `HardFailure` — renders the 3 recovery action buttons from `RECOVERY_ACTIONS`
- All wording from the schema doc — never invent banner copy

### P1-9 · Cost guard middleware · **Codex**

- Middleware on `/api/analysis/*`, `/api/rewrite`, `/api/shot/generate`
- Per-run cap: ¥3 default, configurable per user
- Per-user daily cap: ¥30 default
- 80% threshold → soft warning banner; 100% → block with `S8_UPSTREAM_REFUSED`-style banner
- Emits `generation_cost` event per call (event #10)
- Backend reads from `events` table to compute current consumption — no separate cost ledger in Phase 1

### P1-10 · 10 creator trial + interviews · **Founder + Claude**

- Founder runs concierge onboarding (Growth Plan §4)
- Claude provides:
  - 5-question interview script (UX Researcher §5)
  - `interview_logged` event template with required fields
  - Post-interview Gate check SQL (event spec §3)

---

## 3. Event instrumentation routing

All 11 events from `02_event_spec.md` go in **one backend module** to avoid drift: `backend/src/agent/cascade/events.py`. Owner: Claude (small, contract-adjacent, must not fork).

```
event_emitted: 11 codes
  ↓
backend writes to events table (single source)
  ↓
founder runs Gate SQL from event spec §3
```

Front-end never directly writes events (Analytics Reporter §7 anti-event rule).

---

## 4. Hand-offs to Codex (separate brief files)

Three files in `docs/nexus/handoff/`:
- `codex_backend_P1-2.md` — analysis endpoint + adapter wiring
- `codex_backend_P1-3.md` — rewrite chain + cost cap
- `codex_backend_P1-9.md` — cost guard middleware

Each hand-off includes: file paths, function signatures, test acceptance, event emission contract, no-go list.

---

## 5. Hand-offs to Cursor (separate brief files)

Five files in `docs/nexus/handoff/`:
- `cursor_frontend_P1-1.md` — landing card stack
- `cursor_frontend_P1-4.md` — card-stack UI replacing canvas as default
- `cursor_frontend_P1-6.md` — anchor sidebar
- `cursor_frontend_P1-7.md` — publish-pack clipboard
- `cursor_frontend_P1-8.md` — warning + failure banners

Each hand-off includes: Tailwind tokens, term translation table, mock data path (synthetic_v1 fixtures), no-go terms.

---

## 6. Sequencing

The sequence below respects the Sprint Plan critical path:

```
W1 ─ founder: hand-label P0-1 real fixtures (parallel: recruitment outreach)
   ─ claude: P0 review & contract re-validation against real fixtures
W2 ─ founder: complete real fixture corpus → Phase 0 GATE
   ─ codex: kick off P1-2 backend wiring against fixtures
W3 ─ cursor: P1-1 landing
   ─ codex: P1-2 endpoint live
   ─ claude: P1-3 prompts iter 1 (per niche)
W4 ─ cursor: P1-4 card stack
   ─ codex: P1-3 chain wiring
   ─ claude: P1-6 anchor backend
W5 ─ cursor: P1-6 anchor sidebar + P1-7 publish-pack + P1-8 warnings
   ─ codex: P1-9 cost guard
   ─ founder: onboard creators 1-3 (concierge)
W6 ─ founder: creators 4-10 onboard, observation window for G3 return
   ─ claude: Gate SQL + event audit + assist with creator interviews
```

---

## 7. Coordination protocol

- All three tools (Claude / Codex / Cursor) commit to the same git repository
- One feature branch per Phase 1 ticket (`p1-2/shallow-analysis`, etc.)
- PR must pass: existing tests + new contract tests + brand-term lint (forbidden words check via simple grep in CI)
- Senior PM (this session) reviews each PR for contract-drift; Reality Checker reviews at Stage 4

---

## 8. Anti-routing rules

These changes are FORBIDDEN at this stage:
- Tooling other than Claude touching `cascade/contract.py` or `cascade/failures.py` (single source of truth)
- Any frontend tool writing to `cascade.ts` directly (only Claude regenerates from contract.py source)
- Any tool introducing a new event name not in `02_event_spec.md` (must update spec first, get PM sign-off)
- Cursor adding `framer-motion` / `swr` / any new top-level dep (Phase 1 stays on existing dep set)
- Codex adding a new third-party API integration without cost-cap wiring
