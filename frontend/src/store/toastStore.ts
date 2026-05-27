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

/**
 * W4D5-T2 — 可选的 recovery action 按钮。
 *
 * 用途:transient WS 错误(malformed_json / 已知瞬时故障)有时存在"用户一键就
 * 能尝试恢复"的操作(刷新页面、再试一次等)。Toast 是 transient 通道,**不**
 * 用于业务级 retry — 那些走 FailureBanner / inline UI。
 *
 * `closeOnClick` 默认 true:点完按钮自动 dismiss,不让 toast 阻碍后续操作。
 */
export interface ToastAction {
  label: string;
  onClick: () => void;
  closeOnClick?: boolean;
}

export interface Toast {
  id: string;
  kind: ToastKind;
  title: string;
  body?: string;
  ttlMs: number;
  action?: ToastAction;
}

interface ToastStore {
  toasts: Toast[];
  push: (input: {
    kind?: ToastKind;
    title: string;
    body?: string;
    ttlMs?: number;
    action?: ToastAction;
  }) => string;
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

  push: ({ kind = "info", title, body, ttlMs = 5000, action }) => {
    const id = _nextId();
    const toast: Toast = { id, kind, title, body, ttlMs, action };
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
