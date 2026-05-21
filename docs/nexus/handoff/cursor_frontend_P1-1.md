# Cursor handoff — P1-1 Landing page (card-stack hero)

**Source of truth**: `02_brand_guardrails.md` · `01_ux_research.md` §3 · `cardCopy.ts` (will be created in P1-4)
**Time budget**: 2 days

---

## 0. What you build

The Cascade landing page. Card-stack hero (3-5 hand-picked hot cards), URL input as a small fallback affordance below the cards, waitlist form CTA. NO `/topics` page yet — just the landing.

UX Researcher §F1: persona doesn't have a URL handy. URL field as hero kills conversion. **Cards-first** is non-negotiable.

---

## 1. Files

| Path | Purpose |
|---|---|
| `frontend/src/pages/Landing.tsx` | The new default route |
| `frontend/src/components/landing/HotCard.tsx` | One pre-curated hot card |
| `frontend/src/components/landing/HotCardGrid.tsx` | The 3-5 card grid |
| `frontend/src/components/landing/UrlFallback.tsx` | Small URL input under the grid |
| `frontend/src/components/landing/WaitlistCta.tsx` | Sticky waitlist CTA |
| `frontend/src/data/featured_cards.json` | 3-5 hand-curated cards (founder edits) |

Modify `frontend/src/App.tsx` so `/` renders `Landing` and `/canvas` renders the existing canvas root.

---

## 2. Hero copy (locked by Brand Guardian — do NOT paraphrase)

```
看到刷屏的视频，想做一条自己的？挑一张开始 ↓
```

That sentence. Nothing else above the cards. No subhead. No "Powered by AI." No "Welcome to Cascade." No logo above the headline.

Below cards: small text in `text-stone-500 text-sm`:
```
或者粘贴你看到的爆款链接 →
```

---

## 3. Forbidden terms (CI greps fail the build)

`节点` · `锚点` · `DAG` · `agent` · `Agent` · `画布` · `AI` · `平台` · `工具` · `智能` · `pipeline` · `workflow` · `Welcome to` · `Powered by`

---

## 4. Visual

Per brand guardrails §5:
- `bg-stone-50` page bg
- Cards: `rounded-2xl bg-white shadow-sm border border-stone-200 p-5 hover:shadow-md transition-shadow`
- Primary CTA: `bg-orange-500 hover:bg-orange-600 text-white rounded-xl py-3 px-5 font-medium`
- Type: hero `text-2xl font-medium`, card title `text-lg`, body `text-base`, caption `text-sm`
- Max width 720px, centered, mobile-first even on desktop
- Icons: `lucide-react` only, no emoji

---

## 5. Hot card structure (per HotCardGrid item)

```
┌────────────────────────────┐
│  [thumbnail]               │
│                            │
│  ⚡ 今天值得拍                │
│                            │
│  这条 5 万赞辅食视频           │
│  开头怎么抓人 / 节奏密度        │
│  / 结尾反差                  │
│                            │
│        [挑这一张 →]          │
└────────────────────────────┘
```

Data shape (`featured_cards.json`):
```json
[
  {
    "id": "card_001",
    "niche": "baomam_fushi",
    "thumbnail_url": "https://...",
    "title_three_lines": ["这条 5 万赞辅食视频", "开头 1.2 秒抛痛点", "结尾反差"],
    "fixture_analysis_id": "ana_syn_baomam_001"
  }
]
```

3-5 entries (founder curates). Clicking "挑这一张" loads `Canvas` route with `?analysis_id=...` and the existing P1-4 card-stack renders from the analysis fixture.

---

## 6. Waitlist CTA

Sticky footer (only after scroll 50%). Text:
```
内测 10 人 · 6 周免费 · 我陪你做完第一条
[ 私信我加入 → ]
```

Click opens a modal with a one-field form (微信号 or 私信链接), POST to `/api/waitlist`. NO backend implementation in this brief — stub with `console.log` + toast "我们收到了". Backend wiring is W2.

---

## 7. Acceptance (`scripts/check_progress.sh` greps for these)

- `npm run build` exits 0 (no warnings about new files)
- `find frontend/src/pages/Landing.tsx frontend/src/components/landing -type f | wc -l` ≥ 5
- `grep -rn "节点\|锚点\|DAG\|agent\|Agent\|画布\|AI\|平台\|工具\|智能\|pipeline\|workflow\|Welcome to\|Powered by" frontend/src/pages/Landing.tsx frontend/src/components/landing/ frontend/src/data/featured_cards.json` returns 0 matches
- Lighthouse on `/`: LCP < 1.5s simulated 4G
- 5 non-engineer testers identify "挑这一张" as the primary action within 3 seconds

---

## 8. NOT in this ticket

- No actual `/topics` page (Phase 2)
- No `analysis_id` resolution from backend (P1-2's job)
- No anchors visibility (P1-6 sidebar lives in canvas, not landing)
- No waitlist backend (stub only)
