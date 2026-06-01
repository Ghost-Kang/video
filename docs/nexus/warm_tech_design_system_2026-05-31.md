# 暖色科技 设计语言 / 视觉风格规范(2026-05-31)

**状态**: 权威视觉规范(Source of Truth)+ Phase 1 视觉固化基线 —— 所有前端实现以此 + 代码为准
**代码侧 SoT**: `frontend/src/index.css`(Tailwind v4 `@theme` 令牌 + ~40 个 `@keyframes` + `@layer components` utilities)
**关联**: [phase1_retro_handoff_2026-05-31.md](phase1_retro_handoff_2026-05-31.md) · [analysis_page_ux_redesign_2026-05-31.md](analysis_page_ux_redesign_2026-05-31.md)

founder 定向:整体年轻化 + 科技感,多交互动画,**重点内容用动画突出引人注意**,尤其爆款分析结果页。选定方向 = **暖色科技**(保留品牌暖橙 `#7c2d12`/`#ea580c`,叠加科技质感)+ **高级克制**动效。不引 framer-motion,继续扩展 `index.css` keyframe 层 + `useInView`/`useCountUp` hook;所有动效进 `prefers-reduced-motion` 收口。

---

## 0. 视觉铁律(改 UI 前先读)

1. **优先复用** `index.css` 既有 token / utility,不为一次性场景新造。
2. **暖橙做品牌主调,暖不冷** —— 不引冷色霓虹;品牌渐变 = 陶土 `#7c2d12` → 落日橘 `#ea580c` → 金 `#f59e0b`。
3. **高级克制** —— 动效只服务「引导注意 / 数据感」,不晃眼;只在关键维度 / 关键数字处强调。
4. **任何新 `.anim-*` 必须追加进 `prefers-reduced-motion` 名单**(`index.css` ~571 行;fallback 统一 `animation:none; opacity:1; transform:none`)。
5. **玻璃 / blur 节制**:只用在少量重点卡;长列表(逐幕可能 12 张)用实色卡,避免 backdrop-blur 性能开销。
6. **改 UI 必跑** `npm run lint`(rules-of-hooks 0 违规)+ Playwright 真浏览器旅程(jsdom 测不到「hook 在 early-return 之后」,prod 会被错误边界吞成空白页 React #310)。

---

## 1. 基础令牌(`@theme`,Tailwind v4)

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--color-paper` | `#faf8f3` | 暖纸基底(light-first 主背景) |
| `--color-paper-deeper` | `#f5f1e8` | 次级背景 / 分区 |
| `--color-ink` | `#1c1917` | 主文字 |
| `--color-ink-soft` | `#44403c` | 次要文字 |
| `--color-clay` | `#7c2d12` | 品牌主色(陶土暖橙) |
| `--color-clay-soft` | `#c2410c` | 品牌亮色 |
| `--color-cream` | `#fef9e7` | 暖白点缀 |

**深色模式**:`@custom-variant dark (&:where(.dark, .dark *))`;`html.dark` → 背景 `#0c0a09`、文字 `#f5f1e8`;`.glass`/`.tech-grid`/`.anim-sheen` 均有 dark 变体。

**字体**:系统字体栈(PingFang SC / HarmonyOS Sans SC 等)+ `font-feature-settings: "ss01","ss02","cv11"` + `letter-spacing: -0.005em`;数据字用 `.num-tech`(tabular-nums);标题可选 `.font-serif-cn`(思源宋体)。

---

## 2. 可复用 token(`src/index.css`)

**暖色科技核心**:
- `.glass` — 玻璃拟态卡面(backdrop-blur(14px) + 半透 + 细边);`html.dark` 有对应变体。
- `.glow-warm` / `.hover-glow` — 暖色光晕 + 悬浮加强。
- `.tech-topline` — 顶部流光渐变描边条(陶土→橙→金,`hueFlow` 持续微流动)。
- `.tech-grid` — 暖色细科技网格背景(dark 变体更亮)。
- `.num-tech` — 等宽数据字(`tabular-nums` + `tnum`),给数字「数据感」。
- `.text-shimmer-clay` — 陶土→落日橘 流光渐变文字。

**入场 / 强调**:
- `.anim-tech-in` — 科技揭示(下移 + 轻放大 + 去模糊),重点卡入场用它替代 plain fadeUp。
- `.anim-sheen` — 卡片入场一束斜向光扫过(父需 `relative` + `overflow-hidden`)。
- `.anim-glow-pulse` — 重点内容入场一次性发光脉冲(吸睛)。
- `.anim-draw-line-y` — 纵向左条绘入(爆点英雄维度)。
- stagger 范式 = inline `style={{ animationDelay }}`。

**通用动效族**(均已在 reduced-motion 名单内):`.anim-fade-up`/`.anim-fade-in`、`.anim-draw-line`、`.anim-slide-in-right`/`.anim-slide-in-up`(抽屉)、`.anim-icon-breathe`、`.anim-pulse-ring`、`.anim-spin-slow`、`.anim-aurora-1/2`、`.anim-marquee`(轮播)、`.ripple-dot`(点击扩散)、`.anim-page-out`(页面退出)。
**入口专用**:`.anim-cta-breathe`/`.anim-cta-glow`(CTA 呼吸/光晕)、`.anim-arrow-nudge`、`.anim-input-glow`、`.anim-sweet-band`/`.anim-sweet-ripple`/`.anim-bob`/`.anim-meter-flow`(时长甜蜜点)。
**装饰**:`.anim-float-a/b/c`、`.anim-steam`/`.anim-flame`/`.anim-heart-beat`/`.anim-wobble`/`.anim-blink`/`.anim-sparkle-twinkle`。

**阴影 / 其它**:`.shadow-soft` / `.shadow-soft-lg`(暖墨柔影);`.paper-grid` / `.paper-noise`(纸感肌理);`.scrollbar-hidden`。

**辅助资产**:`cardStyles.ts` → `CARD_GLASS`(玻璃卡);`hooks/useCountUp.ts`(数字滚动,reduced / 无 IntersectionObserver 时直接终值,保证测试 & 可访问性);`hooks/useInView.ts`(滚入视口触发,once)。

---

## 3. 结果页落地(`CardStack` + cards)

- `CardStack`:暖色科技背景层(`.tech-grid` + 顶部径向柔光);区块滚入用 `useInView`。
- `AnalysisStatStrip`:镜头 / 时长 / 把握 三个关键数字玻璃卡 + 滚动计数。
- `ViralAnalysisCard`(爆点卡,**三级视觉层级**):`CARD_GLASS` + `.tech-topline` + 入场 `.anim-tech-in .anim-sheen`;主题 `.text-shimmer-clay`;
  - **英雄四维**(钩子 / 痛点需求 / 情绪触发 / 目标人群)= 大字 + 暖橙描边 + `.anim-glow-pulse` 入场吸睛 + `.hover-glow` + `.anim-draw-line-y` accent 绘入 + stagger;
  - **次级**(素材利益点 / 主要视频元素 / 微创新方向)= 常规网格、细描边;
  - **辅助**(BGM 风格)= 单行、最弱、末尾。
  - 右上「原视频脚本」pill → `ScriptDrawer`。
- `SceneAnalysisCard`(逐幕卡):`.hover-glow` + `.anim-tech-in` 入场;时间码做成 `.num-tech` 数据徽标;视觉/听觉双栏;顶部 `SceneClip` 播放器。**逐幕卡可能 12 张,用实色卡(非玻璃)避免 backdrop-blur 开销。**
- `ScriptDrawer`:桌面右抽屉(`anim-slide-in-right`)/ 手机底 sheet(`anim-slide-in-up`),两 tab(分镜脚本 / 逐字稿)+ sticky 复制。
- `SceneClip`:原生 `<video preload="none">` 状态机(POSTER / LOADING / PLAYING / POSTER_ONLY / null),桌面 hover 静音预览,`clip_url` 空则降级海报或不渲染。

> 结果页交互/动效完整 SPEC + 状态机见 `analysis_page_ux_redesign_2026-05-31.md`。

---

## 4. 原则

- **高级克制**:动效服务「引导注意 / 数据感」,不晃眼;关键处(重点维度、关键数字)才强调。
- **暖不冷**:保留品牌暖橙做主调。
- **全程尊重 reduced-motion**;玻璃 / blur 只用在少量重点卡,长列表用实色卡。
- **一致性**:扩到落地页 / 其它页时复用以上 token,保持一致(入口落地页已铺,见 commit `b938bed`)。

> ⚠️ 旧版本曾写「暖橙贴合宝妈 / 育儿暖生活内容与受众」——**该 niche 已于 commit `929cb21` 清理,产品定位收窄为「任意短视频 / 抖音」**。暖橙保留为品牌色,但「暖 = 贴合宝妈」的理由已过时;Phase 2 不要据此做 niche 假设。

---

## 5. Phase 2 继承

- 本规范是 Phase 1 视觉固化基线,Phase 2 在其上**增量,不推翻**。
- 改写解封后的「你的版本 / 拿去发」UI:呈现走暖色科技 + 当前卡结构(玻璃卡 + tech-topline + 三级层级范式),复用上述 token。
- 任何新页面 / 新组件:先查本规范 token 是否可复用;新动效先看现有 keyframe,再考虑新增,且**必须进 reduced-motion 名单**。
