import { StrictMode, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import App from "./App";
import { Login } from "./components/Login";

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

function AuthGate() {
  const [user, setUser] = useState<string | null>(() => localStorage.getItem("rhtv_user"));

  const handleLogin = useCallback((uid: string) => {
    setUser(uid);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("rhtv_user");
    setUser(null);
  }, []);

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to={getChatRedirect(user)} replace /> : <Login onLogin={handleLogin} />}
      />
      <Route
        path="/chat/:threadId"
        element={user ? <App userId={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
      />
      <Route path="*" element={<Navigate to={user ? getChatRedirect(user) : "/login"} replace />} />
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthGate />
    </BrowserRouter>
  </StrictMode>
);
