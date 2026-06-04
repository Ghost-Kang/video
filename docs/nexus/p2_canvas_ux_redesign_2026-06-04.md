# P2 画布 UX 重设计规范 — 2026-06-04

**触发**: 创始人实测 ?view=pro 画布:① 中间空节点黑/白块卡住挡操作 ② 右侧 NodeDetail 太窄读不了 ③ 整体 vanilla React Flow、不高级、步骤不清。要求「让用户很容易明白每一步干啥 + 兼顾 P1 暖色科技风」。
**产出**: 5-agent UX workflow(UX Architect / UX Researcher / Brand Guardian / UI Designer 四维诊断 → UX Architect 合成)。均读真实组件 + 对齐 P1 SoT(`warm_tech_design_system` / `frontend/src/index.css`)。

## 核心思路
把 `?view=pro` 画布收口成**和 CardStack 同源的暖色科技级联流水线**。三主线:① 灭硬故障 ② 套 P1 皮 ③ 引导可视化。新动效复用 index.css keyframe + 进 reduced-motion(铁律⑧),不引 framer-motion。

## 根因诊断(截图问题)
- **黑块 #1**:`StoryboardNode` 组件存在,但 `Canvas.tsx` nodeTypes(L25-31)**没注册 storyboard**(只 script/image/video/composite/group)→ RF 回退到内置 `default` 节点(深描边/无背景)= 黑框。NodeType union(types/canvas.ts)也只 4 种,storyboard 是孤儿。
- **黑块 #2**:空占位硬编码 `#fff` 无暗色分支(ImageNode L51 / VideoNode L44),暗色画布下白卡突兀 + RF 默认 `<Background/>` 点阵在暗色偏黑 → 「白区+黑块」观感。整套节点无 P1 token。
- **卡住**:`ChapterGroupNode` 半透明覆盖层吃 pan 手势;parentId 子节点每帧同步丢拖动坐标(Canvas L211-212)→ 弹回。
- **窄面板**:NodeDetail 宽度写死 320(S.panel L368);版本对比 `1fr 1fr`(L177)每列 ~136px 读不了。

## 落地顺序(build order)

### P0 — 灭硬故障(截图痛点)
1. **灭黑块**:Canvas 注册 storyboard + 新增 `nodes/FallbackNode.tsx`(未注册 type 渲染暖纸占位卡,非 RF 黑 default)。
2. **灭卡住**:`ChapterGroupNode` S.group 加 `pointerEvents:none`(标题条 `pointerEvents:auto` 仍可点)+ group 声明 `draggable:false`。
3. **灭弹回**:Canvas L211-212 对 parentId 子节点用 prevMap 合并保留 `existing.position`(只 group 自身套新布局)。
4. **灭窄面板**:NodeDetail width `320 → clamp(360px,30vw,560px)` + 左缘 4px resize handle(nodrag/nopan,clamp 320–720,localStorage 记忆)+ Canvas 外层补 `minWidth:0`;窄屏 <900px 覆盖式 + 遮罩。
5. **灭对比挤**:NodeVersionHistory S.compare `1fr 1fr → repeat(auto-fit,minmax(200px,1fr))`(宽并排/窄堆叠)+ 剧本 maxHeight 折叠可展开。

### P1 — 套 P1 暖色科技皮
1. **画布底**:`proOptions hideAttribution:true`(去 "React Flow" 水印)+ Background 换 Dots(gap 22,color `rgba(124,45,18,.10)` / 暗 `rgba(234,88,12,.12)`)或挂 `tech-grid`+`paper-noise`;外层叠极淡 `anim-aurora-1/2`(opacity .04–.06,pointer-events-none)。
2. **节点皮**:index.css 新增 `.canvas-node`(半透明白 blur(10px)、border `rgba(124,45,18,.14)`、圆角 16、shadow-soft、暗色分支)+ `.canvas-node--selected`(套 glow-warm);类型靠左 4px borderLeft(script #7c2d12 / image #ea580c / video #f59e0b / composite·storyboard #d4a574);title 加 font-serif-cn;hover 复用 hover-glow。收敛内联异色边(#18181b/#d4d4d8/#eab308/#faad14)。
3. **生成态**:新增 `nodes/MediaNodeShell.tsx` 收口 Image/Video/Composite 占位(aspectRatio 16:9 消抖、空态陶土降权、loading 用 `anim-shimmer`+`anim-glow-pulse`)+ img/video `onError`(根治坏 url 黑块);**删内联蓝 spinner #1890ff(违反铁律⑧)**,badge 用 `anim-pulse-ring`。
4. 新增 keyframe 全部登记 reduced-motion(index.css L571-587)。

### P2 — 引导可视化 + 交互质感
1. **向导条 StageRail**:TodoProgress 重构成**常驻顶部六步真相源**(策划书→角色→场景→分镜宫格→逐镜视频→合成),不再 todos 空就 `return null`;双源(有 write_todos 用 todos,否则按 nodes 的 type+subtype+node_status 反推);三态(completed 陶土勾 / in_progress 暗橙+`anim-cta-breathe` / pending 暖灰);glass。
2. **状态语义 StatusChip**:把 node_status × asset_status × needs_regen 折叠成**一枚中文芯片**:待你确认(琥珀 #f59e0b)/ 可生成(陶土 #7c2d12)/ 生成中(+anim-pulse-ring)/ 已生成(绿 #16a34a)/ 失败重试(红)/ 需重生·上游已改(琥珀)。替掉并排三枚英文枚举。
3. **空态 + 导航**:`CanvasEmptyState`(nodes 空时画布中央玻璃卡 + 衬线标题 + 三步图示 + 主 CTA「让导演开始」向 dock 发 prompt);`ActiveNodeRing`(reviewing/generating 节点陶土橙光环 anim-pulse-ring);右下角「下一步」按钮 fitView+selectNode 到第一个 reviewing 节点;`StageBadge`(节点卡面阶段编号,解决三张 image 长一样)。
4. **连线 + 控件**:edge stroke `rgba(124,45,18,.45)`+smoothstep+ArrowClosed `#c2410c` 有向+hover #7c2d12+仅 generating 端 animated;MiniMap glass+nodeColor 强调色族;Controls 玻璃底陶土;layoutBtn 换 glass;NodeDetail 内 zinc 换 P1 token(确认 badge/generateBtn 用 #7c2d12、标题 font-serif-cn)。
5. **验证**:npm run lint(rules-of-hooks 0)+ tsc + build + Playwright 真旅程(暗色 + reduced-motion)。

> 全文 workflow 输出存 task wvmnsfut4。本规范是工程落地的单一参照。
