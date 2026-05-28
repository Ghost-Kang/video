import { StrictMode, useState, useCallback, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import App from "./App";
import { Login } from "./components/Login";
import { Landing } from "./pages/Landing";
import { InviteCode, readInviteCode } from "./pages/InviteCode";
import { AnchorAnalytics } from "./pages/AnchorAnalytics";
import { AdminCreators } from "./pages/AdminCreators";
import { AdminEvents } from "./pages/AdminEvents";
import { AdminCost } from "./pages/AdminCost";
import { LegalDoc } from "./pages/LegalDoc";
import { ConnectionBanner } from "./components/feedback/ConnectionBanner";
import { ToastContainer } from "./components/feedback/ToastContainer";

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

  if (!inviteCode) {
    return <InviteCode onAccept={setInviteCode} />;
  }

  // Phase 1 anon-consent bridge: useConsent.accept() writes rhtv_user
  // then dispatches this event so /chat becomes accessible without an
  // explicit /login round-trip.
  useEffect(() => {
    const refresh = () => setUser(localStorage.getItem("rhtv_user"));
    window.addEventListener("rhtv-auth-changed", refresh);
    return () => window.removeEventListener("rhtv-auth-changed", refresh);
  }, []);

  const handleLogin = useCallback((uid: string) => {
    setUser(uid);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("rhtv_user");
    setUser(null);
  }, []);

  return (
    <Routes>
      {/* Phase 1 public routes — accessible without login (legal docs must
          be readable pre-login per user_agreement_v0 §11.1 click-through). */}
      <Route path="/" element={<Landing />} />
      <Route path="/legal/:slug" element={<LegalDoc />} />
      <Route path="/analytics/anchors" element={<AnchorAnalytics />} />
      <Route path="/admin/creators" element={<AdminCreators />} />
      <Route path="/admin/events" element={<AdminEvents />} />
      <Route path="/admin/cost" element={<AdminCost />} />

      {/* Authed routes (upstream 66758bd: WS auth + multi-user isolation) */}
      <Route
        path="/login"
        element={user ? <Navigate to={getChatRedirect(user)} replace /> : <Login onLogin={handleLogin} />}
      />
      <Route
        path="/chat/:threadId"
        element={user ? <App userId={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
      />

      {/* Legacy redirect */}
      <Route path="/canvas" element={<Navigate to={`/chat/${newSessionId()}?view=pro`} replace />} />

      {/* Catch-all: anon users land on Landing first, can opt to login */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AppRoutes />
      <ConnectionBanner />
      <ToastContainer />
    </BrowserRouter>
  </StrictMode>
);
