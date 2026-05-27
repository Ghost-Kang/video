# Cursor handoff — W4D5-T1 WS 重连失败持久 banner

**Owner**: Cursor
**Source**: W4D5 cycle index ([`_cursor_W4D5_index.md`](_cursor_W4D5_index.md))
**优先级**: 🔴 高(phase 1 内测中真实可能遇到网络抖动,先做)
**Effort**: M (1 天)
**Dependencies**: 无 — 立即可开

---

## 0. 你做什么

`useWebSocket.ts` 现在有指数退避重连(1s → 30s),`connected` / `connecting` 已暴露给
Header(显示一个绿/黄/灰点)。但是:

- **3+ 次连续重连失败**用户没有任何明显感知 — 只有 Header 角落的小灰点
- **重连成功**时也没正向反馈(从 disconnected → connected 切回时)
- toast 因为 ttl 自动消失,不适合表达"持续断连"这种状态

需要一个**持久 banner**(顶部条状,非 toast),只在 reconnect 试 ≥ 3 次仍失败时出现,
重连成功时立刻消失。

---

## 1. 目标文件

| 文件 | 操作 |
|---|---|
| `frontend/src/hooks/useWebSocket.ts` | 暴露 `reconnectAttempt: number`(已有 `retryRef.current`,提为 state) |
| `frontend/src/components/feedback/ConnectionBanner.tsx`(新) | 持久 banner 组件 |
| `frontend/src/main.tsx` | mount `<ConnectionBanner/>` 到 `<AppRoutes/>` 旁(同 `<ToastContainer/>`) |
| `frontend/src/store/wsStore.ts` | 可选:加 `reconnectAttempt` state,wsStore 暴露给 ConnectionBanner;**或** Banner 直接订阅 useWebSocket 返回值(更简单) |

---

## 2. 设计要求

### useWebSocket 改动

`retryRef.current` 已经在追 attempt 计数(scheduleReconnect 累加)。提到 state:

```ts
const [reconnectAttempt, setReconnectAttempt] = useState(0);

const scheduleReconnect = useCallback(() => {
  const attempt = reconnectAttempt + 1;
  setReconnectAttempt(attempt);
  ...
}, [reconnectAttempt, connect]);

// connect() 成功时 reset:
ws.onopen = () => {
  ...
  setReconnectAttempt(0);
};

// 返回:
return { connect, sendCommand, connected, connecting, reconnectAttempt };
```

注意:`useState` 的 stale closure 风险 — 推荐用 functional update `setReconnectAttempt(n => n + 1)`。

### ConnectionBanner 组件

```tsx
export function ConnectionBanner() {
  const { connected, connecting, reconnectAttempt } = useWSConnection();  // 你新建的 hook 或从 useWebSocket 透出

  // 阈值 = 3 次重连失败
  const show = !connected && reconnectAttempt >= 3;
  if (!show) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 z-[55] bg-amber-50 dark:bg-amber-950/90 border-b border-amber-200 dark:border-amber-900/50 px-4 py-2 text-center text-xs text-amber-900 dark:text-amber-200"
    >
      {connecting ? `正在重连…(第 ${reconnectAttempt} 次)` : `连接断开,${...}秒后再试`}
    </div>
  );
}
```

**z-index**:Toast 是 z-60,Banner 用 z-55,banner 永远在 toast 下面。

**消失逻辑**:`connected === true` → 不渲染。`reconnectAttempt` 在 onopen 重置后 banner 自动消失。

**正向反馈**:可选,connect 后第一次 onopen 时(检测从 disconnected 到 connected)pushToast({ kind: "info", title: "网络已恢复", ttlMs: 2000 })。

---

## 3. 验收

**必过**:
1. 模拟 3 次重连失败 → banner 出现(可在 dev console 强制断网或 mock useWebSocket return)
2. `connected === true` → banner 消失
3. `npm test` 92 + 你的新 unit 全绿
4. `npm run test:e2e` 12 smoke 全绿
5. `npm run build` tsc 通过

**E2E 测试建议**(可选,加分项):
- Playwright `page.routeWebSocket` 模拟 WS 不停断 → 第 3 次后 banner DOM 出现
- 然后 fulfill onopen → banner 消失

**单测**:
- 给 ConnectionBanner 写 vitest:mock `useWSConnection` 返回不同状态,断言 DOM 是否出现/消失

---

## 4. 边界

- **不要**改 reconnect 算法(指数退避保持原样)
- **不要**改 Header 的小灰点(那是另一个 indicator,banner 是补充而非替代)
- **不要**让 banner 阻断用户操作(纯视觉提示,不弹窗)

---

## 5. 提交规范

- Commit msg:`feat(frontend): Cursor-W4D5-T1 持久重连 banner`
- 同时更新本 brief 末尾加 `**Status**: ✅ <commit hash>`

---

**Status**: ⏳ pending
