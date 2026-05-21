import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import App from "./App";
import { Landing } from "./pages/Landing";
import { AnchorAnalytics } from "./pages/AnchorAnalytics";

function newSessionId() {
  return `session-${Date.now().toString(36)}`;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/analytics/anchors" element={<AnchorAnalytics />} />
        <Route path="/chat/:threadId" element={<App />} />
        <Route path="/canvas" element={<Navigate to={`/chat/${newSessionId()}?view=pro`} replace />} />
        <Route path="*" element={<Navigate to={`/chat/${newSessionId()}`} replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
