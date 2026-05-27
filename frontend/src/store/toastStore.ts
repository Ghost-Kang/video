/**
 * Toast store — transient notification UI 的 single source of truth。
 *
 * 接 wsStore 的 error 帧(Claude-B Pydantic 校验失败时后端推):
 *   `{ type: "error", code: "invalid_command", message, bad_type? }`
 *
 * 也可以被任何 UI 路径(API 调用失败、用户操作错误等)调用 push。
 *
 * 自动消失:push 后 ttlMs 后自动 dismiss(默认 5s)。用户可点叉手动关闭。
 */

import { create } from "zustand";

export type ToastKind = "error" | "warning" | "info";

export interface Toast {
  id: string;
  kind: ToastKind;
  title: string;
  body?: string;
  ttlMs: number;
}

interface ToastStore {
  toasts: Toast[];
  push: (input: { kind?: ToastKind; title: string; body?: string; ttlMs?: number }) => string;
  dismiss: (id: string) => void;
  clear: () => void;
}

let _seq = 0;
function _nextId(): string {
  _seq += 1;
  return `t-${Date.now().toString(36)}-${_seq}`;
}

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],

  push: ({ kind = "info", title, body, ttlMs = 5000 }) => {
    const id = _nextId();
    const toast: Toast = { id, kind, title, body, ttlMs };
    set((state) => ({ toasts: [...state.toasts, toast] }));

    if (ttlMs > 0) {
      setTimeout(() => {
        // 关键:dismiss 通过 store API,避免 stale closure
        get().dismiss(id);
      }, ttlMs);
    }

    return id;
  },

  dismiss: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },

  clear: () => {
    set({ toasts: [] });
  },
}));
