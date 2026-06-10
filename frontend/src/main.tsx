import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import { syncAnonIdCookie } from "./hooks/useConsent";
import { AppRoutes } from "./AppRoutes";
import { ConnectionBanner } from "./components/feedback/ConnectionBanner";
import { ErrorBoundary } from "./components/feedback/ErrorBoundary";
import { ToastContainer } from "./components/feedback/ToastContainer";
import { reportClientError, extractThreadId } from "./lib/errorReporter";

// W5D2-E: 浏览器端 Sentry-lite。在所有 React tree 挂载前装好,捕获:
//   - window 'error' — script 抛出的 sync error / asset load 失败
//   - window 'unhandledrejection' — Promise reject 无 catch
// 失败静默(reporter 自身保证),不阻塞主线程,1 分钟内同 (kind+msg) 去重。
if (typeof window !== "undefined") {
  window.addEventListener("error", (e: ErrorEvent) => {
    reportClientError({
      kind: "window_error",
      message: e.message || "(no message)",
      stack: e.error?.stack,
      filename: e.filename,
      lineno: e.lineno,
      colno: e.colno,
      url: location.href,
      user_id: localStorage.getItem("rhtv_user"),
      thread_id: extractThreadId(location.pathname),
      ua: navigator.userAgent.slice(0, 200),
    });
  });
  window.addEventListener("unhandledrejection", (e: PromiseRejectionEvent) => {
    const reason = e.reason;
    const message =
      reason instanceof Error ? reason.message : String(reason ?? "(no reason)");
    const stack = reason instanceof Error ? reason.stack : undefined;
    reportClientError({
      kind: "unhandled_rejection",
      message,
      stack,
      url: location.href,
      user_id: localStorage.getItem("rhtv_user"),
      thread_id: extractThreadId(location.pathname),
      ua: navigator.userAgent.slice(0, 200),
    });
  });
}

// P3(2026-06-10):app 启动即同步匿名身份 cookie 备份(存量用户续期 / 清
// localStorage 后从 cookie 恢复)。任何路由都生效,不依赖走过同意门。
syncAnonIdCookie();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <AppRoutes />
      </ErrorBoundary>
      <ConnectionBanner />
      <ToastContainer />
    </BrowserRouter>
  </StrictMode>
);
