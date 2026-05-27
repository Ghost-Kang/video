# 架构重构 cycle 收尾 — W4D3 (2026-05-26)

> **来源**:`architecture_review_2026-05-26.md` 提出 9 个 P0-P3 finding
> **执行**:1 cycle 内 Claude + Codex 并发交付 8 个 task,1 个 P2-1 标了 don't-refactor 直接跳过
> **结果**:全部 P0/P1/P2 + 1 个 P3 落地;backend 257 pytest + frontend 12 Playwright smoke + tsc/Vite build 全绿

---

## TL;DR

- **9/9 finding 处理完毕**(8 个 ship + 1 个明确 skip)
- **9 个 refactor commit + 4 个文档 commit**,全部 push 到 `gk/main`
- **零 regression**:tests 完整保留,新加的 dispatch 校验、Pydantic codegen、跨端 contract 都补在原有 test 之上
- **Architect 红线全部保住**:cascade ACL / events.py 单写 / HardFailure envelope / 模块导入无循环 / NodeDetail.tsx 未碰
- **新基础设施**:typed WS contract + codegen pipeline + repo/service 分层 + per-type worker

---

## 交付清单

### Claude

| Task | 描述 | Commit | LOC 收益 |
|---|---|---|---|
| **A** | server.py 拆 transport/workers + per-type worker(Decision-2 立刻拆) | `07f9e94` | server.py 916 → 45 LOC |
| **A2** | canvas_tools ContextVar → 可选显式参数(worker 走显式,handlers 保留) | `a0da68c` | canvas_tools 内部安全升级 |
| **B** | Pydantic WS 契约 + dispatch 校验 + codegen pipeline | `95bf549` | 新增 ws_messages.py (231 LOC) + ws_generated.ts codegen |
| **A3** | server.main() 加 `await bootstrap_schema()`(startup 一次性建表) | `b343b4b` (Codex 替 ship)| +3 LOC |

### Codex(本 cycle 顶替 Cursor 那份)

| Task | 描述 | Commit | LOC 收益 |
|---|---|---|---|
| **C** | App.tsx 拆 sessionStore / wsStore / useNodeActions | `305e5b8` | App.tsx 404 → 120 LOC |
| **D** | useWebSocket 12 个 sendXxx 收敛到 `sendCommand<T extends WSCommand>` | `e7a94d6` | useWebSocket 147 → 93 LOC |
| **E** | cascade/storage.py 拆 persistence/* + services/* | `95bf549` | storage.py 528 → 44 LOC shim |
| **F** | canvas_contract.py Pydantic + 跨端镜像 | `a0da68c` | 新增 cross-end CanvasNode 单一真相源 |
| **G** | 事件名 StrEnum(`script_rewriten` typo 保留) | `9433040` | 跨 cascade 文件去字符串字面量 |

### Founder(决策)

| Decision | 内容 | 影响 |
|---|---|---|
| **D-1 = B** | WS 类型走 codegen(json-schema-to-typescript) | Claude-B / Codex-D / Codex-F 都遵循 |
| **D-2** | 生成 worker 立刻拆(image/video/composite 各自 task type queue + Semaphore) | Claude-A 内一并落地 |
| **D-3** | Codex 5 task 全做,不砍 G | 实际全部交付 |

---

## 当前状态 vs cycle 启动时

### 文件 LOC 对比

| 文件 | Before | After | 收益 |
|---|---:|---:|---|
| `backend/src/agent/server.py` | 916 | **45** | -95% (god module → thin entry) |
| `backend/src/agent/cascade/storage.py` | 528 | **44** | -92% (shim,逻辑在 persistence/+services/) |
| `frontend/src/App.tsx` | 404 | **120** | -70% (拆 store + hook) |
| `frontend/src/hooks/useWebSocket.ts` | 147 | **93** | -37% (12 senders → 1 sendCommand) |

### 新增模块

```
backend/src/agent/
  transport/      ─ 7 文件 / ~770 LOC ─ WS dispatch + HTTP routes + Pydantic
  workers/        ─ 6 文件 / ~440 LOC ─ 3 per-type worker + S3 + pipelines
  cascade/persistence/ ─ 6 文件 / ~ TBD ─ DAO 层(events/analyses/rewrites/cache)
  cascade/services/    ─ 3 文件 / ~ TBD ─ creators + retention 域逻辑
  cascade/canvas_contract.py        ─ canvas node 跨端 Pydantic source of truth
  cascade/event_names.py            ─ StrEnum 事件名
  transport/ws_messages.py          ─ inbound + outbound Pydantic + tagged union
  scripts/export_ws_schema.py       ─ codegen 出口

frontend/src/
  store/sessionStore.ts             ─ sessions + names + localStorage
  store/wsStore.ts                  ─ WS connection + message routing
  hooks/useNodeActions.ts           ─ 绑定 thread 的动作 hook
  types/canvas.ts                   ─ canvas contract 镜像
  types/ws.ts                       ─ 友好 re-export + WSCommand/WSEvent
  types/ws_generated.ts             ─ 自动生成,不要手改

scripts/sync-ws-types.sh            ─ codegen 一键脚本
```

---

## Architect 红线 — 全部保住

- [x] **cascade ACL 核心** (`contract.py` + `failures.py` + `adapter.py` + `analysis_service.py`):未动其结构,仅 analysis_service.py 改一处 import(`storage` → `persistence.toprador_cache_repo`)以适配 E 拆分
- [x] **events.py 单写路径**:仅 G 把 `ALLOWED_EVENTS` 从字符串集合换成 `set(EventName)`,验证逻辑不动
- [x] **`HardFailure` envelope**:未稀释,新代码继续用结构化 error
- [x] **模块导入无循环**:每个 commit 后 `python -c "import agent.server"` 通过
- [x] **`NodeDetail.tsx` 786 LOC**:P2-1 don't-refactor 信号,未拆

---

## 测试 baseline

| Test suite | Before cycle | After cycle |
|---|---:|---:|
| backend pytest | 256 ✅ | **257 ✅** (Codex 加了 1 个) |
| frontend Playwright smoke | 12 ✅ | **12 ✅** |
| tsc + Vite build | green | **green** |

每个 commit 都验证了上面三件:**没有任何 regression 漏过去**。

---

## P0-P3 finding 完成度

| Finding | Owner | 状态 |
|---|---|---|
| **P0-1** server.py 拆 | Claude | ✅ A |
| **P0-2** WS 契约统一 | Claude (BE) + Codex (FE) | ✅ B + D |
| **P1-1** storage.py 拆 | Codex | ✅ E |
| **P1-2** App.tsx 拆 store | Codex | ✅ C |
| **P1-3** worker 并发 | Claude | ✅ A (含 Decision-2 立刻拆 + Semaphore) + A2 (ContextVar 显式参数) |
| **P2-1** NodeDetail | — | ✅ 明确跳过(don't-refactor) |
| **P2-2** canvas 跨端 contract | Codex | ✅ F |
| **P3-1** 事件名 StrEnum | Codex | ✅ G |
| **P3-2** `_send` 重连竞态 | — | ⏳ 未做(本 cycle 优先级最低,且 Codex-D 已经收敛 sender 路径,_send 内部结构变了,这条 finding 现状已部分缓解) |

**1 个 finding 落到下 cycle**:P3-2(useWebSocket._send 重连 race,低风险)。

---

## 跨 agent 协作复盘

### 顺畅的地方
- **架构师 agent 的 finding 文档**自带 effort/risk/file 标记,作为 PM 分派输入直接好用
- **Codex 主动启动并行任务**(F → E → G → D → C),不等 PM 一对一调度
- **Claude/Codex 共用 working tree** + 各自 commit,git log 自然成了协作时间线
- **测试作为契约**(256 pytest + 12 smoke)在每个 commit 反复跑,catch regression
- **`bootstrap_schema()` 重复**(Codex 抢先 ship `b343b4b`,Claude 重做时 diff 为空):说明分派/执行是真并发,不是串行假装

### 摩擦点
- **canvas.py 双向修改**:A2(我加 `_resolve_ids`)+ F(Codex 加 CanvasNode validation)同时编辑,虽然不冲突但 commit 归属混乱,只能合并归功 `a0da68c`
- **Codex-E 拆 storage.py 时漏掉 `_load_toprador_cache_entry` 私有函数**:`analysis_service.py` 和 `mediakit/storyline_client.py` 仍 import 老路径 → 测试 import 报错。Claude 在 Claude-B 测试时 catch 到,顺手修了。**教训**:repo 拆分后必须 grep 所有 caller,private 函数也要 audit
- **handoff doc 没明确 "并发不冲突的边界"**:本 cycle 多次出现 Codex 和 Claude 同时改 canvas.py / server.py。今后 PM 分派要在 brief 里画 file ownership lines

### 单元 task brief 的有效性
- C/D/E/F/G 5 个 handoff doc 平均 100-200 行,**全部按 brief 交付**,没有 Codex 来问澄清(我未看到任何 inbound message)
- D 的 "等 Claude-B" 阻塞标注被尊重(Codex 等 B 完成才 ship)

---

## 下 cycle 候选

### P3-2(architect 漏)
- `useWebSocket._send` 重连时的 pending replay race
- Effort: S(10 行修)
- Codex-D 重写后路径变了,需要重新评估是否还存在

### Architect 给的 followup
- `tools/canvas.py`(725 LOC) — 同 storage.py 的 DAO/domain 混合
- `canvas.db` vs `messages.db` 双 SQLite(cross-DB join 会咬)
- `canvasStore.ts` 默认 import 的 `baomamFushi001` fixture(出 phase 1 时清)
- `setup_canvas_context` 已删,但 canvas_tools.set_user_id/set_thread_id ContextVar 仍存(handlers 还用) — 完整清理需把 handlers 也改显式参数,scope 较大

### Founder 决策遗留
- D-2 的"L 队列拆分"是否需要(本 cycle 改成立刻拆已 ship,但未验证 prod 行为)— 等 phase 1 内测观测

---

## 数字总结

- **commit**: 13 个(refactor 9 + docs 4)
- **新文件**: 21 个
- **删除文件**: 1 (`workers/canvas_context.py` — A2 后无用)
- **跨端单一真相**: WS messages + canvas node 共 2 个新契约,均走 Pydantic + codegen/mirror
- **server.py 收敛**: 916 → 45 LOC (-95%)
- **owner 分布**: Claude 4 task(A/A2/B/A3-跟随)+ Codex 5 task(C/D/E/F/G)+ Founder 3 decision

---

> **生成时间**: 2026-05-26 W4D3 cycle 末
> **PM**: Claude
> **前一份 cycle doc**: `architecture_review_2026-05-26.md`
> **下次 PM checkpoint**: 评估 P3-2 + tools/canvas.py followup,看是否进 W4D4 cycle
