# Cursor handoff — W4D5-T2 Toast 加 recovery action 按钮

**Owner**: Cursor
**Source**: W4D5 cycle index ([`_cursor_W4D5_index.md`](_cursor_W4D5_index.md))
**优先级**: 🟡 中
**Effort**: M (1 天)
**Dependencies**: 建议在 T1 之后做(都改 toastStore 类型,避免 merge conflict)

---

## 0. 你做什么

现在 toast 只显示文字 + 关闭按钮。后端 `HardFailure` 有 `RecoveryAction` 枚举(见
`backend/src/agent/cascade/failures.py:34` + `frontend/src/lib/recoveryHints.ts`),
能告诉前端可执行的恢复操作("再试一次" / "换条 URL" / "刷新页面")。

目前 `FailureBanner.tsx` 把这些 actions 用在 analysis/rewrite 出错时的 inline banner。
但 transient WS error(invalid_command / malformed_json / network glitch)目前没法附
recovery action — 用户只能干瞪眼。

需要扩 `Toast` 数据模型加可选 `action`,UI 渲染一个按钮;wsStore 在已知 case 下注入
合适的 action。

---

## 1. 文件改动

| 文件 | 操作 |
|---|---|
| `frontend/src/store/toastStore.ts` | `Toast` interface 加 `action?: ToastAction`;`push` 接受 |
| `frontend/src/components/feedback/ToastContainer.tsx` | 渲染 action 按钮 |
| `frontend/src/store/wsStore.ts` | error case 按 `code` map 注入 action(invalid_command → 无 action;malformed_json → reload) |
| `frontend/src/store/__tests__/toastStore.test.ts` | 加 action 字段单测 |
| `frontend/src/store/__tests__/wsStore.error.test.ts` | 加 reload action 注入单测 |

---

## 2. 数据模型

```ts
// store/toastStore.ts
export interface ToastAction {
  label: string;     // 例:"刷新页面"、"再试一次"、"换条 URL"
  onClick: () => void;
  /** action 按下后是否自动 dismiss toast,默认 true */
  closeOnClick?: boolean;
}

export interface Toast {
  id: string;
  kind: ToastKind;
  title: string;
  body?: string;
  ttlMs: number;
  action?: ToastAction;   // ← 新增
}
```

`push` 增加 `action?` 入参:

```ts
push: (input: {
  kind?: ToastKind;
  title: string;
  body?: string;
  ttlMs?: number;
  action?: ToastAction;
}) => string;
```

---

## 3. UI 渲染

ToastContainer 的 `ToastCard` 在 close 按钮 **左边**加 action 按钮(更接近用户视线):

```tsx
{toast.action && (
  <button
    type="button"
    onClick={() => {
      toast.action!.onClick();
      if (toast.action!.closeOnClick !== false) onClose();
    }}
    className="ml-2 shrink-0 rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-2.5 py-1 text-xs font-medium text-stone-700 dark:text-stone-300 transition-colors hover:border-[#7c2d12] hover:text-[#7c2d12] dark:hover:border-[#ea580c] dark:hover:text-[#ea580c]"
  >
    {toast.action.label}
  </button>
)}
```

布局变成:`[dot] [content] [action] [×]`。

**a11y**:action 按钮加 `aria-label={toast.action.label}`,close 按钮已有 aria-label。Tab 顺序:action → close。

---

## 4. wsStore 的 action 注入

```ts
// store/wsStore.ts
case "error": {
  console.warn("[WS] error", event.code, event.message, event.bad_type);
  const title = ERROR_CODE_TITLES[event.code] ?? "请求出错";
  const body = event.bad_type ? `操作:${event.bad_type}` : undefined;

  // 已知 code 注入 action
  let action: ToastAction | undefined;
  if (event.code === "malformed_json") {
    action = {
      label: "刷新页面",
      onClick: () => window.location.reload(),
    };
  }
  // invalid_command: 用户没法主动恢复,不给 action(避免误导)

  useToastStore.getState().push({ kind: "error", title, body, action });
  break;
}
```

**不要**注入 action 时硬编码 `reload()` 之外的副作用 — 那种 case 用 T1 的 banner 或
FailureBanner 更合适。Toast action 只承诺"用户一键就能尝试恢复"。

---

## 5. 验收

**必过**:
1. `toastStore.push({ ..., action: { label: "x", onClick: () => {} } })` → ToastCard 渲染按钮
2. 点 action → onClick 触发 + toast 自动消失(closeOnClick=true 默认)
3. `closeOnClick: false` 时点 action,toast 保留
4. 后端推 `{type:"error", code:"malformed_json"}` → toast 有"刷新页面"按钮
5. 后端推 `{type:"error", code:"invalid_command", bad_type:"execute_node"}` → toast 无 action(只 title + body)
6. `npm test` + `npm run test:e2e` + `npm run build` 全绿

**vitest 必加**:
- toastStore: action 字段保存、action onClick 调用、closeOnClick 行为
- wsStore.error: malformed_json 注入 reload action、invalid_command 不注入

---

## 6. 不要

- **不要**改 backend(`failures.py` / `recoveryHints.ts`)— T2 纯 frontend
- **不要**让 toast action 直接调用 sendCommand 之类的业务操作 — 那是 T1 banner 或
  FailureBanner 的职责,toast 是 transient 通知
- **不要**把 `FailureBanner.tsx` 的 recovery actions 换成 toast — 它的 inline banner
  是 deliberate UX choice(用户停在那一步,不会消失)

---

## 7. 提交规范

- Commit msg:`feat(frontend): Cursor-W4D5-T2 toast recovery action 按钮`
- 末尾加 `**Status**: ✅ <commit hash>`

---

**Status**: ✅ 9967512
