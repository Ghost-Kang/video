/**
 * 全局 toast 容器 — 右上角固定堆叠。在 main.tsx 根 mount,所有路由共享。
 *
 * 样式跟 v8 design system 一致:warm-paper 背景 + clay accent;dark mode 配套。
 *
 * a11y(W4D5-T3):
 * - role=status + aria-live(error=assertive,其他 polite)做 SR 播报。
 * - reduced-motion 由全局 `index.css @media (prefers-reduced-motion: reduce)`
 *   覆盖 `.anim-fade-up`,toast 自动跳过淡入(无需 JS hook)。
 * - ESC 键关闭 focused toast(限定容器内 focus)。
 * - close 按钮 32x32(WCAG 2.5.5 AAA pointer target),focus-visible:ring 给
 *   键盘用户可见焦点圈。
 */

import { useEffect, useRef } from "react";
import type { Toast, ToastKind } from "../../store/toastStore";
import { useToastStore } from "../../store/toastStore";

const KIND_STYLES: Record<ToastKind, { wrap: string; icon: string; label: string }> = {
  error: {
    wrap: "border-rose-300/70 bg-rose-50/95 dark:border-rose-900/60 dark:bg-rose-950/90",
    icon: "text-rose-700 dark:text-rose-300",
    label: "出错",
  },
  warning: {
    wrap: "border-amber-300/70 bg-amber-50/95 dark:border-amber-900/60 dark:bg-amber-950/90",
    icon: "text-amber-700 dark:text-amber-300",
    label: "提示",
  },
  info: {
    wrap: "border-stone-300/70 bg-white/95 dark:border-stone-700/60 dark:bg-stone-900/90",
    icon: "text-stone-700 dark:text-stone-300",
    label: "通知",
  },
};


function ToastCard({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const s = KIND_STYLES[toast.kind];
  return (
    <div
      role="status"
      aria-live={toast.kind === "error" ? "assertive" : "polite"}
      data-toast-kind={toast.kind}
      data-toast-id={toast.id}
      className={`anim-fade-up pointer-events-auto flex w-[320px] max-w-[90vw] items-start gap-2.5 rounded-xl border ${s.wrap} px-3.5 py-2.5 shadow-soft backdrop-blur-md`}
    >
      <span className={`mt-[3px] inline-block h-1.5 w-1.5 shrink-0 rounded-full ${s.icon} bg-current`} aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="text-[11px] uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">
          {s.label}
        </div>
        <div className="mt-0.5 break-words font-serif-cn text-sm text-stone-900 dark:text-stone-50">
          {toast.title}
        </div>
        {toast.body && (
          <div className="mt-1 break-words text-xs leading-relaxed text-stone-600 dark:text-stone-400">
            {toast.body}
          </div>
        )}
      </div>
      {toast.action && (
        <button
          type="button"
          aria-label={toast.action.label}
          onClick={() => {
            toast.action!.onClick();
            // closeOnClick 默认 true — 点完按钮 toast 自动消失,不再阻碍。
            if (toast.action!.closeOnClick !== false) onClose();
          }}
          className="ml-2 shrink-0 rounded-md border border-stone-300 bg-white px-2.5 py-1 text-xs font-medium text-stone-700 transition-colors hover:border-[#7c2d12] hover:text-[#7c2d12] dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300 dark:hover:border-[#ea580c] dark:hover:text-[#ea580c]"
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        aria-label="关闭通知"
        onClick={onClose}
        className="-mr-1 -mt-1 ml-1 flex h-8 w-8 shrink-0 items-center justify-center rounded text-stone-400 transition-colors hover:text-stone-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7c2d12] focus-visible:ring-offset-1 dark:hover:text-stone-100 dark:focus-visible:ring-[#ea580c]"
      >
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
          <path d="M3.5 3.5L12.5 12.5M12.5 3.5L3.5 12.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}


export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);
  const containerRef = useRef<HTMLDivElement>(null);

  // W4D5-T3: ESC 关闭当前 focused toast。只在容器内 focus 时响应,不 hijack
  // 全局 ESC(modal / 其他键盘交互优先)。focused 元素 closest('[data-toast-id]')
  // 找到所属 toast,dismiss 之。
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      const focused = document.activeElement;
      if (!containerRef.current?.contains(focused)) return;
      const card = (focused as HTMLElement | null)?.closest<HTMLElement>("[data-toast-id]");
      const id = card?.dataset.toastId;
      if (id) dismiss(id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dismiss]);

  if (toasts.length === 0) return null;

  return (
    <div
      ref={containerRef}
      data-testid="toast-container"
      className="pointer-events-none fixed right-4 top-4 z-[60] flex flex-col gap-2"
    >
      {toasts.map((t) => (
        <ToastCard key={t.id} toast={t} onClose={() => dismiss(t.id)} />
      ))}
    </div>
  );
}
