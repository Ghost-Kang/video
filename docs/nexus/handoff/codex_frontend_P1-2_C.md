# Codex handoff — Task C (P1-2 App.tsx 拆 store)

**Owner**: Codex
**Source**: `docs/nexus/architecture_review_2026-05-26.md` P1-2
**优先级**: 最高(整个 Codex bucket 里最大头,先做)
**Effort**: M (1-2 天)
**Dependencies**: 无 — 立即可开

---

## 0. 你做什么

`frontend/src/App.tsx` 现在 404 LOC,塞了 4 个不相关关注点:
- sessions state + localStorage 持久化(`:71-72, 178-224`)
- WS 入站消息路由 6 个 type 分支(`:103-172`)
- 布局 state(sidebar/chat open + viewport listener,`:73-87`)
- 节点动作 handler 6 个(`:256-329`)

每加一个 UI feature 都撞这一个文件 → 你要拆出 3 个 store + 1 个 hook,让 `App.tsx`
收敛到 layout shell。

---

## 1. 目标文件树

```
frontend/src/
  store/
    sessionStore.ts       # 新建
    wsStore.ts            # 新建(或 useWSConnection + useWSDispatch pair)
    canvasStore.ts        # 现有, 不动
  hooks/
    useNodeActions.ts     # 新建
    useWebSocket.ts       # 现有, 仅在 Codex-D 改
  App.tsx                 # 收敛到 ~100 LOC
```

---

## 2. 各文件契约

### `store/sessionStore.ts`

zustand-style(参考现有 `store/canvasStore.ts`),持有:

```ts
type SessionStore = {
  sessions: string[];            // thread id 列表
  names: Record<string, string>; // thread_id → display name
  setSessions: (s: string[]) => void;
  setNames: (n: Record<string, string>) => void;
  addSession: (tid: string) => void;
  deleteSession: (tid: string) => void;
  rename: (tid: string, name: string) => void;
  reset: () => void;
};
```

**localStorage 同步**:在 set 函数内部调 `localStorage.setItem(lsKey("sessions", userId), JSON.stringify(...))`。
`userId` 怎么拿 → 看下面"边界问题"。

**初始加载**:`useEffect` 在 App 内调一次 `store.setSessions(loadJSON(lsKey("sessions", userId), []))`。
或者把 userId 设计成 store 参数,store 创建后用 `subscribeWithSelector` 自动 persist。
我倾向简单:store 不知道 userId,App 在 user 变化时调 `reset() + setSessions(...)`。

**单测**:`store/__tests__/sessionStore.test.ts` — addSession 写入、deleteSession 移除、reset 清空。
不测 localStorage(那是 App 层职责),只测 store 内部状态。

### `store/wsStore.ts`(或两个 hooks)

把现在 `App.tsx:103-172` 的 onMessage switch 移过来。WS 入站 message 类型有 6 个:
- `session_list` → 写 sessionStore
- `session_state` → 写 canvasStore + messages
- `agent_stream` → append 到当前 streaming
- `agent_response` → 写 messages + 清 streaming
- `processing` → 设 loading=true
- `canvas_updated` → 写 canvasStore
- `prompt_optimized` → trigger 一次 NodeDetail 内 callback

**两种实现路径**(选一):

**(a) 单一 wsStore**:store 持有 `messages, streaming, thinking, loading` + dispatch 函数 + WS connect/send 方法。`useWebSocket.ts` 内部用这个 store。App.tsx 直接 `useWSStore()` 拿 state。

**(b) useWSConnection + useWSDispatch hook**:
- `useWSConnection()` 返回 `{ connected, send }`,内部维护 ws 实例。
- `useWSDispatch(threadId)` 注册 message handler,把入站消息分发到 sessionStore / canvasStore / 本地 state。

**推荐 (a)** — 更接近你现在的 zustand 风格,App.tsx 内 hook 调用少。

不管选哪种,**onMessage 在 App.tsx 里必须变空**(Architect 的明确要求)。

### `hooks/useNodeActions.ts`

封装 6 个动作 handler,绑定当前 `tid`:

```ts
type NodeActions = {
  handleReview: (nodeId: string, action: "approve" | "reject", feedback?: string) => void;
  handleExecuteNode: (nodeId: string, nodeType: NodeType, description: string, opts?: ExecuteOpts) => void;
  handleUpdateNodeStatus: (nodeId: string, status: NodeStatus) => void;
  handleOptimizePrompt: (nodeId: string, prompt: string, feedback: string) => void;
  handleCreateEdge: (source: string, target: string) => void;
  handleDeleteEdge: (edgeId: string) => void;
};

export function useNodeActions(threadId: string): NodeActions {
  const send = useWSStore(s => s.send);
  return {
    handleReview: (id, action, feedback) => send({ type: "review_node", thread_id: threadId, node_id: id, action, feedback }),
    // ...
  };
}
```

`NodeDetail` 改为接收 `actions: NodeActions` 整体,不再 6 个独立 callback prop。

### `App.tsx` 终态(目标 ~100 LOC)

```tsx
export default function App({ userId, onLogout }) {
  const { threadId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const isProView = searchParams.get("view") === "pro";

  const { sidebarOpen, chatOpen, toggleSidebar, toggleChat } = useLayoutState();
  const actions = useNodeActions(threadId);
  const wsConnected = useWSStore(s => s.connected);

  // mount-only effects: connect WS, hydrate sessionStore from localStorage
  useEffect(() => { ... }, [userId]);

  return (
    <PageShell ambient={false}>
      <Header onLogout={onLogout} connected={wsConnected} onToggleProView={toggleProView} ... />
      <div className="flex flex-1">
        {sidebarOpen && <Sidebar />}
        {isProView ? <Canvas actions={actions} /> : <CardStack actions={actions} />}
        {chatOpen && <ChatPanel onSend={...} />}
        <NodeDetail actions={actions} />
      </div>
    </PageShell>
  );
}
```

---

## 3. 边界问题与坑

- **userId 注入**:目前 `lsKey` 函数把 userId 编进 storage key。store 内部要知道 userId 才能 persist。最简单:store 暴露 `setUserId(uid)` → store 切 userId 时清空 + 重新 hydrate from localStorage。或者用 zustand `persist` middleware 配合 dynamic key。我倾向显式 `setUserId` (less magic)。
- **WS 重连**:现有 `useWebSocket` 的指数退避重连不要丢。wsStore 内部用同一套(或封装现有 hook)。
- **localStorage 命名空间**:`openrhtv_${userId}_${key}` 保持不变,别动 key 否则用户的本地 sessions 看起来全没了。
- **Optimistic state**:`App.tsx:288-301` 现在直接 `useCanvasStore.setState` inline 写乐观状态(execute_node 发送后立刻把节点设 generating)。这部分逻辑搬到 `useNodeActions.ts` 内,handler 发 WS 之前先 patch canvasStore。

---

## 4. 验收

**必过**:
1. `App.tsx` ≤ 120 LOC(留 20 buffer,但目标 100)
2. `frontend/e2e/` 12 个 Playwright smoke 全绿(`npm run test:e2e`)
3. `frontend/src/store/__tests__/sessionStore.test.ts` 加单测,vitest 全绿(`npm test`)
4. `NodeDetail` 接收 `actions: NodeActions` prop,不再传 6 个独立 callback
5. `App.tsx` 的 `onMessage` 函数体不再存在(分派全在 wsStore)

**手测**:
- 创建一个新 session → 出现在 Sidebar
- 删除一个 session → 从 Sidebar 消失,localStorage 也清
- 刷新页面 → sessions 列表恢复
- 切 dark mode → 持久化跨页

---

## 5. 不要碰

- `frontend/src/types/cascade.ts`(Codex-F 会单独动 canvas 类型)
- `frontend/src/hooks/useWebSocket.ts` 内部的 12 个 `sendXxx`(Codex-D 收敛)
- `frontend/src/components/NodeDetail.tsx`(只改 props 接收 `actions`,不重构内部 — Architect P2-1 标了 don't-refactor)

---

## 6. 提交规范

- 单个 commit 或拆 ≤3 个 commit(stores / hook / App.tsx 收敛)
- Commit msg 前缀:`refactor(frontend): Codex-C ...`
- PR 标题 / commit body 引用本文件路径

---

## 7. 完成后

更新 `docs/nexus/architecture_review_2026-05-26.md` 的 "PM 分派" 段落,在 Codex-C 后面打 ✅ + commit hash。
