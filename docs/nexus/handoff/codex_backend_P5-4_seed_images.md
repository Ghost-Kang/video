# Codex handoff — P5-4 小红书 seed 帖 9 张 image2 AI 生成

**Owner**: Codex session(backend)
**Status**: ✅ **READY**(2026-05-23 W3D6 PM 写就,prompts + 脚本规格全 ship)
**Time budget**: **~30 min**(脚本 + 9 张 gen + 上传)
**Allocation**: ad-hoc(不在 PM_W5_allocation,founder W3D6"现在就启动"现场触发)
**Trust risk acknowledgement**: founder W3D6 chat 明示选择 Option 2 = 全 9 张 AI gen(已知 AI 食物图在母婴 niche 有 trust 损失风险)。PM 不再 reality-check。
**Source of truth**:
- 9 张图原始 brief:`docs/nexus/founder_log/xhs_post_2026-05-23.md`(Content Creator agent 出)
- 9 个 image2 prompts:本文件 §4(Image Prompt Engineer agent 出,2026-05-23)
- **GoogleProvider 接口**:`backend/src/agent/tools/generation.py:125`(W3D7 founder 选 B 路径,gemini-3.1-flash-image-preview 免费层)
- model:`backend/src/agent/config.py:28` `IMAGE_GEN_GOOGLE_MODEL=gemini-3.1-flash-image-preview`

---

## 0. ENV BLOCKER(必读,Codex 起跑前 verify)

**2026-05-24 W3D7 founder 选路径 B**(`PM W3D7 reality-check`):用 GoogleProvider 而非 ApimartProvider。

`.env` 必须有:
```
GOOGLE_API_KEY=<在 aistudio.google.com 拿>
IMAGE_GEN_PROVIDER=google   # 已是默认值,可省;为 explicit 推荐显式写
```

Verify:
```bash
grep -E "^GOOGLE_API_KEY|^IMAGE_GEN_PROVIDER" .env
```

若 `GOOGLE_API_KEY` 未设 → 脚本第 1 张就抛 `genai.Client(api_key=None)` 异常,**整体 abort**。

**不要** 尝试切到 ApimartProvider 兜底(`.env` 也没 `IMAGE_GEN_API_KEY`)— founder W3D7 显式拒绝 A 路径。两 provider 都缺 key 时 → Codex 在 chat ping founder "ENV BLOCKER, 待补 GOOGLE_API_KEY"。

---

## 0. 背景

founder W3D6(2026-05-23 Sat)触发"现在就启动"路径 B(`founder_punchlist_W4D1_2026-05-28.md §2-§3` 提前到 W3D6),原本 seed 帖封面 + 8 正文图由 founder iPhone 5 min 拍 + 美图秀秀套模板。founder 现场决定 9 张全 AI gen,以节省拍摄 5 min。

PM W3D6:
1. 已 Image Prompt Engineer 调出 9 个 gpt-image-2 prompts(本文件 §4)
2. 风险已 reality-check(`PM W3D6 chat → founder 选 Option 2`)
3. founder 仍需做"复制文案 + 发小红书"unproxyable 步骤(P5-4 仅替换"拍照片"环节)

P5-4 = Codex 跑 ApimartProvider × 9 次,产 9 张 PNG,落 `docs/nexus/founder_log/xhs_post_2026-05-23_images/`,founder 收到立即上传小红书。

---

## 1. Done-signal

- `docs/nexus/founder_log/xhs_post_2026-05-23_images/` 目录下 9 张 PNG:
  - `cover.png`(封面,3:4 portrait)
  - `img_2.png` ~ `img_9.png`(正文 8 张,3:4 portrait)
- `docs/nexus/founder_log/xhs_post_2026-05-23_images/_gen_log.md` 记录:
  - 每张图:prompt_index、actual_time(秒)、attempt 次数、bytes 大小、本地 PNG 路径
  - 总成本估算(Gemini 3.1 flash image preview 免费层 ≤ X 次/分钟;若进入付费按 google ai pricing 查)
  - 失败重试次数(GoogleProvider.poll 返回 error 自动重试 ≤ 2 次)
- 在 chat 给 founder 一行:"P5-4 done,9 张图本地 `docs/nexus/founder_log/xhs_post_2026-05-23_images/`,文件名 cover.png + img_2-9.png,直接发小红书"
- commit `feat(P5-4): seed 帖 9 张 image2 gen — Codex ship`

---

## 2. 实现指引

### 2.1 脚本位置

`scripts/p5-4_seed_images.py`(新)

### 2.2 接口要点(`tools/generation.py:125 GoogleProvider`)

```python
from agent.tools.generation import GoogleProvider

provider = GoogleProvider()  # 内部 genai.Client(api_key=GOOGLE_API_KEY)
result = await provider.generate(
    prompt="...",
    size="3:4",   # 注意:GoogleProvider 当前实现 size 参数未传到底层(genai 接口不需要),
                  # 比例由 prompt 显式声明 "3:4 portrait" 控制(每个 prompt 已嵌入)
    resolution="2k",
)
# result = {"image_data": <bytes>, "actual_time": 12.3} 或 {"error": "..."}
```

**重要差异 vs ApimartProvider**:GoogleProvider 直接返回 `image_data: bytes` 而非 URL — 不需要 httpx 下载步骤,bytes 直接 `path.write_bytes(image_bytes)` 落盘。

### 2.3 脚本骨架(GoogleProvider 版)

```python
"""P5-4 seed 帖 9 张图 image gen (Google Gemini 3.1 flash image preview)。

使用:
    cd backend && uv run python ../scripts/p5-4_seed_images.py
"""
import asyncio, json, time
from pathlib import Path

from agent.tools.generation import GoogleProvider

OUT_DIR = Path(__file__).parent.parent / "docs/nexus/founder_log/xhs_post_2026-05-23_images"
PROMPTS_JSON = Path(__file__).parent / "p5-4_prompts.json"

async def gen_one(provider, name, prompt, retries=2):
    for attempt in range(retries + 1):
        result = await provider.generate(prompt=prompt, size="3:4", resolution="2k")
        if "image_data" in result:
            return {**result, "attempt": attempt + 1}
        if attempt == retries:
            return result
        print(f"[{name}] 重试 {attempt + 1}/{retries}: {result.get('error')}")
        await asyncio.sleep(3)

async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompts = json.loads(PROMPTS_JSON.read_text())
    provider = GoogleProvider()
    log_lines = [
        "# P5-4 image gen log (GoogleProvider · gemini-3.1-flash-image-preview)",
        f"started: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
    ]

    for idx, item in enumerate(prompts, start=1):
        name = item["name"]
        print(f"[{idx}/9] {name} 提交中...")
        result = await gen_one(provider, name, item["prompt"])
        if "image_data" in result:
            local = OUT_DIR / f"{name}.png"
            local.write_bytes(result["image_data"])
            log_lines.append(
                f"- {name}: ✅ time={result['actual_time']:.1f}s "
                f"attempt={result['attempt']} bytes={len(result['image_data'])} → {local.name}"
            )
        else:
            log_lines.append(f"- {name}: ❌ {result.get('error', 'unknown')}")
            print(f"[{name}] 失败:{result.get('error')}")

    log_lines += ["", f"finished: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"]
    (OUT_DIR / "_gen_log.md").write_text("\n".join(log_lines), encoding="utf-8")
    print(f"完成,日志 {OUT_DIR / '_gen_log.md'}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2.4 Codex 实现建议

- prompts 写到 `scripts/p5-4_prompts.json`(从本文件 §4 提取,数组顺序 = 1..9,`name` = `cover` / `img_2` / ... / `img_9`)
- 跑前 verify `.env` 有 `GOOGLE_API_KEY`(参考 §0 ENV BLOCKER)
- 跑前 + 跑后看 `aistudio.google.com` quota 是否进入付费;Gemini 3.1 flash image preview 免费层一般够 9 张
- 顺序提交即可(GoogleProvider 内部 `asyncio.create_task` 并发友好,但本场景顺序更便于人工 review 单张失败)
- 单张 timeout 120s(GoogleProvider hard-coded),9 张约 1-3 min 总耗

---

## 3. 边界(不在此票)

- **不动** `xhs_post_2026-05-23.md` 文件(已 commit `bb99ebe`,founder 仍按文案部分发)
- **不发** 帖子到小红书(founder unproxyable)
- **不做** 后期 P&S 加大字标题"招募 10 位宝妈..."(本来 Image Prompt Engineer 已让封面左上留白,founder 在小红书 app 自己用美图秀秀 / Canva 套模板加字)
- **不做** image gen quality 评审 — gpt-image-2 第一张产出 founder 看一眼即可,不达预期由 founder 在 chat 说"重生 cover" → PM 触发本 brief 单图重跑

---

## 4. 9 个 image2 prompts

**统一 style anchor**(每张图 prompt 内已嵌入):shot on iPhone 14, natural window light, Chinese home kitchen aesthetic, lived-in not staged
**统一 size**: `3:4`(portrait,小红书 feed)
**统一 resolution**: `2k`
**色调一致性 critical**:封面 + 图 9 的南瓜泥颜色必须完全一致(以保证 9 图视觉连贯)— prompt 9 已显式加 "color tone must match cover exactly"

---

### Prompt 1 — `cover.png`(封面)

Top-down overhead flat-lay photograph of a small plain white ceramic bowl placed slightly off-center on a worn light-wood cutting board, filled with a small portion of warm orange-red pumpkin puree showing a slightly uneven, hand-mashed texture with one tiny visible lump. Beside the bowl, half a raw kabocha pumpkin chunk with rough skin and a simple unvarnished wooden baby spoon rest casually, as if just set down. Generous negative space in the upper-left third of the frame for later text overlay. Soft 45-degree side window light from camera-right, warm 4500K color temperature, gentle natural shadows falling left, no harsh highlights. Subtle linen or unbleached cotton cloth corner peeking in bottom-right. Muted warm palette: cream, soft orange, honey-wood brown, off-white. Shallow depth of field on a phone camera, slightly grainy, candid mom-blog aesthetic, not commercial food styling. Authentic Chinese home kitchen feel. No human hands, no fingers, no faces. No text, no watermarks, no logos. No marble countertop, no oak floor, no Western kitchen styling. No glossy commercial food-styling sheen. No over-saturated colors, no HDR. No restaurant-style garnish.

### Prompt 2 — `img_2.png`(手机展示爆款九宫格)

Top-down close-up photograph of a smartphone lying at a slight 15-degree tilt on the same worn light-wood cutting board from the cover shot. The phone screen displays a vertical social-feed app interface showing a 3-by-3 grid of small thumbnail tiles, each tile depicting a different simple baby-food dish in a small bowl — warm pumpkin, green vegetable puree, orange carrot mash, white rice cereal, soft fruit, mixed porridge — all in muted warm tones consistent with home cooking. The tiles look like authentic mom-creator content, not magazine photos. Each thumbnail has a small heart icon and a number indicator in the corner, abstract and unreadable. One whole fresh carrot with green tops rests beside the phone. Soft 45-degree window light from camera-right, warm 4500K, gentle shadows. Palette: cream, honey wood, soft orange, muted green. Shallow phone-camera depth of field, slight grain, candid feel. No readable Chinese or English text on the phone screen. No recognizable app logos. No human hands, no fingers, no faces. No brand names. No Western kitchen elements. No glossy commercial sheen.

### Prompt 3 — `img_3.png`(食材九宫格平铺)

Top-down overhead flat-lay arrangement of six raw baby-food ingredients loosely placed on an unbleached off-white cotton cloth backdrop, organized in a relaxed 3-by-3 grid with the center square left intentionally empty. Ingredients: a wedge of orange kabocha pumpkin, a small head of fresh broccoli, two whole carrots with green tops, two brown-shell eggs in a small ceramic dish, an unbranded paper-style pouch of pale rice cereal with neutral kraft surface, one ripe avocado halved showing the pit. In the empty center square sits a small folded handwritten paper note on cream paper, blank or with illegible scribbles — no readable text. Soft 45-degree side window light, warm 4500K, natural shadows. Color palette: warm orange, soft green, cream, honey, muted brown. Slight phone-camera grain, candid lived-in arrangement, not magazine-perfect alignment. Authentic Chinese home cook aesthetic. No readable text. No visible brand logos. No human hands. No over-styled gourmet garnish. No marble surface, no Western kitchen elements. No glossy commercial sheen.

### Prompt 4 — `img_4.png`(模拟群聊痛点截图)

Vertical smartphone screenshot mockup of a generic mobile group-chat interface with a soft pale-yellow cream background, no recognizable app branding. The screen shows three to four stacked message bubbles in muted gray and soft beige, each containing illegible blurred placeholder text strokes that read as Chinese-looking handwriting blur — no actual readable characters. One central message bubble is slightly larger and emphasized, with a hand-drawn imperfect red circle annotation around a small portion of its blurred content, the red circle drawn loosely like a marker scribble. Small abstract avatar circles on the left of each bubble, soft gray, no faces. Timestamp markers in the corner are abstract dots. Overall warm 4500K tint, candid screenshot feel as if photographed off a phone screen at a slight angle with subtle moiré, not a pixel-perfect render. Color palette: pale cream yellow, soft gray, off-white, accent red circle. No readable Chinese characters, no readable English words. No real app logos. No human faces in avatars. No real phone numbers, no real usernames. No watermarks. No harsh neon red — use muted hand-drawn red. No Western-style messaging UI. No emojis that look like specific brand sets.

### Prompt 5 — `img_5.png`(手写交付清单白纸)

Top-down overhead photograph of a single sheet of slightly textured cream-white A5 paper resting on a warm honey-wood desk surface. The paper shows handwritten ballpoint pen marks in dark navy ink — four short bullet lines with small circled numbers, written in a casual feminine handwriting style. The actual letterforms are intentionally soft and slightly out of focus so no specific language is legible, reading as abstract handwritten strokes rather than real words. A simple black ballpoint pen rests diagonally on the lower-right corner of the paper, weighing it down. Soft 45-degree side window light from camera-right, warm 4500K tone, gentle shadow of the pen falling left across the paper. Palette: cream paper, honey wood, navy ink, black pen. Slight phone-camera grain, candid journaling aesthetic, not stationery-brand styled. No readable text, no specific Chinese or English words. No human hands. No brand logos on the pen. No notebook lines. No Western desk styling. No stickers, no washi tape clutter.

### Prompt 6 — `img_6.png`(中式厨房灶台辅食锅)

Slightly angled three-quarter view photograph of a corner of a simple Chinese home kitchen stovetop. A small stainless-steel milk pot with a slim handle sits on a standard white gas stove, gentle steam rising softly. Beside it, a small round stainless-steel steamer basket with a wooden-rimmed lid partially open. In the foreground, a small plain white ceramic bowl holds a finished portion of warm orange baby-food puree. The background shows a hint of a white-tiled wall and a soft out-of-focus edge of a basic range hood — utilitarian, not designer. Soft diffused daylight from a side window, warm 4500K, gentle ambient shadows. Color palette: stainless silver, white tile, honey wood, warm orange, cream. Lived-in everyday feel, slight smudges and water marks on the stove suggesting real use, not a showroom. Slight phone-camera depth of field, candid grain. No human hands, no faces. No marble countertop, no oak cabinetry, no Western range. No induction cooktop with branded touchscreen. No visible brand logos. No overly clean showroom sterility.

### Prompt 7 — `img_7.png`(笔记本贴爆款封面拆解)

Top-down overhead photograph of an open spiral-bound notebook with cream pages resting on a worn honey-wood desk. The left page shows three small rectangular printed photo cutouts arranged vertically, each depicting a soft-toned warm baby-food bowl image — pumpkin, green vegetable, mixed porridge — attached with small pieces of beige washi tape. The right page shows three short handwritten bullet lines in dark navy ballpoint ink with small circled numbers, the handwriting deliberately soft and unreadable, reading as abstract strokes rather than specific words. Soft 45-degree side window light from camera-right, warm 4500K, gentle shadow across the spine. Palette: cream paper, honey wood, navy ink, warm orange and green accents in the photo cutouts. Lived-in journaling feel, slight pen indentations visible, candid not curated. Phone-camera grain, shallow depth of field. No readable text. No recognizable Xiaohongshu interface elements. No human hands. No brand logos. No neon-colored washi tape. No Western planner-influencer styling.

### Prompt 8 — `img_8.png`(手机报名表单截图)

Top-down close-up photograph of a smartphone lying at a slight 15-degree tilt against a small white ceramic bowl on a worn light-wood cutting board, with a single fresh red apple resting nearby for casual context. The phone screen displays a generic vertical form-style interface with a cream-white background — a title bar at the top showing soft blurred unreadable header text, followed by four to five rectangular input field placeholders in light gray, and a single rounded primary action button in muted warm orange at the bottom. No specific words are legible, all text rendered as soft horizontal placeholder strokes. The form looks clean, minimal, and lived-in, photographed off the phone screen at a slight angle. Soft 45-degree window light from camera-right, warm 4500K, gentle shadows. Palette: cream, honey wood, soft orange button, off-white, apple red accent. Phone-camera grain, candid mom-creator aesthetic. No readable Chinese or English text on the screen. No recognizable app or platform logos. No human hands. No brand markings. No Western kitchen elements. No overly polished SaaS-product-shot aesthetic. No QR codes visible yet.

### Prompt 9 — `img_9.png`(收尾辅食碗便签留白)

Top-down overhead flat-lay photograph of a small plain white ceramic bowl placed slightly right-of-center on the same worn light-wood cutting board used in the cover shot, filled with a small portion of warm orange-red pumpkin puree matching the exact color tone of the cover image for visual consistency. Beside the bowl on the left rests a small folded square of cream paper, a handwritten note in dark navy ballpoint ink with soft unreadable strokes, deliberately illegible. Generous negative space in the lower-left third of the frame, intended for a later QR code overlay. A simple unvarnished wooden baby spoon rests at the top edge of the bowl. Soft 45-degree side window light from camera-right, warm 4500K, gentle natural shadows. Palette: cream, soft orange, honey wood, navy ink, off-white. Phone-camera grain, candid mom-blog aesthetic, lived-in not staged. No readable text on the note. No actual QR code rendered (leave space blank). No human hands. No brand logos. No marble countertop. No glossy commercial food-styling sheen. No over-saturated HDR. **Color tone of the pumpkin puree must exactly match the cover image (Prompt 1)** to maintain 9-image visual consistency.

---

## 5. 失败兜底

- GoogleProvider 返回 `{"error": "timeout"}` → 自动重试 ≤ 2 次,仍失败标注 `_gen_log.md` + PM 在 chat 给 founder 报 "图 N 失败,founder 决定:跳过 / 重试 / 降回 hybrid(founder 自拍 1 张 + 其他重试)"
- GoogleProvider 返回 `{"error": "Google 生图失败: ..."}` 含 quota / billing 字样 → 极大概率免费 quota 用完;Codex 直接报 founder,founder 决定补付费 OR 切回 Option C hybrid(打回原始 founder 自拍流程)
- 9 张图全部失败 → P5-4 标 blocked,founder 决定:(a)开通 Google 付费 quota 重跑,(b)切 Apimart(需新补 IMAGE_GEN_API_KEY),(c)founder 5 min 拍封面 + 美图秀秀伪造其余
- 单张图质量明显不符合 prompt(例如出现可读 Chinese text / 出现 Western kitchen / 出现 human hands)→ founder review 后 chat 说"图 N 重生,加约束 X",Codex 现场改 prompt + 单图重跑

---

## 6. Upstream dep

- ✅ `xhs_post_2026-05-23.md`(seed 帖文案 + 9 图 brief,commit `bb99ebe`)
- ⛔ `GOOGLE_API_KEY` 待 founder W3D7 现场补到根 `.env`(`aistudio.google.com` → API keys → Create)
- ✅ `google-genai>=1.75.0` 已在 `backend/pyproject.toml:11`
- ✅ GoogleProvider 已生产环境验证(canvas image gen 现实使用)

---

## 7. Output 清单

- `scripts/p5-4_seed_images.py`(新)
- `scripts/p5-4_prompts.json`(从 §4 提取的 9 个 prompts,Codex 现场抄进去)
- `docs/nexus/founder_log/xhs_post_2026-05-23_images/cover.png` + `img_2.png` ~ `img_9.png`(9 PNG)
- `docs/nexus/founder_log/xhs_post_2026-05-23_images/_gen_log.md`(gen 日志)
- commit:`feat(P5-4): seed 帖 9 张 gemini-3.1-flash image gen — Codex ship`(若一遍过)/`feat(P5-4): seed 帖 9 张 image gen — N 张需重生`(若有失败)

---

## 8. PM 写回 founder

Codex ship 后 PM chat 给 founder:

> P5-4 done,9 张图在 `docs/nexus/founder_log/xhs_post_2026-05-23_images/`:
> - `cover.png` — 直接用作封面
> - `img_2.png` ~ `img_9.png` — 正文图按序
>
> 直接复制本地 9 张 PNG 到小红书 app 上传 → 套美图秀秀"萌系手账风"模板加大字标题 `招募 10 位宝妈 6 周 1v1 免费陪跑` → 复制 `xhs_post_2026-05-23.md` §"帖子文案" 3 段(标题 / 正文 / tag)→ 发布。
>
> 总成本 ¥<X>,gen 日志 `_gen_log.md`。
