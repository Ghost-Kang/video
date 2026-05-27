# 架构审视报告 + PM 分派 — 2026-05-26 (W4D3)

> **触发**:Founder 要求审视项目架构是否合理、是否有可重构优化点
> **执行**:Software Architect agent 阅读 backend `~8k LOC` + frontend `~8k LOC`,产出优先级排序的 refactor 报告
> **PM 分派**:Claude / Codex / Founder 三 owner(Cursor 任务本 cycle 合并给 Codex)

---

## Part 1 · Architect 报告原文

### TL;DR
- **健康**:cascade 核心域(contract → failures → adapter → service)分层清晰;事件单写路径 `events.py` 是正解;Pydantic envelope 锐利;WS/HTTP server 是有意保持的薄传输层;导入无循环。
- **最大风险**:`backend/src/agent/server.py` 是 transport 文件冒充 application — 它同时拥有 auth / 消息分派 / 队列 worker / S3 上传 / HTTP 路由。dispatch loop 或某个慢 `_run_agent` 出 bug,会同时污染 worker、registry、HTTP routes。也是 WS 契约 drift 到 `useWebSocket.ts` 的发生地。
- **第一动作**:抽 WS message-handler registry + 把 generation worker 拎出 `server.py`。这一步单独打通后端可测性 + 解锁 typed WS contract。

### Findings(P0 → P3)

#### P0-1 — `server.py` 是塞在一个文件里的三个模块
**证据**
- WS 分派:`backend/src/agent/server.py:474-676`(13 个 `if msg_type == ...` 分支挤在一个 loop)
- 生成 worker:`server.py:367-468`(单一 `_generation_worker` 同时跑 image / video / composite / recover)
- HTTP 路由:`server.py:690-900`(10 个 endpoint 用 `route_path` 的 if/elif)
- 跨切关注点全局变量:`_ws_registry`, `_worker_started` 在模块顶层(`server.py:35-36`)

**为什么重要**
- 任何一改都动 900 行的文件
- 测试需要同时 fake WS 流 + HTTP reader(`tests/test_server_ws_http.py:1-60`)
- worker 不能脱开 WS 模块单测(强拖 `langgraph` + `deepagents`)
- 新 owner(Codex)无法并行加 handler

**建议拆分草图**
```
agent/transport/
  ws_server.py             # accept loop, auth gate, registry
  ws_handlers.py           # HANDLERS: dict[str, Callable[[Ctx, dict], Awaitable[None]]]
  http_router.py           # tiny route table (method, path) → handler
agent/workers/
  generation_worker.py     # _generation_worker + _process_*_task
  image_pipeline.py        # _process_image_task + _upload_to_s3
  video_pipeline.py
  composite_pipeline.py
agent/transport/context.py # Ctx(user_id, ws, pool, notify)  ← 替代 contextvars+globals
```
handler 形状:`async def handle_execute_node(ctx: WSCtx, msg: ExecuteNodeMsg) -> None`
分派 loop 收敛到 ~30 行:parse → validate type → look up handler → call。

**Effort**:M(1-2 天,纯机械抽取,seam 已被 tests 覆盖)
**不修风险**:Phase 2 协作摩擦 — 第二个后端 owner 上来,每个 PR 都在这里冲突。

---

#### P0-2 — WS 契约重复 3 处,没有 single source of truth
**证据**
- 前端 types:`frontend/src/types/index.ts:42-164`(手写 interface)
- 前端 sender:`frontend/src/hooks/useWebSocket.ts:93-144`(12 个 `sendXxx` 手工拼 payload)
- 后端 reader:`server.py:497-669`(字符串类型 `msg.get(...)` 满天飞,inbound 没 schema 验证 — 对照 HTTP 路径用 Pydantic)

**为什么重要**
`node_type` vs `nodeType` 之类 typo 只有运行时才暴,唯一保护是 `if not isinstance(msg, dict)`。HTTP 用 Pydantic / `HardFailure`,WS 没有。这是前后端协作的最高 velocity tax。

**建议**
1. `agent/transport/ws_messages.py` 用 Pydantic 定义所有入站类型(`AuthMsg`, `UserMessageMsg`, `ExecuteNodeMsg`, ...)+ tagged union `WSInbound = Annotated[Union[...], Field(discriminator="type")]`
2. 在 handler registry(P0-1)里 per-type 验证:`msg_model = WS_HANDLERS[mtype].model.model_validate(raw)`
3. 从同源 Pydantic 模型生成 TS(datamodel-code-generator 或手镜像到 `frontend/src/types/ws.ts`),12 个 `sendXxx` 收敛到 `sendCommand<T extends WSInbound>(cmd: T)`。出站也走 tagged union。
4. 加 `make sync-ws-types` 脚本 — 即使是机械镜像也比两边手改强。

**Effort**:M(Pydantic 半天,前端类型替换半天;**需 founder 决策:codegen vs 手镜像**)
**不修风险**:契约破坏静默地推给 10 人 cohort — 他们看到"请求超时",因为 `server.py:499` 把畸形消息 drop 了。你要花一天 bisect。

---

#### P1-1 — `cascade/storage.py` 把 5 个不相关 DAO 混在一起,每次调用都开关连接
**证据**
- 5 个实体 DAO 同居:analyses / events / rewrites / toprador_cache / creators-aggregate(`storage.py:39-99` schema, `:106-528` ops)
- "开连接、跑一句、关连接" 13×:`grep -c "await _connect()" storage.py` = 13,对应 13 个 `await db.close()`
- `list_creators`(`storage.py:364-435`)做跨表 aggregation = 域逻辑,不是持久层(它知道哪些 event_name 表示"run started"、哪些表示"publish copied")
- retention policy 硬编码:`_FAILURE_RETENTION_EVENTS`(`:286-326`)— 业务规则住在 DAO 里

**为什么重要**
- 每个 event emit 都付 connect+commit+close 代价(Phase 1 10 人看不出,但读 `storage.py` 加新实体的人被迫翻 528 行)
- `list_creators` 的跨表查询属于 `creators_service`,这样能独立测

**建议拆分草图**
```
cascade/persistence/
  db.py                 # _connect, schema bootstrap, retention table-registry
  analyses_repo.py
  events_repo.py        # 调用点最多(6 处),先做这个
  rewrites_repo.py
  toprador_cache_repo.py
cascade/services/
  creators_service.py   # 复合 events_repo + anchors_repo
  retention.py          # retention_sweep
```
连接:open-per-call 保留(SQLite WAL,目前 OK),但抽 `@asynccontextmanager async def session()` 让模板消失。
**关键**:增量拆 — 从 `events_repo.py` 起步(6 处调用)。

**Effort**:M(主要是 move-and-rename;`_connect` 内的 schema bootstrap 是唯一 tricky 点 — 统一到 startup 一次性的 `bootstrap_schema()`)
**不修风险**:Phase 2 加新实体(`anchors_reuses_v2`、`publish_packs`、`niche_briefs`)时,`storage.py` 过 1k 行,变成 merge-conflict 文件。

---

#### P1-2 — `App.tsx` 拥有 4 个不相关关注点;sessions 应该是 store
**证据**
- 会话 state(`App.tsx:71-72, 178-224`)— list / names / localStorage / delete sync
- WS 路由(`App.tsx:103-172`)— 6 个 message-type 分支
- 布局 state(`App.tsx:73-87`)— sidebar/chat open + viewport listener
- 动作 handler(`App.tsx:256-329`)— handleSend / handleReview / handleExecuteNode 等,只是把 `tid` 塞给 `sendXxx`
- handler 内 inline optimistic state(`App.tsx:288-301`)— `useCanvasStore.setState` 直接从 App 调用

**为什么重要**
- 每个 UI feature 都撞这个文件
- 加个新 node action 要改 `App.tsx` + `useWebSocket.ts` + `NodeDetail.tsx` props
- 不渲染整树就没法测 handler 行为

**建议**
1. `frontend/src/store/sessionStore.ts` — 持有 `sessions[]`, `names`, localStorage 同步, `switchSession`, `deleteSession`。通过 WS-store bridge 直接订阅 `session_list`。
2. `frontend/src/store/wsStore.ts`(或 `useWSConnection` + `useWSDispatch` pair)— 持有连接,把 typed inbound 分派到关心的 store。`App.tsx` 的 `onMessage` 变空。
3. `frontend/src/hooks/useNodeActions.ts` — 封装 `handleReview / handleExecuteNode / handleOptimizePrompt`,绑定当前 `tid`。把这个 hook 的返回值整体传给 `NodeDetail`,不再传 6 个独立 callback。
4. `App.tsx` 收敛到 layout shell(Header + Sidebar + Canvas/CardStack + ChatPanel + Detail)— ~100 LOC。

**Effort**:M(3 个 store + 1 个 hook;sessionStore 测试直白)
**不修风险**:每加一个 feature 都拓宽 `App.tsx`。CardStack vs Canvas 已经在 `:362-378` 分叉,该分叉会继续膨胀。

---

#### P1-3 — 生成 worker 是全局 singleton,与 `canvas_tools` contextvar 隐式耦合
**证据**
- `_worker_started` 旗标 + `_start_worker()` 被 auth handler + main() 同时调用(`server.py:463-468, 508, 906`)
- worker 每个 task 都要 `canvas_tools.set_user_id / set_thread_id`,因为 `canvas_tools._db()` 读 `ContextVar`(`tools/canvas.py:22-31`,在 `server.py:212-215, 246, 304, 424` 反复调)
- 一次 worker tick **串行**处理 task;一个 60s 视频轮询会卡所有图片生成(`server.py:367-436`)

**为什么重要**
- 当前设计只在 Phase 1 = 同时只有 1 个活跃用户 时有效
- cohort 里两个 creator 同时点"生成",图片提交就排在 60s 视频轮询后面
- contextvar 模式意味着 worker 代码忘了 `_setup_canvas_context` 会静默写错线程

**建议**(**需 founder 决策**)
- 短期 S 修:per-task 并发上限 `asyncio.Semaphore(N)` + 在一个 tick 内 `asyncio.gather` claimed tasks
- 移除 `ContextVar` 改显式参数:`canvas_repo.load_node(user_id, thread_id, node_id)`。contextvar 在 agent tools 里省字,但烧 worker
- 中期 M 拆分:按 task type 分 worker(`image_worker`, `video_worker`)— 各自轮询自己的 queue 子集

**Effort**:Semaphore + 显式参数 = S;队列拆分 = founder 决策
**不修风险**:第一次两个 creator 同时跑视频,两人都觉得系统卡死。看起来像"性能 bug",其实是队列设计 bug。

---

#### P2-1 — `NodeDetail.tsx` 是误判,不要重构
**证据**
- 786 LOC 中只有 ~350 行是组件:外层 `NodeDetail`(`:16-114`)、`NodeStatusToggle`(`:116-134`)、`MediaPanel`(`:136-267`)、`ResultView`(`:269-348`)、`mdComponents`(`:350-366`)
- 行 368-786 是一个 `S` 内联样式对象 — 故意的设计
- 4 部分内聚:都按 `node.type` 和 `node.asset_status` 分支

**为什么重要** — **don't-refactor 信号**
拆开要么复制 `S`,要么发明共享样式模块。样式 pattern 没问题,只是体量看着吓人。

**建议**:留着。可选:抽 `mediaNodeStyles.ts`(只抽 `S` 对象),让文件显示 ~350 LOC。**不要**把 3 个内部组件拆文件 — 它们只在这里用且共用 `S`。

**Effort**:S(10 分钟)或跳过
**不修风险**:无

---

#### P2-2 — Canvas node model 是 BE/FE 间唯一没共享的契约
**证据**
- 后端 node:`tools/canvas.py:47-63`(SQLite schema)+ `:96-109`(`_row_to_node`)
- 前端 node:`frontend/src/types/index.ts:16-30`(手写 `CanvasNode`)
- cascade contract **已**镜像:`backend/src/agent/cascade/contract.py` ↔ `frontend/src/types/cascade.ts`(好!)
- 字段 drift 风险:后端有 `feedback`, `generation_status`, `generation_task_id`, `generation_error` — 前端没建模

**为什么重要**
canvas/node 域比 cascade contract 在 UI 里还核心,却是唯一没共享 shape 的。加字段要改 4 处文件且无编译保护。

**建议**
- `cascade/canvas_contract.py` 定义 Pydantic `CanvasNode` / `CanvasEdge` / `CanvasState`,`_row_to_node` 返回模型(或 `.model_dump()`)
- 镜像到 `frontend/src/types/canvas.ts`,挨着 `cascade.ts`
- 同套镜像纪律(codegen 或手镜像同进 `make sync-types`)

**Effort**:S
**不修风险**:静默 drift;后端已发 `feedback` 和 `image_gen_provider` 但前端 `CanvasNode` 只声明了 `image_gen_provider`。

---

#### P3-1 — `cost_cap.py` (12 LOC) + `cost_guard.py` (94 LOC) 重叠;storage 知道事件名
**证据**
- `cost_cap.py:1-12` 定 `predict_rewrite_cost`;`cost_guard.py` 出口 `PREDICT_REWRITE_CNY`
- `storage.sum_generation_cost` 硬编码 `event_name = 'generation_cost'`(`storage.py:335`);`list_creators` 硬编码 4 个事件名(`:398-424`)

**为什么重要**
事件名字符串在 `events.py`(canonical `ALLOWED_EVENTS`)、`storage.py`(查询)、`analysis_service.py`(emit)三处重复。一个 typo 就静默丢数据。

**建议**:`cascade/event_names.py` StrEnum,全 import。可选合并 `cost_cap.py` 入 `cost_guard.py`。
**Effort**:S
**不修风险**:外观问题,直到有人拼错 `script_rewriten`。

---

#### P3-2 — `useWebSocket._send` 在每次发送时重 flush pending
**证据**:`useWebSocket.ts:79-91` — 每个 `_send` 循环 `pendingRef.current` 后再发新 payload。`onopen` 也做同样事(`:40-46`)。

**为什么重要**
断线时入队 m1,再断线时入队 m2 → 第二条仍不发(OPEN check 还 false)。一旦 OPEN,下一个 send 全 flush — 但顺序可能跟 `onopen` 的 replay 在重连 race 时交错。低风险但真实 correctness wart。

**建议**:单点 flush 放 `onopen`;`_send` 要么现发(OPEN),要么 append。删掉 double-flush。

**Effort**:S(10 行)
**不修风险**:重连罕见乱序 — 10 人 cohort 不太会遇到。

---

### 健康部分(不要碰)
- **Cascade 核心域已分层好**:`contract.py` + `failures.py` + `adapter.py` + `analysis_service.py` 是教科书级 anti-corruption-layer for Toprador upstream。**不要动**。
- **`events.py` 单一验证写路径**(`events.py:78-103`):validation + per-run 单调时间戳 + asyncio lock。真域层思维,加 `canvas_events` 时复用这个 pattern。
- **Cascade contract 镜像到 TS**(`contract.py` ↔ `types/cascade.ts`):对的 pattern;canvas(P2-2)和 WS(P0-2)都按这个复制。
- **Failure envelope**(`HardFailure` + `RecoveryAction`):结构化错误 + 用户可见 recovery action 是对的域建模。**新代码不要用 generic `Exception` 稀释它**。
- **导入无循环**:`grep` 显示 `contract → failures → adapter → service → server` 流向干净,无 module-init 时循环 dance。**重构时不能破坏这个**。

### Out of scope / Followups
- **生成 worker 扩展策略**(founder 决策):单 SQLite-queue + asyncio worker 在 Phase 1 是对的。Phase 2(>10 concurrent users)要么按 task type 拆 worker,要么换真队列(Redis / Postgres LISTEN)。**别预建**;记下触发条件("worker tick > 5s 持续 → 拆")。
- **agent tool 层**:`tools/canvas.py`(725 LOC)不在 scope 但有同 `storage.py` 的 DAO/domain 混合。下次动它时一起拆。
- **`fixtures/baomamFushi001`** 在 `canvasStore.ts:7,49-52,113-115` 作 default state import — 是真故事,不是 bug,但 production canvas store 不该带 fixture 数据。出 phase 1 内测后清理。
- **`canvas.db` vs `messages.db`**:两个 SQLite 文件,连接层不同(`tools/canvas.py:21` 用 sync `sqlite3`,cascade 用 `aiosqlite`)。今天不是 bug;想 cross-DB join 时会咬。

---

## Part 2 · PM 分派(W4D3 cycle)

> **本 cycle 简化为 3 owner**:Claude / Codex / Founder。
> **Cursor 任务本 cycle 全部合并给 Codex**(founder 指示)。
> **预警**:Codex 容量已超载(5 task) — 见 Decision-3 砍件请求。

### Owner: Claude(我)

#### Claude-A · P0-1 拆 `server.py`
- 范围:`backend/src/agent/server.py`(916 LOC)
- 目标结构:
  ```
  agent/transport/{ws_server, ws_handlers, http_router, context}.py
  agent/workers/{generation_worker, image_pipeline, video_pipeline, composite_pipeline}.py
  ```
- handler 形状:`async def handle_execute_node(ctx: WSCtx, msg: ExecuteNodeMsg) -> None`
- 验收:`server.py` < 100 LOC(只剩 entry + glue);`tests/test_server_ws_http.py` 全绿;无新增 import 循环
- 依赖:无 — 立即开工
- Effort:M(1-2 天)

#### Claude-B · P0-2 后端 Pydantic WS 契约
- 范围:新增 `agent/transport/ws_messages.py`
- 内容:全部入站类型 Pydantic 模型 + `WSInbound = Annotated[Union[...], Field(discriminator="type")]`
- 接入:Claude-A 的 handler registry 加 per-type `model_validate`
- 验收:畸形消息不再 silently drop,返回结构化错误;现有 e2e + smoke 全绿
- 依赖:Claude-A 完成
- Effort:M(1 天)

---

### Owner: Codex(本 cycle 顶 Cursor 那份)

> **以下 5 个任务彼此独立(除 Codex-D 等 Claude-B),可以并行**。建议优先级:E → F → C → D → G。

#### Codex-C · P1-2 `App.tsx` 拆 store(原 Cursor 任务)
- 范围:`frontend/src/App.tsx`(404 LOC)→ 拆出
  - `frontend/src/store/sessionStore.ts`
  - `frontend/src/store/wsStore.ts`
  - `frontend/src/hooks/useNodeActions.ts`
- 验收:`App.tsx` ~100 LOC layout shell;`NodeDetail` 接收 `useNodeActions()` 返回的对象,不再传 6 个独立 callback;Playwright 12 个 smoke 全绿;`sessionStore` 加单测
- 依赖:无
- Effort:M

#### Codex-D · P0-2 前端 WS 类型镜像(原 Cursor 任务)
- 范围:新增 `frontend/src/types/ws.ts`(镜像 Claude-B 的 Pydantic 模型)
- 重写:`useWebSocket.ts` 的 12 个 `sendXxx` → `sendCommand<T extends WSInbound>(cmd: T)`
- 验收:`grep -c "sendXxx" useWebSocket.ts` 收敛;类型错配会 tsc 编译错;smoke 全绿
- 依赖:**等 Claude-B 出 Pydantic 模型**
- Effort:S(半天,Claude-B 之后)

#### Codex-E · P1-1 `cascade/storage.py` 增量拆分 ✅ `95bf549`
- 范围:`backend/src/agent/cascade/storage.py`(528 LOC)→
  ```
  cascade/persistence/{db, events_repo, analyses_repo, rewrites_repo, toprador_cache_repo}.py
  cascade/services/{creators_service, retention}.py
  ```
- 顺序:**先做 `events_repo.py`**(调用点最多,6 处)
- 验收:`storage.py` 收敛为 re-export shim(向后兼容);所有调用点无须改;`bootstrap_schema()` startup 一次性调用
- 依赖:无
- Effort:M

#### Codex-F · P2-2 Canvas node 跨端 contract ✅ `a0da68c`
- 范围:新增 `backend/src/agent/cascade/canvas_contract.py` + `frontend/src/types/canvas.ts`
- 内容:Pydantic 定义 `CanvasNode` / `CanvasEdge` / `CanvasState`,镜像到 TS
- 接入:`tools/canvas.py:_row_to_node` 返回模型;前端 `CanvasNode` 补齐 `feedback / generation_status / generation_task_id / generation_error`
- 依赖:无
- Effort:S

#### Codex-G · P3-1 事件名 StrEnum(候选砍件) ✅ `9433040`
- 范围:`cascade/event_names.py` StrEnum;替换 `events.py` / `storage.py` / `analysis_service.py` 的字符串字面量
- 验收:`grep "event_name = '"` 在 cascade 里返回 0
- 依赖:无
- Effort:S
- **如果 Codex 超载,本 cycle 砍掉,留下 cycle**

---

### Owner: Founder(决策点,本 cycle 必须回)

#### Decision-1 · WS 类型镜像方式 → **B(codegen)** [2026-05-26]
- **决策**:`datamodel-code-generator` + `make sync-ws-types`
- **影响 task**:Claude-B 在写 Pydantic 时即开 codegen pipeline;Codex-D 消费 codegen 输出;Codex-F (canvas contract) 同走 codegen
- **执行**:Claude-B 一并设置 `make sync-ws-types`(Pydantic → TS)

#### Decision-2 · 生成 worker 拆分策略 → **立刻拆**(Update 2026-05-26)
- **决策**:不挂触发条件,本 cycle 直接按 task type 拆 worker
  - `image_worker`:轮询 image 类型 pending
  - `video_worker`:轮询 video 类型 pending
  - `composite_worker`:轮询 composite 类型 pending
  - 每个 worker 独立 `asyncio.Task`,互不阻塞
- **执行影响 Claude-A**:
  - `agent/workers/generation_worker.py` 改为 orchestrator,启动 3 个 worker task
  - `claim_pending_tasks` 加 `task_type` filter(canvas_tools 接口微改)
  - Semaphore 在 image_worker 内做(image 多 + 快,需控并发);video/composite 单并发(慢任务自然串行)
- **ContextVar 移除**仍走 **Claude-A2** 独立 commit(scope 太大,不绑入 Claude-A)

#### Decision-3 · Codex 容量超载 → **不动 (5 task 全做)** [2026-05-26]
- **决策**:Codex C/D/E/F/G 本 cycle 全部交付
- **风险**:G 是 S 但 C 是 M;若 cycle 末交不齐,优先级 C > E > F > D > G
- **PM 跟进**:cycle 中段 checkin,看 Codex 进度;必要时 founder 重新决策延期项

---

## Part 3 · 依赖图

```
Claude   A (server.py 拆) ──→ B (Pydantic WS)
                                     │
Codex    C (App.tsx 拆) ─────[独立]
         D (前端 WS 类型) ←──── 阻塞 B 完成
         E (storage 拆) ─────[独立, 先做 events_repo]
         F (canvas contract) ─[独立]
         G (StrEnum) ─────────[独立, 候砍]

Founder  Decision-1/2/3 ────[必须本 cycle 给]
```

**最早可启动**:Codex-E / Codex-F / Codex-C / Claude-A 完全独立,可并行立即开工。
**串行链**:Claude-A → Claude-B → Codex-D。

---

## Part 4 · Risk Register

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| Claude-A 拆出新 import 循环 | 低 | 中 | 完成后 `python -c "import agent.server"` + 全 test 跑一遍 |
| Codex-C 拆 store 时打破 5 个 Playwright smoke | 中 | 中 | 验收必须含 smoke 全绿 |
| Codex-D 等 Claude-B 阻塞,cycle 内来不及 | 中 | 低 | Claude-B 完成即同步通知;前端类型可先 stub `ws.ts` 跑通流水线 |
| Codex 容量超载漏交付 F 或 E | 高 | 中 | 必砍 G;F 优先于 E(F 是 S, E 是 M) |
| Founder Decision-2 拖延导致 P1-3 短期修没合 | 中 | 高(cohort 体验) | 短期修不依赖 L 决策,可先合;Decision-2 只决策 L 部分 |

---

## Part 5 · 不动清单(Architect 标记)

1. `cascade/contract.py` + `failures.py` + `adapter.py` + `analysis_service.py` — Toprador ACL,教科书级,**不许动**
2. `events.py` 验证写路径 — 加新事件流时**复用这个 pattern**,不要发明新的
3. `cascade` ↔ `types/cascade.ts` 镜像 — 是 Codex-D/F 的模板,**别意外破坏**
4. `HardFailure` + `RecoveryAction` — 新代码继续用,**别用 generic Exception 稀释**
5. 模块导入无循环 — 重构前后都 `grep`,**红线**
6. `NodeDetail.tsx`(786 LOC)— **don't-refactor 信号**,不要被尺寸吓到

---

> **生成时间**:2026-05-26 W4D3
> **架构师**:Software Architect agent
> **PM**:Claude
> **追踪**:本 cycle 完成后 git log + status 复盘各 task 完成度
