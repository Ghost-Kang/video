import { StrictMode, Suspense, lazy, useState, useCallback, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import { Login } from "./components/Login";
import { Landing } from "./pages/Landing";
import { InviteCode, readInviteCode } from "./pages/InviteCode";
import { LegalDoc } from "./pages/LegalDoc";
import { ConnectionBanner } from "./components/feedback/ConnectionBanner";
import { ErrorBoundary } from "./components/feedback/ErrorBoundary";
import { ToastContainer } from "./components/feedback/ToastContainer";
import { reportClientError, extractThreadId } from "./lib/errorReporter";

const App = lazy(() => import("./App"));
const ProCanvas = lazy(() => import("./pro/ProCanvas"));
const AnchorAnalytics = lazy(() =>
  import("./pages/AnchorAnalytics").then((mod) => ({ default: mod.AnchorAnalytics })),
);
const AdminCreators = lazy(() =>
  import("./pages/AdminCreators").then((mod) => ({ default: mod.AdminCreators })),
);
const AdminEvents = lazy(() =>
  import("./pages/AdminEvents").then((mod) => ({ default: mod.AdminEvents })),
);
const AdminCost = lazy(() =>
  import("./pages/AdminCost").then((mod) => ({ default: mod.AdminCost })),
);
const AdminHealth = lazy(() =>
  import("./pages/AdminHealth").then((mod) => ({ default: mod.AdminHealth })),
);
const AdminFunnel = lazy(() =>
  import("./pages/AdminFunnel").then((mod) => ({ default: mod.AdminFunnel })),
);

function RouteFallback() {
  return <div className="min-h-screen bg-[var(--color-paper)] dark:bg-stone-950" />;
}

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

function newSessionId() {
  return `session-${Date.now().toString(36)}`;
}

function getLastSession(userId: string): string | null {
  try {
    const sessions = JSON.parse(localStorage.getItem(`openrhtv_${userId}_sessions`) || "[]");
    return sessions.length > 0 ? sessions[0] : null;
  } catch {
    return null;
  }
}

function getChatRedirect(userId: string): string {
  const last = getLastSession(userId);
  return `/chat/${last || newSessionId()}`;
}

function AppRoutes() {
  const [user, setUser] = useState<string | null>(() => localStorage.getItem("rhtv_user"));
  // 内测准入门 — 全局,在 Landing 之前。一旦输入,localStorage 持久,后续 WS
  // auth 自动带。真正准入判定在 backend 的 INVITE_CODES 集合,这里只是 UX。
  const [inviteCode, setInviteCode] = useState<string | null>(() => readInviteCode());

  // W5D3 hotfix — Rules of Hooks: 必须在任何 early return *之前* 声明所有 hooks。
  // 之前 useEffect/useCallback 放在 invite-gate early return 之后,导致第一次渲染
  // (inviteCode=null) hooks count=2,第二次(inviteCode 已 set) hooks count=5,
  // 触发 React minified error #310 "Rendered more hooks than during the previous
  // render" → ErrorBoundary。所有首次访问用户 100% crash 在 invite gate → Landing
  // 的过渡上。Evidence Collector e2e 测试发现并定位。
  useEffect(() => {
    const refresh = () => setUser(localStorage.getItem("rhtv_user"));
    window.addEventListener("rhtv-auth-changed", refresh);
    return () => window.removeEventListener("rhtv-auth-changed", refresh);
  }, []);

  // W5D4 — when the WS is closed with a terminal auth code (4003 invalid invite
  // / 4001 unauth), useWebSocket clears the stored code and fires this event.
  // Drop back to the invite gate instead of letting the reconnect loop spin
  // forever (the "拆解 95% + 网络已恢复 狂闪" symptom).
  useEffect(() => {
    const onRejected = () => setInviteCode(null);
    window.addEventListener("rhtv-invite-rejected", onRejected);
    return () => window.removeEventListener("rhtv-invite-rejected", onRejected);
  }, []);

  const handleLogin = useCallback((uid: string) => {
    setUser(uid);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("rhtv_user");
    setUser(null);
  }, []);

  if (!inviteCode) {
    return <InviteCode onAccept={setInviteCode} />;
  }

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        {/* Phase 1 public routes — accessible without login (legal docs must
            be readable pre-login per user_agreement_v0 §11.1 click-through). */}
        <Route path="/" element={<Landing />} />
        <Route path="/legal/:slug" element={<LegalDoc />} />
        <Route path="/analytics/anchors" element={<AnchorAnalytics />} />
        <Route path="/admin/creators" element={<AdminCreators />} />
        <Route path="/admin/events" element={<AdminEvents />} />
        <Route path="/admin/cost" element={<AdminCost />} />
        <Route path="/admin/health" element={<AdminHealth />} />
        <Route path="/admin/funnel" element={<AdminFunnel />} />

        {/* Authed routes (upstream 66758bd: WS auth + multi-user isolation) */}
        <Route
          path="/login"
          element={user ? <Navigate to={getChatRedirect(user)} replace /> : <Login onLogin={handleLogin} />}
        />
        <Route
          path="/chat/:threadId"
          element={user ? <App userId={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
        />
        {/* Pro 高级子画布(tldraw + ComfyUI 计算图)。flag PRO_CANVAS_ENABLED 默认 OFF 时
            后端 estimate/seed/run 入口会回 pro_canvas_disabled,前端 toast 提示。 */}
        <Route
          path="/pro/:threadId"
          element={user ? <ProCanvas userId={user} /> : <Navigate to="/login" replace />}
        />

        {/* Legacy redirect */}
        <Route path="/canvas" element={<Navigate to={`/chat/${newSessionId()}?view=pro`} replace />} />

        {/* Catch-all: anon users land on Landing first, can opt to login */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

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
