# Pro 高级子画布落地方案 · tldraw + ComfyUI(litegraph)双轨模式

> 在 OpenRHTV(Cascade)现有「低门槛 Agent 模式」之外,**增量**引入一个 ComfyUI 式的「Pro 高级子画布」:用户自己拖拽连线、编排通用可执行计算图,由 ComfyUI(litegraph 内核)+ 队列执行。两模式并存,共享认证/合规/成本/存储。
>
> 关联:[`RHTV_CANVAS_NEW_ARCH_COMPARISON.md`](./RHTV_CANVAS_NEW_ARCH_COMPARISON.md)(对比文档)、[`CANVAS_DESIGN.md`](./CANVAS_DESIGN.md)
>
> **本方案根据用户拍板,覆盖对比文档 §6.2/§6.3 中"不引入 ComfyUI 全栈"的保守口径**:Pro 模式确定为完整 ComfyUI 范式。

---

## 0. 定调(用户拍板的 spec)

1. **画布范式** = 用户连线的**通用可执行计算图**(不是 Agent 搭的产物树)。
2. **谁建图** = **用户拖拽连线**(Agent 仅作可选的 NL→graph 辅助)。
3. **执行** = **ComfyUI(litegraph 内核)+ 队列**。
4. **画布层** = **tldraw**(参照 `tldraw/image-pipeline-template`)。
5. **ComfyUI 部署** = **Provider 抽象,双轨可切换**:
   - `SelfHostedComfyUI`(境内 GPU,**默认**,数据不出境)
   - `RunningHubComfyUI`(境外托管 workflow-as-API,**opt-in**,需二次同意 + 跨境闸)
   - 经 `config.COMFYUI_PROVIDER` 切换。
6. **其他按 §6 建议**:与 Agent 模式双轨并存;复用现有异步队列 / cost_guard / 熔断 / 存储;Agent 框架保留 **LangGraph**;护城河(境内合规、成本闸、锚点级联、time-travel)继续接线进 Pro 模式。

---

## 1. 范围

**做(Pro MVP)**
- 新增 `/pro/:threadId` 路由 + tldraw 画布(用户拖拽连线)。
- ~5 类节点:`LoadImage/Anchor` · `Prompt` · `Model` · `Generate(image)` · `Preview`。
- tldraw 图 → 编译 → ComfyUI prompt(自建)/ workflowId+nodeInfoList(RunningHub)。
- 经现有队列执行(新增 `task_type="comfyui_graph"`),Run 前走 cost_guard 估算 + 确认弹窗。
- 双 provider 抽象,默认 SelfHosted 境内。
- **分析 → 种子可执行图**(核心入口):从爆点拆解分析一键"展开"成一张**完整可执行**的计算图,不改可直接 Run,改了在其上增删(deterministic builder,见 §6)。

**不做(MVP 之后)**
- 端口强类型 + 环检测的完整体验(P2)。
- 视频 / ControlNet / Upscale / img2img 全节点集(P2)。
- Agent NL→graph 自动布图(P3)。
- RunningHub provider 正式开放(P3,先留抽象位)。

**绝不动(护城河,Agent 模式继续独占)**
- 现有 React Flow 产物树画布、人在环审核、层级约束、Cascade 改写流水线——Pro 是**另一条轨**,不替换。

---

## 2. 双轨架构

### 2.0 两模式定位(为什么要两轨)
两个模式服务**同一个用户的不同阶段/不同诉求**,不是重复造轮子:

| | 模式 A · Agent(现有) | 模式 B · Pro(本方案) |
|---|---|---|
| 驱动方 | **AI 驱动**:Director agent 搭建、人在关键点拍板 | **用户驱动**:用户在种子图上主导 |
| 自由度 | 低——只能在 Cascade 领域流水线内走 | **高——可随时增 / 删 / 改任意节点与连线** |
| 体验取向 | 低门槛、快、省心(说话即出片) | **灵活、可精控、所见即所改** |
| 起点 | 空 thread + 一条 URL | **种子图**(从爆点拆解一键展开,§6) |
| 适合 | 不想动手 / 要速度的创作者 | 想精调每一镜、玩花活的进阶创作者 |
| 控制粒度 | 节点级审核(reviewing→confirmed) | 节点 / 连线 / 参数级自由编辑 |

> 关键衔接:**种子图(§6)是从「AI 驱动的产物」降落到「用户可控的可执行图」的桥**。用户不改 = 享受 AI 驱动的省心;想改 = 拿到 Pro 的全部灵活性。两者无缝切换,而非二选一。

```
┌───────────────────────────── 前端(React 19 + Vite) ─────────────────────────────┐
│  模式 A(现有/主):/chat/:threadId                模式 B(新/Pro):/pro/:threadId   │
│  React Flow 产物树 + Zustand                       tldraw 计算图 + Zustand          │
│  Agent 搭建 + 人审(reviewing→confirmed)          用户拖拽连线 + Run               │
└───────────────┬───────────────────────────────────────────┬────────────────────────┘
                │  WebSocket + HTTP(同端口 8765,共享)      │
┌───────────────▼───────────────────────────────────────────▼────────────────────────┐
│                         后端(Python 3.12 asyncio,单进程)                            │
│  LangGraph Director(模式 A)      │   comfyui/ 编译+Provider(模式 B,本方案新增)     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  共享层:auth · cost_guard · circuit_breaker · 异步生成队列(generation_repo) │  │
│  │           · media 存储(media_root/S3)· anchors · versions_repo(time-travel) │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                   │ ComfyUIProvider(抽象)                            │
│                    ┌──────────────┴───────────────┐                                   │
│         SelfHostedComfyUI(境内,默认)      RunningHubComfyUI(境外,opt-in)         │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

执行链路(模式 B):
`用户连线 → tldraw graph JSON → compiler → ComfyUI prompt(或 RunningHub payload) → 入队(comfyui_graph)→ generation_worker claim → cost_guard.check → ComfyUIProvider.submit → poll/progress → 产物落 media → WS 推前端预览`。

ComfyUI 自身负责**图内 DAG 拓扑执行 + 节点级缓存**(litegraph 内核强项);OpenRHTV 队列只在**整图提交粒度**包一层 cost/lease/retry/熔断/合规。

入口链路(模式 B 的主入口,见 §6):
`Agent 模式爆点拆解分析 → 点「展开为计算图」→ seed_builder 把 analysis+rewriteShots+anchors 编成种子图 → tldraw 渲染可编辑图 →(不改直接 Run / 改后 Run)`。

---

## 3. 后端落地

### 3.1 新增包 `backend/src/agent/comfyui/`
```
comfyui/
├── __init__.py
├── provider.py        # ComfyUIProvider ABC + SelfHosted + RunningHub + get_comfyui_provider()
├── compiler.py        # tldraw graph JSON → ComfyUI prompt / RunningHub payload
└── node_registry.py   # Pro 节点类型 → ComfyUI class_type + 端口类型 映射
```

**`provider.py`** —— 对齐现有 `tools/generation.py` 的 `submit()/poll()` + `get_provider()` 范式:
```python
class ComfyUIProvider(ABC):
    @abstractmethod
    async def submit(self, graph: dict, *, user_id: str, run_id: str) -> dict: ...   # → {task_id} | {error}
    @abstractmethod
    async def poll(self, task_id: str) -> dict: ...                                   # → {status, outputs[], error?}

class SelfHostedComfyUIProvider(ComfyUIProvider):
    # POST {COMFYUI_BASE_URL}/prompt  → prompt_id;GET /history/{id};/ws 取进度
    ...
class RunningHubComfyUIProvider(ComfyUIProvider):
    # POST /openapi run(workflowId + nodeInfoList);轮询 Check Task Status/Output
    # 仅当 user 二次同意 + STRICT_CROSS_BORDER_REJECT 校验通过才允许
    ...

def get_comfyui_provider() -> ComfyUIProvider:
    return {"selfhosted": SelfHostedComfyUIProvider,
            "runninghub": RunningHubComfyUIProvider}[config.COMFYUI_PROVIDER]()
```

**`compiler.py`** —— 把 tldraw 图(节点 + 连线)编成执行后端格式:
- self-host:输出 ComfyUI **prompt(API format)**——`{ "<nodeId>": {"class_type": ..., "inputs": {...连线引用...}} }`。
- runninghub:输出 `{ workflowId, nodeInfoList:[{nodeId, fieldName, fieldValue}] }`(对齐 RunningHub Advanced API)。
- 连线 = inputs 引用上游节点输出(`["<srcNodeId>", <outputIndex>]`),与 litegraph 语义一致。

**`node_registry.py`** —— 单一映射真相源(前后端共用一份 schema,MVP 5 类):
| Pro 节点 | self-host ComfyUI class_type | 端口(in→out) |
|---|---|---|
| Prompt | `CLIPTextEncode` | —→text |
| Model | `CheckpointLoaderSimple` | —→model |
| LoadImage/Anchor | `LoadImage`(锚点:从 anchors 表取 url)| —→image |
| Generate(image) | `KSampler`+`VAEDecode`(或 seedream 节点)| model,text,image?→image |
| Preview | `SaveImage` | image→— |

> **合规闸**:`node_registry` 标注每个节点的 provider 归属;RunningHub-only 节点在 SelfHosted 模式下不出现在面板,反之亦然。跨境模型节点受 `STRICT_CROSS_BORDER_REJECT` 拦截。

### 3.2 队列复用(零新表起步)
现有 `canvas_persistence/generation_repo.py` 已支持 `task_type` 参数:
- `claim_pending_tasks(task_type="comfyui_graph")`
- `update_generation_state(...)` / `schedule_generation_retry(...)`

落地:
1. 新增一张轻表 `pro_runs`(或复用 generation 队列,task_type 区分):`run_id, user_id, thread_id, graph_json, provider, status, task_id, cost_est, outputs, error, lease_until, attempt_count`。
2. `workers/generation_worker.py` 的 worker loop 增加分支:claim 到 `comfyui_graph` → `cost_guard.check(user_id, run_id, est)` → `get_comfyui_provider().submit(graph)` → poll → 产物落 media → `update_generation_state`。
3. `circuit_breaker` 包住 ComfyUI endpoint(self-host 宕机/超时熔断);`schedule_generation_retry` 复用指数退避。

### 3.3 config 新增(`backend/src/agent/config.py` + `.env.example`)
```python
COMFYUI_PROVIDER   = os.getenv("COMFYUI_PROVIDER", "selfhosted")   # selfhosted | runninghub
COMFYUI_BASE_URL   = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
RUNNINGHUB_API_KEY = os.getenv("RUNNINGHUB_API_KEY")               # opt-in,境外
RUNNINGHUB_BASE_URL= os.getenv("RUNNINGHUB_BASE_URL", "https://www.runninghub.ai")
PRO_CANVAS_ENABLED = os.getenv("PRO_CANVAS_ENABLED", "0") == "1"   # 灰度开关
```
RunningHub 路径复用现有 `google` provider 的"双轨 + 二次同意 + `STRICT_CROSS_BORDER_REJECT`"合规模式,口径一致。

### 3.4 WS 协议新增(`server.py` 路由 + `frontend/src/types/`)
- `pro_run_submit`(前→后):`{graph, provider?}`
- `pro_run_progress`(后→前):`{run_id, node_id, status, pct}`
- `pro_run_node_done`(后→前):`{run_id, node_id, output_url}`
- `pro_run_done` / `pro_run_failed`

---

## 4. 前端落地

### 4.1 依赖 + 路由
```bash
cd frontend && npm i tldraw   # React 19 + Vite 8 兼容
```
`src/main.tsx` 加 lazy 路由(与现有 AdminX 同模式):
```tsx
const ProCanvas = lazy(() => import("./pro/ProCanvas"));
// <Route path="/pro/:threadId" element={<ProCanvas/>}/>
```
入口:Agent 模式工具栏加「⚡ Pro 画布」按钮跳 `/pro/:threadId`(同 thread,共享 anchors/media)。`PRO_CANVAS_ENABLED` 灰度。

### 4.2 新增 `frontend/src/pro/`(参照 image-pipeline-template,但执行走后端)
```
pro/
├── ProCanvas.tsx          # tldraw 挂载 + 自定义 shape + Run 按钮
├── nodes/                 # NodeShapeUtil + 5 类节点 UI(从 node_registry 派生)
├── connection/            # 连线 shape + binding(端口绑定)
├── ports/                 # 端口类型 + 兼容规则(MVP 先弱校验,P2 强类型)
├── compileGraph.ts        # tldraw shapes → graph JSON(发后端)
└── proExecution.ts        # 发 pro_run_submit + 订阅 progress(不在前端跑 DAG)
```
> **关键**:执行在 ComfyUI 后端,前端**不需要本地 DAG 引擎**——只做"序列化图 + 发送 + 渲染进度/结果"。比纯前端 image-pipeline 更薄。

### 4.3 状态:`frontend/src/store/proCanvasStore.ts`(Zustand,独立于 `canvasStore.ts`)
`nodes / edges / runStatus / nodeResults / costEst`,所有改动过 store(对齐现有 Zustand 受控模式)。复用现有 `useWebSocket` hook 订阅 `pro_run_*`。

### 4.4 Run 前成本确认(护城河接线)
点 Run → 前端先请求 `POST /api/pro/estimate`(后端按图节点数 × 单价估算)→ 弹 cost 确认 modal → 确认后才 `pro_run_submit`。复用现有 cost 看板口径。

---

## 5. 护城河如何接进 Pro 模式

> 原则:**能不削弱 Pro 灵活性的护城河,完整保留甚至增强;会与"用户随时增删改任何内容"冲突的护城河,转形保留其价值,而不是照搬其约束。**

### 5.1 完整保留(甚至增强)
| 护城河 | 在 Pro 模式的接线 |
|---|---|
| **境内合规** ✅ | 默认 SelfHosted 境内;RunningHub 仅 opt-in + 二次同意 + `STRICT_CROSS_BORDER_REJECT`;跨境节点在面板按 provider 过滤 |
| **锚点级联** ✅(增强) | Pro 注册表内置「Load Anchor」节点 → 从 `anchors` 表拉 character/scene 图作 `LoadImage` 输入;种子图跨镜共享同一锚点节点,两模式复用同一锚点资产 |
| **time-travel** ✅ | Pro run 产物经 `versions_repo.snapshot_version` 存版本,可回滚(复用现有逻辑) |
| **成本闸** ✅ | 每次 Run 经 `cost_guard.check(user_id, run_id, est)`,真 run_id 注入;超限拒绝 |
| **熔断/重试** ✅ | ComfyUI endpoint 套 `circuit_breaker` + `schedule_generation_retry` |
| **Agent(LangGraph)** ✅ | P3 增「NL→graph」工具:产出 tldraw graph JSON,用户可编辑再 Run;**不**退回 bare LangChain |

### 5.2 转形保留(保价值,不照搬约束)
> 这两个在 Agent 模式是**强制闸**;在 Pro 模式若强制,会直接违背"用户随时增删改任何内容"。故保留其**意图**、去掉其**强制性**。

| 护城河(Agent 模式形态) | 在 Pro 模式的转形 |
|---|---|
| **人在环审核** ⚠️ 转形<br>(`node_status: reviewing→confirmed`,上游未确认禁建下游) | **不设强制审核闸**——Pro 里「人就是环」:用户直接编辑每个节点 + 显式 **Run 动作** + **Run 前 cost 确认弹窗**就是人审点。审核从"流程闸"变成"用户主导 + 花钱前确认"。(可选:给图加一个非强制的「标记已确认」徽标,纯展示) |
| **层级约束** ⚠️ 转形<br>(领域硬规则 `script→image(character\|scene)→image(grid)`) | **不强制领域层级**——改为通用的**端口类型兼容 + 环检测**(image≠model,P2)。种子图(§6)按合理创作管线**打底**,但用户可自由打破/重连。约束从"领域硬规则"变成"类型安全 + 合理默认"。 |

> **已定**:Pro 提供**可选的**强制审核 / 强制层级,做成 **thread 级开关,默认关**(兑现 Pro 灵活性承诺;团队协作/新手保护时可手动开)。落在 **P2**(见 §7)。
>
> 实现要点:
> - 开关存 thread 配置(如 `pro_threads.enforce_review` / `enforce_hierarchy`,默认 `false`)。
> - `enforce_review=true`:Run 前要求图中节点逐个「标记已确认」才放行(复用 Agent 模式 `node_status` 语义,但落在 Pro 节点上)。
> - `enforce_hierarchy=true`:连线时套用 Agent 模式的 `HIERARCHY` 领域规则(复用 `_validate_hierarchy`),非法连线即时拦截;关时仅端口类型兼容 + 环检测。
> - 默认关 = 两个校验都跳过,用户随意增删改。

---

## 6. 分析 → 种子可执行图(Pro 模式核心入口)

> 用户拍板新增:基于 OpenRHTV 整体,**从当前的爆点拆解分析,点击进入无限画布后,展开一张通用可执行计算图**;用户可在其上修改,**不修改则可直接生成**。

### 6.1 为什么是核心
Pro 画布若冷启动为空白,用户得从零连线(门槛高),且白白丢掉 Agent 模式已产出的**爆款拆解智能**(hook 分类、分场结构、改写文案、锚点)。把分析"编译"成一张**开箱可跑**的种子图,等于:
- **降门槛**:用户进来看到的是已经连好、能直接出片的图,不是空画布。
- **保护城河**:hook / anchor / rewrite 的领域智能被**编译成可运行管线**——Pro 模式因此不是裸 ComfyUI,而是带 OpenRHTV 智能的种子图。
- **两模式数据连续**:同一 thread 的 analysis / anchors / media 跨模式复用。

### 6.2 数据来源(全部已有,无需新采集)
| 来源 | 取自 | 喂给种子图 |
|---|---|---|
| 分场结构 / hook | `CascadeAnalysisContract`(`analyses` 表)| 子管线数量、分镜顺序、Prompt 默认值 |
| 每镜改写文案 | `rewriteShots`(`rewrites` 表)| 每条 `Prompt` 节点的文本 |
| 锚点 | `anchors` 表(character / scene)| `Load Anchor` 节点(跨镜共享) |
| 既有首帧/视频 | rewriteShot 的 `firstFrameUrl/videoUrl` | 已生成的镜可标"命中缓存",避免重复花钱 |

### 6.3 种子图模板(deterministic builder)
每个 `rewriteShot` → 一条子管线;character/scene 锚点节点**跨镜复用**(锚点级联的图形化);末尾可挂 `Compose` 整片:
```
[Load Anchor:character]─┐
                        ├─▶[Prompt: shot.rewriteText]─▶[Generate image 首帧]─▶[Generate video i2v]─▶[Preview]
[Load Anchor:scene]─────┘            (同一 character/scene 锚点节点被多镜共享一份)
        ⋮  每个 shot 一条 ⋮
[shot1.video][shot2.video]…─────────────────────────────────────────────────▶[Compose 整片]─▶[Preview 成片]
```
- **deterministic,不用 LLM**:`seed_builder` 纯按 `node_registry` 模板 + analysis 字段填充,可复现、便宜、快。
- **"不改直接生成"的硬保证**:builder 产出的图必须**编译通过**(`compiler` 校验每个节点必填 inputs 已从 analysis 填默认值);Run 前 `cost_guard` 估算整图成本并弹确认。
- **缓存友好**:已有 firstFrame/video 的镜,对应 Generate 节点标 `cached`(命中已生成产物),只跑缺口节点。

### 6.4 入口与链路
1. Agent 模式分析卡(`ViralAnalysisCard` / `SceneAnalysisCard` / rewrite 区)加按钮「**⚡ 展开为计算图**」。
2. 跳 `/pro/:threadId?seed=analysis:<analysis_id>`。
3. `ProCanvas` 检测 `seed` 参数 → `GET /api/pro/seed?analysis_id=...` → 后端 `seed_builder.build_seed_graph()` 返回 graph JSON → 注入 `proCanvasStore`。
4. 用户:**不改 → 点 Run**(cost 确认 → 整图入队执行);**改 → 在种子图上增删节点(换 Prompt / 加 ControlNet / 删镜)→ Run**。
5. (可选,P3)Pro 跑完产物**回写** Agent 模式画布(首帧/成片),两模式保持一致。

### 6.5 与 NL→graph 的关系
- **种子图 = 分析→图**(确定性,P2,本节):有分析就能一键出可跑图,**这是主入口**。
- **NL→graph = 自然语言→图**(LangGraph,P3,§5 表):用户用一句话在种子图上做增量调整("把第 3 镜换成夜景")。二者叠加:先种子图打底,再 NL 微调。

### 6.6 后端落地
- 新增 `backend/src/agent/comfyui/seed_builder.py`:`build_seed_graph(analysis_id, user_id) -> graph_json`(读 `analyses/rewrites/anchors` → 按 `node_registry` 模板拼图 → 返回 tldraw 兼容 graph JSON)。
- 新增 HTTP `GET /api/pro/seed?analysis_id=...`(`server.py`)。
- 复用 §3 的 `compiler` / 队列 / cost_guard,无新执行路径。

---

## 7. 分阶段落地(每阶段可独立验收)

### P0 · Spike(打通 provider,无 UI)— 1~2 天
- [ ] 起一个 SelfHosted ComfyUI(境内),后端 `SelfHostedComfyUIProvider.submit()` 跑一个 hardcoded prompt → 产物落 media。
- [ ] `RunningHubComfyUIProvider` 用一个已成功跑过的 workflowId round-trip 验证(opt-in 路径)。
- ✅ 验收:两 provider 都能 submit→poll→拿图。

### P1 · MVP(tldraw + 5 节点 + 队列)— 1~1.5 周
- [ ] `comfyui/{provider,compiler,node_registry}.py` + `task_type="comfyui_graph"` 入队 + worker 分支。
- [ ] config 新增 + `.env.example`;WS `pro_run_*` 协议。
- [ ] 前端 `/pro/:threadId` + tldraw + 5 节点 + 连线 + compileGraph + Run + cost modal + 进度/预览。
- [ ] cost_guard / circuit_breaker 接线。
- ✅ 验收:用户在 `/pro` 拖 `Model→Prompt→Generate→Preview`,Run 出图,成本被记账。

### P2 · 增强 + 种子图入口(本阶段战略核心)— 1~2 周
- [ ] **分析 → 种子可执行图**(§6):`seed_builder.py` + `GET /api/pro/seed` + 分析卡「⚡ 展开为计算图」入口;不改可直接 Run。
- [ ] 「Load Anchor」节点 live(锚点级联接入,种子图依赖)。
- [ ] 端口强类型 + 环检测(对齐 image-pipeline `portCompatibility`)。
- [ ] 节点扩展:ControlNet / Upscale / img2img / Video(Seedance 节点)。
- [ ] graph 模板存取(复用 versions / 新表)。
- [ ] 已生成镜的 Generate 节点标 `cached`(避免重复花钱)。
- [ ] **可选强制开关**(thread 级,**默认关**,§5.2):`enforce_review`(Run 前逐节点确认)+ `enforce_hierarchy`(连线套 `HIERARCHY` 规则);默认关 = 用户随意增删改。

### P3 · 智能 + 开放 — 按需
- [ ] LangGraph「NL→graph」自动布图工具。
- [ ] Pro run time-travel 版本 + 节点级缓存呈现。
- [ ] RunningHub provider 正式灰度开放(二次同意 UI 完整)。

---

## 8. 风险与开放问题

| 风险 | 说明 / 缓解 |
|---|---|
| **SelfHosted ComfyUI 算力** | 需境内 GPU;MVP 可单卡 + 队列串行,P2 再扩并发(ComfyUI 自带队列) |
| **tldraw 授权水印** | 默认带「Made with tldraw」水印;商用去水印需买 business license——上线前确认预算 |
| **图编译正确性** | tldraw 图 ↔ ComfyUI prompt 的 inputs 引用易错;`node_registry` 做单一真相源 + 编译单测(对齐现有 pytest/vitest 文化) |
| **两模式认知割裂** | Pro 是高级模式,入口需明确"这是给会连线的人";普通用户留在 Agent 模式 |
| **RunningHub 跨境合规** | 严格走二次同意 + `STRICT_CROSS_BORDER_REJECT`;默认不开,文档/隐私需补 Pro+境外口径 |
| **节点版本漂移** | ComfyUI 自建实例的自定义节点版本需 pin(Dockerfile 锁),否则 prompt 失配 |

---

## 9. 首批文件清单(P1 起手)

**后端(新增)**
- `backend/src/agent/comfyui/__init__.py`
- `backend/src/agent/comfyui/provider.py`
- `backend/src/agent/comfyui/compiler.py`
- `backend/src/agent/comfyui/node_registry.py`
- `backend/src/agent/comfyui/seed_builder.py`(分析→种子图,§6,P2)
- `backend/migrations/<n>_pro_runs.sql`(若用独立表)

**后端(改)**
- `backend/src/agent/config.py`(COMFYUI_* 等)
- `backend/src/agent/workers/generation_worker.py`(comfyui_graph 分支)
- `backend/src/agent/server.py`(pro_run_* WS 路由 + `/api/pro/estimate` + `/api/pro/seed`)
- `.env.example`

**前端(新增)**
- `frontend/src/pro/ProCanvas.tsx` + `nodes/` + `connection/` + `ports/` + `compileGraph.ts` + `proExecution.ts`
- `frontend/src/store/proCanvasStore.ts`
- `frontend/src/types/pro.ts`(WS 消息 + graph schema)

**前端(改)**
- `frontend/src/main.tsx`(`/pro/:threadId` 路由)
- `frontend/package.json`(`tldraw`)
- Agent 模式工具栏加「⚡ Pro 画布」入口;分析卡(`ViralAnalysisCard`/`SceneAnalysisCard`)加「⚡ 展开为计算图」按钮(§6 种子图入口)

---

## 10. 参考
- `tldraw/image-pipeline-template` · tldraw.dev/starter-kits/image-pipeline(节点/端口/连线结构参照)
- `Comfy-Org/ComfyUI` prompt(API format)· litegraph.js
- RunningHub API:`runninghub.ai/runninghub-api-doc-en`(Advanced 调用 + nodeInfoList + Task Status/Output)
- 内部:[`RHTV_CANVAS_NEW_ARCH_COMPARISON.md`](./RHTV_CANVAS_NEW_ARCH_COMPARISON.md) · `tools/generation.py`(provider 范式)· `canvas_persistence/generation_repo.py`(队列)· `cascade/cost_guard.py` · `cascade/circuit_breaker.py`
