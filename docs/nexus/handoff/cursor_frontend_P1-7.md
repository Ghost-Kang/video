# Cursor handoff — P1-7 publish-pack copy

**Source of truth**: `02_event_spec.md` event #5 · `02_brand_guardrails.md` term table
**Time budget**: 1 day

---

## 0. What you build

The PublishPackCard at the bottom of the card stack. One button copies a clipboard-ready bundle: 3 candidate titles + 5-8 tags + the full rewritten script + each shot image URL.

No OAuth. No direct platform publish. Just copy to clipboard.

---

## 1. Files

| Path | Purpose |
|---|---|
| `frontend/src/components/cards/PublishPackCard.tsx` | The card UI |
| `frontend/src/lib/buildPublishPack.ts` | Pure function: `(rewriteResult, shotImages) -> string` (the clipboard payload) |
| `frontend/src/lib/__tests__/buildPublishPack.test.ts` | Unit tests for the payload builder |

---

## 2. UI

```
┌──────────────────────────────────────┐
│   准备发出去                          │
│                                      │
│   候选标题（挑一个）                   │
│   • 宝宝拒食 3 次，第 4 次终于吃了      │
│   • 这一勺下去我哭了                    │
│   • 妈妈版的「30 分钟搞定辅食」         │
│                                      │
│   标签                                │
│   #辅食 #育儿日常 #宝妈 #辅食教程 ...    │
│                                      │
│   ┌────────────────────────────────┐  │
│   │      一键复制，去发              │  │
│   └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

Title text (per Brand Guardian): `准备发出去`, `候选标题（挑一个）`, `标签`, `一键复制，去发`.

After click: toast "复制好了，去抖音粘贴吧" (per `02_brand_guardrails.md` copy_success).

---

## 3. Clipboard payload format

```
【标题候选】
1. {title_1}
2. {title_2}
3. {title_3}

【标签】
{tag_1} {tag_2} {tag_3} {tag_4} {tag_5} {tag_6} {tag_7}

【完整脚本】
{rewritten_script}

【镜头图】
镜头 1: {shot_1_image_url}
镜头 2: {shot_2_image_url}
...

—— 用 Cascade 做的 · cascade.app
```

(The trailing line is the only place "Cascade" name appears in the kit. Founder may strip it pre-paste; that's their choice.)

---

## 4. Title generation (where titles come from)

Phase 1 = client-side template inserts using the rewrite result. Three variants:
- Hook-led: "{viral_analysis.hook 简化版}"
- Result-led: "{rewrite_notes 中的'改了什么'部分} {emoji?}" (NO emoji — per brand guardrails)
- Question-led: "{painpoint 提问式}"

If LLM-generated titles are needed, defer to Phase 2 — not in this ticket.

---

## 5. Tags

Source: niche-specific tag list per Brand Guardian §5 + the analysis `viral_analysis.target_audience` keyword. Total 5-8 tags. Hard-coded niche tag list in `buildPublishPack.ts`:

```ts
const NICHE_TAGS = {
  baomam_fushi: ['#辅食', '#辅食教程', '#宝妈日常', '#育儿干货'],
  yuer_richang: ['#育儿日常', '#宝妈', '#新手妈妈', '#带娃日常'],
  jiating_chufang: ['#家庭厨房', '#简单晚餐', '#美食教程', '#在家做饭'],
};
```

Pick 4 from the niche + 1-3 from `viral_analysis.target_audience`. Always 5-8 total.

---

## 6. `publish_pack_copied` event

Frontend POSTs to `/api/events` with:
```json
{
  "event_name": "publish_pack_copied",
  "user_id": "...",
  "run_id": "...",
  "payload": {
    "rewrite_id": "rw_...",
    "shots_count": 5,
    "titles_offered": 3,
    "tags_count": 7,
    "payload_size_chars": 1432
  }
}
```

Use the same `/api/events` endpoint Codex builds for the events module. If it doesn't exist yet, stub the POST + queue in localStorage; backend later drains it.

---

## 7. Tests

`buildPublishPack.test.ts`:
- 3 titles always returned
- 5-8 tags always
- Image URLs in order
- Forbidden terms grep on output → 0 matches (excluding the `Cascade · cascade.app` trailer)
- Payload size < 4096 chars (clipboard sanity)

---

## 8. Done-signal

- `npm run build` clean
- `grep -rn "锚点\|节点\|画布\|workflow" frontend/src/components/cards/PublishPackCard.tsx` = 0
- Manual: load mock canvas state, click copy, paste into a text editor — payload matches §3 format
- Event POST visible in network tab on click

---

## 9. NOT in this ticket

- OAuth platform publish (Phase 3)
- LLM-generated titles (Phase 2)
- Image hosting / signed URLs (existing S3 in `s3_upload.py`)
- Stripe / paywall around publish (Phase 2)
