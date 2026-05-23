# OpenRHTV · Cascade

> **面向中文个人创作者的 AI 短视频创作平台**:把"看懂别人的爆款"和"做自己的版本"合二为一 —— 从源视频分析到锚点级联的画布创作,一条龙。

**Codename**: Cascade(锚点级联 character → scene → grid → frame;叙事级联 开场 → 中段 → 高潮 → 结尾)
**Phase**: Phase 1 内测(2026-05 起,10 人 cohort,3 个 niche)

---

## 一句话定位

**用户粘一条抖音/小红书爆款 URL → 系统提取"爆款公式"(钩子模式 + 分场结构 + 锚点) → 用户选自己的 niche → LLM 改写成创作者本人的版本 → 画布生成分镜 + 锚点 + 成片 → 一键复制发布包**。

不是又一个生图工具,是把**发现 + 学习 + 复刻**三件事串成一条 agent 驱动的画布工作流。

---

## 为什么不是又一个 AI 视频生成器

| 现有产品 | 强项 | 缺什么 |
|---|---|---|
| 即梦 / 可灵 / Sora 2 | 单条生成质量 | 只有"生成",没有"发现 + 学习" |
| Heygen / Synthesia | Talking head 工业化 | 不适合中文短视频生态 |
| 剪映 / CapCut | 后期剪辑 | 不能从零生成 |
| 新榜 / 飞瓜 / 卡思 | 热度数据 | 只看数据,不能创作 |

Cascade 在做的事:把上面四列**用 agent + 画布串起来**。Day-1 就有的护城河:
- **锚点级联**(character → scene → grid → frame):同一角色 / 同一场景跨视频复用,避免风格漂移
- **钩子分类 H1-H9**:9 大开场钩子模式(月龄宝宝、一周不重样、千万别、师傅做、当妈以后…)+ niche-specific 权重
- **真实输入,真实输出**:不是合成模板,改写来自真实爆款的拆解

---

## 核心概念

### 三位一体:Agent + 人 + 画布

```
┌────────────────────────────────────────────────────┐
│                    无限画布                          │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────┐ │
│  │ 源视频  │─▶│ 分析(爆款 │─▶│ 改写(自│─▶│ 分镜 + │ │
│  │ URL     │  │ 公式提取)│  │ 己版本)│  │ 锚点  │ │
│  └─────────┘  └──────────┘  └────────┘  └────────┘ │
│       ▲             ▲             ▲          ▲      │
│       │     Agent 自动搭建 + 人随时干预         │      │
│       └─────────────┴─────────────┴──────────┘      │
│                       │                              │
│                对话面板(自然语言交互)                 │
└────────────────────────────────────────────────────┘
```

| 角色 | 职责 |
|---|---|
| **Agent**(Director) | 理解创作意图,在画布上搭建节点,调度 cascade 分析 + 改写 + 生成 API |
| **人** | 下达指令,在关键节点做决策(选 niche、定锚点、审改写),随时干预 |
| **画布** | 承载全流程的可视化节点树,每一步透明可追溯,单节点精准修改 |

### Cascade 流水线

```
源 URL ──┐
         ├─▶ Toprador analysis(分析上游) ──▶ CascadeAnalysisContract(JSON)
         │     │
         │     └─▶ hook_taxonomy.py 标 H1-H9
         │
         └─▶ rewrite_service ──▶ LLM(Doubao seed-1.6,Gemini fallback)──▶ 改写产物
                                                                          │
                                                                          ▼
                                                                  shots[] + anchors[]
                                                                          │
                                                                          ▼
                                                                  画布节点 + 生图/生视频 API
```

每个环节都 emit 事件到 `events` 表(see `cascade/events.py`),admin 面板可观测。

---

## Phase 1 范围

**3 个 niche**(2026-05 起):

| Niche | 中文 | Hook 偏好 |
|---|---|---|
| `baomam_fushi` | 宝妈辅食 | H1(月龄)+ H2(一周)+ H3(蹭蹭涨) |
| `yuer_richang` | 育儿日常 | H5(爸视角)+ H7(一家人)+ H8(当妈以后) |
| `jiating_chufang` | 家庭厨房 | H4(千万别)+ H6(节日)+ H9(反常识) |

**做了** ✅:
- 源视频分析合约(`backend/src/agent/cascade/contract.py`)+ 适配层
- 改写流水线 + niche-specific prompts
- 锚点系统(`anchors.py`)+ 跨 run 复用统计
- 评估 harness(`scripts/p2-6_eval.py` — fixture 和 LLM 双模 + judge)
- Admin 面板 4 张:`/admin/creators` `/admin/events` `/admin/cost` `/analytics/anchors`
- 落地合规闭环:用户协议 + 隐私 v0(`docs/legal/`)、Click-through 同意门(`ConsentGate.tsx`)、PII 脱敏、未成年人关键词审计、跨境数据硬阻塞

**没做** ❌(超出 Phase 1):
- 多 cohort scale-up(只 10 人 concierge)
- 算法备案审批完成(预登记已签,正式备案公测前)
- 视频生成全自动(图生视频还是 manual 触发)
- 非中文支持

---

## 技术栈

| 层 | 技术 |
|---|---|
| Agent 框架 | [LangGraph](https://github.com/langchain-ai/langgraph) + [DeepAgents](https://github.com/langchain-ai/deepagents) |
| 画布前端 | [React Flow](https://reactflow.dev/) (`@xyflow/react`) + React 19 + TypeScript |
| LLM | 默认 Doubao(火山方舟 ARK,境内不出境);Gemini 作为 fallback |
| 图片生成 | Apimart(OpenAI 兼容)/ Google Gemini(用户主动二次同意才走) |
| 视频生成 | Doubao Seedance 2.0(ARK)+ Volcengine SDK |
| 后端 | Python 3.12 + asyncio(单进程,WebSocket + 手写 HTTP API 同端口) |
| 持久化 | SQLite + aiosqlite(events / analyses / anchors / rewrites)|
| 评估 | 自研 harness(mechanical checks + LLM judge) |
| 测试 | pytest(后端 85+ 测试)+ vitest(前端 79+ 测试) |

---

## 项目结构

```
OpenRHTV/
├── backend/                          # Python 3.12 服务
│   ├── pyproject.toml
│   ├── src/agent/
│   │   ├── main.py                   # Director agent 入口(单 agent + canvas-manager subagent)
│   │   ├── server.py                 # WebSocket + HTTP API 单进程服务
│   │   ├── llm_factory.py            # Doubao / Gemini provider 切换
│   │   ├── config.py                 # .env 加载(根目录 .env)
│   │   ├── pool.py                   # Agent 实例 LRU 池
│   │   ├── prompts/                  # director.md + canvas-manager.md + rewrite_<niche>.md
│   │   ├── tools/                    # canvas / generation / video_generation / s3_upload
│   │   └── cascade/                  # 核心改写流水线
│   │       ├── contract.py           # CascadeAnalysisContract (Pydantic)
│   │       ├── analysis_service.py   # 源分析(fixture 或 Toprador 上游)
│   │       ├── rewrite_service.py    # niche-specific LLM 改写
│   │       ├── adapter.py            # 上游 payload → contract;含 PII 脱敏 + 跨境阻断
│   │       ├── anchors.py            # 锚点 CRUD + 跨 run 复用
│   │       ├── hook_taxonomy.py      # H1-H9 钩子正则 + niche 权重
│   │       ├── minor_audit.py        # 未成年人关键词审计
│   │       ├── circuit_breaker.py    # 上游 API 熔断器(60s 窗口,5 次失败开)
│   │       ├── cost_guard.py         # 预测成本守门(每 run 限额)
│   │       ├── events.py             # 12 + 4 个事件类型的单一写路径
│   │       ├── storage.py            # SQLite 持久化(events / analyses / anchors / rewrites)
│   │       ├── eval/                 # 评估 harness(fixture + LLM judge)
│   │       └── fixtures/             # synthetic_v1(单元测试)+ real_v1(真实 URL 标注)
│   └── tests/                        # pytest
│
├── frontend/                         # React 19 + Vite + Tailwind v4
│   ├── package.json
│   └── src/
│       ├── main.tsx                  # 路由根
│       ├── App.tsx                   # 画布 chat 主页(/chat/:threadId)
│       ├── pages/
│       │   ├── Landing.tsx           # /  (含 ConsentGate)
│       │   ├── LegalDoc.tsx          # /legal/:slug  (协议 + 隐私)
│       │   ├── AnchorAnalytics.tsx   # /analytics/anchors
│       │   ├── AdminCreators.tsx     # /admin/creators
│       │   ├── AdminEvents.tsx       # /admin/events    (事件直播流)
│       │   └── AdminCost.tsx         # /admin/cost      (成本看板)
│       ├── components/
│       │   ├── landing/ConsentGate.tsx
│       │   ├── Canvas.tsx            # React Flow 实例
│       │   ├── CardStack.tsx         # 非 pro 视图卡片栈
│       │   ├── nodes/                # 自定义画布节点
│       │   └── cards/                # 卡片 UI(ShotCard / ScriptCard / PublishPackCard…)
│       ├── hooks/                    # useWebSocket / useAnchors / useEvents / useGenerationCost…
│       ├── lib/                      # anchorApi / creatorsApi / eventsApi / buildPublishPack
│       ├── store/canvasStore.ts      # Zustand 全局画布状态
│       └── types/                    # cascade.ts 镜像后端 contract
│
├── docs/                             # 设计 + 合规 + 路线
│   ├── PRODUCT_VISION.md
│   ├── MVP_SCOPE.md
│   ├── ROADMAP_6M.md
│   ├── CANVAS_DESIGN.md
│   ├── TOPRADOR_SCHEMA.md            # 上游分析合约文档
│   ├── TOPIC_TO_CREATION_PIPELINE.md
│   ├── DATA_DASHBOARD.md
│   ├── legal/                        # user_agreement_v0 + privacy_v0
│   └── nexus/                        # PM 周期文档 + 评估 + 招募(internal)
│
├── scripts/
│   ├── p2-6_eval.py                  # 跑全 niche 评估,产 baseline JSON + report MD
│   ├── p2-4_run_real_urls.py         # 真实 URL 改写 batch runner
│   └── check_progress.sh             # 项目进度 probe(给 PM cycle 用)
│
├── .env.example                      # 配置模板
└── README.md
```

---

## 快速开始

### 0. 前置

- Python 3.12
- Node 20+(用 pnpm 或 npm)
- [uv](https://github.com/astral-sh/uv)(Python deps + venv 管理)
- 一个 Doubao(火山方舟 ARK)API key —— [开通指南](https://console.volcengine.com/ark)

### 1. 配置 LLM

```bash
git clone https://github.com/<your-org>/OpenRHTV.git
cd OpenRHTV
cp .env.example .env
# 编辑 .env:
#   ARK_API_KEY=ark-...
#   DOUBAO_MODEL=doubao-seed-1-6-250615   # 或您 ARK 控制台开通的 model id / ep-XXX
```

> Gemini 走 fallback:在 .env 把 `LLM_PROVIDER` 改 `gemini` 并填 `GOOGLE_API_KEY` 即可,无需改代码。

### 2. 起后端

```bash
cd backend
uv sync
uv run python -m agent.server
# 启动 WS:    ws://localhost:8765
# 启动 HTTP:  http://localhost:8765/api/*  (共用同端口)
```

### 3. 起前端

```bash
cd frontend
pnpm install   # 或 npm install
pnpm dev       # http://localhost:5173
```

### 4. 跑一遍 cascade

1. 浏览器开 `http://localhost:5173/`
2. 同意用户协议 + 隐私(`ConsentGate`)
3. 进入 chat session,粘一条 Douyin / 小红书 URL
4. Director 调用 `request_shallow_analysis(url)` → 拿到 `CascadeAnalysisContract`
5. 选 niche → 调用 `request_rewrite(analysis_id, niche)` → 改写产物
6. 画布生成 shots + anchors
7. 后续生图 / 生视频 / 配音可手动触发

### 5. 运行测试

```bash
# 后端
cd backend && uv run pytest -q

# 前端
cd frontend && pnpm vitest run
```

### 6. 跑评估 baseline

```bash
cd backend
uv run python ../scripts/p2-6_eval.py --niche all --mode llm
# 产物:
#   docs/nexus/founder_log/p2-6_baseline_<UTC>.json
#   docs/nexus/founder_log/p2-6_report_<UTC>.md
# 报告含 Delta from baseline 自动对比
```

---

## API 概览

后端在同一端口 `8765` 上提供 WebSocket(画布 + chat)和 HTTP(REST)两路:

### HTTP

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/cost/status` | 当前用户 cost guard 余额 |
| GET | `/api/creators` | Admin 创建者看板聚合 |
| GET | `/api/events` | 事件直播流(filter: type / user_id / since_ts) |
| GET | `/api/anchors` | 列表锚点(kind=character\|scene) |
| GET | `/api/anchors/<id>/reuses` | 锚点复用历史 |
| POST | `/api/anchors` | 创建锚点 |
| POST | `/api/anchors/<id>/reuse` | 标记锚点被复用 |
| POST | `/api/events` | 写入 telemetry 事件 |
| POST | `/api/rewrite` | niche 改写 |
| POST | `/api/analysis/shallow` | 源 URL 浅分析 |

### WebSocket

`ws://localhost:8765` —— 首条消息 auth 绑定 `user_id`,后续消息隔离。

主要 message types(详见 `frontend/src/types/`):
- `user_message`(前 → 后): 用户输入
- `agent_response`(后 → 前): 完整回复 + 画布快照
- `agent_stream`(后 → 前): 流式 token + tool_call 事件
- `canvas_updated`(后 → 前): 单独画布推送
- `session_state` / `session_list` / `processing` 等

---

## 合规与隐私(Phase 1 内测口径)

- **数据全境内**:Doubao 在境内推理,SQLite 存于本地;Gemini 仅 fallback 且需用户二次同意
- **Click-through 同意**:进入应用前必须勾选用户协议 + 隐私;localStorage 存证 + 服务端 `consent_accepted` event 审计
- **PII 脱敏**:`_strip_pii` 自动剔除 IP / 作者昵称等字段(`backend/src/agent/cascade/adapter.py`)
- **跨境数据硬阻塞**:`STRICT_CROSS_BORDER_REJECT=True` 默认开,触发 W9 → S9 拒绝
- **未成年人审计**:13 词中英文关键词命中 `W14_MINOR_SUBJECT_DETECTED`(INFO 级,不阻断)
- **删除承诺**:邮件请求 24h 内删全部 run(协议 §5.2 + 隐私 §7.2)

详见 `docs/legal/user_agreement_v0.md` + `docs/legal/privacy_v0.md`。

---

## 路线图

- [x] **Phase 0** — 基础设施 + 合规闭环(2026-05 close)
- [x] **Phase 1 工程**(2026-05): Cascade 分析 + 改写 + 锚点 + 画布 + 4 个 admin 看板 + 评估 harness
- [ ] **Phase 1 内测**(进行中): 10 人 concierge cohort,3 niche
- [ ] **Phase 2**(规划中): cohort scale 到 30 人,引入新榜热度雷达,完整生视频自动化
- [ ] **Phase 3**: 算法备案审批通过,公测开放
- [ ] **Phase 4-6**: 详见 `docs/ROADMAP_6M.md`

North star:**Day 1 创作完成率 ≥ 40%、14 天留存 ≥ 25%、人均 7 天 ≥ 3 条**。

---

## 参考

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [DeepAgents](https://github.com/langchain-ai/deepagents)
- [React Flow](https://reactflow.dev/) (`@xyflow/react`)
- [火山方舟 ARK 控制台](https://console.volcengine.com/ark)
- [RHTV 官方](https://rhtv.ai/)(原型参考)
- [RunningHub 社区](https://www.runninghub.cn/)

---

## License

(待定 — 项目处于内测阶段,license 公开发布时确定)
