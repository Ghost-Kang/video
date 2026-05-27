# 架构 cycle 收尾 — W4D5 (2026-05-26 续)

> **触发**:W4D4 cycle 末发现 Claude-B 的 Pydantic 验证后端落地了,但**前端 error 帧只 `console.warn`,用户看不见**。Cursor 在 W3+ 被 deprecated,本 cycle 重新激活。
> **执行**:Claude 半天 ship,Cursor 接 3 个 follow-on brief。

---

## TL;DR

- **Claude-B closure**:WS error 帧从 console.warn → 用户可见 toast,完成后端 Pydantic 验证的端到端闭环
- **Pydantic 契约现有直接测试**:从间接 0 → **39 unit tests**,covers discriminator / extra=forbid / min_length / Literal
- **Cursor 重新激活**,接 3 brief(reconnect banner / toast action / toast a11y),全部独立可并行
- **0 regression**:296 backend pytest + 92 vitest + 12 Playwright smoke + tsc/Vite build 全绿

---

## 交付清单(Claude 本 cycle)

| Commit | 内容 | 收益 |
|---|---|---|
| `fd72a92` | feat: WS error 帧 → toast(toastStore + ToastContainer + wsStore wiring) | +293 LOC, +9 vitest |
| `8d194ea` | docs: 3 个 Cursor handoff brief + index | +510 LOC docs |
| `e9a5a7d` | test: ws_messages Pydantic 契约 unit 测试 | +385 LOC, +39 pytest |
| `c01c72b` | test: transport context/notify + agent_runner.extract_text | +27 pytest |
| `b79a32e` | test: agent_runner.run_agent integration(mock LangChain stream) | +10 pytest |
| `f95d949` | test: workers/{s3, image_pipeline} | +25 pytest |
| `8d3d5d3` | test: workers/{video, composite}_pipeline | +20 pytest |
| `173f621` | test: workers/generation_worker(loop + recovery + idempotent start) | +20 pytest |

---

## 交付清单(Cursor 本 cycle)

3/3 brief 全部 ship:

| Task | 标题 | Commit | 收益 |
|---|---|---|---|
| **W4D5-T1** | WS 重连失败 → 持久 banner(useWebSocket 暴露 reconnectAttempt + 正向恢复 toast) | `9b84998` | +ConnectionBanner.tsx + wsStore connection state |
| **W4D5-T2** | Toast 加 recovery action 按钮(extends Toast model + wsStore 注入 reload action 给 malformed_json) | `9967512` | +ToastAction + 6 vitest |
| **W4D5-T3** | Toast 可访问性 polish(prefers-reduced-motion / ESC 关 focused toast / 32×32 触摸目标 / focus-visible ring) | `4d37347` | +RTL ToastContainer.test.tsx |
| _housekeeping_ | mark 3 brief Status: ✅ | `d8cb666` | docs only |

详见 [`_cursor_W4D5_index.md`](handoff/_cursor_W4D5_index.md)。

---

## 测试覆盖大补完(W4D5 续)

W4D5 启动时 backend pytest 256,最初只想做 Claude-B closure(toast)。期间扫描出
所有新建模块(transport/、workers/、cascade/persistence/、tools/canvas_persistence/)
都只有**间接**覆盖,没有直接 unit。决定一并补完。

新建测试文件 7 个,共 **+142 backend pytest**(256 → 398):

| 文件 | tests | 覆盖模块 |
|---|---:|---|
| `test_ws_messages.py` | 39 | Pydantic 13 inbound + 8 outbound + WSInbound 联合 + INBOUND_MODELS 注册表 |
| `test_transport_context.py` | 9 | WSCtx / send_json(中文 + multi-kwargs)/ canvas_data 三种状态 |
| `test_transport_notify.py` | 9 | _ws_registry register/unregister + notify_user 注册/未注册 + _safe_notify 异常吞咽 |
| `test_agent_runner.py` | 9 | extract_text 纯函数(str / part-list / 非 text 跳过 / fallback) |
| `test_agent_runner_run.py` | 10 | run_agent 集成(text/tool_call stream + ContextVar + save_message + 错误路径) |
| `test_workers_s3.py` | 9 | upload_bytes_to_s3 + download_and_upload 失败路径(httpx timeout/4xx/upload exception) |
| `test_workers_image_pipeline.py` | 16 | make_image_provider + get_ref_urls(真实 DB)+ process_image_task 全状态机 |
| `test_workers_video_pipeline.py` | 9 | submit param 传递 + 无 fallback 失败 + explicit user/thread |
| `test_workers_composite_pipeline.py` | 11 | parent collection(混合 image/video)+ ffmpeg/S3 失败 + happy path |
| `test_workers_generation_worker.py` | 20 | start_workers idempotent + _worker_loop tick + recover_one + apply_poll_result 4 branches |

**关键技巧**:`_worker_loop` 用 monkeypatched `asyncio.sleep` raise BaseException 后退出
(BaseException 穿透 `except Exception`);real asyncio.sleep 在 patch 前抓引用避免递归调用。

---

## Pydantic 契约 unit 测试覆盖明细

`tests/test_ws_messages.py` (+39):

| 测试组 | 覆盖 |
|---|---|
| **AuthMsg** (5) | happy / missing user_id / empty user_id / extra field / wrong type literal |
| **ListSessionsMsg** (2) | happy / 不需要 thread_id |
| **ExecuteNodeMsg** (6) | full / minimal / missing thread_id / empty thread_id / invalid node_type / video ok |
| **UserMessageMsg** (2) | happy / empty content rejected |
| **ReviewNodeMsg** (3) | approve / reject + feedback / invalid action |
| **ReorderEdgeMsg** (3) | default direction / explicit down / invalid direction |
| **UpdatePositionMsg** (3) | happy / int coords coerce / missing x |
| **UpdateNodeStatusMsg** (2) | default reviewing / invalid status |
| **OptimizePromptMsg** (1) | happy |
| **EdgeMsgs / SessionMsgs** (4) | create_edge / delete_edge / delete_session requires thread_id / get_session_state |
| **WSInbound discriminator** (5) | routes auth / routes execute_node / routes user_message / unknown rejected / missing discriminator rejected |
| **INBOUND_MODELS registry** (3) | type Literal 与 key 对齐 / auth 入 registry / 精确 key set |

---

## 测试 baseline 进展(累积)

| Suite | 启动时 | W4D3 末 | W4D4 末 | W4D5 末 |
|---|---:|---:|---:|---:|
| backend pytest | 256 | 257 | 257 | **398** (+142) |
| frontend vitest | 81 | 81 | 81 | **115** (+34) |
| Playwright smoke | 12 | 12 | 12 | **12** |
| tsc + Vite build | green | green | green | **green** |

frontend vitest +34 来自 toast 全套(9 toastStore + 3 wsStore.error + Cursor T2 加的 6 个 action + T3 加的 RTL ToastContainer 测试)。

---

## Architect 红线(继续保住)

- [x] cascade ACL 未动
- [x] events.py 单写路径未动
- [x] HardFailure envelope 未稀释(toast 是补充层,不替代 FailureBanner)
- [x] 导入无循环
- [x] NodeDetail.tsx 未碰(P2-1 don't-refactor)
- [x] canvas_contract.CanvasNode validation 保留
- [x] Claude-A2 `_resolve_ids` 显式参数逻辑保留

---

## Claude-B closure 复盘

W4D3 把 Pydantic 校验加到后端 dispatch(invalid_command / malformed_json 返结构化 error
帧)。但前端 wsStore.case "error" 只 `console.warn` — **后端契约保护对用户完全不可见**。

Cycle 内闭环:
- toastStore + ToastContainer 提供全局 transient 通知设施(复用在所有路由,包括 Landing)
- wsStore 把 error code 映射成中文 title:
  - `invalid_command` → "请求格式不对"
  - `malformed_json` → "数据格式不对"
  - 未知 code → "请求出错"(fallback)
- `bad_type` 字段进 toast body:`操作:execute_node` — 给开发者线索,不暴露 Pydantic 详细 message
- 9 vitest 单元验证 wiring 完整

**教训**:契约设计要看端到端。后端 + 前端 + UI 三层都到位才算 ship,不要因为后端测试通过就 declare done。

---

## Pydantic unit test 选型理由

为什么花一份 commit 加 39 个 unit test?

直接测试 vs 间接覆盖的对比:
- **间接**(test_ws_handler / test_server_ws_http)只测 server.handle 整体路径,Pydantic
  失败原因(missing field vs invalid literal vs extra field)被 `ValidationError` 吞掉
- **直接**测试可以分别验证每条 Pydantic 规则的边界

更关键:**Pydantic 是 single source of truth**。前端 ws_generated.ts 走 codegen,从这个文件出。
任何对 ws_messages.py 的破坏会顺着 codegen pipeline 静默污染前端。直接 unit 是这条链的第一道防线。

未来加新消息类型的流程:
1. 加 Pydantic model
2. **加直接 unit 测试**(在 test_ws_messages.py 加 TestXxxMsg 类)
3. `INBOUND_MODELS.set_test` 自动 catch 注册遗漏(test_registry_has_no_unexpected_keys)
4. 跑 `npm run sync:ws-types` 更新前端

---

## 跨 agent 协作复盘(W4D5)

### 新模式:Cursor 重新激活
- W3D3+ 之后 Cursor 因为"frontend 都被 Claude 接走"被 deprecated
- W4D5 Claude 集中精力做后端 + 主前端工作,周边 frontend polish 改路由到 Cursor
- 3 个 brief 写得**比 W4D3 Codex briefs 更细**(因为 Cursor 是 fresh 上手,不像 Codex 已经积累 phase 1 context)

### 教训:contract closure 比 contract ship 更重要
- Claude-B 在 W4D3 ship 时 256/256 pytest 全绿,看起来"完工"
- 但前端只 console.warn → 实际用户不感知
- W4D5 半天加 toast UI 才真闭合 — 这种 "ship 而未闭环" 应该在 PR 时被 catch
- 给以后类似工作的 checklist:**新 backend feature ship 时,frontend 上有可见显式信号了吗?**

### 测试缺口扫描
- 这次发现 ws_messages.py 0 直接测试 — 比 architect 当初的 finding 还狠
- 类似 audit 应该每个 cycle 末做一次:`grep -rE "from <new module>" tests/` 看哪些 module 没被直接 import 过

---

## 下 cycle 候选

### Phase 1 内测启动观察(主线)
- 2026-05-28 W4D1 founder 启动第一次 concierge
- 第一次 cohort 真实用 → 收集 toast / banner / reconnect 在真实网络下的表现
- 等 W4D7 周报对账 DM 回复率 vs 预测

### 残余 architect followup(优先级渐进)
- handlers ContextVar 显式参数(workers 已经走 explicit,handlers 还用 ContextVar)
- `canvasStore.ts` 默认 import `baomamFushi001` fixture(出 phase 1 时清)
- `canvas.db` vs `messages.db` 跨 DB join(目前不冲突,先放着)

### 测试覆盖率(已大幅补完,剩余空白都是低 ROI)
- ~`transport/notify.py`~ ✅ done(c01c72b)
- ~`transport/agent_runner.py::extract_text`~ ✅ done(c01c72b)
- ~`agent_runner.run_agent` integration~ ✅ done(b79a32e)
- ~`workers/{s3, image, video, composite}_pipeline}`~ ✅ done(f95d949 + 8d3d5d3)
- ~`workers/generation_worker._worker_loop`~ ✅ done(173f621)
- 剩下没直接测的:`transport/http_router::handle_http`(间接覆盖良好)、`ws_server.handle`
  dispatch(间接覆盖良好)— ROI 已边际,建议除非有 bug 发生否则不动

---

## 数字总结(W4D3 + W4D4 + W4D5 累积)

- **commit 总数**:**27**(refactor 12 + docs 5 + feat 2 + test 7 + fix 1)
- **测试增量**:backend **+142**(256→398),frontend vitest **+34**(81→115)
- **Cursor 重新激活并交付完整 cycle**:T1(banner)+ T2(toast action)+ T3(a11y polish)
- **新基础设施**:transport / workers / persistence / services / canvas_persistence / **toast** 共 6 个 package
- **跨端契约**:WS (codegen) + canvas (mirror) + cascade (mirror)= 3 个 + Pydantic 39 unit 保护
- **直接测试覆盖**:架构 review 起点 0 → 现在 **所有新建模块都有直接 unit / 集成**(只剩 http_router/ws_server.handle 是 dispatch 层间接覆盖)

---

> **生成时间**: 2026-05-26 → 2026-05-27 W4D5 cycle 跨日完结
> **PM**: Claude
> **前两份 cycle doc**: [`architecture_cycle_W4D3_wrap.md`](architecture_cycle_W4D3_wrap.md) · [`architecture_cycle_W4D4_wrap.md`](architecture_cycle_W4D4_wrap.md)
> **Cursor brief 入口**: [`handoff/_cursor_W4D5_index.md`](handoff/_cursor_W4D5_index.md)
> **下次 PM checkpoint**: phase 1 第一次 cohger run(W4D1 = 2026-05-28)/ founder DM 回复率对账(W4D7 = 2026-05-31)
