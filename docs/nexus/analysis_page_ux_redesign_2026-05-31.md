# 分析结果页 交互 + 动效重设计 SPEC

**日期**: 2026-05-31 · **作者**: UX Architect (agent) → 编排实现
**范围**: `CardStack.tsx` + `ViralAnalysisCard.tsx` + `SceneAnalysisCard.tsx`，新增「原视频脚本」抽屉 + 逐幕 clip 播放器
**痛点 (founder)**: 页面静、平、扁,第一眼看不出「什么最重要 / 该看哪」。要「活感」+ 重点内容动起来 + 一看就 GET 为什么火。

> 本文是设计 SPEC。落地状态见末尾「实现记录」。

---

## 0. 关键决策

1. **动效 = 扩展现有 CSS-keyframe 层,不引 framer-motion。** `src/index.css` 已有完整 `@keyframes` + `.anim-*` utility + 统一的 `prefers-reduced-motion` 收口(411–422 行)+ inline `animationDelay` stagger 范式。新需求(入场揭示/滚动强调/抽屉/clip)用 CSS + 一个 ~30 行 `useInView` IntersectionObserver hook 覆盖,零依赖、移动端更稳。framer-motion(+~40KB)会和现有 reduced-motion 收口割裂。
2. **爆点卡三级层级**:英雄四维 `钩子 / 痛点需求 / 情绪触发 / 目标人群`(大字+accent 左条+绘入)→ 次级 `素材利益点 / 主要视频元素 / 微创新方向` → 辅助 `BGM 风格`(弱化,最末)。打破「8 维全等权」的扁平。
3. **原视频脚本入口** = 爆点卡右上角 pill → 右侧抽屉(桌面)/ 底部 sheet(手机),两 tab(`分镜脚本` 从 `scenes[]` 组装 / `逐字稿` 从 `full_transcript`)+ sticky 复制。复用 MessagesOverlay 的 Esc/backdrop 约定。
4. **逐幕 clip 播放器** = 原生 `<video preload="none">`,状态机 POSTER / LOADING / PLAYING / POSTER_ONLY / null。点按 inline 播放(`playsInline`),桌面 hover 静音预览,`clip_url` 为空降级到海报或不渲染。
5. **全程尊重 `prefers-reduced-motion`**:所有新 `.anim-*` 追加进 index.css reduced-motion 名单。

---

## 1. 现状诊断(基于实际代码)

- `CardStack`:`space-y-4` 静态堆叠,无入场/滚动动效;逐幕区是等权 `scenes.map()`,N 张同构卡不知从哪看起。
- `ViralAnalysisCard`(**重点问题区**):8 维网格每维视觉完全相同(`border-l-2 border-stone-200`)。钩子(命脉)和 BGM(边角料)权重一致 → founder「看不出什么重要」根因。右上角空着(正好放脚本入口)。
- `SceneAnalysisCard`:视觉/听觉双栏是全卡最好的层级(暖色/emerald 区分);`first_frame_url` 在 type 里有但没用 → clip 的天然落点。
- 资产:`src/index.css` 动效层 + reduced-motion 收口齐全;MessagesOverlay overlay 约定;`lucide-react` 已装;framer-motion 未装。`full_transcript` 已有;`clip_url` 需新增。

---

## 2. 布局 & 层级

```
英雄区   钩子 · 痛点需求 · 情绪触发 · 目标人群   ← 大字、accent 左条加粗、入场逐个亮、滚入绘入
次级     素材利益点 · 主要视频元素 · 微创新方向   ← 常规网格、stone 细描边
辅助     BGM 风格                              ← 单行、最弱、末尾
顶部锚   主题 + 总结 + 右上「原视频脚本」pill
```

手机单列;桌面爆点 2 列、抽屉从右滑入 `max-w-[420px]`。逐幕卡:顶部 clip 槽 → 头部(时间+主题+情感)→ 段描述/口播 → 视觉/听觉双栏 → 拍摄/美术网格。

---

## 3. 逐元素 交互 + 动效表

> 默认缓动 `cubic-bezier(0.16,1,0.3,1)`。滚入视口用共享 `useInView`(threshold 0.2, rootMargin `0 0 -10% 0`, once)。reduced-motion fallback 统一:无动画、终态可见。

| 元素 | 触发 | 动画 | reduced fallback |
|---|---|---|---|
| 爆点卡整卡 | 挂载 | `fadeUp` 600ms | 直接显示 |
| 英雄四维逐个 | 挂载 stagger | `fadeUp` + delay 120/200/280/360ms | 全显 |
| 英雄 accent 左条 | 挂载 stagger | `drawLineY`(scaleY 0→1) delay 260+i·80ms | 满格 |
| 英雄块 hover | hover | `-translate-y-0.5` + `shadow-soft-lg` 180ms | 仅颜色 |
| 次级 + BGM 块 | 挂载延 460ms | `fadeIn` | 直接显示 |
| 脚本入口 pill | hover | 图标 `anim-icon-breathe` | 静态 |
| 视频分析 h2 | 滚入视口 | `fadeUp` | 直接显示 |
| 逐幕卡顺序揭示 | 每卡滚入视口 | `fadeUp`(IO 按需,非全量 delay) | 直接显示 |
| 逐幕卡 hover | hover | `shadow-soft-lg` | 无 |
| clip ▶ 按钮 | hover | 圈 `anim-pulse-ring` + scale | 静态实心 |
| clip 点按 | tap | 海报切到 `<video>` | 直接切 |
| clip 桌面 hover 预览 | hover ≥150ms | 静音 loop 预览 | 不预览 |
| clip 缓冲 | waiting | `anim-spin-slow` spinner | 静态 |
| 脚本抽屉开 | pill click | 桌面 `slideInRight` / 手机 `slideInUp` + backdrop `fadeIn` 320ms | 直接出现 |
| tab 切换 | tab click | 内容 `fadeIn` + 选中下划线 `drawLine` | 直接换 |
| 复制 | click | 文案「复制脚本→已复制 ✓」+ `active:scale` | 文案切换 |

---

## 4. 原视频脚本抽屉

- **入口**:爆点卡标题行右侧低调 pill(`ScrollText` 图标 + 文案),`aria-haspopup="dialog"` / `aria-expanded`。
- **容器**:桌面右侧抽屉(`md:` 右贴边 full-height max-w-420);手机底部 sheet(`max-h-[85vh] rounded-t-2xl` + grabber 横条)。Esc / ✕ / backdrop `onMouseDown` 关。`role="dialog" aria-modal`,打开聚焦面板。
- **分镜脚本 tab**(照着拍):每幕 `序号 时间 + 主题`,下列 `景别/运镜`(cinematography+camera_position)、`画面`(segment_description→visual_content)、`台词`(dialogue_and_narration)、`道具/服装`(props_list+costume);缺失行省略;块间 `divide-y`。
- **逐字稿 tab**:`full_transcript`,`whitespace-pre-wrap`;空显占位。
- **复制**:sticky 底部;分镜 tab → 结构化多行文本;逐字 tab → 原文;`navigator.clipboard` + `aria-live`。
- 所有文本过 `scrubUiForbidden`(品牌护栏)。

---

## 5. 逐幕 clip 播放器(状态机)

```
挂载 ─ clip_url? ─是→ POSTER(海报+▶) ─点按→ LOADING(海报+⟳) ─canplay→ PLAYING(原生 inline)
              └否→ first_frame? ─是→ POSTER_ONLY(纯海报+「仅首帧」,不可点)
                              └否→ 不渲染媒体槽(return null)
```
- 海报 `object-cover`(干净缩略),播放 `object-contain`(全帧可见);槽 `h-56 rounded-xl bg-stone-950`。
- `preload="none"`(省流量)、海报 `loading="lazy"`、`playsInline`(不全屏劫持)。
- 桌面 hover 预览:`(hover:hover) and (pointer:fine)` 且非 reduced-motion 才启用,150ms 防抖,静音 loop。
- poster = `clip_poster_url ?? first_frame_url` → MediaKit 快照路径(无 clip)也能显 POSTER_ONLY。

---

## 6. 落地清单

1. `types/cascade.ts` Scene `clip_url?` / `clip_poster_url?`(+ 后端契约 + bump revision)。
2. `index.css`:`drawLineY/slideInRight/slideInUp` keyframes + `.anim-*` + 追加进 reduced-motion 名单。
3. `hooks/useInView.ts`。
4. `cards/SceneClip.tsx`(状态机)。
5. `cards/ScriptDrawer.tsx`(抽屉 + 两 tab + 复制)。
6. `ViralAnalysisCard.tsx`:脚本 pill + 抽屉 state + dims 拆 hero/次级/bgm。
7. `SceneAnalysisCard.tsx`:顶部 `<SceneClip>` + 根 `useInView` 入场。
8. `CardStack.tsx`:h2 `useInView`。
9. `cardCopy.ts`:script_* / clip_* 文案(过 FORBIDDEN_TERMS)。
10. 测试:clip 四态 + 降级、抽屉 tab/Esc、reduced-motion。

---

## 实现记录(2026-05-31)

全部落地。后端 clip 走 doubao_direct 流水线 best-effort 抽取(ffmpeg `-c copy`,失败跳过该幕,绝不阻断分析);`/media/<analysis_id>/scene_<i>.mp4|.jpg` 由 nginx serve(前端容器挂 `./data/media` 只读卷)。`ANALYSIS_PIPELINE_REVISION` 2→3(旧缓存重生成带 clip)。前端按本 SPEC 实现;动效全部进 reduced-motion 收口。测试:backend 542、frontend 203 绿。
