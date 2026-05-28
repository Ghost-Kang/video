/**
 * Top-level React ErrorBoundary — W5D2-E。
 *
 * 套在 `<AppRoutes/>` 外层,把 render 阶段的 throw 转成"页面遇到问题"
 * fallback,而不是白屏。同时把 error + component stack 投递到 backend
 * `/api/client_error`,founder 可以在 events.db 里检索。
 *
 * 文案合规:不出现 节点/锚点/Agent/AI/平台/工具/画布/DAG 等 FORBIDDEN_TERMS。
 * 直接告知用户"刷新或联系客服" — 内测期内已经在 ChatPanel 右下角放了诊断
 * 复制 chip,文案只要 hint 用户去用它即可。
 */

import { Component, type ErrorInfo, type ReactNode } from "react";
import { reportClientError, extractThreadId } from "../../lib/errorReporter";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message?: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error?.message ?? "Unknown error" };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    try {
      reportClientError({
        kind: "react_error_boundary",
        message: error?.message ?? String(error),
        stack: error?.stack,
        component_stack: info?.componentStack ?? undefined,
        url: typeof location !== "undefined" ? location.href : "",
        user_id:
          typeof localStorage !== "undefined" ? localStorage.getItem("rhtv_user") : null,
        thread_id:
          typeof location !== "undefined" ? extractThreadId(location.pathname) : null,
        ua: typeof navigator !== "undefined" ? navigator.userAgent : "",
      });
    } catch {
      // Reporter 自身静默 — Boundary 不能再 throw。
    }
  }

  handleReload = () => {
    if (typeof location !== "undefined") location.reload();
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;

    return (
      <div
        role="alert"
        data-testid="error-boundary-fallback"
        className="min-h-screen flex items-center justify-center bg-[var(--color-paper)] dark:bg-stone-950 px-6 py-10"
      >
        <div className="max-w-md w-full rounded-2xl bg-white dark:bg-stone-900 shadow-soft border border-stone-200/70 dark:border-stone-800/70 p-7 text-center">
          <p className="text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400">
            页面遇到问题
          </p>
          <h1 className="mt-3 font-serif-cn text-2xl text-stone-900 dark:text-stone-50">
            出了点小状况
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-stone-600 dark:text-stone-400">
            页面遇到一个意外问题。你可以刷新重试,或联系客服 —
            对话窗口右下角有「📋 复制诊断」可以一键打包问题信息。
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="mt-5 inline-flex items-center justify-center rounded-xl bg-stone-900 dark:bg-[#7c2d12] px-5 py-2.5 text-[13px] font-medium text-[#faf8f3] transition-colors hover:bg-stone-800 dark:hover:bg-[#9a3412]"
          >
            刷新页面
          </button>
        </div>
      </div>
    );
  }
}
