# Phase 1 + Phase 2 统一架构设计 — 端到端创作流水线

**创建**: 2026-05-31
**作者**: 架构师 (Backend Architect, Opus 4.8)
**类型**: 后端 / 系统架构 (与暖色科技视觉无关 — 视觉见 `warm_tech_design_system_2026-05-31.md`)
**继承基线**:
- [PHASED_PLAN.md](../PHASED_PLAN.md) — 四阶段 + Gate (Phase 2 = 30 人 Beta 产品化)
- [phase1_retro_handoff_2026-05-31.md](phase1_retro_handoff_2026-05-31.md) — Phase 1 复盘 + 8 条工程铁律
- [architecture_comms_review_2026-05-29.md](architecture_comms_review_2026-05-29.md) — W5D4 通讯加固 P0-A/B/C

> 本文是 **Phase 1 → Phase 2 统一架构**:把 `分析 → 改写 → 生成 → 发布` 设计成一条健壮、可校验、可观测、可断点续跑的流水线。所有断言均经 Read/Grep/Bash 对真实代码核验;路径与行号以本文为准(`CLAUDE.md` 与首版任务书的若干路径不准,已在 §10 列出更正)。

---

## 0. TL;DR(给 Founder / 下游实现 agent 的一段话)

Phase 1 已经把这条流水线的 **每一段单独建好且加固过**:分析 leg(doubao_direct 视觉单发)生产中跑通且对齐 toprador 维度;改写 leg 代码完整但被双开关暂挂(前端 `REWRITE_ENABLED=false` + 后端默认 fixture);生成 leg 是全仓最成熟的子系统(异步队列 + 租约 + 指数退避 + 重启恢复);发布 leg 代码齐全但未接入 UI。**问题不在"每段能不能跑",而在四段之间没有一个统一的领域模型把它们串成一条可校验、可重连、可观测的流水线** —— 这正是 Phase 2 的核心架构工作。

本文给出 7 块设计:① 统一 **CreationRun** 领域模型 + 四个字段级可校验的 handoff 契约;② 把 W5D4 通讯加固延展到长跑生成的 **慢任务架构**(job model / 并发 / 超时 / 重试 / 断点续跑 / boot 对账);③ 每 leg 的 **失败/恢复矩阵**(失败有下一步 100%,best-effort vs 硬阻断边界);④ **持久化健壮性**(DB 路径已修但有一个被忽略的第二库隐患 + 正式收口);⑤ **凭证轮换 + secrets 管理机制**;⑥ **Phase1→Phase2 衔接**(继承/加固/迁移顺序,不回退 5 同源 bug);⑦ **可观测性**(对接 P2-10 的 25 事件 + 成本计量挂钩)。

**最关键的三条架构判断**:
1. **不要重构,要延展。** W5D4 的三件套(实时注册表 / run_lifecycle 持久化 / 帧缓冲重放)是资产,慢生成应复用同一范式(铁律④),而不是另起炉灶。
2. **run_lifecycle 表只为 20-50s 的 agent turn 设计,不适配慢生成。** 慢生成有自己一套 `canvas_nodes.generation_*` 状态机 + 租约。Phase 2 必须新增一层 **JobProgress 投影**,把两套生命周期统一成"一次创作 run 的可重连进度",否则会重蹈"卡 95%"覆辙。
3. **成本是最大裸奔点。** 分析 + 改写有 `cost_guard`,但生成 leg 零成本护栏(Seedance 按秒、图片按张),30 人 Beta 会真金白银失控。把生成纳入统一 cost_guard 是 P2 的硬 Gate 项。

---

## 1. 统一数据 / 状态模型

### 1.1 领域模型:CreationRun 是流水线的聚合根

当前四个 leg 各有各的存储,没有一个把它们绑成"一次创作":

| Leg | 当前权威存储 | 主键 | 生命周期记录 |
|-----|-------------|------|-------------|
| 分析 | `analyses` 表 (`persistence/db.py`) | `analysis_id = SHA256(user_id\0source_url)[:24]` | `run_lifecycle` 表 (per-thread) |
| 改写 | `rewrites` 表 | `rewrite_id` | 无独立守卫 |
| 生成 | `canvas_nodes.generation_*` 列 (`canvas_persistence/db.py`) | `(user_id, thread_id, node_id)` | 节点内 `generation_status` + lease |
| 发布 | 无服务端产物 (仅 `events` 表打点 `publish_pack_copied`) | — | — |
| 会话 | `session_results` (per-thread → 最新 analysis/rewrite 指针) | `(user_id, thread_id)` | — |

**设计:引入 `CreationRun` 作为聚合根**,以 `thread_id` 为天然连接键(分析/改写/生成/会话全部已按 thread 组织)。不新建大表,而是用 **一张轻量投影表 `creation_run`** 把已有的散落主键聚合起来,作为"一次创作"的权威索引。

```text
CreationRun (聚合根, 1 thread = 1 creation run)
├── thread_id        (PK, 已有于 run_lifecycle / session_results / canvas_nodes)
├── user_id
├── stage            枚举: analyzing | analyzed | rewriting | rewritten
│                          | generating | generated | publishable | published
├── analysis_id      → analyses.analysis_id        (分析 leg 产物指针)
├── rewrite_id       → rewrites.rewrite_id          (改写 leg 产物指针)
├── shot_node_ids[]  → canvas_nodes.node_id 列表    (生成 leg 产物指针)
├── publish_pack_id  → publish_packs.id (Phase2 新建)(发布 leg 产物指针)
├── pipeline_revision_analysis  = ANALYSIS_PIPELINE_REVISION (=3, contract.py:28)
├── pipeline_revision_rewrite   = REWRITE_PIPELINE_REVISION  (P2 新建, 见 §1.4)
├── created_at / updated_at
```

`stage` 是 **派生 + 写穿透** 的:每个 leg 完成时把 `creation_run.stage` 推进并 upsert(类似 `session_results` 已有的 upsert 模式 — `db.py:132` session_results 即是先例)。这给了前端结果页一个权威的"我这次创作走到哪了"的单一真相源,替代当前靠 `session_results` 指针 + `run_lifecycle` 状态拼凑。

> **铁律④对齐**:`creation_run` 是持久化真相,任何 stage 推进推送走 `notify.send_to_user`(实时注册表),绝不发往启动时捕获的 ws/thread。

### 1.2 端到端流水线图(ASCII)

```text
                          一次 CreationRun (thread_id 为聚合键)
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                                                                                │
  │  [URL 入口]                                                                    │
  │   WS execute / HTTP /analysis/shallow                                          │
  │       │                                                                        │
  │       ▼                                                                        │
  │  ┌─────────────┐  AnalysisOutput   ┌─────────────┐  RewriteOutput             │
  │  │  分析 LEG   │ ───契约 C1──────▶ │  改写 LEG   │ ───契约 C2──────┐          │
  │  │ doubao_direct│  CascadeAnalysis  │  llm rewrite │  RewriteResult  │          │
  │  │ 视觉单发     │  Contract (rev=3) │ (REWRITE_    │  (shots 3-5)    │          │
  │  │ 同步 20-50s  │                   │  ENABLED)    │                 │          │
  │  └──────┬──────┘                   └─────────────┘                 │          │
  │         │ best-effort                                              ▼          │
  │         │ _attach_scene_clips                          ┌────────────────────┐ │
  │         ▼ (clip → /media)                              │     生成 LEG       │ │
  │  ┌─────────────┐                                       │  慢任务队列        │ │
  │  │ analyses 表 │                                       │  enqueue → worker  │ │
  │  │ (永久缓存)  │   ShotPrompt 契约 C3 ◀────桥接(P2新建)│  image/video/comp  │ │
  │  └─────────────┘   (analysis/rewrite → image-node)     │  租约+退避+恢复     │ │
  │                                                        └─────────┬──────────┘ │
  │                                                                  │ 产物→S3    │
  │                                                                  ▼            │
  │                                                        ┌────────────────────┐ │
  │                                                        │     发布 LEG       │ │
  │                                  PublishInput 契约 C4 ▶│  buildPublishPack  │ │
  │                                  (标题/标签/脚本/镜头图)│  纯前端 + 打点      │ │
  │                                                        └────────────────────┘ │
  │                                                                                │
  └──────────────────────────────────────────────────────────────────────────────┘

  贯穿层 (每段都挂):
    通讯  notify.send_to_user (实时注册表, 铁律④)  ── 进度/结果/失败帧
    生命周期  run_lifecycle (agent turn) + canvas_nodes.generation_* (慢任务)
              + creation_run (聚合 stage 投影, P2 新建)
    成本   cost_guard (分析✓ 改写✓ 生成✗→P2必补)
    可观测  events 表 (P2-10: 25 事件) + trace_id (P2 透传)
    持久化  cascade.db (analyses/rewrites/events/run_lifecycle/session_results)
            + canvas.db (canvas_nodes/edges)  ── 双库, 均 WAL, §4
```

### 1.3 Handoff 契约(字段级 / 可校验 / 向后兼容)

四段之间的"交接"必须是显式、字段级、Pydantic/TS 双向可校验的契约。下表给出每段的 **输出 → 下一段输入** 映射。**C1/C2 已存在并稳定**(`contract.py`);**C3 是 Phase 2 必须新建的桥接**(当前分析不自动建镜头节点 — 这是 P1-4/P2-1 缺口);**C4 已存在于前端 `buildPublishPack.ts` 但未接数据**。

#### 契约 C1 — 分析输出 → 改写输入 (`AnalysisOutput`)

来源:`CascadeAnalysisContract` (contract.py)。改写 leg 已消费它(`rewrite.py` 注入 `{CONTRACT_JSON}`)。

| 字段 | 类型 | 必填 | 改写侧消费 | 向后兼容策略 |
|------|------|:---:|-----------|-------------|
| `schema_version` | str ("1.0") | ✓ | 硬校验 | 升版必走 adapter `normalize` 兜底 |
| `pipeline_revision` | int (=3) | ✓ | 缓存命中判据 | 缺失/旧值 → 视为 miss 重生(铁律①) |
| `analysis_id` | str (SHA256 派生) | ✓ | rewrite 缓存键的一部分 | 决定性派生,幂等 |
| `source_url` / `platform` | str / enum | ✓ | 标题回退来源 | — |
| `viral_analysis` (10 维) | object | ✓ | `replicable_formula`/hook 注入改写 prompt | 缺维 → adapter W2 中文兜底填充 |
| `scenes[]` (16+ 维, 3-12 幕) | array | ✓ | 改写按幕重写 dialogue/visual | pad 到≥3 (W18) / 截≤12 (W3) / 排序 (W5) |
| `scenes[].clip_url` / `clip_poster_url` | str? | ✗ | 发布包镜头图候选 | **best-effort**,null 时降级 first_frame_url |
| `confidence` | float [0,1] | ✓ | 低置信度 UI 降权 | 缺失 → 启发式兜底 (W7/W11) |
| `cost_cny` | float | ✓ | 累加进 run cost | 缺失 → W8 |

#### 契约 C2 — 改写输出 → 生成输入 (`RewriteOutput`)

来源:`RewriteResult` (rewrite.py, `extra='forbid'`,QA 字段白名单已过滤)。

| 字段 | 类型 | 必填 | 生成侧消费 | 兼容策略 |
|------|------|:---:|-----------|---------|
| `rewrite_id` | str | ✓ | creation_run 指针 | — |
| `script_markdown` | str (80-600 字) | ✓ | 发布包脚本正文 | 超长/含 scrub → confidence≤0.4 |
| `shots[]` (3-5) | array | ✓ | **每 shot → 一个 image 生成节点**(C3 桥接) | min 3 max 5 强校验 |
| `shots[].dialogue` | str | ✓ | 标题候选来源 + SRT 字幕 (P2-7) | scrub `_FORBIDDEN_SUBS` |
| `shots[].visual` | str | ✓ | **image prompt 主体**(C3) | scrub |
| `confidence` | float [0,1] | ✓ | 低置信度提示重写 | 硬约束严,需真跑标定 |
| `cost_cny` | float | ✓ | 累加 run cost | 定价当前硬编码 Gemini,切 doubao 需改 |

#### 契约 C3 — 生成输入 (`ShotPrompt`) ★ Phase 2 必须新建的桥接

**这是当前最大的架构缺口**:分析/改写产物到 `canvas_nodes` image-node 之间没有桥。`process_image_task` 期待节点已有 prompt,但没有任何代码把 `scenes[].visual` / `shots[].visual` 写成镜头节点。设计一个纯函数 `build_shot_prompts(analysis, rewrite) -> list[ShotPrompt]`:

| 字段 | 类型 | 必填 | 来源 | 校验 |
|------|------|:---:|------|------|
| `node_id` | str | ✓ | 派生 `{thread_id}:shot:{i}` | 决定性,幂等 enqueue |
| `shot_no` | str | ✓ | shot 序号 | 1..5 |
| `image_prompt` | str | ✓ | `rewrite.shots[i].visual`,无改写时回退 `analysis.scenes[i].visual_content` | 非空,scrub 禁词 |
| `anchor_refs[]` | str[] | ✗ | 角色/场景锚点引用 (P1-6/P2-2) | 可选,best-effort |
| `image_gen_provider` | enum | ✓ | `IMAGE_GEN_PROVIDER` 默认 google | **合规审查点**(见 §5/铁律⑦) |
| `predicted_cost_cny` | float | ✓ | `PREDICT_SHOT_IMAGE_CNY=1.5` | **进 cost_guard**(P2 必补) |

> 桥接是 **显式人类确认门**(PHASED_PLAN §1「草稿 → 用户确认 → 生成」),不是分析完自动 enqueue 烧钱。前端"生成草稿图"按钮调 `build_shot_prompts` → 批量 enqueue。

#### 契约 C4 — 发布输入 (`PublishInput`)

来源:前端 `buildPublishPack.ts`(已存在,7 单测)。

| 字段 | 类型 | 必填 | 来源 | 当前缺口 |
|------|------|:---:|------|---------|
| `titles[]` (≤3) | str[] | ✓ | 改写 `shots[].dialogue`,回退源片 hook/climax | 改写暂挂 → 只能回退源片 |
| `tags[]` (≤8) | str[] | ✓ | 当前硬编码 niche 标签 | **niche 已砍**(929cb21),需改从 theme/用户自填 |
| `script` | str | ✓ | 改写 `script_markdown` | 需先 `scrubUiForbidden`(当前只 stripHookCode) |
| `shotImages[]` | {url}[] | ✗ | 镜头节点 S3 url + 逐幕 clip /media url | 当前恒传空 → "镜头 N: 待补充" 空壳 |

### 1.4 改写侧的版本守卫(独立于 ANALYSIS_PIPELINE_REVISION)★ 必修

**铁律①只守 analysis 永久缓存,对 rewrite 完全无效。** `rewrites` 24h 缓存(`rewrite_service.py:75-80`,`load_recent_rewrite` 键 = `analysis_id+niche+user_id+since`)无任何版本号。切 fixture→llm 或改 rewrite prompt 后,24h 内旧 fixture 结果被当缓存返回 —— 这是"分析缓存版本守卫"那个坑在改写侧的精确翻版。

**设计**:新增 `REWRITE_PIPELINE_REVISION`(放 `rewrite.py` 模块顶,与 `ANALYSIS_PIPELINE_REVISION` 对称),写进 `rewrites` 表新增列 `pipeline_revision`,`load_recent_rewrite` 查询追加 `AND pipeline_revision = ?`。改任一 rewrite prompt / 切 upstream / 改 doubao 模型 → bump 它。**解封改写时(REWRITE_ENABLED=true)同时 bump 它**,否则首批用户必看到旧 fixture 套娃("还是老样子")。

---

## 2. 慢任务架构(把 W5D4 加固延展到长跑生成)

### 2.1 现状底座(已就位,无需重写)

生成 worker 已是全仓最成熟的子系统(`generation_worker.py` + `generation_repo.py`,自 2026-05-28 冻结):

- **3 个独立常驻 task**:image `Semaphore(5)` / video `Semaphore(2)` / composite 串行 1,按 `type` 在 SQL 层过滤认领(避免 60s 视频卡死图片)。
- **状态机**:`idle→pending→submitted→polling→done/failed`,`claim_pending_tasks` 把 pending→submitted + `attempt_count+1` + 300s lease。
- **指数退避**:`schedule_generation_retry`,base 15s,cap 300s,`GENERATION_MAX_ATTEMPTS=3`。
- **重启恢复**:`recover_generation_tasks` 捞 lease 过期的 submitted/polling 续轮询;Google 内存 task 重启丢 → 特判重入队 pending。
- **通讯**:`notify_user → send_to_user`(实时注册表,铁律④✓);worker 全程显式传 `user_id/thread_id`(不依赖 ContextVar,跨用户后台 task 安全)。

### 2.2 三个必须正面回答的延展问题

W5D4 的三件套是为 **20-50s 的 agent turn** 设计的;慢生成(视频 poll 上限 900s)从两个角度压测它。

#### 问题 A:run_lifecycle ≠ 慢任务生命周期(割裂)

`run_lifecycle` 表 (`run_state.py`) 只覆盖 agent run:`RUN_TURN_TIMEOUT_S=180`,`_resolve_run_status`(ws_handlers.py:129)把 running 超 210s 判 `stale`。**慢生成真实耗时可超 210s → 会被误判 stale,或反过来真挂死的任务在 210s 内一直显 running。** 慢生成有自己一套 `canvas_nodes.generation_*`(submitted/polling/done/failed + lease),与 run_lifecycle 完全割裂。

**设计:JobProgress 投影层(把 P0-B 思路扩展到 worker)。** 不合并两套状态机(它们职责不同),而是在 `get_session_state` / reconnect 时,**额外读 canvas_nodes 的 generation 状态并投影成可重连进度**。给 `creation_run.stage` 增加 `generating` 态;前端结果页订阅的是 `creation_run` 的聚合进度,而非裸 run_lifecycle。这样:

```text
  reconnect / get_session_state
        │
        ├── run_state.load(thread_id)          → agent turn 状态 (分析/改写)
        ├── canvas generation_state 聚合查询    → 慢生成进度 (N 个 shot 节点 done/total)
        └── 合成 creation_run.stage + 进度百分比 → 单一权威进度给前端 replay
```

> 这正是防"卡 95%"同构风险的关键:断线期间 worker 完成的进度帧目前只有 `notify_user → canvas_updated` 实时推送,**没有 session_state 级 replay**。JobProgress 投影给 reconnect 补上这条 replay,与 P0-C(前端 pendingByThread 缓冲重放)互补。

#### 问题 B:单事件循环 + 3 常驻 worker 的并发反压(Phase 2 头号脆弱点)

WS 推送、HTTP、agent run、3 个 worker 共享一个 asyncio loop。慢生成越多/越慢,Semaphore 排队 + 每 2s tick(`TICK_INTERVAL_SEC=2`)轮询越拥塞,反压 `send_to_user` 推送延迟。**任何在 worker pipeline 里漏掉 await 的同步阻塞(同步 sqlite3 或同步网络)会卡死整条 WS 链路。**

**设计(不引 Redis/多进程 — 三份 review 一致反对为 10-30 人引入)**:
1. **并发参数 env 化**:`IMAGE_CONCURRENCY` / `VIDEO_CONCURRENCY` / `TICK_INTERVAL_SEC` 改为可调 env,Beta 期按实测调,不改代码。
2. **backpressure 观测**:每 tick 记录 `claim 数 / in-flight 数 / tick 耗时` 为结构化事件(对接 §7 可观测性),让队列深度可见。
3. **同步阻塞审计**:video/composite pipeline 的 ffmpeg / boto3 调用必须走 `asyncio.to_thread`(`clip_extractor._run` 已用 25s 超时 kill 范式可参照);任何新慢调用进 worker 前必须确认非阻塞。
4. **队列深度上限**:enqueue 时若该用户 in-flight 生成任务 > 阈值,直接拒并提示"上一批还在生成中"(避免重试风暴 + 排队不可见)。

#### 问题 C:claim 原子性假设是硬约束

`generation_repo.py` 注释自述:"asyncio 单线程下 claim 是原子的(sqlite3 同步调用,SELECT+UPDATE 之间无 yield 点)"。**若未来把 worker 改 `to_thread`/多进程,这个假设破裂 → 双认领 → 重复生成 → 重复扣费。** 设计纪律:**claim 的 SELECT+UPDATE 必须保持在同步无 yield 的临界区**;若 §2.2-B 第 3 点要把 pipeline body 移到 `to_thread`,只移 **provider 调用**,不移 claim。

### 2.3 慢任务 job/queue 模型(统一规范)

| 维度 | image | video | composite | 设计依据 |
|------|-------|-------|-----------|---------|
| 并发上限 | Sem(5) | Sem(2) | 1 串行 | env 化 (§2.2-B) |
| 单任务超时 | 120s | 900s | best-effort | provider poll 上限 |
| 租约 | 300s lease | 300s | 300s | `GENERATION_LEASE_SECONDS` |
| 重试 | 指数退避 base15/cap300, ×3 | 同 | 同 | `schedule_generation_retry` |
| 断点续跑 | recover 续 poll(Google 重入队) | recover 续 poll | recover | `recover_generation_tasks` |
| boot 对账 | recover + lease 过期捞回 | 同 | 同 | worker tick 内置 |
| 成本护栏 | **P2 必补** ¥1.5/张 | **P2 必补** 按秒 | 本地 ffmpeg ≈0 | §2.4 |
| 通讯 | send_to_user(铁律④) | 同 | 同 | notify.py |

### 2.4 把生成纳入统一 cost_guard ★ P2 硬 Gate

当前 `cost_guard.py` 有 `PREDICT_SHOT_IMAGE_CNY=1.5` 但 **生成 leg 从不调用它**(grep 确认生成 leg 零 cost 命中)。设计:

1. **enqueue 前置 cost_guard**:`build_shot_prompts` → enqueue 时,对每个节点调 `cost_guard.cost_guard(user_id, run_id, predicted)`,超 run_cap/user_day_cap 抛 S8 拒绝(复用现成分级)。
2. **video 按秒预测**:新增 `predict_video_cost(duration_s)`,Seedance 按秒计费需建模。
3. **retry×3 重复扣费防护**:`recover` 对 Google 内存 task 重入队会重复花钱 —— 重入队前也要过 cost_guard;`attempt_count` 已记录,可作为"已花费 N 次"的审计依据。
4. **真实成本回写**:provider 返回后把实际 cost 写 `events` 表 `generation_cost`(已有事件名),`cost_guard._run_cost` 用真实值而非预测值累加。

---

## 3. 失败 / 恢复矩阵(失败有下一步 100%)

PHASED_PLAN §4.4 + §3.2 要求"每类失败都有 UI 可见的恢复路径 100%,0 静默失败"。现有 `failures.py` 已是完整资产:S1-S11 硬失败 + W1-W18 软警告,每个 S 码有中文 `RECOVERY_HINTS` + 最多 3 个 `RECOVERY_ACTIONS` 按钮 + HTTP 状态映射。下表把它 **延展到四段流水线**,并标注 best-effort vs 硬阻断边界。

### 3.1 失败矩阵(per-leg)

| Leg | 失败态 | 分类 | 用户可见下一步 | best-effort? |
|-----|--------|------|--------------|:---:|
| 分析 | URL 读不到 | S1 | 换链接 / 今日精选 / 反馈 | 硬阻断 |
| 分析 | 时长越界 (<5s/>180s) | S10 | 剪到 5s-3min / 换链接 | 硬阻断 |
| 分析 | 境外平台 | S9 | 换境内链接(PIPL,铁律⑦) | 硬阻断 |
| 分析 | ARK JSON 非法 | S5 (重试≤3) | 重试 / 换链接 / 反馈 | 硬阻断(重试后) |
| 分析 | ARK 超时 (120s) | S7 | 30s 后重试 / 换更短 | 硬阻断 |
| 分析 | ARK 拒/限流/auth | S8 | 1min 后重试 / 精选 | 硬阻断 |
| 分析 | 成本超 cap | S8 | 1min 后重试 / 精选 | 硬阻断(护钱) |
| 分析 | 无可救幕(全空) | S5 | 同上 | 硬阻断 |
| 分析 | **clip 抽取失败** | — | 降级 first_frame_url / 纯文字 | **best-effort**(范式标杆) |
| 分析 | 部分维度缺 | W2 | 中文兜底占位 + UI 降权 | **best-effort** |
| 改写 | LLM JSON 非法 | S5 (重试 1 次 nudge) | 重试 / 反馈 | 硬阻断 |
| 改写 | 成本超 cap | S8 | 拒绝 | 硬阻断(护钱) |
| 改写 | 低置信度 (<0.4) | — | 标"系统不太有把握" + 可重写 | **best-effort**(出稿但降权) |
| 改写 | 禁词触发 | — | scrub 后出稿 + parser_warning | **best-effort** |
| 生成 | provider 超时/失败 | — (写 generation_error) | 节点显失败 + 可重新生成 | **best-effort**(单 shot 失败不阻断其他) |
| 生成 | 重试耗尽 (×3) | — | 节点 failed + 手动重试按钮 | 硬阻断(该节点) |
| 生成 | 成本超 cap (enqueue) | S8 | 拒绝 + 提示额度 | 硬阻断(护钱) |
| 生成 | ffmpeg 合成失败 | — | composite 跳过 + 单镜头仍可用 | **best-effort** |
| 发布 | 镜头图缺失 | — | 占位/省略该行,不塞坏链 | **best-effort** |
| 发布 | 复制 API 失败 | — | localStorage 队列降级 | **best-effort** |
| 全局 | 进程死于 run 中 | S11 | boot reconcile → failed + 重试提示 | 硬阻断(确定终态) |

### 3.2 best-effort vs 硬阻断的判定原则(参照 clip 范式)

clip 抽取是范式标杆:**缺 ffmpeg / 下载失败 / 超时 / 无 scenes 全部返回 `{}` 不抛**,`_attach_scene_clips` 整体 try/except 吞异常,UI 降级到 first_frame_url。判定边界:

- **best-effort(装饰/增强层)**:失败只损失"锦上添花",核心价值仍在 → 静默降级 + 可选 UI 提示。包括:clip、镜头图、低置信改写出稿、单 shot 生成失败、composite 合成、发布复制。
- **硬阻断(核心价值缺失 / 花钱前)**:失败导致用户拿不到承诺的核心产物,或会烧钱 → 必须给 S 码 banner + 恢复按钮,**绝不静默**。包括:分析全失败、成本超 cap、时长/境外拒绝、重试耗尽。

### 3.3 必修债:工具级失败漏标 lifecycle ★

`cascade.py` 4 处 HardFailure(`_push_failure_frame`,行 224/304/409/577)**只推 `analysis_failed` 帧,不调 `run_state.mark_failed`**;工具把 HardFailure 吞成 error dict 返回给 LLM,`run_agent` 正常跑完反而调 `mark_done`(agent_runner.py:127)——**工具级失败在 run_lifecycle 表记成 done**。重连 replay 拿到 `done` + 无 failure,工具级失败的恢复提示丢失。复盘 §P1 已点名。**修法**:在 `_push_failure_frame` 里追加 `await run_state.mark_failed(thread_id, payload)`。Phase 2 慢任务失败率上升前必补。

---

## 4. 持久化健壮性

### 4.1 DB 路径 off-by-one — 现状核验(交接文档此条已过期)

经核验,`persistence/db.py`(cascade.db:analyses/rewrites/events/run_lifecycle/session_results)**已正式修复**:`db_path()`(db.py:38)用 `Path("/app/src").exists()` 检测容器布局 → `/app/data/cascade.db`(挂载卷);本地 → `<repo>/backend/data/cascade.db`;`CASCADE_DB_PATH` 仅作 override。docker-compose.yml:31 注释明确"no longer required"。**retro §5 / 首版任务书把这条列为"未修、靠 env 兜底"是过期信息。**

### 4.2 ★ 真正未收口的隐患:第二个库 canvas.db 用的是另一套解析

`canvas_persistence/db.py:17-18` 的 **canvas.db**(canvas_nodes/edges — 生成队列状态全在这)用的是 **纯相对 `parent×5/data/canvas.db`,无容器检测**:

```python
_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "canvas.db"
```

核验路径算术:文件在 `/app/src/agent/tools/canvas_persistence/db.py`,5 个 parent = `canvas_persistence→tools→agent→src→/app`,得 `/app/data/canvas.db`。**当前恰好落在挂载卷上,所以现在不丢。** 但这是 **脆弱的巧合**,不是设计:
- 它依赖"目录层级恰好是 5 层 + WORKDIR 恰好 /app",任一改动(挪文件、改 Dockerfile)就回到 off-by-one。
- 它 **不响应 `CASCADE_DB_PATH`**,与 cascade.db 的解析策略不一致 —— 两个库可能漂移到不同卷。
- 慢生成队列状态全在这个库,一旦它漂到 ephemeral,**重启丢整个生成队列**(recover 依赖 lease,但 Google 内存 task 重启必丢 = 重复花钱)。

**正式修法(P2,不长期靠巧合)**:
1. **统一路径解析**:把 `canvas_persistence/db.py` 的 `_DB_PATH` 改为复用 `persistence/db.py` 的容器检测逻辑(抽一个共享 `resolve_data_dir()`),`canvas.db` = `resolve_data_dir()/canvas.db`。两库同卷、同 override、同策略。
2. **兼容/迁移**:容器内当前已是 `/app/data/canvas.db`,改后路径不变 → **零数据迁移**;只是把"巧合正确"变成"显式正确"。本地若旧文件在别处,boot 时检测旧路径存在则一次性 move(best-effort)。
3. **回归测试**:加单测断言"容器布局下两库都解析到 `/app/data`,且都响应 `CASCADE_DB_PATH`"。

### 4.3 SQLite 单库写竞争天花板(Beta 期实测项)

P2 plan 阈值:≤30 创作者且 p95 health<150ms / WS accept<250ms / 锁竞争<1/1000 才留 SQLite。30 人 Beta 正踩线上。慢生成 worker 频繁写 canvas_nodes(每 task 多次 `update_generation_state`)+ run_lifecycle 写穿透,WAL 下写串行。**纪律**:Beta 期把锁竞争/p95 纳入 §7 观测,触阈值才议 Postgres,**不预先迁**。另:`run_state` 每次 mark_*/load 都 `_connect()→close` 新连接(run_state.py:58/94/117),慢生成频繁状态变更放大连接开销 —— 可观测后再议连接复用。

---

## 5. 密钥 / 凭证(机制,不含任何真实值)

### 5.1 prod 凭证轮换(retro §5 + memory reference_prod_server 列为待办,未确认完成)

三类已泄露 + 一个 admin token,**Phase 2 上线前作为 Gate 项核实轮换**:

| 凭证 | 位置 | 轮换流程 | 注入方式 |
|------|------|---------|---------|
| SSH 私钥 | `~/.ssh/cascade_prod` | 生成新 keypair → 部署新公钥 → 删旧 authorized_keys → 验证新钥登录 → 销毁旧私钥 | 仅运维本地,永不进仓库 |
| root 口令 | prod 主机 | 登录已禁仍需轮换;改强口令 → 确认 sudo 路径可用 | 不存任何文件,仅密码管理器 |
| Cloudflare API token | `cloudflared.service` | CF 控制台吊销旧 token → 签发最小权限新 token(仅 tunnel)→ 更新 service 文件 → 重启隧道验证 | systemd unit,文件权限 600 |
| `CASCADE_ADMIN_TOKEN` | prod `.env`(曾现于 transcript) | 生成新随机 token → 更新 .env → 重启 backend → curl 验证 admin 端点 403→200 | env_file,永不进仓库 |

### 5.2 后续 secrets 管理机制

- **单一注入面**:所有密钥经 `.env`(`env_file` in docker-compose),`.env` 在 `.gitignore`,仓库只留 `.env.example`(占位,无真值)。
- **fail-closed**:`ENV=prod` 时 `INVITE_CODES` 空则 abort boot、admin 端点未设 token 则 403(docker-compose.yml:24-27 已是此模型)—— 继承,不退。
- **合规边界(铁律⑦)**:`ARK_API_KEY`(doubao,境内)是分析/改写的唯一 LLM 凭证。**生成 leg 默认 `IMAGE_GEN_PROVIDER=google`(Gemini,跨境)是 PIPL §38 待 PM/法务确认项** —— 30 人 Beta 真实用户数据合规性必须 founder 拍板:要么默认切境内图片 provider(Apimart),要么明确接受跨境并加同意条款。改写已隔离境内,生成图不能裸奔跨境。
- **轮换纪律**:任何凭证一旦出现在 transcript/日志/commit,立即进轮换队列。`events` 表打点严禁记任何 token/key 值。

---

## 6. Phase 1 → Phase 2 衔接(继承 / 加固 / 迁移顺序)

### 6.1 组件继承矩阵

| 组件 | 判定 | 理由 |
|------|------|------|
| W5D4 通讯三件套(注册表/run_lifecycle/帧缓冲) | **原样继承** | Opus 三轮 review 判内测规模健壮;铁律④落实 |
| `failures.py` S/W 码 + 恢复路径 | **原样继承** | 失败有下一步 100% 的资产,延展不重写 |
| 生成 worker(队列/租约/退避/恢复) | **原样继承 + 加固** | 底子最成熟;加 cost_guard + JobProgress 投影 |
| `CascadeAnalysisContract`(C1) + adapter 兜底 | **原样继承** | toprador 对齐稳定契约;改维度必 bump revision(铁律①) |
| cascade.db 路径解析 | **原样继承** | 已正式修,容器/本地自适应 |
| 三级鉴权(OPEN/COHORT/ADMIN) | **原样继承** | 公网刷钱 P0 已关 |
| 改写 leg(rewrite.py/prompts/scrub) | **加固后解封** | 代码完整;需 ① 加 REWRITE_PIPELINE_REVISION ② 真 URL 质量验收 ③ 双开关同开 |
| canvas.db 路径解析 | **加固** | §4.2 统一到容器检测,消除巧合 |
| 工具级 HardFailure | **加固** | §3.3 补 mark_failed |
| 生成 cost 护栏 | **新建** | §2.4 enqueue 前置 cost_guard |
| C3 分析/改写→镜头节点桥接 | **新建** | P2-1 视频链路 + P1-4 草稿图的前提 |
| creation_run 聚合 + JobProgress 投影 | **新建** | §1.1 + §2.2-A |
| 发布 leg 接入 UI + 数据 | **加固后接入** | §1.3-C4;niche 砍后重设标签源 |
| trace_id 端到端透传 | **新建** | §7 排障线 |
| 25 事件埋点 (P2-10) | **新建/扩展** | §7 |

### 6.2 迁移顺序(依赖驱动,不回退 5 同源 bug)

> 5 同源 bug 的共同雷区 = 发往启动时捕获的 ws/thread。**每步都过铁律④ + 铁律②(改 UI 跑 lint + Playwright 真旅程)+ 铁律⑤(真 URL 验证)。**

```text
M0  地基收口(不依赖任何新功能,先还债)
    ├─ §4.2 canvas.db 路径统一到容器检测 + 回归测试
    ├─ §3.3 cascade 工具 HardFailure 补 mark_failed
    ├─ §5.1 prod 凭证 4 项轮换 + 核实
    └─ 修 §7 遥测失真:http_router analysis cost provider "fixture"→真实上游
         (并把生成 cost 写回 events)

M1  统一模型 + 改写版本守卫(为解封铺路,纯后端,不动通讯)
    ├─ §1.4 REWRITE_PIPELINE_REVISION + rewrites 表加列 + 缓存键加守卫
    ├─ §1.1 creation_run 投影表(upsert 模式复用 session_results 先例)
    └─ 单测:缓存版本守卫双侧生效 / creation_run stage 推进幂等

M2  改写解封(第一张多米诺,恢复完整闭环前半段)
    ├─ 真 URL + doubao 端到端质量验收(铁律⑤,铁律⑦境内合规)
    ├─ cost 定价从 Gemini 改 doubao;标定 confidence 阈值
    ├─ REWRITE_ENABLED=true(前端重建) + CASCADE_REWRITE_UPSTREAM=llm(后端 env)
    ├─ bump ANALYSIS_PIPELINE_REVISION(铁律①) + bump REWRITE_PIPELINE_REVISION
    └─ 前端把"你的版本"接回结果页(暖色科技 + 现行卡结构,非 W4 三幕)

M3  生成桥接 + 慢任务加固(最大新建块)
    ├─ §1.3-C3 build_shot_prompts 桥接(改写/分析 → 镜头节点, 人类确认门)
    ├─ §2.4 enqueue 前置 cost_guard(image + video 按秒预测)★ Gate 项
    ├─ §2.2-A JobProgress 投影:reconnect 时聚合 generation 进度 replay
    │      (防"卡 95%"同构;复用 send_to_user, 铁律④)
    ├─ §2.2-B 并发参数 env 化 + backpressure 观测 + 队列深度上限
    └─ P2-1 单镜头 video(Seedance;Kling 按 PHASED_PLAN 可后补)

M4  发布闭环 + 终点 UX
    ├─ §1.3-C4 发布包接真数据:标签从 theme/用户自填(niche 已砍),script 先 scrub
    ├─ 镜头图接 S3 url + clip /media url(best-effort 降级)
    ├─ 发布包接回结果页 CardStack(去掉 _props 忽略)
    └─ 分字段复制(标题/标签/脚本)对齐抖音发布表单

M5  可观测 + Gate 收口(贯穿,M0 起逐步埋,M5 收口)
    ├─ §7 25 事件埋点补全 + trace_id 透传
    ├─ 转化漏斗(H1-H8 假设可验证)
    └─ 短链 302 跟随补齐(retro §5 移动端隐形流失)
```

**回退防护**:M2/M3/M4 任何动通讯/前端的步骤,必须 ① 不引入新的 ws/thread 闭包捕获(铁律④)② 新增 WS 帧走 Pydantic 契约 + codegen ③ 不删 P0-C 的 pendingByThread 缓冲 ④ 改 UI 跑 rules-of-hooks lint + Playwright 真旅程(铁律②)⑤ 新 `.anim-*` 进 reduced-motion 名单(铁律⑧)。**明确不做**(三份 review 一致):不迁 SSE / 不换 websockets / 不引 LangGraph stream-resume / 不为 30 人引 Redis / Postgres / 不做 P2 per-run seq replay(YAGNI)。

---

## 7. 可观测性(对接 P2-10 的 25 事件 + 成本计量)

### 7.1 现有事件基线(EventName, event_names.py — 已 23 个)

`run_started / analysis_returned / analysis_answer_returned / script_rewritten / shot_generated / shot_first_frame_returned / publish_pack_copied / anchor_created / anchor_reused / failure_emitted / failure_recovered / generation_cost / interview_logged / consent_accepted / cascade_retry / cascade_circuit_open / cascade_cache_hit / cascade_cache_miss / niche_selected / uncaught_exception / client_error`(+ run_started)。

### 7.2 P2-10 "25 事件"对齐(每 leg 全覆盖)

| Leg / 贯穿 | 事件 | 状态 | 用途(漏斗/成本/排障) |
|-----------|------|------|---------------------|
| 入口 | `run_started` | ✓ 有 | 漏斗起点 (H1) |
| 分析 | `analysis_returned` / `cascade_cache_hit` / `cache_miss` | ✓ 有 | 成功率 + 缓存命中 |
| 分析 | `cascade_retry` / `cascade_circuit_open` | ✓ 有 | 上游健康 |
| 改写 | `script_rewritten` | ✓ 有 | 改写采用率 (H2/H3) |
| 改写 | **`rewrite_started`** | 新建 | 改写转化漏斗分母 |
| 生成 | `shot_generated` / `shot_first_frame_returned` | ✓ 有 | 生成成功率 (H5) |
| 生成 | **`generation_enqueued`** / **`generation_failed`** | 新建 | 队列深度 + 失败可见性 (§2.2-B) |
| 生成 | `generation_cost` | ✓ 有(但需修 provider 失真) | 成本计量 (H6) |
| 发布 | `publish_pack_copied` | ✓ 有 | 闭环终点 (H5) |
| 复用 | `anchor_created` / `anchor_reused` | ✓ 有 | 复用率 (H4, P2 Gate ≥60%) |
| 失败 | `failure_emitted` / `failure_recovered` | ✓ 有 | 失败有下一步 (H7) |
| 全局 | `uncaught_exception` / `client_error` | ✓ 有 | 后端/前端 bug |
| 商业 | `consent_accepted` / `interview_logged` | ✓ 有 | Beta 招募 (P2-11) |
| 商业 | **`quota_exceeded`** / **`paywall_viewed`** / **`subscription_started`** | 新建 | 配额/付费 (P2-5, Gate ≥5 付费) |

### 7.3 成本计量挂钩(修失真 + 补生成)

- **修遥测失真**:`http_router.py:217` analysis `generation_cost` 事件硬编码 `provider:"fixture"`,实际是 doubao_direct —— 改为真实上游名。否则 Beta 期成本/上游成功率 dashboard 误判(铁律⑤同类:数字好看≠真相)。
- **补生成成本**:provider 返回后把实际 image/video cost 写 `generation_cost`(`call_kind:"image"|"video"`,`provider:"google"|"apimart"|"seedance"`,`cost_fen`)。
- **trace_id 透传**(P2):`events` 表加 `trace_id` 列,run_started 生成、贯穿 WS/agent/cascade/上游;让"一次创作 run"的全链路事件可串联排障(Phase 2 慢任务失败排障的关键线)。

### 7.4 日志纪律

worker 当前失败只 `print` 到 stdout(`generation_worker.py`)+ 写 `generation_error` 文本,无结构化告警。设计:失败路径除写节点外,**emit `generation_failed` 结构化事件**(带 node_id/attempt/error/trace_id),让离线用户完成/失败的任务可被 founder 在 /admin/events 看到,而非靠下次 canvas 拉取或 ssh 看 print。日志严禁记任何密钥(§5.2)。

---

## 8. 与 8 条工程铁律的对照(逐条)

| # | 铁律 | 本设计如何 honor |
|---|------|-----------------|
| ① | 改 prompt/维度/模型 bump `ANALYSIS_PIPELINE_REVISION`(=3, contract.py:28) | M2 解封改写时同步 bump;**并新增对称的 `REWRITE_PIPELINE_REVISION`**(§1.4,补铁律①在改写侧的盲区) |
| ② | 改 UI 跑 lint(rules-of-hooks)+ Playwright 真旅程 | M2/M4 所有前端步骤纳入(§6.2 回退防护) |
| ③ | 批量删会话用原子 `delete_sessions` | 继承,handle_delete_sessions 单事务已落实(ws_handlers.py:101) |
| ④ | 实时通讯永不发启动捕获的 ws/thread | JobProgress 投影 + 所有新帧走 `send_to_user`(§2.2);M3/M4 回退防护硬约束 |
| ⑤ | 容器健康≠功能可用,真 URL 验证 | M2 改写解封 + M3 生成 + 修成本遥测失真都以真 URL 验证为准 |
| ⑥ | 改 mirror/依赖必重 lock | 本设计不改依赖;若 M3 引新 provider SDK 必 `[[tool.uv.index]]` 重 lock |
| ⑦ | doubao 境内合规(PIPL §38,禁 gemini 跑改写),模型全名带后缀 | 改写继承境内 doubao;**生成图默认 Gemini 跨境列为 §5.2 待 founder 拍板的合规 Gate 项** |
| ⑧ | 不引 framer-motion,新动效进 reduced-motion 名单 | 本文为后端架构,不引入动效;M4 前端接入沿用 index.css 层(§6.2) |

---

## 9. 给下游实现 agent 的硬提示(防踩坑)

1. **不要重构通讯/生成底座** —— W5D4 三件套 + 生成队列是资产,延展(JobProgress 投影 + cost_guard + 桥接),不重写。
2. **run_lifecycle 不要拿去管慢生成** —— 它是 20-50s turn 的,210s stale 阈值会误判慢生成;用 §2.2-A 的 JobProgress 投影。
3. **改写解封必须三件事联动**(漏一即假通):前端 `REWRITE_ENABLED=true` 重建 + 后端 `CASCADE_REWRITE_UPSTREAM=llm` + bump 两个 revision。
4. **改写缓存有独立版本守卫**(§1.4),别以为 bump `ANALYSIS_PIPELINE_REVISION` 能让新 rewrite prompt 生效 —— 它对 rewrites 表无效。
5. **canvas.db 路径是巧合正确不是设计正确**(§4.2),P2 统一到容器检测,别挪文件层级前先改它。
6. **生成 leg 零成本护栏是真金白银裸奔**(§2.4),enqueue 前置 cost_guard 是 P2 硬 Gate。
7. **生成图默认 Gemini 跨境是合规未决项**(§5.2/铁律⑦),改写已隔离境内,生成图需 founder 拍板。
8. **结果页是 toprador 维度 + 三级层级 + 脚本抽屉,不是抓/留/带三幕**(retro §2.2);发布/改写 UI 接回时走暖色科技 + 现行 CardStack 结构。

---

*本文为 Phase1+Phase2 统一架构基线。所有代码断言经 Read/Grep/Bash 核验(2026-05-31, HEAD 929cb21)。后续实现以本文 §1 契约表 / §2 慢任务规范 / §3 失败矩阵 / §6.2 迁移顺序为准,增量而非重写。*
