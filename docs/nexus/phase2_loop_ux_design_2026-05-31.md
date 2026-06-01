# Phase 2 闭环 UX 设计：分析 → 改写 → 生成 → 发布

**状态**: 设计稿（待 founder 评审 + 架构对齐）
**作者**: PM/UX（Alex，Opus 4.8）
**创建**: 2026-05-31
**视觉基线**: [warm_tech_design_system_2026-05-31.md](warm_tech_design_system_2026-05-31.md)（代码侧 SoT = `frontend/src/index.css`）
**架构契约**: [architecture_phase1_phase2_design_2026-05-31.md](architecture_phase1_phase2_design_2026-05-31.md)（CreationRun 聚合根 + C1–C4 handoff + JobProgress + 失败矩阵 M0–M5）
**阶段计划**: [../PHASED_PLAN.md](../PHASED_PLAN.md) · **复盘交接**: [phase1_retro_handoff_2026-05-31.md](phase1_retro_handoff_2026-05-31.md)

> 本文是「分析→改写→生成→发布」端到端**产品与交互**设计。所有现状断言已用 Read/Grep 对真实代码核验，关键行号附在引用处。设计承接当前结果页真实形态（toprador 维度 + 三级层级 + 脚本抽屉），**不是**被覆盖的 W4「抓/留/带」三幕提案。

---

## 0. 一页纸（给 Founder）

**用户走完闭环的一句话故事**：粘一条抖音链接 → 一眼看懂「为什么火」（已上线）→ 一键得到「我自己的版本」脚本（改写解封）→ 给关键镜头出 3–5 张草稿图（生成）→ 标题/标签/脚本/镜头图打成一包，复制去抖音发（发布）。

**当前断点**（代码核验）：
- 闭环只跑到第 1 幕「为什么火」。`App.tsx:157 REWRITE_ENABLED=false` 关掉自动改写；`CardStack.tsx:18-21` 注释明确「改写本轮暂挂，不渲染 CTA/改写脚本/发布包」。
- 生成（草稿图）代码存在（`onGenerateFirstFrame` → `[generate_first_frame: shot_index=N]` → `shot_first_frame_returned` 帧），但分析页**没有任何按钮触达它**——它是为旧 ShotCard 设计的，当前 `SceneAnalysisCard` 不渲染生成入口。
- 发布包 `PublishPackCard`/`buildPublishPack` 代码齐全、测试绿，但**不被任何页面渲染**，且镜头图恒空、niche 硬编码已被 `929cb21` 砍掉的辅食/育儿/厨房。

**本设计的四个交付**：
1. **改写如何重回结果页** —「你的版本」卡的位置、自动 vs 手动触发、在途态（复用 `rewriteShots` 为空判定 + `loading`）、把握度呈现。
2. **生成如何呈现** — Phase1 范围只做 3–5 张关键镜头草稿图（image-grounded）；慢任务的进度/部分完成/失败降级 UI（对齐架构 JobProgress + 失败矩阵）；视频（P2-1）留扩展位。
3. **发布如何收尾** — 发布包（标题/标签/脚本/镜头图）一键复制 + 分字段复制 → 去抖音；复用 `buildPublishPack`，堵住源片标签/hook-code 泄漏。
4. **全程暖色科技 token 复用**，新动效进 reduced-motion；改 UI 守铁律②。

**两个必须 founder 拍板的前置**（详见 §9）：① 生成图 provider 合规（默认 Gemini 跨境 vs 境内 Apimart）；② 改写解封是先灰度还是达标全量。

---

## 1. 闭环全景（结果页四幕信息架构）

闭环不是四个页面，是**同一个结果页向下滚动的四幕**——这是 Phase1 沉淀的「单页渐进」范式（`CardStack` 顺序渲染），Phase2 在其下游**追加**两幕，不动已上线的前两幕。

```
┌─────────────────────────── 结果页（CardStack，手机优先单列 max-w-[680px]）────────────────────────────┐
│                                                                                                        │
│  ① 为什么火（已上线，不动）                                                                            │
│     ConfidenceBanner → AnalysisStatStrip(镜头/时长/把握) → ViralAnalysisCard(英雄四维三级层级)        │
│        └ 右上 pill →「原视频脚本」ScriptDrawer(分镜/逐字稿双 tab)                                      │
│     "视频分析" header → SceneAnalysisCard × N(逐幕 14 维 + 视觉/听觉双栏 + 顶部 SceneClip)             │
│                                                                                                        │
│  ── 闭环推进器（新）：分析回来后,在 ViralAnalysisCard 与逐幕之间插一条「下一步」引导带 ──             │
│                                                                                                        │
│  ② 你的版本（改写解封）           RewriteCard                                                          │
│        在途: RewritePendingCard(在 ②位置原地占位,~30-60s)                                             │
│        产物: 逐幕「你的台词 / 你的画面」+ 把握度 chip + 「重写」「微调方向」                             │
│                                                                                                        │
│  ③ 关键镜头草稿图（生成,Phase1=3-5 张 image-grounded）  StoryboardCard                                 │
│        每镜: 草稿图缩略(pending/polling/done/failed 四态) + 「重出这张」                               │
│        慢任务: 卡级进度(对齐 JobProgress) + 部分完成可继续 + 失败降级到纯文字镜头                       │
│        [视频生成 P2-1 留扩展位:同一卡下方「合成短片」按钮,灰置 + "即将开放"]                          │
│                                                                                                        │
│  ④ 拿去发（发布）                 PublishPackCard                                                      │
│        标题候选 / 标签 / 完整脚本 / 镜头图 → 「一键复制,去抖音」+ 分字段复制                            │
│                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**渐进披露原则**（防止重蹈「20+ 卡 dump」覆辙，retro §2.2）：
- 第 ① 幕永远完整显示（分析是地基价值）。
- 第 ②③④ 幕**逐步解锁、按需展开**：每幕完成才把下一幕的「推进器」点亮，未触达的幕折叠成一行 CTA 而非铺开空壳。
- 任何一幕失败或降级，闭环**不阻断**——用户始终能停在「已拿到的价值」（参照 clip best-effort 范式，架构失败矩阵）。

---

## 2. 闭环推进器（连接四幕的引导带）

四幕之间需要一条明确的「下一步」线索，否则用户看完分析就走了（Phase1 Gate「热点→创作转化≥15%」靠它）。

**形态**：一条贴在 `ViralAnalysisCard` 之后的 `LoopProgressBar`（暖色科技 stepper，非导航 tab）。

```
 ①看懂 ──●──── ②你的版本 ──○──── ③镜头图 ──○──── ④拿去发
   已完成        当前可做        待解锁        待解锁
```

- 已完成步：实心暖橙圆点 + `.num-tech` 勾。
- 当前可做步：`.anim-glow-pulse` 一次性脉冲吸睛（reduced-motion 下静态高亮）。
- 待解锁步：空心灰点，点击平滑滚动到对应幕但显示「先完成上一步」微提示。
- 复用 token：圆点连线用 `.anim-draw-line`（绘入）；高亮用 `glow-warm`。
- 移动端：横向单行可滚，sticky 在视口顶（滚动时跟随），高度 ≤44px。

> 这条 bar 是埋点漏斗的可视锚：每步点亮 = 一个转化节点（P2-10：`rewrite_started` / `generation_enqueued` / `publish_pack_copied`）。

---

## 3. 第 ② 幕：改写「你的版本」重回结果页

### 3.1 解封需要联动的三个开关（设计稿必须钉死，漏一处 = 假通）

| # | 开关 | 现状（核验） | 解封动作 |
|---|------|-------------|---------|
| 1 | 前端 `App.tsx:157 REWRITE_ENABLED` | `false`，自动改写 effect 第一行短路（`:159`） | 改 `true` **并重新构建部署**（源码硬常量，非运行时 flag）|
| 2 | 后端 `CASCADE_REWRITE_UPSTREAM` | 默认 `fixture`，部署文件全没设 | `.env`/compose 显式设 `=llm` + 真 URL doubao 实跑验收 |
| 3 | **改写缓存版本守卫** | **无**——`rewrites_repo` 只按 24h 窗口查，不带版本号 | 架构 M1 新增 `REWRITE_PIPELINE_REVISION`；否则切 llm 后 24h 内返回旧 fixture 套娃（founder 会看到「还是老样子」）|

> **UX 含义**：解封首日，若守卫未上，第一批用户点改写会拿到旧 fixture 模板——这是体验 P0。设计前端时**不**假设「点了就是新的」；改写卡顶部带一行极小的来源标识（仅 admin/pro 视图可见，见 §7），便于灰度期人工核对是否真过模型。

### 3.2 触发方式：自动为主，手动兜底

Phase1 已埋好「自动改写」逻辑（`App.tsx:158-169`，三重守卫：`justSubmitted` 防冷 replay / 每 `analysis_id` 只发一次 / 已有 rewrite 或 loading 则跳过）。但它依赖 `niche`，而 niche 已被产品砍掉（运行时恒 null）。

**Phase2 调整**：
- **去 niche 化**。改写不再要求用户先选赛道（`onTriggerRewrite(niche)` 的 niche 参数体系已死）。改写 = 「把这条爆款的套路，用你自己的口吻重写一遍」，**不绑定预设赛道**。
  - 后端 prompt 当前是三个 niche 文件（`rewrite_*_*.md`）。Phase2 改写解封需要一个**通用代笔 prompt**（不预设辅食/育儿/厨房），或让用户**自填一句话主题**（"我想拍的是 ___"）作为改写锚点。这是改写解封的 prompt 工作项，**任何改动必 bump `REWRITE_PIPELINE_REVISION`**（不是 `ANALYSIS_PIPELINE_REVISION`——铁律①只守分析缓存，对 rewrites 表无效）。
- **自动触发**（解封后默认）：分析回来 + 本会话刚提交过链接 → 自动跑改写，「你的版本」卡进入在途态。理由（保留 `App.tsx:151` 原注释精神）：别把唯一的下游价值锁在用户手动点 CTA 后面。
- **手动兜底**：若用户自填主题或想换方向，`ViralAnalysisCard` 下方 / `LoopProgressBar` 第②步提供「改成我的版本」按钮（`.anim-cta-breathe` 呼吸引导）。手动触发消费掉自动信号（沿用 `justSubmittedRef.current=false` 范式）。

### 3.3 在途态：`RewritePendingCard`（~30–60s）

改写是 LLM 单发，doubao 真输出可能 30–60s。在途态必须占位且有进度感，否则用户以为卡死。

- **位置**：第 ② 幕原地（`ViralAnalysisCard` 之后），不弹窗、不跳页。
- **判定**：复用现有状态——`rewriteShots.length === 0 && loading`（`canvasStore` 已有 `rewriteShots`）+ 改写专属的 in-flight 标志（建议加 `rewritePending: boolean`，由发出改写命令时置 true、`rewrite_returned`/`analysis_failed` 置 false；当前没有独立标志，靠全局 `loading` 会和分析混淆）。
- **视觉**：`CARD_GLASS` 玻璃卡 + `.tech-topline` + 三行骨架（你的台词 / 你的画面 占位条用 `.anim-sheen` 流光扫过模拟「在写」），顶部一行进度文案「📝 在用你的口吻重写…」（复用 `wsStore` 的 `TOOL_LABELS.rewrite_to_niche` 文案，去 niche 化改为「在写你的版本…」）。
- **进度对齐**：改写没有 `analysis_progress` 那样的分阶段帧（只有结果帧 `rewrite_returned`）。在途用**时间感 ramp**（非真进度，明确不显百分比，避免假 95%——retro 卡 95% 教训），文案随时间推进：0–10s「读懂套路」→ 10–30s「换成你的口吻」→ 30s+「快好了…」。
- **超时**：沿用 `App.tsx:76` 的 300s 客户端安全计时；改写在途超时 → `synthesizeClientTimeout()` → 失败带「重写」按钮（不污染分析卡，分析已在上方完好）。

### 3.4 产物态：`RewriteCard`

- **结构**：逐幕「你的台词 / 你的画面」两栏（复用 `RewriteShot{shot_index, dialogue, visual}`，`cascadeMapper.ts` 已定义）。每幕一行台词（引用式，复用 ScriptDrawer 的 emerald accent 台词框范式）+ 一行画面提示（暖橙 accent 框）。
- **与源片并置**：不覆盖源片逐幕（`canvasStore` 注释明确 `shots` 永远绑 `analysis.scenes`，rewrite 共存）。可提供「对照源片」折叠（默认折叠，避免信息过载）。
- **把握度呈现**：`RewriteResult.confidence`（0–1，后端强校验）。
  - ≥0.7：暖橙「把握度 高」chip（`.num-tech` 显示百分比 + glow-warm）。
  - 0.4–0.7：中性「把握度 中」chip。
  - ≤0.4：灰「把握度 一般 · 建议微调」chip + 不阻断，但弱化。
  - **设计警告**（架构核验）：doubao 真输出若常触发 scrub/超长，`_llm_rewrite` 会把 confidence 压到 ≤0.4（硬约束很严）。解封前需真跑标定阈值；UX 不能让「一般」chip 大面积出现却无解释，否则用户信任崩。建议低把握时给一句「可点重写换个角度」的可操作话术。
- **动作**：「✅ 用这版去出图」（推进到第③幕）/「↻ 重写」/「调整方向」（展开自填主题输入）。
- **禁词安全**（核验）：改写文本进发布包前，前端必须经 `scrubUiForbidden`（当前 `buildPublishPack` 只 `stripHookCode` 不 scrub）。`RewriteCard` 渲染层已可复用 `ViralAnalysisCard` 的 `clean()` = `scrubUiForbidden(stripHookCode(...))` 范式。

### 3.5 改写帧已就绪（核验，无需新建后端帧）

`wsStore.ts:334 rewrite_returned` 已 wired：清 loading/progress + `setScript(script_markdown)` + `setRewriteShots(mapRewriteShotsToScenes(...))`。前端只需把 `rewriteShots` 渲染回 `CardStack`（当前被注释掉），并加 `rewritePending` 标志区分在途。

---

## 4. 第 ③ 幕：关键镜头草稿图（生成）

### 4.1 Phase1 范围：3–5 张 image-grounded 草稿图（不做 60s 合成）

PHASED_PLAN P2-1 明确「先单镜头不做 60s 合成」、P1「3–5 张关键镜头草稿图」。本幕 = 为改写后的关键镜头各出一张草稿图，帮创作者「看见画面」再去拍/二创。

**镜头来源（架构 C3 桥接，P2 必新建）**：
- 主来源 = 改写产物 `rewriteShots[].visual`（创作者目标版本的画面，最贴切）。
- 回退 = 无改写时用 `analysis.scenes[].visual_content`（源片画面，"照着复刻"）。
- **不是全部 N 幕都出图**：选「关键镜头」（建议前 3–5 个高信息镜头，或让用户勾选），控成本（每张真金白银，架构核验生成 leg 零成本护栏是 P2 硬 Gate）。

**触发链路（核验现有 + 需扩展）**：
- 现有：`onGenerateFirstFrame(idx)` → `sendChatMessage([generate_first_frame: shot_index=N])` → Director 调 `cascade_generate_first_frame` → `shot_first_frame_returned` 帧 → `updateShotFirstFrame(scene_index, url)`（`canvasStore:103`）。
- 现状问题：这是**逐镜手动**触发、为旧 ShotCard 设计、当前页面无按钮。Phase2 需要：① 一个「StoryboardCard」批量入口（「给这 4 个关键镜头出草稿图」）；② 每镜独立可重出；③ 把生成的慢任务进度/失败纳入 §4.3 的卡级状态机。

### 4.2 `StoryboardCard` 形态

- **位置**：第 ③ 幕（改写产物之后）。未解锁时折叠成一行 CTA「🎬 给关键镜头出草稿图」。
- **网格**：3–5 个镜头缩略卡（横向可滚 / 移动端 2 列），每卡：镜头号 + 缩略图槽（四态见 §4.3）+ 该镜的一句画面提示（来自 `visual`）。
- **整体动作**：「全部出图」（批量 enqueue）/ 单镜「重出这张」。
- **成本可见**（架构要求纳入 cost_guard）：批量出图前显示「约 N 张 · 预计 ¥X」轻提示（不吓人，但透明）；配额耗尽走 §6 paywall 态。

### 4.3 慢任务卡级状态机（对齐架构 JobProgress + 失败矩阵）

每个镜头缩略图是一个独立的慢任务，四态 + 降级：

```
 IDLE ──点"出图"──▶ PENDING ──worker认领──▶ POLLING ──done──▶ DONE(草稿图)
                      │                        │
                      └────────失败/超时────────┴──▶ FAILED(降级)
```

| 态 | UI | 数据源 |
|----|----|--------|
| IDLE | 灰占位 + 「出图」按钮 | 节点 `generation_status` 未置 |
| PENDING | 缩略框 + 「排队中…」+ `.anim-spin-slow` | enqueue 后 `pending` |
| POLLING | 缩略框 + 「绘制中…」+ 暖橙呼吸边 | `submitted/polling` |
| DONE | 草稿图（`object-cover`）+ hover「重出/下载」 | `shot_first_frame_returned` 的 url |
| FAILED | **降级**：不显破图，回退到纯文字镜头卡（画面提示文字 + 「再试一次」） | `generation_error` |

**关键设计（防「卡 95%」同构，对齐架构 JobProgress 投影）**：
- 生成是**后台慢任务**，用户可能切走/断线再回。进度**不能只靠实时帧**——必须能在 reconnect 时从权威状态（架构新增 JobProgress 投影 / canvas 节点 generation 状态）重建每个缩略图的态。前端在 `session_state` resume / `canvas_updated` 时按 `shot_index` 重映射缩略图态，而非依赖一次性 `shot_first_frame_returned`。
- **部分完成可继续**：4 张里 2 张成功 2 张失败 → 成功的正常显示，失败的单独降级 + 可重试，**不整卡失败**。这是「失败有下一步 100%」Gate 的直接落地。
- **离线完成**：架构指出 worker 完成时若用户离线，`notify_user` skip。UX 对策：用户回到页面时由 `canvas_updated`/`session_state` 拉到已完成的 url，缩略图直接 DONE（无需用户重触发）。

### 4.4 视频生成（P2-1）留扩展位

- `StoryboardCard` 底部预留一个「🎞 合成短片」按钮，Phase1 **灰置 + "即将开放" 角标**（不删、不空跑）。
- 视频是更慢的任务（架构核验：Seedance 轮询上限 900s，Semaphore(2)，无 Kling）。其进度/失败/成本 UX 走与草稿图**同一套**卡级状态机（§4.3），只是时长更长——这是把状态机设计成「任务无关」的原因，避免 P2-1 时再造一套。
- 留位即可，本设计不展开视频交互细节（PHASED_PLAN P2-1 范畴）。

---

## 5. 第 ④ 幕：拿去发（发布）

### 5.1 复用 `buildPublishPack`，但堵三个洞（核验）

发布包纯函数 + `PublishPackCard` 代码齐全、7 个单测含回归（防源片标签/受众泄漏缺陷 E、hook-code 泄漏）。Phase2 复活需修：

| 洞 | 现状（核验） | 修法 |
|----|-------------|------|
| **镜头图恒空** | `buildPublishPack(script, analysis, [], ...)` 永远传空 `shotImages` → 「镜头 1: 待补充」 | 把第③幕生成的草稿图 url（成功的那些）传入；缺图的镜头优雅降级（跳过该行,不塞坏链接/占位）|
| **niche 硬编码已死** | `NICHE_TAGS`/`NICHE_TAGLINE` 仍是辅食/育儿/厨房（`929cb21` 已从产品砍掉），运行时 niche 恒 null → 默认套辅食标签 | **重设标签来源**：从分析 `theme`/改写主题经 scrub 生成，或让用户自填/编辑标签（见 §5.3）|
| **标题硬回退辅食句** | `buildPublishPack.ts:80-81` 写死「宝宝拒食三次…」「这一勺下去我哭了」 | 去 niche 化:无改写时回退源片 hook/climax(已 stripHookCode);删辅食兜底句,改通用空态「补一句你的标题」|

> **铁律对齐**：改 `buildPublishPack` 的标签/标题来源逻辑**不需要** bump `ANALYSIS_PIPELINE_REVISION`（那是后端分析缓存守卫，纯前端字符串拼接不进缓存）。但改写 prompt 若变 → bump `REWRITE_PIPELINE_REVISION`（§3.1）。

### 5.2 发布数据「发什么版本」的语义决策（founder 待定，retro §7.3）

- 当前若不复活改写：发布包只能输出「源片 hook/climax 回退标题 + 源片脚本」——本质是「把别人的爆款原样拿去发」，语义可疑。
- **本设计立场**：发布幕**依赖改写幕**（架构 M4 依赖 M2）。发布包标题/脚本主来源 = `rewriteShots`（创作者口吻的「你的版本」），镜头图 = 第③幕草稿图。**先解封改写，再接发布**——否则发布是空的或抄袭性的。
- 这与 founder「改写-发布闭环」定位一致（= 恢复原 Phase1 完整闭环，retro §6，不是新方向）。

### 5.3 终点 UX：整段复制 + 分字段复制

抖音发布表单是分字段的（标题、正文/话题分开），整段纯文本粘贴体验差。

- **主按钮**：「📋 一键复制，去抖音」（复用现有 `handleCopy` + `navigator.clipboard.writeText(payload)` + toast「复制好了，去抖音粘贴吧」+ `publish_pack_copied` 打点已 wired，含离线 localStorage 降级队列）。
- **新增分字段复制**：标题（点任一候选复制单条）/ 标签（复制全部 #tag）/ 脚本（复制正文）各一个小复制图标。降低粘贴摩擦。
- **标签可编辑**：去 niche 化后标签来源不确定，给用户「+ 加标签 / × 删」轻编辑（chip 可增删），默认从分析 theme 生成 3–5 个候选。
- **禁词把关**：复制前对**拼入的 script/标题**跑 `scrubUiForbidden`（当前 `buildPublishPack` 只 `stripHookCode`，会漏禁词到剪贴板）——这是上线前必补的安全项。
- **去抖音深链**（PHASED_PLAN 不做 OAuth 一键发布，§5.2）：Phase2 不做自动发布，但可加一个「打开抖音创作中心」的外链按钮（纯跳转，不传数据），把「复制→切 App→粘贴」的断点显式化、有引导。

### 5.4 trailer 与品牌

保留 `—— 用 Cascade 做的 · cascade.app` trailer（已有，正文与 trailer 间禁词测试覆盖）。

---

## 6. 配额 / 付费触点（P2-5，闭环里的钱闸）

闭环每一步真花钱（分析 ¥0.5、生成按张/按秒）。配额/付费不是单独页面，是**嵌在闭环里的轻触点**：

- **额度条**（可选，pro/正常视图）：Header 或第③幕顶显「今日剩余 N 次生成」。
- **超额态**：生成/改写 enqueue 前若超配额 → 不报错，弹**轻量 paywall 卡**（暖色科技，非弹窗劫持）：「免费额度用完了 · 升级 Pro ¥39/月 继续」+「明天再来」。埋点 `quota_exceeded` / `paywall_viewed`。
- **降级而非阻断**：超额时已拿到的分析/改写**不收回**，只挡新生成。守「失败/限制有下一步」。

> freemium ¥0 / Pro ¥39（PHASED_PLAN P2-5，不做 Team）。具体额度数字待 founder + 成本核算定。

---

## 7. 状态总表（前端需新增/复用）

| 状态 | 来源 | 现状 | Phase2 动作 |
|------|------|------|------------|
| `analysis` | `analysis_returned` | ✅ 已 wired | 不动 |
| `failure` | `analysis_failed`/resume | ✅ FailureBanner | 扩 §8 矩阵动作 |
| `rewriteShots` / `script` | `rewrite_returned` | ✅ wired 但 UI 注释掉 | 渲染回 `RewriteCard` |
| `rewritePending` | 发改写命令时置 | **缺** | 新增,区分改写在途 vs 分析在途 |
| 镜头生成态(按 shot_index) | `shot_first_frame_returned` + `canvas_updated`/`session_state` | 部分(updateShotFirstFrame) | 扩成四态状态机 + reconnect 重建 |
| 配额/订阅 | 新后端字段 | **缺** | P2-5 |
| 来源标识(fixture/llm) | 改写产物元数据 | **缺** | 仅 admin/pro 视图,灰度核对用 |

**admin/pro 视图**：`App.tsx` 已有 `?view=pro` + `isAdminUser`。改写来源标识、成本明细、生成 task 深度等「调试感」信息走 pro 视图，不污染普通用户。

---

## 8. 失败 / 降级 UX（对齐架构失败矩阵，守 Gate「失败有下一步 100%」）

每幕的失败都必须给「下一步」，且**不连累上游已拿到的价值**。复用 `FailureBanner`（已有 S 码→中文 + 恢复按钮 `RECOVERY_HINTS`/`ACTION_LABELS`）+ best-effort 降级（clip 范式）。

| 幕 | 失败/降级 | UX | 判定:硬阻断 vs best-effort |
|----|----------|----|--------------------------|
| ①分析 | S5/S7/S8 等 | 整页 `FailureBanner` + 恢复按钮(现状) | 硬阻断(无分析=无价值) |
| ①clip | ffmpeg/下载失败 | `SceneClip` 降级到首帧/不渲染(现状) | best-effort(纯装饰) |
| ②改写 | LLM 超时/S5 | 第②幕原地失败卡 +「重写」,分析卡保留 | 硬阻断**该幕**,不连累分析 |
| ②改写 | confidence≤0.4 | 「把握一般」chip + 不阻断 + 可重写 | best-effort(可用但弱化) |
| ③生成 | 单镜失败 | 该镜降级到文字镜头 + 重试,其他镜正常 | best-effort(部分完成) |
| ③生成 | 全部失败/超配额 | 卡级提示 +「再试/升级」,改写脚本保留 | 硬阻断**该幕** |
| ④发布 | 剪贴板被拦 | toast「复制没成功,请再试」(现状) + 手动选中兜底 | best-effort |

**判界原则**（架构 clip 范式）：**核心价值缺失 = 硬阻断给 banner；花钱前必给确认/进度；装饰层缺失 = 静默降级不打扰**。

---

## 9. 待 Founder 决策（阻塞实现的开放问题）

1. **生成图 provider 合规**（架构 + 铁律⑦）：默认 `IMAGE_GEN_PROVIDER=google`（Gemini 跨境）。30 人 Beta 真实用户数据，要么默认切境内 Apimart，要么明确接受跨境 + 加同意条款。改写已隔离境内（doubao），生成图不能裸奔。**阻塞第③幕 provider 默认值。**
2. **改写解封灰度策略**（retro §7.2）：先灰度（部分邀请码可见 `RewriteCard`）还是达标全量？灰度则前端需按邀请码/cohort gate 第②幕渲染。
3. **发布发什么版本**（retro §7.3）：本设计立场是「发布依赖改写」（先解封改写再接发布）。确认这个依赖顺序（架构 M2→M4）。
4. **改写去 niche 化的锚点**：通用代笔 prompt（不要用户输入）vs 用户自填一句话主题。影响第②幕是否需要一个主题输入框 + 改写 prompt 改写工作量（+ bump `REWRITE_PIPELINE_REVISION`）。
5. **关键镜头数量与选取**：固定前 3–5 个 vs 用户勾选?直接影响成本与第③幕交互密度。
6. **Phase1 Gate 是否硬卡 Phase2**（retro §7.1）：本设计为埋点（P2-10）和改写质量验证（H3）预留了入口（`LoopProgressBar` 漏斗 + pro 视图来源标识），但 Gate 收口需真实陪跑数据。

---

## 10. 实现顺序（对齐架构 M0–M5，每步守铁律②/⑤/⑧）

| 步 | 前端交付 | 依赖 | 铁律 Gate |
|----|---------|------|----------|
| **S0** | `LoopProgressBar`(空步全灰,纯视觉) + `rewritePending` 标志接入 | 无 | ②lint+真浏览器;⑧新动效进 reduced-motion |
| **S1** | `RewriteCard` + `RewritePendingCard` 渲染回 `CardStack`(改写帧已 wired) | 架构 M1(`REWRITE_PIPELINE_REVISION`) + M2(双开关) | ⑤真 URL doubao 实跑验收质量;②lint |
| **S2** | `StoryboardCard` + 镜头四态状态机 + reconnect 重建 | 架构 M3(C3 桥接 + JobProgress + cost_guard) + §9.1 provider 决策 | ⑤真 URL 验证慢任务断线重连;② |
| **S3** | `PublishPackCard` 复活 + 修三个洞 + 分字段复制 + scrub 把关 | S1(改写数据源) + S2(镜头图 url) | ②;buildPublishPack 测试扩充(镜头图接入 + 去 niche 标签) |
| **S4** | 配额/paywall 触点 | 架构 P2-5 | ② |
| **S5** | 视频生成扩展位激活(P2-1) / 短链 302 / 埋点收口 | 架构 M5 | ⑤ |

**强依赖**：S1(改写) 必须先于 S3(发布)——发布数据源是改写产物。S2(生成) 镜头来源主用改写 visual，回退分析 visual_content，可与 S1 并行但 C3 桥接依赖改写解封后才有最佳来源。

---

## 11. 设计铁律自检（动手前对照）

1. **承接真实形态**：第①幕 = toprador 维度 + 三级层级（英雄四维：钩子/痛点需求/情绪触发/目标人群）+ 脚本抽屉 + AnalysisStatStrip。**不是**抓/留/带三幕（W4 提案已被 toprador 对齐反转覆盖，retro §2.2）。✅
2. **改 prompt/维度/模型** → bump `backend/src/agent/cascade/contract.py:28 ANALYSIS_PIPELINE_REVISION`（现=3）；**改写 prompt** → bump 新增 `REWRITE_PIPELINE_REVISION`（铁律①对 rewrites 表无效）。✅
3. **改 UI** → `npm run lint`(rules-of-hooks 0 违规) + Playwright 真浏览器旅程（jsdom 测不到 early-return 后的 hook，prod 吞成空白页 React #310）。✅
4. **新 `.anim-*`** → 追加进 `index.css` reduced-motion 名单（~571 行）；**不引 framer-motion**，复用现有 keyframe + `useInView`/`useCountUp`。✅
5. **玻璃/blur 节制**：重点卡(改写/发布)用 `CARD_GLASS`；逐幕长列表保持实色卡。✅
6. **doubao 境内合规**：改写走 doubao（已隔离）；生成图 provider 合规待 founder（§9.1）。✅
7. **容器健康 ≠ 功能可用**：每步真 URL 跑完整闭环验证（尤其改写真过模型、生成断线重连）。✅
8. **失败有下一步 100%**：每幕失败给恢复按钮 + 不连累上游价值（§8 矩阵）。✅

---

*本文为 Phase2 闭环 UX 设计稿。承接 [phase1_retro_handoff](phase1_retro_handoff_2026-05-31.md) §6 基线与 [architecture_phase1_phase2_design](architecture_phase1_phase2_design_2026-05-31.md) 的 CreationRun/C1–C4/JobProgress/失败矩阵契约。所有现状断言已对真实代码 Read/Grep 核验。*
