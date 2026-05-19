import { StrictMode, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import App from "./App";
import { Login } from "./components/Login";

function newSessionId() {
  return `session-${Date.now().toString(36)}`;
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
        element={user ? <Navigate to={`/chat/${newSessionId()}`} replace /> : <Login onLogin={handleLogin} />}
      />
      <Route
        path="/chat/:threadId"
        element={user ? <App userId={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
      />
      <Route path="*" element={<Navigate to={user ? `/chat/${newSessionId()}` : "/login"} replace />} />
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
