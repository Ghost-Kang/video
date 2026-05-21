# Cursor handoff — P1-4 卡片栈 UI (replaces minimal canvas as default)

**Target tool**: Cursor (interactive frontend iteration)
**Owner accountability**: This brief is a contract. Any divergence requires PM sign-off in `docs/nexus/03_routing.md`.
**Source of truth**: `docs/nexus/01_ux_research.md` §2 · `docs/nexus/02_brand_guardrails.md` §4-§5 · `frontend/src/types/cascade.ts`

---

## 0. The pivot

UX Researcher's finding: the 宝妈 persona will reject `node + edge` UI within 10 seconds. The DAG data model stays underneath — but the default render in Phase 1 is a **vertical card stack**.

The existing `frontend/src/components/Canvas.tsx` (React Flow) stays in the codebase and is reachable via a header toggle for MCN seed users. Default new users see the card stack.

This brief is for the card stack. Do not touch `Canvas.tsx`.

---

## 1. What you are building

Three card components and a single-column page that stacks them:

```
┌────────────────────────────────────────┐
│  Header                                 │
│  ┌──────────────────────────────────┐   │
│  │  ScriptCard                       │   │  ← from contract.viral_analysis.replicable_formula
│  │  + 三段式人话                       │   │     and rewritten dialogue
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  ShotCard #1 (thumb + text)       │   │  ← from contract.scenes[0]
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  ShotCard #2                      │   │
│  └──────────────────────────────────┘   │
│  ... (3-5 ShotCards total)              │
│  ┌──────────────────────────────────┐   │
│  │  PublishPackCard                  │   │  ← copy-to-clipboard
│  └──────────────────────────────────┘   │
└────────────────────────────────────────┘
```

Single column. Max width 640px centered. Mobile-first sizing even on desktop.

---

## 2. Files you will create

| Path | Purpose |
|---|---|
| `frontend/src/components/cards/ScriptCard.tsx` | Script + viral_analysis 三段式 |
| `frontend/src/components/cards/ShotCard.tsx` | One scene (thumb + text + actions) |
| `frontend/src/components/cards/PublishPackCard.tsx` | Final copy button + clipboard payload |
| `frontend/src/components/CardStack.tsx` | Vertical stack page; the entry view |
| `frontend/src/components/ProViewToggle.tsx` | Header toggle: card stack ↔ React Flow canvas |
| `frontend/src/lib/cardCopy.ts` | Term translation table (engineer term → user term); single import for any user-facing string |

You will modify:
- `frontend/src/App.tsx` — default route renders `CardStack`; `?view=pro` renders existing `Canvas`
- `frontend/src/components/Header.tsx` — add the toggle

---

## 3. Term translation table (mandatory)

`frontend/src/lib/cardCopy.ts` is the only place any user-facing copy lives. Brand Guardian §4:

```ts
export const COPY = {
  // headers
  script_header: '改完的版本',
  shots_header: '镜头草稿',
  publish_header: '准备发出去',
  // viral_analysis 三段式
  hook_label: '开头怎么抓人',
  pacing_label: '中间为什么不快进',
  climax_label: '结尾为什么忍不住点赞',
  // shot card
  shot_label_prefix: '第',
  shot_label_suffix: '段',
  shot_dialogue_placeholder: '（这段没有台词，是画面）',
  // anchor reuse
  anchor_picker_title: '你之前用过的',
  anchor_character_label: '角色',
  anchor_scene_label: '场景',
  // publish pack
  copy_button: '一键复制，去发',
  copy_success: '复制好了，去抖音粘贴吧',
  // failure banners (use RECOVERY_HINTS from contract.ts — re-import there if not yet ported)
} as const;
```

**Forbidden anywhere in this UI** (CI grep blocks them):
`节点` · `锚点` · `DAG` · `agent` · `Agent` · `画布` · `AI` · `平台` · `工具` · `智能` · `pipeline` · `workflow`

If a future requirement seems to need one of these words, escalate — don't ship.

---

## 4. Visual style (from brand guardrails §5)

- Tailwind only. No new CSS files.
- Background: `bg-stone-50`
- Card: `rounded-2xl bg-white shadow-sm border border-stone-200 p-5`
- Primary action: `bg-orange-500 hover:bg-orange-600 text-white rounded-xl py-3 px-5 font-medium`
- Type scale: text-sm (caption), text-base (body), text-lg (card title), text-2xl (hero only)
- Icons: lucide-react. No emoji.
- No gradients. No purple. No illustrations. No animations beyond `transition-colors`.

---

## 5. Data flow

```ts
// CardStack reads from the Zustand store (existing canvasStore)
const analysis = useCanvasStore((s) => s.analysis); // CascadeAnalysisContract | null
const script = useCanvasStore((s) => s.script);
const shots = useCanvasStore((s) => s.shots);

// Each card is purely presentational. State stays in the store.
```

If `analysis` is null → show empty state with copy from `cardCopy.ts` (you'll add an empty_state key).

If `analysis.confidence < 0.5` → banner at top of `CardStack`:
> "系统对这条分析的把握一般，仅供参考"

If `analysis.warnings` non-empty → small chip on the corresponding card showing `RECOVERY_HINTS[warning.code]`.

---

## 6. ScriptCard contents

In order top-to-bottom:
1. **"为什么这条会火"** section (3 short bullets from `viral_analysis.hook` / `pacing` / `climax`)
2. **"改完的版本"** section (the rewritten script — from store, not from contract directly)
3. Edit button (small, secondary) — opens inline textarea to edit the rewritten script

NO field names visible. NO `viral_analysis` shown as a label.

---

## 7. ShotCard contents

In order:
1. Thumbnail (use `first_frame_url` if present, else placeholder)
2. Label "第 {scene_index} 段"
3. Dialogue text (or `shot_dialogue_placeholder` if empty)
4. Visual description (small, secondary text)
5. Two actions:
   - "换个角色" → opens `AnchorPicker` filtered to `kind=character`
   - "用我之前的场景" → opens `AnchorPicker` filtered to `kind=scene`

The `AnchorPicker` component is **P1-6 scope** — for this brief, stub it as a button with `onClick={() => alert("coming soon")}` and a TODO comment referencing P1-6.

---

## 8. PublishPackCard contents

1. Three suggested titles (placeholder; real generation is P1-7 backend work)
2. Tag list (5-8 chips)
3. Single `Copy` button using the cardCopy.copy_button text
4. Toast `copy_success` on success

The actual clipboard payload assembly lives in `frontend/src/lib/buildPublishPack.ts` (you'll create this; one pure function).

---

## 9. ProViewToggle behavior

- Default: card stack
- Click toggle: navigate to `?view=pro`, render existing `Canvas.tsx`
- `?view=pro` persists in URL only — no localStorage, no user profile setting (Phase 1 keeps it simple)
- For users on the 10-creator trial allowlist, the toggle is **hidden by default** (env flag or hardcoded list — your call, keep it simple)

---

## 10. Tests

Two test files using vitest (already in the repo if you find it; if not, escalate before adding a test framework):
- `frontend/src/components/cards/__tests__/ScriptCard.test.tsx` — renders all 3 bullets, never displays raw field names
- `frontend/src/components/cards/__tests__/ShotCard.test.tsx` — placeholder copy when dialogue empty, anchor buttons present

A simple regex test that asserts no forbidden term appears in rendered HTML for any card.

---

## 11. What you must NOT do

- ❌ Add any new top-level dependency (no `framer-motion`, no `radix-ui` packages beyond what's already installed, no `swr`, no `react-query`).
- ❌ Modify `Canvas.tsx` / `canvasStore.ts` structure. You may add new state slices, not change existing ones.
- ❌ Introduce a design system / theme provider. Use Tailwind utility classes directly.
- ❌ Add animation libraries. Use Tailwind `transition-*` only.
- ❌ Display any field name (no "hook:", no "viral_analysis", no "shot_index") in the rendered DOM.
- ❌ Touch the React Flow canvas implementation.

---

## 12. Acceptance

When you are done:
1. `frontend/` builds without warnings.
2. Default route renders the card stack with the `baomam_fushi/001` synthetic fixture (mocked in store init).
3. `?view=pro` renders the existing canvas.
4. Forbidden-term grep over `frontend/src/components/cards/` returns zero hits.
5. 5 internal testers (non-engineers preferred, at least one parent of young child) can identify "next action" on each card within 5 seconds.
6. Lighthouse on the card stack route: LCP < 1.5s on simulated 4G.

---

## 13. Time budget

**4 days** per Sprint Plan. The 4 days assume the existing Canvas + Zustand + WebSocket plumbing is reused as-is for state; if you find yourself needing to refactor state, stop and escalate. Card stack changes WHAT P1-4 IS, not HOW MUCH P1-4 takes.
