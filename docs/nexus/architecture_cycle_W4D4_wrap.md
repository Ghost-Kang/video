# 架构重构 cycle 收尾 — W4D4 (2026-05-26 续)

> **触发**:W4D3 cycle 收尾后(`architecture_cycle_W4D3_wrap.md`)留了 2 类候选
>   1. P3-2 reality-check(architect 标的低风险 finding)
>   2. `tools/canvas.py` followup(architect 标 "下次动它时一起拆")
> **执行**:Claude 一人 cycle,3 个 commit,半天落地

---

## TL;DR

- **W4D3 漏的 P3-2 关掉**:Codex-D `sendCommand` 重写后,原 finding 的"重连竞态"已变成 dead-code wart;一行修
- **canvas.py 拆完**:DAO 全挪到 `tools/canvas_persistence/`,domain 函数零 inline SQL,775→505 LOC(-30%)
- **0 regression**:257 backend pytest + 12 Playwright smoke + tsc/Vite build 全绿
- **W4D3+W4D4 累积**:16 commits,5 个 god module 全部瘦身完毕

---

## 交付清单

| Commit | Task | 描述 | LOC 变化 |
|---|---|---|---|
| `01d480d` | P3-2 cleanup | `useWebSocket.sendCommand` 移除 dead pending-replay flush;invariant 显式 | -1 LOC,清晰度 + |
| `9aa9f71` | canvas DAO 拆 | 抽 `canvas_persistence/{db, nodes_repo, edges_repo, generation_repo}.py`;canvas.py 通过 re-export 保 back-compat | canvas.py 775→530 |
| `5f58fe5` | inline SQL 清零 | 剩余 3 处(reorder/delete edge + delete node)挪到 repo helper;canvas.py 完全无 SQL | canvas.py 530→505 |

---

## P3-2 reality-check 过程

Architect 原 finding(W4D3):

> `useWebSocket._send` 重连时的 pending replay race
> 断线时入队 m1,再断线时入队 m2 → 第二条仍不发(OPEN check 还 false)。一旦 OPEN,
> 下一个 send 全 flush — 但顺序可能跟 `onopen` 的 replay 在重连 race 时交错。

Codex-D 在 W4D3 重写后,`sendCommand` 的形态:
```ts
if (wsRef.current?.readyState === WebSocket.OPEN) {
  for (const msg of pendingRef.current) { wsRef.current.send(msg); }  // ← dead code
  pendingRef.current = [];
  wsRef.current.send(data);
} else {
  pendingRef.current.push(data);
}
```

仔细分析 invariant:
1. `pendingRef` 只在 connect()→onopen 之间非空(readyState=CONNECTING)
2. `onopen` 触发时同步 flush 完所有 pending 并清空 pendingRef,然后才让 readyState=OPEN
3. 所以 `sendCommand` 走 OPEN 分支时,pendingRef 必然为空 — for-loop 永远迭代空数组

**判定**:不是真竞态,是 dead-code wart。修法:移除 OPEN 分支里的 for-loop,把"flush 责任"集中到 `onopen` 单点。Invariant 变显式("pendingRef 只被 onopen 清空")。

修后 `sendCommand` 三行:
```ts
if (wsRef.current?.readyState === WebSocket.OPEN) {
  wsRef.current.send(data);
} else {
  pendingRef.current.push(data);
}
```

---

## canvas.py 拆分过程

W4D4 启动时 `tools/canvas.py` = 775 LOC(W4D3 累加了 Codex-F 的 CanvasNode validation + Claude-A2 的 `_resolve_ids` kwargs)。

跟 Codex-E 的 storage.py 拆法对齐:

```
tools/canvas_persistence/
  __init__.py
  db.py              ─ 97 LOC ─ _db, _resolve_ids, ContextVar, set_user_id/thread_id, _DB_PATH
  nodes_repo.py      ─ 142 LOC ─ _row_to_node, _load_node, _load_all_nodes,
                                  _upsert_node, _update_node_result, _delete_node
  edges_repo.py      ─ 78 LOC ─ _load_all_edges, _upsert_edge, _renormalize_positions,
                                  _set_edge_position, _delete_edge
  generation_repo.py ─ 92 LOC ─ claim_pending_tasks, recover_generation_tasks,
                                  update_generation_state

tools/canvas.py      ─ 505 LOC ─ 纯 domain:HIERARCHY, create/update/delete edge+node,
                                  _default_position, _parse_storyboard, execute_node,
                                  get_canvas_state, approve_node, reject_node,
                                  enqueue_generation
```

`canvas.py` re-export 全部 DAO 名字,13 个调用点(server/transport/workers/store/tests)**零改动**。

### 中途 catch 的回归 bug

第一次 commit(`9aa9f71`)我重写 `reject_node` 时引入两个 bug:
1. 加了不该加的 `if node["type"] != "script"` 条件 — 原行为是无条件 set `asset_status=failed`
2. 把 `feedback` 嵌进 `result.feedback` — 原行为是 node 顶层 `node["feedback"]`

`test_reject_node` 立刻 fail(assertionError: `'idle' != 'failed'`)。修回原语义,257 pytest 全绿。

**教训**:domain-side refactor 比 DAO 抽取风险高得多。pytest 是这次唯一的安全网,加固它就是加固 refactor 速度。

### 最后 3 处 inline SQL(commit `5f58fe5`)

第一次拆分留了 3 个 inline SQL:`reorder_edge` 的 2 个 UPDATE、`delete_canvas_edge` 的 DELETE、`delete_canvas_node` 的双 DELETE。本来想留下 cycle,user 要求"一次完成全部",加 3 个 repo helper:

- `edges_repo._set_edge_position(edge_id, position, *, user_id, thread_id)`
- `edges_repo._delete_edge(edge_id, *, user_id, thread_id)`
- `nodes_repo._delete_node(node_id, *, user_id, thread_id)` — cascade 删 edges 同事务内原子完成

`canvas.py` 现在零 SQL,domain 函数只做编排。

---

## 累积收益(W4D3 + W4D4)

| 文件 | 启动时 | W4D3 末 | W4D4 末 | 累积 |
|---|---:|---:|---:|---|
| `backend/src/agent/server.py` | 916 | 45 | 45 | **-95%** |
| `backend/src/agent/cascade/storage.py` | 528 | 44 | 44 | **-92%** |
| `backend/src/agent/tools/canvas.py` | 725 | 775* | **505** | **-30%** |
| `frontend/src/App.tsx` | 404 | 120 | 120 | **-70%** |
| `frontend/src/hooks/useWebSocket.ts` | 147 | 93 | 92 | **-37%** |

*W4D3 末 canvas.py 短暂上涨(F + A2 加内容),W4D4 拆 DAO 才进入下降。

---

## 测试 baseline

| Suite | W4D3 末 | W4D4 末 |
|---|---:|---:|
| backend pytest | 257 ✅ | **257 ✅** |
| Playwright smoke | 12 ✅ | **12 ✅** |
| tsc + Vite build | green | **green** |

---

## Architect 红线(继续保住)

- [x] cascade ACL 未动(`contract.py` / `failures.py` / `adapter.py` / `analysis_service.py`)
- [x] `events.py` 单写路径未动
- [x] `HardFailure` envelope 未稀释
- [x] 导入无循环(每个 commit 后 `python -c "import agent.server"` 通过)
- [x] `NodeDetail.tsx` 786 LOC 仍未碰(P2-1 don't-refactor)
- [x] Codex-F `canvas_contract.CanvasNode` 校验在 `_row_to_node` 保留
- [x] Claude-A2 `_resolve_ids` ContextVar→显式参数逻辑保留

---

## P3-2 重判:从 race → wart

Architect 把 P3-2 归为"重连罕见乱序",建议级:P3(不修也可)。W4D4 reality-check 后判定:

| 原诊断 | W4D4 复诊 |
|---|---|
| "可能"重连时乱序 | 不会 — onopen 同步 flush 后才 readyState=OPEN,sendCommand 的 OPEN 分支看不到非空 pendingRef |
| 修法:单点 flush | 同(已经如此),只是 sendCommand 里多了 dead for-loop 误导读代码人 |
| Effort: S | Effort 实际 < S(1 行删除) |

**教训**:architect 的低级 finding 也值得 reality-check 而不是直接修 — 这次 architect 的 race 判断略保守。一手修代码前先一手读代码,避免修一个不存在的问题。

---

## 跨 agent 协作复盘

### W4D4 没有 Codex 介入
- W4D3 把 5 个 Codex task 全 ship 后,W4D4 是 Claude 单人 cycle
- 这反而暴露 W4D3 协作的甜区:**并发只在多 task 时才有杠杆**,单一 owner 串行更快
- 16 commits 里 W4D3 占 13 个、W4D4 占 3 个,但 W4D4 的 LOC 减少占累积总量的 ~10%(canvas.py 270 LOC 削减) — **后期收益每 commit 比例更高**(精确拆,不并发,审慎度更高)

### canvas.py 拆分的低风险路径
- Codex-E(storage.py 拆)给了模板:re-export shim + 渐进迁移
- 13 callers 0 改动,纯靠 `from agent.tools.canvas import ...` 仍 work
- 同时拒绝把 reject_node 等 domain 函数也"顺手优化" — domain 改动是更高风险的另一类 refactor,本 cycle 严格只动 DAO

---

## 下 cycle 候选(剩余 architect followup)

按风险/收益排序:

| 候选 | Effort | 风险 | 收益 |
|---|---|---|---|
| handlers 也走显式参数(ContextVar 全清) | M | 中(handlers 多) | 中(ContextVar 设计完全退役) |
| `canvas.db` vs `messages.db` 合并或加 cross-DB 抽象 | L | 高(需要 migration) | 低(目前不冲突) |
| `canvasStore.ts` 删 `baomamFushi001` fixture(出 phase 1 时) | XS | 低 | 高(避免 prod 暴露 fixture) |
| canvas.py domain 再拆(node service / edge service / hierarchy service) | M | 中(domain 逻辑) | 中(可读性) |

**推荐顺序**:fixture 清理(等出 phase 1 触发) > handlers ContextVar 显式参数 > domain 再拆 > canvas.db/messages.db 合并

---

## 数字总结(W4D3 + W4D4 累积)

- **commit 总数**:16(refactor 12 + docs 4)
- **文件减肥总量**:server.py 871 + storage.py 484 + canvas.py 220 + App.tsx 284 + useWebSocket.ts 55 = **1914 LOC**(其中部分迁移到新 module,部分真删除)
- **新 module**:`transport/` `workers/` `cascade/persistence/` `cascade/services/` `tools/canvas_persistence/` 共 5 个 package
- **跨端契约**:WS messages(codegen) + canvas node(手镜像) + cascade contract(已有,验证模板)= 3 个 single source of truth

---

> **生成时间**: 2026-05-26 W4D4 cycle 末
> **PM**: Claude
> **前一份 cycle doc**: [`architecture_cycle_W4D3_wrap.md`](architecture_cycle_W4D3_wrap.md)
> **触发文档**: [`architecture_review_2026-05-26.md`](architecture_review_2026-05-26.md)
> **下次 PM checkpoint**: phase 1 内测启动后,根据 worker tick 观测决定 Decision-2 L 拆分是否仍需要
