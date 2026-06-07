# 基于无限画布统筹「爆点分析 + 创作」实施方案

> ⚠️ **过期提示(2026-06-06,审计 L4)**:本文「现状盘点」里的行数/节点数已漂移,勿据此做架构判断。
> 真实现状以代码与最新审计为准:`canvas.py`≈760 行、`NodeDetail.tsx`≈900 行;画布节点实为 **4 类**
> (script/image/video/composite),原文「6 节点」含的 storyboard/audio 已是死组件并于本次清理删除。
> 端到端现状见 [`pro_canvas_e2e_audit_2026-06-06.md`](./pro_canvas_e2e_audit_2026-06-06.md)。

**日期**：2026-06-02
**触发**：founder 指出视频创作的本质形态是「无限画布 + agent 底层编排统筹」,要求把爆点分析也统筹进画布,做到「看懂别人为什么火」↔「做自己的版本」**丝滑切换**;并要求吸收 LangGraph / DeepAgents / ReactFlow 的开源能力。
**性质**：实施方案(不写代码),待 founder 拍板方向后再动手。
**关联**：`README.md`(产品定位)、`docs/CANVAS_DESIGN.md`(画布设计)、`backend/src/agent/prompts/director.md`(编排规则)、`project_analyzing_wait_redesign`(上一轮 CardStack 线性形态,保留)。

---

## 0. 一句话目标

> 一张无限画布,左端是「源视频 → 爆点分析」(看懂为什么火),顺势向右展开「改写 → 锚点级联(角色/场景/宫格) → 逐镜视频 → 合成」(做我的版本)。**Director agent 编排整条 DAG,人在每个闸门审核干预,分析与创作在同一张画布上丝滑衔接** —— 而不是现在分析走 CardStack 线性卡片、创作走另一个 pro-view 画布、两者割裂。

---

## 1. 现状盘点(代码事实,不是猜)

### 1.1 已经 live、能复用的(好消息:地基都在)

| 能力 | 代码位置 | 状态 |
|---|---|---|
| **画布编排后端** | `tools/canvas.py`(530 行):create/update/delete node+edge、`_validate_hierarchy` 层级校验、`execute_node`、`approve/reject_node`、异步生成队列(`enqueue_generation`/`claim_pending_tasks`/`recover_generation_tasks`) | ✅ 完整 |
| **画布 WS 路由** | `transport/ws_handlers.py`:`handle_create_edge/update_position/review_node/execute_node/update_node_status`;`ws_messages.py` 消息定义 | ✅ 完整 |
| **Director agent + 编排规则** | `main.py`(create_deep_agent + 9 工具 + `canvas-manager` subagent)、`prompts/director.md` §2–6 把「策划书→角色三视图→场景图→宫格图→视频→合成」的锚点级联流程定义得**极完整** | ✅ 完整 |
| **前端画布** | `Canvas.tsx`(ReactFlow + dagre 自动排版) + 6 节点(`Script/Image/Storyboard(宫格)/Video/Audio/Composite`) + `NodeDetail.tsx`(781 行:prompt 编辑/生成/审核/合成/音频) + `useNodeActions` | ✅ 完整 |
| **锚点系统** | `cascade/anchors.py` + 前端 `anchors/`(Sidebar/Card/PickerModal) + 跨 run 复用统计 | ✅ 完整 |
| **生成底座** | `tools/generation.py`(图)、`video_generation.py`(Seedance)、`compose.py`(ffmpeg 合成) | ✅ 完整(CardStack 路径已在用) |

### 1.2 关键缺口(这才是要做的)

| 缺口 | 证据 | 影响 |
|---|---|---|
| **① 分析↔画布无桥** | `grep seed_canvas` 前后端**查无此物**(CANVAS_DESIGN §8 设计了,代码没建)。分析走 `cascade_analyze → CardStack`,创作走 Director 画布,两条路**断开** | 无法「分析完顺势在画布创作」—— 丝滑切换的**头号缺口** |
| **② 画布被关在 pro-view** | `App.tsx`:`isProView ? <Canvas/> : <CardStack/>`,`director.md` §0.5 白纸黑字「Cascade 走卡片栈渲染(Phase 1),**不走 Director 画布**」 | 内测用户根本看不到画布形态 |
| **③ 爆点分析不是画布节点** | 分析结果只进 `CardStack` 卡片,画布上没有「源视频节点 / 爆点分析节点」 | 分析无法作为画布创作的「起点」 |
| **④ 审核闸门靠 prompt 约定** | `director.md`「只创建不执行,用户在前端点确认」—— 是**口头约定**,不是机制;agent 可能跑过头 | 审核不可靠(见 §3 LangGraph interrupt 可治本) |
| **⑤ 锚点级联在 CardStack 形态被旁路** | 上一轮图生视频(`project_video_loop_built`)走 CardStack 扁平线性(草稿图→视频→合成),**没有角色三视图/场景图/宫格图** | 护城河(跨片角色一致性)没启用 |

---

## 2. 开源能力 → 我们能加的功能(founder 让学的三个底座)

研究了 LangGraph / DeepAgents / ReactFlow 的最新能力,挑出**正好补我们缺口**的,按价值排序:

### 2.1 LangGraph(我们 Director 的运行时)

| 开源能力 | API | 补我们哪个缺口 / 加什么功能 |
|---|---|---|
| **Interrupt(human-in-the-loop)** | `interrupt()` 暂停 graph + `Command(resume=...)` 恢复;需 checkpointer | **治本缺口④**:审核闸门从「prompt 约定」升级为**原生机制** —— Director 生成完剧本/锚点后**真的暂停**,前端弹审核 UI(CANVAS_DESIGN §5 的 5 触发器×3 形态),用户审完 resume。agent 不再跑过头 |
| **Time travel** | `get_state_history()` 取任意历史 checkpoint + `update_state()` 改 + 从该 checkpoint replay,**fork alternate branch** | **CANVAS_DESIGN 设计原则④「任何时候回到上游节点修改」**:用户在画布回到「锚点」节点改描述,fork 出新分支重生下游宫格/视频,旧版本保留可对比。**也是「分析↔创作丝滑切换」的底层** —— 创作就是从分析 checkpoint fork 出的分支 |
| **Durable execution** | `stream(durability="sync")` 每步落 checkpoint | 长时视频生成(几分钟)崩溃可续;我们已用 `AsyncSqliteSaver`,深化即可 |
| **Streaming modes** | `stream(stream_mode="updates")` 节点完成即推 | 已有 `agent_stream`+`canvas_updated`,对齐 |

### 2.2 DeepAgents(我们 `create_deep_agent` 的来源)

| 开源能力 | 补我们哪个缺口 / 加什么功能 |
|---|---|
| **async subagents(后台跑 + 进度检查 + 取消)** | **多镜并行渲染**(CANVAS_DESIGN 闪电模式「6/8 镜头并行」)+ 用户可**取消单镜**;比我上一轮手搓的 background poll 更原生 |
| **planning / `write_todos`** | 把创作多步(剧本→锚点→宫格→视频→合成)做成**画布顶部的进度/章节清单**(CANVAS_DESIGN 闪电模式进度视图) |
| **更多专家 subagent** | 现在只有 `canvas-manager`。可加**爆点分析专家 / 锚点设计专家 / 分镜导演专家**,context 隔离不互相污染 |
| **context middleware(压缩历史 + 大结果 offload 到 fs + prompt caching)** | 长创作会话 token 爆炸 → 压缩;分析 JSON/图等大结果 offload;降本提速 |

### 2.3 ReactFlow / xyflow(我们的画布)

| 开源能力 | 补我们哪个缺口 / 加什么功能 |
|---|---|
| **Sub-flows / 节点分组**(`parentNode`+`type:'group'`+`extent:'parent'`) | **章节层**(开场/中段/高潮/结尾):8 个镜头按叙事章节分组,整组折叠/移动(CANVAS_DESIGN V2 章节层) |
| **NodeToolbar** | 把「生成/重生/确认/删除」**直接挂到节点上**,减少对 781 行 `NodeDetail` 侧面板的依赖,更符合「节点为主体」 |
| **Computing flows / 节点间数据传递** | **锚点级联参考链可视化**:角色/场景→宫格→视频的参考图沿边传递,正好对应 `director.md`「video parent=宫格自动带参考链」 |
| **NodeResizer / Selection grouping / Helper lines** | 锚点/宫格节点可放大看细节;多选镜头成章节;手动排版对齐辅助 |
| **Undo/redo · Copy-paste** | 画布编辑体验(与 LangGraph time-travel 分工:前者 UI 级,后者 agent 状态级) |
| **Collaborative editing** | V2 MCN 团队多人协作(对应 CANVAS_DESIGN 商业化 tenant/seat) |

---

## 3. 目标形态:一张画布,分析→创作丝滑展开

```
   ┌─ 看懂为什么火(爆点分析) ─┐   ┌──────── 做我的版本(锚点级联创作) ────────┐
   │                          │   │                                           │
 [源视频] → [爆点分析]  ──(丝滑切换:一键「做我的版本」)──→  [改写策划书]
   节点       节点(10维+逐幕)                                    │ interrupt 审核闸门
                                                                 ▼
                                              [角色三视图]  [场景图]   ← 锚点(可跨片复用)
                                                    └────┬────┘ interrupt 审核闸门
                                                         ▼
                                                    [宫格图 ×N]  ← 章节分组(sub-flow)
                                                         ▼ 参考链沿边传递
                                                    [逐镜视频 ×N]  ← async subagent 并行+可取消
                                                         ▼ interrupt 成片闸门
                                                    [合成成片] → [发布包]
```

**丝滑切换的两种实现路径(§5 决策点 D1)**:
- **路径 A(同画布级联)**:分析就是画布最左的起点节点,用户看完点「做我的版本」→ Director 在**同一张画布**向右 seed 出创作节点树(README「一条龙」最直接的体现)。
- **路径 B(同数据双视图)**:CardStack(爆点分析的精炼卡片)与 Canvas(同一份数据的画布)是**同一 run 的两种渲染**,顶部一键切换(CANVAS_DESIGN §1「三档模式×同一画布」)。`canvasStore` 已同时持有 `analysis`+`nodes`+`edges`,数据层已具备。

> **founder 已定(2026-06-02):A+B 都要** —— 主走 A(同画布级联,创作分支用 LangGraph time-travel 从分析 checkpoint fork);再给「只想快速看分析」的用户保留 B(轻量卡片视图,即现有 CardStack 复用)。两者用同一 run 数据,天然丝滑。

---

## 4. 分阶段实施(每阶段独立可验,不大爆炸)

> 原则:**复用已 live 的画布编排/生成底座(§1.1),只补缺口(§1.2),逐步把开源能力(§2)接进来**。CardStack 现状保留(founder 已定),作为「闪电/简易」入口并存。
>
> **执行顺序(D4 已定 2026-06-02)**:先跑 **P1 的 demo 子集**(pro-view 验证锚点级联形态对不对)→ 再做 **P0**(seed_canvas 桥,把分析丝滑接进画布)→ P1 全量 → P2(拆细灰度:interrupt→time-travel)。即「**先验证形态,再铺开桥接,最后升级运行时**」—— 呼应「动手前先确认方向对」的教训。

### P0 — 打通「分析→画布」的桥 + 画布可进(解决缺口①②③)
- 建 `seed_canvas(analysis_id)`:分析完,在画布 seed 出「源视频节点 + 爆点分析节点」(+ 留好改写节点锚位)。前后端 WS 消息 + canvasStore 接入。
- 新增「爆点分析节点」类型(画布上渲染 10 维+逐幕,复用现有 ViralAnalysisCard 内容)。
- 入口:分析结果页加「在画布上做我的版本」CTA → 切到 Canvas 并 seed。**不删 CardStack**,作为并行入口。
- **产出**:用户能从分析丝滑进入画布,看到自己这条的分析作为创作起点。**风险低**(纯新增,不动 CardStack)。

### P1 — 锚点级联创作在画布跑通(解决缺口⑤ + 接 ReactFlow 能力)
- 打通 `director.md` §4–6 的真实路径:改写→角色三视图→场景图→宫格图→逐镜视频→合成,全部为画布节点。
- 接 **ReactFlow sub-flows**:镜头按章节分组;接 **NodeToolbar**:节点上挂生成/确认。
- 锚点跨片复用 UI(AnchorSidebar 已有)接进创作流。
- **产出**:护城河(角色一致性的锚点级联)在画布上真正启用。**风险中**(涉及多节点编排联调)。

### P2 — 接 LangGraph/DeepAgents 高级能力(把约定升级为机制)
- **LangGraph interrupt**:审核闸门(剧本/锚点/成片)从 prompt 约定升级为原生 `interrupt()`+`Command(resume)`。
- **LangGraph time-travel**:画布「回到上游节点改了重生下游」用 fork/replay。
- **DeepAgents async subagents**:多镜并行渲染 + 可取消;**planning todo** 映射画布进度。
- **context middleware**:长会话降本。
- **产出**:审核可靠、可回溯、多镜并行、降本。**风险中高**(改 agent 运行时,需充分测试 + 灰度)。

---

## 5. 需要 founder 拍板的决策点

- **D1 丝滑切换形态** ✅ 已定(2026-06-02):**A+B 都要**(主 A 同画布级联 + 辅 B 轻量卡片视图复用 CardStack)。
- **D2 放量节奏** ✅ 已定:**维持双轨并存** —— CardStack 默认看分析,画布作「做我的版本」入口,用户自选;画布作渐进新增入口,不硬性一刀反转 §0.5。
- **D3 CardStack 终局** ✅ 已定:**闪电/简易模式并存**(对应 CANVAS_DESIGN 三档模式),长期保留作快看分析的轻量入口。
- **D4 范围/优先级** ✅ 已定:**先 P1 锚点级联 demo** —— 先在 pro-view 把 分析→改写→角色三视图→场景→宫格→逐镜视频 跑通验证形态,再做 P0 桥铺开。
- **D5 运行时改造** ✅ 已定:**拆细灰度逐个上** —— interrupt 先(审核闸门)、time-travel 后(回溯),各自充分测试+灰度,不一波改 agent 核心。

---

## 6. 我之前错在哪(自省,避免重犯)

- 把 Phase 1 的权宜降级品(CardStack 线性卡片)当成了产品,在它的等待态等边角上精雕细琢(AnalyzingHero),**没理解产品本质是「无限画布 + agent 编排 + 锚点级联」**,把真正的核心(Canvas)晾在 pro-view 没碰。
- 教训:**动手前先吃透产品愿景(README/CANVAS_DESIGN/director.md)与底层技术(LangGraph/DeepAgents/ReactFlow)的能力边界**,再定方向。本方案即此补课的产出。
