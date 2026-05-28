# Codex handoff — W5D3-T2: dock 收尾 + Risk 2 messages overlay + URL truncate

**Owner**: Codex
**Source**: [W5D3 cycle index](_index_W5D3.md)
**优先级**: 🟡 中 (desktop cohort 不阻塞; touch 用户撞到再升 P0)
**Effort**: M (3-4h)
**Dependencies**: 无 (跟 Claude T1 文件不冲突)

---

## 0. 你做什么

UX Architect agent 完成 dock 重构后, 留 3 个收尾 + 1 个 Risk:

1. **Risk 2 解决**: dock 内 messages history 在 touch device 上跟 main CardStack scroll 争。修法: refine state 时 messages history 抽到 dock **上方 overlay**, 不再 dock 内部 scroll
2. **URL bubble truncate UX**: 当前 break-all 长 URL 占满一行,founder 反馈不美观。改成中段省略 (`...` middle ellipsis) + click 展开完整
3. **dock 收起/展开切换**: 当前 chat FAB 收起后没法重新打开 dock (只有 click FAB), 加 ESC 关 / drag 把手 / 双击 chevron 这些细节
4. **failed state retry CTA 联动**: 「再试一条样本」按钮点了应该自动填充输入或直接发, 当前 (UX agent ship 时) 还没接上完整 onSend pipeline

---

## 1. 目标文件

| 文件 | 操作 |
|---|---|
| `frontend/src/components/ChatPanel.tsx` | refine state messages history 抽出 dock 内; 加 drag 把手 chevron; failed retry CTA 真发 sample URL |
| `frontend/src/components/chat/MessagesOverlay.tsx`(新) | 半透明 overlay, 位于 dock 上方 max-h-[40vh], 自己内部 scroll, 点 dock 任何位置自动关 |
| `frontend/src/lib/urlDisplay.ts`(新) | `truncateUrlMiddle(url, totalChars=50)` 中段省略 helper |
| `frontend/src/lib/cardCopy.ts` | 加 messages_overlay_close / url_show_full 等 |

---

## 2. Risk 2 — messages overlay 设计

### 当前结构
```
<dock max-h-50vh>
  <header chevron />
  <div flex-1 overflow-auto>     <-- messages history 在这, 跟 CardStack scroll 争
    {messages.map(...)}
  </div>
  <footer quickChips + input />
</dock>
```

### 新结构
```
<main flex-1 overflow-y-auto>
  <CardStack />
</main>
{messagesOverlayOpen && (
  <MessagesOverlay anchored="bottom" max-h-40vh class="absolute bottom-[dock-height]">
    {messages.map(...)}
  </MessagesOverlay>
)}
<dock>
  <header>
    <h3>{stateTitle}</h3>
    <button onClick={toggleMessages}>历史 ▲ ({messages.length})</button>  <-- 新
  </header>
  <footer />  <-- 只有 chips + input, 没 messages 内部 scroll
</dock>
```

### MessagesOverlay.tsx 行为

- `position: fixed, bottom: <dock height + 8px>, left: sidebar 宽, right: 0`
- 内部 `max-h-[40vh] overflow-y-auto`
- 半透明 backdrop `bg-stone-50/95 dark:bg-stone-900/95 backdrop-blur-sm`
- click outside (dock 之外) 自动关
- ESC 键也关
- 默认收起 (大部分时间用户在看 CardStack, 不在看历史)
- "历史 ({N})" 数字 = 当前 messages.length

### 测试

- `chat/__tests__/MessagesOverlay.test.tsx`: render + 默认 hidden + 点 「历史」 toggle 显示 / 隐藏 + ESC 关
- ChatPanel test: refine state 不再 包含 .map(messages) inline render, 改成 toggle 按钮 + 单独 overlay 组件

---

## 3. URL truncate UX

### urlDisplay.ts helper

```ts
export function truncateUrlMiddle(url: string, maxChars = 50): string {
  if (url.length <= maxChars) return url;
  const half = Math.floor((maxChars - 3) / 2);
  return url.slice(0, half) + "…" + url.slice(-half);
}
```

### ChatPanel.tsx user bubble

```tsx
{m.content.startsWith("http") && m.content.length > 50 ? (
  <UserUrlBubble url={m.content} />
) : (
  m.content
)}
```

`UserUrlBubble`:
- 默认显示 `truncateUrlMiddle(url, 50)`
- 点击切换显示完整 / 截断
- 加 hover tooltip 完整 URL

### 测试

- `chat/__tests__/UserUrlBubble.test.tsx`: 50 字符内不截; >50 中段省略; click 切换

---

## 4. dock 收起/展开 polish

当前 `App.tsx` 用 `chatOpen` state 切。改进:

- ESC 收起 dock (focused state 不在 input/textarea 时)
- 头部 chevron 双击 / 单击切换
- 进 idle 状态时默认收 dock 高度到 80px (不显示 hint, 给 CardStack 更多空间)
- 进 running / failed / refine 自动 expand

加到 `ChatPanel.tsx`:
```tsx
useEffect(() => {
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape" && !(document.activeElement instanceof HTMLInputElement || document.activeElement instanceof HTMLTextAreaElement)) {
      onToggleCollapse();
    }
  };
  window.addEventListener("keydown", onKey);
  return () => window.removeEventListener("keydown", onKey);
}, [onToggleCollapse]);
```

---

## 5. failed retry CTA 联动

UX agent 现在的 failed state 有 「再试一条样本」chip,但 click 之后**没真发**。让它真的:
1. 从 SAMPLES 数组随机抽一条
2. 调 `setFailure(null)` 清掉错误状态
3. 调 `onSend(sample.url)` 触发 cascade
4. 同时 `useNicheStore.setNiche(sample.niche)`

参考 `frontend/src/components/onboarding/SampleUrlChips.tsx` 现有逻辑。

---

## 6. 边界 / 禁区

- **不动 backend** — 这是纯前端 cycle
- **不动 AnalysisProgress.tsx** — Claude lane (T1 真实 progress events) 改这个
- **不动 wsStore.ts 的 analysis_progress case** — Claude lane 加
- **不动 cardCopy.ts 已有 side_*** keys** — 已 ship 别覆盖
- **不引入 framer-motion / 任何动效新 deps** — 用现有 Tailwind transition

---

## 7. 验收 checklist

- [ ] frontend vitest ≥175 (baseline 170 + 5: MessagesOverlay 2 + UserUrlBubble 2 + ChatPanel refine state 重构 1)
- [ ] tsc clean
- [ ] FORBIDDEN_TERMS 新文案过审
- [ ] touch device 上 dock 跟 CardStack scroll 不冲突 (手动验)
- [ ] 长 URL bubble 默认中段省略, click 可展开
- [ ] ESC 收起 dock (不在 input focus 时)
- [ ] failed 「再试一条样本」chip 真发 sample URL + 清 failure 状态

---

## 8. 提交规范

3 个 commit:

```
feat(frontend): W5D3-T2 messages overlay above dock (Risk 2 touch scroll fix)
feat(frontend): W5D3-T2 URL bubble middle-ellipsis + dock collapse polish
feat(frontend): W5D3-T2 failed-state retry CTA wired to sample URL pipeline
```

Push `gk/main`。

---

**Owner sign-off**: Codex
**Estimated**: 3-4h
