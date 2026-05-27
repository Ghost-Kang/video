# Cursor handoff — W4D5-T3 Toast 可访问性 polish

**Owner**: Cursor
**Source**: W4D5 cycle index ([`_cursor_W4D5_index.md`](_cursor_W4D5_index.md))
**优先级**: 🟢 低(基础 a11y 已有 aria-live + role,polish 加分项)
**Effort**: S (0.5 天)
**Dependencies**: 无;独立做(T2 改完后会有 action 按钮,但 T3 不依赖 T2 完成)

---

## 0. 你做什么

`ToastContainer.tsx` 当前 a11y 基础:
- `role="status"` 设了
- `aria-live="assertive"`(error)/ `"polite"`(其他)区分了
- 关闭按钮 `aria-label="关闭通知"`

差的:
- **`prefers-reduced-motion`** 不尊重 — `anim-fade-up` 不管系统设置都跑
- **ESC 键**关不掉当前 focused toast
- **焦点管理** — error toast 出现时 screen reader 用户已经听到 announcement,但视力残障 + 键盘用户可能想 Tab 过去 dismiss,目前 Tab 顺序是隐式的
- **触摸目标尺寸** — 关闭按钮 12x12px svg + p-1 padding,刚卡 WCAG 24x24px AAA 边界,放大到 32x32 更稳

---

## 1. 文件改动

| 文件 | 操作 |
|---|---|
| `frontend/src/components/feedback/ToastContainer.tsx` | reduced-motion 检测 + ESC keydown + focusable 容器 + 关闭按钮触摸目标放大 |
| `frontend/src/components/feedback/__tests__/ToastContainer.test.tsx`(新) | RTL 测试 4 个 polish 行为 |
| `frontend/src/index.css` | 可选:加 `@media (prefers-reduced-motion: reduce)` 覆盖 `.anim-fade-up` |

---

## 2. reduced-motion 处理

最简单的方式 — CSS media query:

```css
/* index.css */
@media (prefers-reduced-motion: reduce) {
  .anim-fade-up {
    animation: none !important;
  }
}
```

如果想要 JS 控制更细(只 toast 不跑动画,其他 anim-fade-up 保留),用 `useReducedMotion` hook:

```tsx
function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);
  return reduced;
}
```

ToastCard 内根据 `useReducedMotion()` 决定是否加 `anim-fade-up` class。

推荐方案:**CSS media query**(更简单 + 全局生效)。JS hook 留给单独需要细粒度控制的场景。

---

## 3. ESC 键关闭 focused toast

容器层加 keydown:

```tsx
export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      const focused = document.activeElement;
      if (!containerRef.current?.contains(focused)) return;
      // 找到 focused 元素所属的 toast,dismiss 它
      const card = (focused as HTMLElement)?.closest<HTMLElement>("[data-toast-id]");
      const id = card?.dataset.toastId;
      if (id) dismiss(id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dismiss]);

  // ...
}
```

`ToastCard` 加 `data-toast-id={toast.id}` 属性。

---

## 4. 触摸目标 + 焦点视觉

关闭按钮放大到 32x32(WCAG AAA `pointer-target-large`):

```tsx
<button
  type="button"
  aria-label="关闭通知"
  onClick={onClose}
  className="-mr-1 -mt-1 ml-1 flex h-8 w-8 items-center justify-center rounded text-stone-400 transition-colors hover:text-stone-900 dark:hover:text-stone-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7c2d12] dark:focus-visible:ring-[#ea580c]"
>
  <svg width="12" height="12" ...>...</svg>
</button>
```

`focus-visible:ring-*` 给键盘用户看得到的焦点圈。

---

## 5. 验收

**必过**:
1. 系统设 reduce motion → toast 出现无动画(用 `window.matchMedia` 真实测;或在 vitest mock matchMedia)
2. Tab 到关闭按钮 → 按 ESC → 对应 toast 消失
3. focus-visible:ring 在键盘 Tab 时可见
4. 关闭按钮 hitbox ≥ 32x32(可用 dev tools 量)
5. 现有 12 Playwright smoke 全绿(toast 出现路径不影响)
6. 新增 RTL vitest 至少 3 个 case:reduced-motion 不渲染 anim class、ESC dismiss、关闭按钮聚焦

**不必过但加分**:
- 用 axe-core 跑一遍 toast 容器(如果有 `@axe-core/react`,issues=0)
- 中文 screen reader 测一遍 announcement(NVDA / VoiceOver 中文模式)

---

## 6. 不要

- **不要**改 `anim-fade-up` 在其他组件的行为(landing 页 anim-fade-up 是 deliberate UX,不应该被 toast a11y 改动连带影响)— 如果用 CSS media query 覆盖,**只**覆盖到 toast scope(用更具体的 selector 比如 `.toast-card.anim-fade-up`)
- **不要**改 `aria-live` 级别(error=assertive 是对的,inflate 到 alert 会过度打扰)
- **不要**给 ToastContainer 加 focus trap — 它不是 modal,不能 hijack 全局焦点

---

## 7. 提交规范

- Commit msg:`fix(frontend): Cursor-W4D5-T3 toast a11y polish`
- 末尾加 `**Status**: ✅ <commit hash>`

---

**Status**: ⏳ pending
