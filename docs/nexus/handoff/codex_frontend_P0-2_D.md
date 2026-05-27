# Codex handoff — Task D (P0-2 前端 WS 类型镜像)

**Owner**: Codex
**Source**: `docs/nexus/architecture_review_2026-05-26.md` P0-2 + Founder Decision-1 (B=codegen)
**优先级**: 中(阻塞在 Claude-B,先做 C/E/F)
**Effort**: S (半天,Claude-B 之后)
**Dependencies**: **必须等 Claude-B 完成**(后端 Pydantic 模型 + codegen pipeline)

---

## 0. 你做什么

后端 WS 入站消息今天没 schema 校验(`server.py:497-669` 全是 `msg.get(...)` 字符串
访问)。前端的 12 个 `sendXxx` 也是手写 payload。Decision-1 决定用 codegen 同源,
**Claude-B 会先在后端定义 Pydantic 模型 + 配置 codegen 生成 TS**;你的工作是
**消费生成出来的 TS 类型**,把 `useWebSocket.ts` 的 12 个 sender 收敛成一个
typed `sendCommand`。

---

## 1. Claude-B 会给你交付什么

预期 Claude-B 会产出:
- `backend/src/agent/transport/ws_messages.py` — Pydantic 模型 + `WSInbound` tagged union(discriminator="type")+ `WSOutbound`
- `Makefile` target `make sync-ws-types` — 运行 datamodel-code-generator,输出到 `frontend/src/types/ws_generated.ts`
- 文档:消息类型清单(`AuthMsg`, `UserMessageMsg`, `ExecuteNodeMsg`, ...)

**等 Claude-B 推送后**,你拉一下:`make sync-ws-types`,确认 `ws_generated.ts` 出现。

---

## 2. 目标改动

### `frontend/src/types/ws.ts`(新)

re-export + 补充类型:

```ts
export * from "./ws_generated";
// re-export 也加一个 helper union 给 useWebSocket 用
import type { WSInbound, WSOutbound } from "./ws_generated";
export type WSCommand = WSInbound;  // 客户端发往后端
export type WSEvent = WSOutbound;   // 后端推给客户端
```

`ws_generated.ts` **不要手改**(make 重生成会覆盖)。

### `frontend/src/hooks/useWebSocket.ts`

现在 12 个 `sendXxx`:
```ts
const sendMessage = (threadId, content) => _send({ type: "user_message", ... });
const sendPosition = (update) => _send(update);
const sendGetSessionState = (threadId) => _send({ type: "get_session_state", ... });
// ... 9 more
```

收敛成:
```ts
const sendCommand = useCallback(<T extends WSCommand>(cmd: T): void => {
  _send(cmd);
}, [_send]);

return { connect, sendCommand, connected, connecting };
```

caller 改成:
```ts
ws.sendCommand({ type: "user_message", thread_id, content });
ws.sendCommand({ type: "execute_node", thread_id, node_id, node_type, description });
```

类型错配 → tsc 编译错。例:漏 `thread_id` 报 missing required property。

### `frontend/src/types/index.ts`

把现有手写的 `WSIncoming`, `WSPositionUpdate`, `WSReviewNode`, `WSExecuteNode`,
`WSOptimizePrompt`, `NodeStatus` 全部删除,改 re-export from `./ws`:

```ts
export type { WSEvent, WSCommand } from "./ws";
// 旧名做 alias 给现存 caller 用,直到 caller 全部迁移完
export type WSIncoming = WSEvent;
```

### 调用点更新

`grep -r "sendMessage\|sendPosition\|sendGetSessionState\|sendReviewNode\|sendExecuteNode\|sendUpdateNodeStatus\|sendOptimizePrompt\|sendCreateEdge\|sendDeleteEdge\|sendReorderEdge\|sendDeleteSession" frontend/src` 找全所有 caller,改成 `sendCommand({...})`。

主要 caller(Codex-C 完成后可能位置变了):
- `App.tsx`
- `hooks/useNodeActions.ts`(Codex-C 创建的)
- `store/wsStore.ts`(Codex-C 创建的)

---

## 3. 验收

**必过**:
1. `useWebSocket.ts` 只 export `connect`, `sendCommand`, `connected`, `connecting`(4 项)
2. `grep -c "sendMessage\|sendPosition\|sendReviewNode" frontend/src` = 0(全收敛)
3. `npm run build` 通过(tsc 严格类型检查 + Vite 构建)
4. `frontend/e2e/` 12 个 Playwright smoke 全绿
5. `frontend/src/types/ws_generated.ts` 存在且 不被手动 commit 修改(`.gitattributes` 可加 `generated` 标记,但不强求)

**手测**:
- 发一条消息 → 触发 user_message 命令 → 后端 Pydantic 验证通过(后端 log 不报 dropped)
- 故意构造 invalid command(在 dev console 调 `wsStore.send({ type: "fake" } as any)`)→ 后端回 type=error code=invalid_command 帧(Claude-B 实现这个)

---

## 4. 阻塞处理

如果 Claude-B 拖延,**先做一个 stub 版本**:
- 手写 `frontend/src/types/ws.ts` 镜像现有 12 个消息 type
- 改 `useWebSocket.ts` 用 stub union
- 等 Claude-B 推送后,替换 stub → `ws_generated.ts`

这样不会被阻塞死。但 stub 版本不要 commit 进 main,放在 feature branch。

---

## 5. 不要碰

- 后端 `ws_messages.py`(Claude-B 的范围)
- `ws_generated.ts`(自动生成)
- 任何 cascade 类型(`types/cascade.ts` 仍是手镜像 — 不强行改 codegen)

---

## 6. 提交规范

- Commit msg 前缀:`refactor(frontend): Codex-D ...`
- 引用 Claude-B 的 commit hash 在 body 里
