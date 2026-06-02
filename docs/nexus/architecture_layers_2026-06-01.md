# OpenRHTV · Cascade 架构分层与调用关系(2026-06-01)

**用途**: 回答「内容创作模块 vs OpenRHTV 框架」的边界,以及新功能落点判断法。
**口径**: 直接读码核实(server.py / transport / pool / tools / cascade / 前端 store),非记忆。

---

## 0. 一句话

`OpenRHTV · Cascade` 本身就是这个 AI 短视频创作平台 —— **内容创作(爆款分析→改写→生成→
发布闭环)就是本仓库的核心产品**,不是叠在别的底座上的插件。仓库内部分三层:**前端
(展示)/ 框架层(通用 agent+画布)/ 内容创作模块(cascade 业务)**。

---

## 1. 三层调用关系图

```
┌──────────────────────────────────────────────────────────────────────────┐
│  前端  frontend/src/                                                         │
│                                                                            │
│   components/CardStack.tsx ── cards/{ViralAnalysisCard, SceneAnalysisCard,  │
│        │                            RewriteCTA, RewriteShotCard,            │
│        │                            PublishPackCard}                        │
│   store/canvasStore.ts  (analysis / script / rewriteShots / shots)         │
│        ▲          ▲                                                         │
│        │ 帧驱动    │ apiFetch (REST)                                          │
│   store/wsStore.ts ── hooks/useWebSocket.ts        lib/apiClient.ts         │
│        │ WS :8765 (实时 agent 流)                    │ HTTP :8766 (REST)      │
└────────┼───────────────────────────────────────────┼──────────────────────┘
         │                                            │ /api/showcase /events
         ▼                                            ▼ /admin /health
┌──────────────────────────────────────────────────────────────────────────┐
│  框架层(通用 agent+画布)  backend/src/agent/                                 │
│                                                                            │
│   server.py  ── WS :8765 ─┐         ┌─ HTTP :8766 ── (showcase/events/admin)│
│                           ▼         │                                       │
│   transport/ws_handlers.py ─► agent_runner.run_agent ─► pool.py            │
│         (handle_user_message)        (注入[selected_niche:]) (LangGraph     │
│                                                          react agent)       │
│                                            │  读 prompts/director.md 决定调谁 │
│                                       ╔═══════════╗                         │
│                                       ║ Director  ║                         │
│                                       ╚═════╤═════╝                         │
│            tools/cascade.py ◄──────────────┤  (cascade_analyze /            │
│            tools/canvas.py  ◄──────────────┤   cascade_rewrite /            │
│            tools/generation.py ◄───────────┘   cascade_generate_first_frame│
│                  │                              / cascade_ask)              │
│                  │ 结果回推:notify.send_to_user(user_id, frame)             │
│                  │ (RUN_CTX/runtime_ctx,实时注册表查当前 ws,非启动时捕获)     │
└──────────────────┼─────────────────────────────────────────────────────────┘
                   ▼ 调业务
┌──────────────────────────────────────────────────────────────────────────┐
│  内容创作模块  backend/src/agent/cascade/                                     │
│                                                                            │
│   analysis_service.py ─► mediakit/doubao_direct_client ─► adapter.py ─►     │
│        (爆款分析)           (ARK 火山 vision)         (normalize)  contract.py │
│   rewrite_service.py ─► rewrite.py (rewrite_for_niche, LLM, prompts/        │
│        (改写)              rewrite_generic.md)                               │
│   anchors.py · hook_taxonomy.py · cost_guard.py · showcase_service.py       │
│   persistence/ (SQLite: analyses / rewrites / sessions / showcase)         │
└────────────────────────────┬───────────────────────────────────────────────┘
                             ▼ 外部
   ARK 火山(doubao-seed-2-0-pro:vision 分析 + LLM 改写) · apimart(境内生成图)
   · 抖音 CDN(分享链解析取 mp4)
```

---

## 2. 各层职责与边界

| 层 | 干什么 | 关键文件 |
|---|--------|---------|
| **前端** | 渲染 + 收发帧。不含业务逻辑,纯展示状态 | `CardStack.tsx` / `wsStore.ts` / `canvasStore.ts` |
| **框架层(通用)** | agent 编排、WS/HTTP 传输、Director 调度、画布。**不懂"爆款分析"是什么** —— 只知道有一组工具可调 | `server.py` / `transport/` / `pool.py` / `prompts/director.md` / `tools/cascade.py` |
| **内容创作模块** | 真正的业务:分析/改写/锚点/合规/成本/持久化。**不碰 WS/agent** —— 纯 service | `cascade/*.py` |

**接缝只有两处**:
1. `tools/cascade.py` = 框架层 ↔ 模块的**适配器**:把 cascade service 包成 Director 能调的
   tool,并负责把结果 `_push_ws`(→ `notify.send_to_user`)回前端。
2. `prompts/director.md` = 框架层用自然语言"知道"何时调哪个 cascade 工具(如见到
   `[selected_niche: generic]` 就调 `cascade_rewrite`)。

---

## 3. 端到端走查:「改成我的版本」(2026-06-01 上线链,已验证)

```
①前端  RewriteCTA 填主题点按钮
   → App.onTriggerRewrite(topic)
   → sendChatMessage("[selected_niche: generic][rewrite_topic: 港式菠萝包] 改成我的版本")
   → wsStore.sendCommand({type:"user_message"})  ──WS :8765──►
②框架层  ws_handlers.handle_user_message → agent_runner.run_agent → pool(LangGraph Director)
   → Director 读 director.md §0.6:[selected_niche: generic]+[rewrite_topic:]
   → tools/cascade.cascade_rewrite(analysis_id, niche="generic", topic="港式菠萝包")
③内容模块  cascade_rewrite → rewrite_service.request_rewrite
   → load_analysis(persistence) + rewrite.rewrite_for_niche(contract,"generic",{topic})
   → LLM(prompts/rewrite_generic.md)→ RewriteResult(script + shots)
④回推  cascade_rewrite → _push_ws({type:"rewrite_returned", rewrite}) → notify.send_to_user
⑤前端  wsStore "rewrite_returned" → canvasStore.setScript + setRewriteShots
   → CardStack 渲染「你的版本」(RewriteShotCard) +「拿去发」(PublishPackCard)
```

---

## 4. 新功能落点判断法

- 新「业务能力」(分析维度 / 改写逻辑 / 成本规则)→ 落 `cascade/`,纯 service,可单测。
- 要让 Director 能用 → `tools/cascade.py` 加 tool 包一层 + `director.md` 写触发条件。
- 要前端展示 → 加 `cards/*.tsx`,`wsStore` 接对应帧写进 `canvasStore`,`CardStack` 渲染。

**例:生成草稿图 leg** —— 后端 `cascade_generate_first_frame`(③④就绪),缺的纯粹是
**⑤前端**(RewriteShotCard 加生成按钮 + 渲染图 + 四态状态机)。是"半条腿已搭好、补前端"的活。

---

*配套:[`phase2_gap_analysis_2026-06-01.md`](phase2_gap_analysis_2026-06-01.md)(剩余 TODO)·
[`architecture_phase1_phase2_design_2026-05-31.md`](architecture_phase1_phase2_design_2026-05-31.md)(更细的通信/生命周期设计)。*
