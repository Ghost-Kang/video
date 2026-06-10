/**
 * 路由树(从 main.tsx 拆出,lint 清理 2026-06-10)。
 *
 * react-refresh/only-export-components:入口文件(无导出)里定义组件无法热刷新,
 * 10 条 lint error 全来自 main.tsx 里的 lazy 组件常量 + AppRoutes。拆到这个
 * 导出组件的文件后,开发时 AppRoutes 及路由组件可正常 fast refresh。
 */

import { Suspense, lazy, useState, useCallback, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Login } from "./components/Login";
import { Landing } from "./pages/Landing";
import { InviteCode } from "./pages/InviteCode";
import { readInviteCode } from "./lib/inviteCode";
import { LegalDoc } from "./pages/LegalDoc";

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

export function AppRoutes() {
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
