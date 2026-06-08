# RHTV 无限画布「新架构」调研 × OpenRHTV 现状对比

> 主题:以 **画布(tldraw / VueFlow)+ 执行后端(ComfyUI / litegraph 内核 + 异步任务队列)+ Agent 层(LangChain 做「NL→节点图」规划)** 这套「新架构」(开源参照 `MaLunan/AIGCCanvasFlow`)为对象,对比它与 OpenRHTV(Cascade)现有无限画布的区别。
>
> 本文 = ① 调研沉淀(RHTV / 新架构 / 开源参照)+ ② OpenRHTV 现状(基于代码实读)+ ③ 逐维度对比 + ④ 迁移评估与建议。
> 关联文档:[`CANVAS_DESIGN.md`](./CANVAS_DESIGN.md)(现有画布详设)、[`TOPIC_TO_CREATION_PIPELINE.md`](./TOPIC_TO_CREATION_PIPELINE.md)、[`PRODUCT_VISION.md`](./PRODUCT_VISION.md)
>
> 调研日期:2026-06-06 · 调研口径:RHTV 官方报道多为转引,缺第三方复现,标注为「官方口径」。

---

## TL;DR(一句话结论)

OpenRHTV 的画布和「新架构」**形似而神不同**:

- **新架构(ComfyUI 范式)= 用户连线的「通用可执行计算图」**——节点是算子,用户从面板拖拽、连线、点运行,引擎拓扑执行;Agent 是「可选的」自动布图器。
- **OpenRHTV = Agent 驱动、人工审核的「创作产物树」**——节点是创作产物(策划书/角色图/场景图/分镜/视频/成片),由 Director agent 用工具搭建,带**人在环审核**(reviewing→confirmed)、**领域层级约束**(script→image→grid)、**境内合规闭环**,执行用的是**自研异步生成队列**而非 ComfyUI/litegraph。

> 两者不是"谁替代谁",而是"通用生成 IDE" vs "垂直创作流水线"。直接迁到新架构会**得到**通用节点生态/模型生态/更强画布 UX,但会**丢失**当前的领域护栏(审核闸、层级约束、锚点级联、合规),除非重新实现。**推荐混合演进而非整体替换**(见 §6)。

---

## 1. 「新架构」是什么(调研沉淀)

### 1.1 RHTV(RunningHub TV)产品形态 — 灵感来源
- 2026-05-07 上线,RunningHub 推出的「原生 AI 智能体全能内容创作平台」,核心载体是**无限画布**。
- 差异化:**Agent 原生嵌入画布**(非侧边栏/聊天外挂),自然语言驱动 `任务拆解 → 工作流规划(画布自动搭 ComfyUI 节点)→ 资产生成 → 成片`,全程透明可逐节点干预。
- 技术底座:建立在 RunningHub 云端 ComfyUI 生态上(官方口径:约 1.37 万节点 + 170+ 标准模型 API + 10 万+社区应用),覆盖图/视频/音频/3D/文本五模态;Agent 与阿里 ComfyUI-Copilot 合作。
- 三种模式:图片生成 / 视频生成(手动搭节点)/ Agent 对话(自动规划)。
- 国际版 rhtv.ai / 国内版 runninghub.cn。

### 1.2 「新架构」四件套
| 层 | 选型 | 职责 |
|---|---|---|
| 画布 | **tldraw** 或 **VueFlow**(React Flow 的 Vue 版) | 无限画布 + 节点/连线交互 |
| 执行后端 | **ComfyUI(litegraph 内核)+ 异步任务队列** | 把节点图编译成 DAG,拓扑执行,跑模型 |
| Agent 层 | **LangChain** 做「NL→节点图」规划 | 把自然语言意图翻译成可执行节点图 |
| 开源参照 | **`MaLunan/AIGCCanvasFlow`** | 这套思路的全栈开源缩小版 |

### 1.2b 实际落地对照(2026-06-07 更新 · Pro 画布已上线 prod 灰度)

> 本文初稿(2026-06-06)写的「OpenRHTV 现状」= 当时的 Agent 画布(React Flow 创作产物树)。**2026-06-07 我们另建了 `/pro` 高级子画布(tldraw + 自研执行器),形态最接近 §1.2 设想**。下表是 §1.2 四件套**设想 vs 我们实际落地**的逐层对照(基于代码,非设想):

| 层 | §1.2 设想 | OpenRHTV 实际落地(`/pro` 画布) | 一致度 |
|---|---|---|---|
| 画布 | tldraw / VueFlow | **tldraw 5.1.0**(`/pro/:threadId`,自定义 `pronode` shape;prod 非 localhost 需 licenseKey) | ✅ 选了 tldraw |
| 执行后端 | **ComfyUI(litegraph 内核)** + 异步队列 | **自研境内 per-node DAG 执行器**:`workers/pro_run_pipeline.py` 的 `_topo()`(Kahn 拓扑排序)+ `_run_domestic()`(逐节点路由);**「跑模型」= 调火山 API**(Generate→Seedream、Video→Seedance)+ 本地 ffmpeg(Compose/字幕/BGM/TTS),**非 litegraph 本地推理**。异步队列 = sqlite `pro_runs` 表 + 第 4 个 worker(claim→执行→续租→推帧) | ◐ **形状一致(DAG+拓扑+异步队列),内核不同(火山 API 非 ComfyUI)** |
| ComfyUI 路径 | (即上一行) | **代码在但 opt-in、默认关、已搁置**:`_run_comfyui()` + `comfyui/compiler.py`(图→ComfyUI prompt)+ `provider.py`(submit /prompt、图 URL 自动上传 /upload/image、poll images/gifs)。节点级 backend 下拉可选 ComfyUI。**搁置原因:prod 2 核 3G 无 GPU 带不动;火山 API 本就 GPU-free 境内合规更省**(founder 2026-06-07 拍板跳过) | ◐ 备而不用 |
| Agent 层 | **LangChain** NL→节点图 | **不是 LangChain 通用规划器**:主题→脚本+分镜 = Doubao 直调结构化(`comfyui/script_gen.py`);图的生成走**确定性编译**(`seed_builder.py`:主题/分析→种子创作图),非「自然语言→任意节点图」LLM 布图。Agent 模式另有 Director(deepagents)编排 Agent 画布 | ◐ 有 LLM 生成、非通用 NL→图 |
| 开源参照 | `MaLunan/AIGCCanvasFlow` | **借鉴思路未照搬**:异步 `task_id` 轮询 ✅、统一 provider 适配器 ✅、受控数据流图(连线住 Zustand store)✅;但栈不同(asyncio worker + sqlite + 火山 provider,无 Vue/Celery/Redis/MinIO) | ◐ 借鉴 |

**一句话**:画布层照 §1.2 选了 tldraw;**执行后端刻意偏离了 §1.2** —— 用「自研 DAG 执行器 + 火山 API」替代「ComfyUI/litegraph 内核」(DAG/拓扑/异步队列的**形状**保留,**引擎**换成境内 API),ComfyUI 仅作可选后端备而不用;Agent 层用确定性编译 + Doubao 生成,非 LangChain 通用 NL→图 规划。代码见 `backend/src/agent/workers/pro_run_pipeline.py`、`backend/src/agent/comfyui/{compiler,provider,seed_builder,script_gen}.py`。

> 补:§1.2 设想保留 ComfyUI 范式的**护城河取舍**——通用节点/模型生态拿到了一半(tldraw 画布 UX),但执行内核换成火山 API 后,失去了 ComfyUI 的 1.37 万节点生态;换来的是境内合规 + GPU-free + 成本闸可控。这正是 TL;DR 说的「混合演进而非整体替换」的落地形态。

### 1.2c Agent 层:设想 vs 实际 的优缺点 + 混合演进状态

**本质区别**:§1.2 设想 = **LLM 即兴规划整张图**(NL→任意节点图);实际落地 = **LLM 只生成内容、图结构由代码确定性编译**(`script_gen` 出脚本/分镜 → `seed_builder` 编成固定形状图)。

| | 设想:LangChain NL→任意节点图 | 实际:Doubao 结构化 + 确定性编译 |
|---|---|---|
| 灵活性 | ✅ 高(任意工作流/长尾节点) | ❌ 低(只出「主题→成片」一种固定流程) |
| 可靠性 | ❌ 低(LLM 布图易连错口/缺节点,要重校验+纠错) | ✅ 高(模板编译 + `validate_graph` 保证不改直接 Run) |
| 领域护栏 | ❌ 难加(自由布图难强制审核闸/合规/成本闸) | ✅ 天然嵌入(模板里直接带成本闸/合规/锚点级联/缓存) |
| 质量稳定 | ❌ 看 LLM 当次发挥 | ✅ 固定 schema + 专调 prompt(可版本守卫) |
| 成本/速度 | ❌ 每次一大轮 LLM(+纠错轮) | ✅ 一次 Doubao 出内容,图编译纯代码 0 LLM,成本可预测 |
| 创意上限 | ✅ 高(自由组合) | ❌ 被模板封顶 |
| 「Agent 原生」体验 | ✅ 对话驱动画布 | ❌ LLM 只种子时介入一次,之后人工编辑+重生 |
| 工程/可测 | ❌ 重(agent+工具schema+校验+恢复) | ✅ 确定性编译=纯函数,好测、故障面小 |

**取舍结论**:当前产品(短视频「主题→成片」批量生产)要的是**可靠/可控/省钱/合规**,不是通用生成 IDE 的灵活 → **确定性编译是对的选择**;LLM 自由布图华丽但失败率/烧钱/护栏缺失会反噬。

**混合演进路径 = 确定性骨架 + LLM 局部布图。实现状态(2026-06-07):**

| 组成 | 状态 | 实现 |
|---|---|---|
| 确定性骨架(主干) | ✅ 完整 | `seed_builder.py`(主题/分析→固定创作图),已上线 |
| 手动局部编辑 | ✅ 有(人驱动,非 LLM) | 增删节点/连线、单节点重生、改脚本/改主题重生 |
| **LLM 局部布图**(在骨架上让 LLM 增删/重连局部节点) | ❌ **未做**,仅方向 | — |
| LLM 工具搭节点(现成内核,在另一轨) | ◐ 有但未接 | Agent 模式 **Director(deepagents)** 能 `create/update_canvas_node`+锚点级联+人在环,但在 **Agent 画布(React Flow)**,**未接到 Pro tldraw 画布**;两套画布尚未打通 |

> 即:混合演进的「**LLM 那一半**」要落地,需把 Director 的工具编排搬到 Pro 画布、或合并两套画布 —— **都还没做**。目前 Pro 画布的「智能」只在种子那一下(主题→脚本/分镜),之后纯人工 + 单点重生。

### 1.3 开源参照的关键实现(读码/读文沉淀)

**`MaLunan/AIGCCanvasFlow`**(Vue3 全栈,架构最接近 RHTV):
- 前端:`Vue3 + VueFlow + Pinia` 受控模式(所有画布改动过 Pinia 单一数据源);`markRaw` 包裹节点组件防响应式代理掉性能;连线 `edge.label` 实时传播上游输出值(「活的数据流图」);分组节点用 `parentNode + extent:'parent'`。
- AI 服务:`FastAPI + Celery + Redis` 异步任务(`POST /generate → task_id → 轮询 → result_url`);`LangChain PromptEnhanceChain` 把中文提示词桥接成英文;统一模型适配器 `BaseImageModel.generate()→url`;结果存 MinIO。
- 后端:Spring Cloud 微服务(网关/鉴权/画布/用户),JWT 无状态。
- 浏览器内 `ffmpeg.wasm` 截帧/转码(需 COOP/COEP 头开 `SharedArrayBuffer`)。

**`tldraw/image-pipeline-template`**(React,类 ComfyUI,代码最规整):
- 节点与连线**都是 tldraw shape**;连线用 binding 绑定到端口。
- **类型安全端口**(image/text/model/number/latent/any),拖线只高亮兼容端口 + 环检测。
- **前端 DAG 执行引擎**(`ExecutionGraph.tsx`):由连线构图 → 拓扑解依赖 → **独立分支并行** → 每节点 `execute(inputs)` → 结果缓存(改一个节点只重跑下游)。
- 后端:Cloudflare Worker + R2,provider 抽象接 Replicate。

**`litegraph.js`**(ComfyUI 内核):老牌节点图引擎,**自带图执行运行时**,和 ComfyUI 工作流 JSON 天然兼容。

### 1.4 「新架构」的可复用心智模型(4 层)
1. **图模型**:节点+连线的可序列化结构(能存能传后端)
2. **端口类型系统**:决定"谁能连谁" + 环检测(体验上限)
3. **DAG 执行引擎**:拓扑解依赖 + 独立分支并行 + 结果缓存(性能)
4. **异步 AI 后端**:任务队列 + provider 抽象(能接多少模型)

---

## 2. OpenRHTV 现有画布架构(代码实读)

> 来源:`frontend/package.json`、`backend/pyproject.toml`、`frontend/src/store/canvasStore.ts`、`backend/src/agent/tools/canvas.py`、`README.md`。

### 2.1 技术栈
| 层 | OpenRHTV 实际 |
|---|---|
| 画布前端 | **React Flow(`@xyflow/react ^12`)+ React 19 + TS**,状态用 **Zustand**(`canvasStore.ts`),非 tldraw/VueFlow |
| Agent 框架 | **LangGraph + DeepAgents**(`deepagents`、`langchain-openai`、`langgraph-checkpoint-sqlite`),Director 单 agent + canvas-manager subagent |
| 执行后端 | **自研 Python asyncio 异步生成队列**(非 ComfyUI/litegraph) |
| 图存储 | **SQLite 侧库 `canvas.db`**(节点/边),DAG 遍历在 Python 侧 |
| LLM/生成 | Doubao(火山方舟 ARK,境内默认)+ Gemini fallback;图 = Apimart(OpenAI 兼容,境内)/ Gemini(二次同意);视频 = Doubao Seedance 2.0(Volcengine SDK) |
| 传输 | 单进程,WebSocket + HTTP 同端口 `8765` |

### 2.2 画布范式:**Agent 驱动的产物树,非用户连线的计算图**
这是与新架构**最本质的区别**:

- **谁建图**:节点由 **Director agent 调工具**创建(`create_canvas_node` / `execute_node` / `approve_node` / `regenerate_node`…),**不是用户从面板拖拽连线**。用户主要"下指令 + 审核",拖拽仅改位置(`updateNodePosition`)。
- **节点是产物不是算子**:类型 `script / image / video / composite / audio`,对应创作产物(策划书、角色图、场景图、分镜 grid、视频、成片),而非通用 compute 节点。
- **领域层级约束**(server 强校验,`HIERARCHY` + `_validate_hierarchy`):
  `script(策划书) → image(character|scene) → image(grid)`。违规连接直接报错。新架构是"类型兼容即可连"的通用端口。
- **人在环审核状态机**:`node_status: reviewing → confirmed`;**上游未 confirmed 不能创建下游**(`create_canvas_node` 里硬闸)。这是 ComfyUI 范式没有的。
- **布局服务端算**:`_default_position` 按父子关系自动排版后推给前端。
- **锚点级联(domain 护城河)**:重生时 worker 按边读父节点最新 `result.url` 作参考(角色/场景跨节点复用,防风格漂移)。

### 2.3 执行后端:自研异步生成队列(不是 litegraph)
- 队列语义:`enqueue_generation`(置 `generation_status=pending`)→ worker `claim_pending_tasks`(**租约 lease** 防重复领取)→ submit → poll → `update_generation_state` / `_update_node_result`。
- 韧性:`schedule_generation_retry`(重试)、`circuit_breaker.py`(上游熔断,60s 窗口 5 次失败开)、`cost_guard.py`(每 run 成本上限)、`cancel_node_generation`(逐镜可取消 + 取消守卫防 in-flight 竞态)。
- **DAG 遍历在 Python 侧**:`_descendants` 沿 `source→target` BFS,`_mark_descendants_stale` 标脏下游(`needs_regen`)。
- **Time-travel 版本**:`snapshot_version` / `restore_node_version`(append-only,回滚换回旧产物不调模型不花钱)。

### 2.4 Agent 层:LangGraph,且「NL→工具调用」而非「NL→图 JSON」
- Director 用 **tool calling**(`create_canvas_node` 等)逐步搭建产物树,辅以 `write_todos` 把多步规划投射到画布进度(`todos`)。
- 这是 Cascade 流水线:`源 URL → 浅分析(爆款公式 + H1-H9 钩子分类)→ niche 改写(Doubao)→ 锚点 → shots → 画布节点`。
- 对比新架构的 LangChain「NL→litegraph 节点图」:OpenRHTV 不产出"可执行图 JSON",产出的是"领域产物 + 审核态"。

### 2.5 合规闭环(新架构开源参照里没有)
境内内测口径:Doubao 境内推理、PII 脱敏(`_strip_pii`)、跨境数据硬阻塞(`STRICT_CROSS_BORDER_REJECT`)、未成年人关键词审计、删除承诺 24h。

---

## 3. 核心对比表

| 维度 | OpenRHTV(现状) | 新架构(ComfyUI 范式) |
|---|---|---|
| **画布库** | React Flow + Zustand | tldraw 或 VueFlow |
| **画布范式** | Agent 驱动的**产物树**,服务端权威 | 用户连线的**通用可执行计算图** |
| **谁建图** | Director agent(工具调用) | 用户拖拽连线;Agent 可选自动布图 |
| **节点语义** | 创作产物(script/image/video/composite) | 通用算子(model/prompt/generate/upscale…) |
| **连线含义** | 领域层级 + 锚点参考(script→image→grid) | 类型化数据流(端口类型兼容) |
| **执行引擎** | 自研 Python 异步队列(lease/retry/熔断/成本闸) | litegraph/ComfyUI 图执行 + 任务队列 |
| **图存储** | SQLite 侧库 `canvas.db`,Python BFS 遍历 | litegraph 图 JSON / ComfyUI prompt 格式 |
| **端口类型系统** | 无(靠领域 HIERARCHY 约束) | 有(image/text/model/number/latent/any)+ 环检测 |
| **人在环审核** | ✅ reviewing→confirmed,上游未确认不建下游 | ❌(默认无,需自建) |
| **Agent 框架** | LangGraph + DeepAgents,NL→工具调用 | LangChain,NL→节点图 |
| **模型/节点生态** | 固定 provider(Doubao/Apimart/Gemini/Seedance) | ComfyUI 海量节点 + 商业模型 API |
| **time-travel** | ✅ 节点级版本快照 + 回滚 | 部分实现有缓存,版本管理需自建 |
| **合规** | ✅ 境内/PII/跨境/未成年闭环 | ❌(开源参照为通用,无内置) |
| **传输** | WS + HTTP 单端口 8765 | 通常 REST 轮询/Webhook(AIGCCanvasFlow:Celery) |
| **定位** | 垂直:中文短视频「发现+学习+复刻」流水线 | 通用:AIGC 生成 IDE |

---

## 4. 关键差异深析

### 4.1 范式:产物树 vs 计算图(最大区别)
- 新架构的节点 = **可重复执行的算子**,图本身就是"程序",用户负责编程(连线)。
- OpenRHTV 的节点 = **一次性创作产物**,图是"创作过程的可视化记录 + 审核单元",Agent 负责"编程",人负责"拍板"。
- 影响:OpenRHTV 用户**门槛更低**(说话即可,不用懂连线),但**自由度更低**(只能在领域流水线内操作);新架构反之。

### 4.2 执行:为什么 OpenRHTV 没用 litegraph
- OpenRHTV 的"执行"不是"跑任意 DAG",而是"对少数几类产物节点调固定生成 API",且需要**领域级韧性**(逐镜取消、成本闸、熔断、锚点参考、time-travel)。这些是 litegraph 默认不给的。
- 反过来,litegraph/ComfyUI 给的"任意节点拓扑执行 + 海量节点生态",OpenRHTV 当前并不需要(Phase 1 只有 5 类节点 + 固定流水线)。

### 4.3 Agent:LangGraph vs LangChain
- 新架构用 LangChain 做"NL→图"(一次性翻译)。
- OpenRHTV 用 LangGraph(带 checkpoint/状态机/subagent),做的是**多轮、带人审、可中断恢复**的编排——更重,但匹配"人在环创作"的需求。

### 4.4 各自的"护城河"无法白嫖
- 迁到新架构能白拿:tldraw/VueFlow 的画布 UX、ComfyUI 节点&模型生态、用户自由连线、类型安全端口。
- 但**带不走**:OpenRHTV 的审核闸、层级约束、锚点级联、境内合规、time-travel、成本/熔断韧性——这些要在新架构上**重新实现**。

---

## 5. 各自适合什么

| 你要的 | 选 OpenRHTV 现状路线 | 选新架构路线 |
|---|---|---|
| 低门槛、说话即创作、强审核与合规 | ✅ | ✗(要补) |
| 垂直短视频流水线(发现+学习+复刻) | ✅ | ✗ |
| 用户自由编排任意 AIGC pipeline | ✗ | ✅ |
| 复用 ComfyUI 海量节点 / 商业模型 | ✗ | ✅ |
| 顶级画布交互体验(平移缩放/连线手感) | 一般(React Flow 够用) | ✅(tldraw 最强) |
| 出海 / 多模态 / 通用生成 IDE | ✗ | ✅ |

---

## 6. 迁移评估与建议:混合演进,不整体替换

整体替换成新架构 = 丢掉 OpenRHTV 已建成的全部领域护栏(审核/合规/锚点/韧性),且把"低门槛 agent 创作"退回"用户连线"——**与产品定位相悖**。建议**分层吸收新架构的优点**:

1. **画布层(低风险,可选)**:React Flow 已满足需求,**短期不必换**。若追求更强交互/手感,可评估 tldraw,但要重写自定义节点 + binding,成本中等且无功能增益(收益主要是体验)。**优先级低。**

2. **执行层(中价值)**:不引入 ComfyUI 全家桶,但可**借鉴其"节点即算子 + provider 抽象"**,把现有固定 provider(Apimart/Doubao/Seedance)收敛到统一 `BaseModel.generate()` 适配器(对齐 AIGCCanvasFlow),为后续接更多模型铺路。**当前队列(lease/retry/熔断/成本闸)是优势,保留。**

3. **可选「Pro/高级模式」(高价值,差异化)**:面向高级创作者,提供一个**真正的 ComfyUI 式子画布**(tldraw image-pipeline 或 litegraph 嵌入),让其自由编排——和现有"低门槛 agent 模式"并存(呼应 RHTV「图片/视频/Agent 三模式」)。这是把新架构当**增量能力**而非替换。

4. **Agent 层(保留)**:LangGraph 的人审/checkpoint 是创作场景的正确选择,**不要退回 LangChain 一次性 NL→图**。可借鉴的是"NL→节点图"的规划能力,用于自动布更复杂的子图。

5. **务必保留(无论怎么演进)**:人在环审核、层级约束、锚点级联、time-travel、境内合规闭环——这些是 OpenRHTV 相对通用 ComfyUI 平台的**核心壁垒**。

> 决策建议:**以 OpenRHTV 现有架构为主干,选择性吸收新架构的「统一模型适配器」和「可选 ComfyUI 式高级子画布」,而非整体迁移。**

---

## 7. 参考

**调研来源**
- RunningHub 官网 / API 文档:runninghub.ai · runninghub.cn · rhtv.ai
- RHTV 报道(官方口径):51allai.com `/posts/2026/05/runninghub-rhtv-canvas-agent-platform/`、aiproducthub.cn、aipuzi.cn
- 开源参照:`github.com/MaLunan/AIGCCanvasFlow`(技术解析见 jishuzhan.net `/article/2052327207922630658`)
- `github.com/tldraw/image-pipeline-template` · tldraw.dev/starter-kits/image-pipeline
- `github.com/Comfy-Org/ComfyUI` · litegraph.js
- 无限画布渲染原理:`github.com/xiaoiver/infinite-canvas-tutorial`(WebGL/WebGPU)

**OpenRHTV 内部**
- [`CANVAS_DESIGN.md`](./CANVAS_DESIGN.md) — 现有画布详设
- [`TOPIC_TO_CREATION_PIPELINE.md`](./TOPIC_TO_CREATION_PIPELINE.md) — Cascade 流水线
- 代码:`frontend/src/store/canvasStore.ts`、`frontend/src/components/Canvas.tsx`、`backend/src/agent/tools/canvas.py`、`backend/src/agent/tools/canvas_persistence/`
