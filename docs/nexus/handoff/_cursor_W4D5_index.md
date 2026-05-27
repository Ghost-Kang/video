# Cursor W4D5 cycle 任务 index

**Cycle**: 2026-05-26 W4D5
**Owner**: Cursor(刚重新激活 — `03_routing.md §0.1` 解除 deprecation)
**Context**: Claude 在 W4D5 ship 了 `fd72a92`(WS error toast 基础),Cursor 接住做 3 件 follow-on 增强
**Total**: 3 个 task,全部独立可并行,优先级按 1→2→3 推荐

---

## 任务清单

| Task | 标题 | 文件 | 优先级 | Effort | 阻塞 |
|---|---|---|---|---|---|
| **W4D5-T1** | WS 重连失败 → 持久 banner | [cursor_frontend_W4D5_T1_reconnect_banner.md](cursor_frontend_W4D5_T1_reconnect_banner.md) | 🔴 高 | M | 无 |
| **W4D5-T2** | Toast 加 recovery action 按钮 | [cursor_frontend_W4D5_T2_toast_actions.md](cursor_frontend_W4D5_T2_toast_actions.md) | 🟡 中 | M | 建议在 T1 之后做(共用 toastStore 改动) |
| **W4D5-T3** | Toast 可访问性 polish | [cursor_frontend_W4D5_T3_toast_a11y.md](cursor_frontend_W4D5_T3_toast_a11y.md) | 🟢 低 | S | 无 |

---

## 推荐执行顺序

```
Day 1:  T1 (M)  ← phase 1 内测中真实可能遇到网络抖动,优先
Day 2:  T2 (M)  ← 整合 HardFailure recovery actions 到 toast
Day 3:  T3 (S)  ← a11y polish + vitest
```

---

## 基础设施(W4D5 Claude 已 ship)

提供给 Cursor 复用:
- `frontend/src/store/toastStore.ts` — `push / dismiss / clear`,kind = error/warning/info,ttl 自动消失
- `frontend/src/components/feedback/ToastContainer.tsx` — 右上角 stack,dark mode + aria-live
- `frontend/src/store/wsStore.ts` — `case "error"` 已接到 toastStore;`ERROR_CODE_TITLES` map 可扩展
- `frontend/src/lib/recoveryHints.ts` + `feedback/FailureBanner.tsx` — 已存在的 HardFailure UI(W4D5 不动它,T2 复用其 hints map)

---

## 不要碰

- `useWebSocket.ts` 的 reconnect 算法(T1 只读 `connected` / `connecting`,不改重连逻辑)
- backend 任何文件(Cursor 是 frontend-only lane)
- `FailureBanner.tsx`(它的 scope 是 analysis/rewrite HardFailure;toast 是 WS-level transient)
- `ToastContainer.tsx` 的样式 baseline(只能加,不能 rewrite 配色 — 保持 v8 design system)

---

## 完成后

- 每个 task ship 后,在 task 自己的 brief 末尾加一行 `**Status**: ✅ <commit hash>`
- cycle 末尾在 [`architecture_cycle_W4D5_wrap.md`](../architecture_cycle_W4D5_wrap.md)(暂未存在,cycle 末由 PM 写)的 "Cursor 交付" 段加记录

---

## 验收 baseline

每个 task ship 前必须:
1. `npm run build` 通过(tsc + Vite)
2. `npm test` 92 vitest + 你新加的 unit 全绿
3. `npm run test:e2e` 12 Playwright smoke 全绿(必要时为新 UI 加新 spec)
4. Commit msg 前缀 `feat(frontend): Cursor-W4D5-Tx ...` 或 `fix(frontend): ...`

---

## 教训复用(从 W4D3 协作)

- Codex/Claude/Cursor 共用 working tree:**做完一个 task 立刻 commit + push**,避免和别人 working tree 撞文件
- toastStore 是新建的,但 wsStore / ToastContainer 是 Claude 刚改的;Cursor 改时先 `git pull` 看是否有新 commit
- 如果触发了 architect 红线(NodeDetail / cascade ACL / events single-write),**停手**,在 task brief 末尾写 "⚠️ blocked — needs PM call"
