# 暖色科技 设计语言(2026-05-31)

founder 定向:整体年轻化 + 科技感,多交互动画,**重点内容用动画突出引人注意**,
尤其爆款分析结果页。选定方向 = **暖色科技**(保留品牌暖橙 #7c2d12/#ea580c,叠加
科技质感)+ **高级克制**动效。不引 framer-motion,继续扩展 `index.css` keyframe 层
+ `useInView`/`useCountUp` hook;所有动效进 `prefers-reduced-motion` 收口。

## 可复用 token(`src/index.css`)
- `.glass` — 玻璃拟态卡面(backdrop-blur + 半透 + 细边);暗色有对应变体。
- `.glow-warm` / `.hover-glow` — 暖色光晕 + 悬浮加强。
- `.tech-topline` — 顶部流光渐变描边条(暖橙→橙→金 持续微流动,`hueFlow`)。
- `.tech-grid` — 细科技网格背景。
- `.num-tech` — 等宽数据字(tabular-nums + tnum),给数字「数据感」。
- `.anim-tech-in` — 入场科技揭示(下移 + 轻放大 + 去模糊)。
- `.anim-sheen` — 卡片入场一束斜向光扫过(父需 relative + overflow-hidden)。
- `.anim-glow-pulse` — 重点内容入场一次性发光脉冲(吸睛)。
- 既有复用:`.text-shimmer-clay`(流光渐变文字)、`.anim-draw-line-y`(描边绘入)、
  `.anim-fade-up`/`.anim-fade-in`、`.anim-icon-breathe`、`.anim-pulse-ring`。
- `cardStyles.ts`:`CARD_GLASS`(玻璃卡)。`hooks/useCountUp.ts`(数字滚动,reduced /
  无 IntersectionObserver 时直接终值,保证测试/可访问性)。

## 结果页落地(`CardStack` + cards)
- `CardStack`:暖色科技背景层(`.tech-grid` + 顶部径向柔光)。
- `AnalysisStatStrip`(新):镜头 / 时长 / 把握 三个关键数字玻璃卡 + 滚动计数。
- `ViralAnalysisCard`:`CARD_GLASS` + `.tech-topline` + 入场 `.anim-tech-in .anim-sheen`;
  主题 `.text-shimmer-clay`;英雄四维(钩子/痛点/情绪/人群)= 暖色描边 + `.anim-glow-pulse`
  入场吸睛 + `.hover-glow` + `.anim-draw-line-y` accent 绘入 + stagger。
- `SceneAnalysisCard`:`.hover-glow` + `.anim-tech-in` 入场;时间码做成 `.num-tech` 数据徽标。
  注:逐幕卡可能 12 张,用实色卡(非玻璃)避免 backdrop-blur 性能开销。

## 原则
- 高级克制:动效服务「引导注意 / 数据感」,不晃眼;关键处(重点维度、关键数字)才强调。
- 暖不冷:保留品牌暖橙做主调,贴合宝妈/育儿暖生活内容与受众。
- 全程尊重 reduced-motion;玻璃/blur 只用在少量重点卡,长列表用实色卡。
- 后续扩到落地页/其它页时复用以上 token,保持一致。前序结果页 UX 见
  `analysis_page_ux_redesign_2026-05-31.md`。
