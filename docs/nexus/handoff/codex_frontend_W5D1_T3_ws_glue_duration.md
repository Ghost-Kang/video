# Codex handoff — W5D1-T3: WS event 接入 + Landing 时长提示

**Owner**: Codex
**Source**: [W5D1 cycle index](_index_W5D1.md)
**优先级**: 🔴 高(T2 部分阻塞,先把 wsStore 接好,T2 才能用真实事件回包)
**Effort**: S (1.5h)
**Dependencies**: 无

---

## 0. 你做什么

后端 cycle 新增了 1 个 WS event 类型 + 修改了 analysis 失败的 friendly chat message。前端这边需要:

1. **wsStore 加 `analysis_answer_returned` 事件 case** — 把 `cascade_ask` 的回复路由到 ChatPanel(作为 agent message 渲染)
2. **Landing UrlFallback 输入框下方加时长提示** — 静态文案,无逻辑
3. **`cardCopy.ts`** 加几个新文案键(下方清单)
4. **失败提示** — 后端 duration_too_long / too_short / 视频私有等 HardFailure 经 chat 回 user,确认前端 ChatPanel 能正常渲染 markdown(已支持,不动)

**不做**:不写新组件(那是 T2 Cursor),不动 canvasStore.shots(那是 T1 Claude)。

---

## 1. 目标文件

| 文件 | 操作 |
|---|---|
| `frontend/src/store/wsStore.ts` | 加 1 个 case `analysis_answer_returned` |
| `frontend/src/components/landing/UrlFallback.tsx` | 输入框下方插入 `<p className="text-[11px] text-stone-500 mt-2">建议 ≤ 3 分钟·最佳 15-90 秒</p>` |
| `frontend/src/lib/cardCopy.ts` | 新增 4 个键(下方清单) |

---

## 2. wsStore.ts 新 case 实现

```ts
case "analysis_answer_returned": {
  // cascade_ask tool 的返回 → 渲染成一条 agent message
  // 后端 Director 还会发一份 agent_response,但 ws push 的 answer 更结构化
  // 这里我们 prefer 这条,避免重复
  const { addMessage } = useCanvasStore.getState();
  addMessage("agent", event.answer);
  break;
}
```

> 注: `analysis_answer_returned` event 已在 `ws_generated.ts` 中(由 backend cycle 触发 sync-ws-types 生成),无需手编 type。直接 `event.answer` 拿。
>
> **去重问题**: backend Director 看到 `cascade_ask` tool 返回后,prompt 要求「把 answer 原文回 chat」。所以 ws 会先收到 `analysis_answer_returned`(我们 push 的),再收到 `agent_response`(Director chat 输出,可能就是同一段)。**对策**: 我们 push 后 wsStore 在 0.5s 内 mark 一个 `lastAnswerEcho` flag,`agent_response` case 收到时如果内容前 50 字相似就 skip addMessage。详见下方 patch。

```ts
// 顶部 zustand state 加:
lastAnswerAt: number | null;
lastAnswerSnippet: string | null;

// analysis_answer_returned case 内,addMessage 后:
set({ lastAnswerAt: Date.now(), lastAnswerSnippet: event.answer.slice(0, 50) });

// agent_response case 内,addMessage 前:
const last = get();
if (
  last.lastAnswerAt !== null &&
  Date.now() - last.lastAnswerAt < 5000 &&
  last.lastAnswerSnippet &&
  event.content.startsWith(last.lastAnswerSnippet)
) {
  set({ lastAnswerAt: null, lastAnswerSnippet: null });
  break; // skip — already echoed by analysis_answer_returned
}
```

如果觉得 dedup 逻辑复杂,**简化版**:`agent_response` 始终渲染,不渲染 `analysis_answer_returned`(WS push 只用作 telemetry / 未来扩展)。这样 zero risk。**推荐用简化版**,把 dedup 留到下个 cycle。

---

## 3. Landing UrlFallback 静态提示位置

在 `<form onSubmit={submit}>` 内,输入框 + 提交按钮 *之后*,加:

```tsx
<p className="mt-2 text-[11px] text-stone-500 dark:text-stone-400 text-center">
  {COPY.duration_hint}
</p>
```

或者放在按钮**左下角**(看你设计感觉)。文案见下方。

---

## 4. 新 cardCopy 键

```ts
duration_hint: "建议 ≤ 3 分钟·最佳 15-90 秒",
duration_too_long_fallback: "这条视频过长,建议先剪到 3 分钟内再来分析",
duration_too_short_fallback: "视频太短,没什么可分析的",
ask_acknowledge: "好的,问下面这个",  // (供未来 UX 复用)
```

注:`duration_too_long_fallback` / `duration_too_short_fallback` 后端实际已经返回中文 friendly message,前端不会用到这俩 — **加上是为了将来如果切到客户端预校验时复用**。可以省略,但加了不增加成本。

**FORBIDDEN_TERMS audit**:全过(节点 / 锚点 / AI / Agent / 平台 / 工具 / 画布 / DAG)。

---

## 5. 验收

- `npm test -- --run` → 119 passed (no regression). 不需要新增测试 — wsStore case 是 wiring,UrlFallback 是静态文案。
- `npx tsc --noEmit` clean
- 手动:
  1. Landing 输入框下方有「建议 ≤ 3 分钟·最佳 15-90 秒」一行小字
  2. 贴一个 > 3 分钟视频 → Director chat 回「这条视频 X 秒太长...」(后端硬卡)
  3. 自由提问 chip(T2 出来后)发问 → chat 出现答案,**不重复**

---

## 6. 边界

- 不写新组件(T2 Cursor 写)
- 不改 canvasStore.shots(T1 Claude 改)
- 不动后端
- 不动 ShotCard / ScriptCard
- dedup 逻辑用**简化版**(skip `analysis_answer_returned`,只渲染 `agent_response`)— 详细版留到下个 cycle 如果出问题再加

---

## 7. 提交规范

commit: `feat(frontend): Codex-W5D1-T3 WS analysis_answer_returned case + Landing duration hint`
