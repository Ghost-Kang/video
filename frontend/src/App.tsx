import { useState, useCallback, useEffect, useRef } from "react";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { Canvas } from "./components/Canvas";
import { ChatPanel } from "./components/ChatPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import { useCanvasStore } from "./store/canvasStore";
import type { WSAgentResponse } from "./types";

const LS_SESSIONS = "openrhtv_sessions";
const LS_NAMES = "openrhtv_session_names";

function loadJSON<T>(key: string, fallback: T): T {
  try {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : fallback;
  } catch { return fallback; }
}

function saveJSON(key: string, val: unknown) {
  localStorage.setItem(key, JSON.stringify(val));
}

function newSessionId() {
  return `session-${Date.now().toString(36)}`;
}

export default function App() {
  const [sessions, setSessions] = useState<string[]>(() => loadJSON<string[]>(LS_SESSIONS, []));
  const [names, setNames] = useState<Record<string, string>>(() => loadJSON<Record<string, string>>(LS_NAMES, {}));
  const [threadId, setThreadId] = useState(() => {
    const saved = loadJSON<string[]>(LS_SESSIONS, []);
    return saved.length > 0 ? saved[0] : newSessionId();
  });
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const messages = useCanvasStore((s) => s.messages);
  const setCanvas = useCanvasStore((s) => s.setCanvas);
  const addMessage = useCanvasStore((s) => s.addMessage);
  const clearMessages = useCanvasStore((s) => s.clear);

  const onResponse = useCallback(
    (res: WSAgentResponse) => {
      setLoading(false);
      addMessage("agent", res.content);
      if (res.canvas?.nodes) {
        setCanvas(res.canvas.nodes);
      } else if (res.canvas !== null) {
        setCanvas({});
      }
    },
    [addMessage, setCanvas]
  );

  const { connect, send, connected } = useWebSocket(onResponse);
  const didInit = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const addSession = useCallback((id: string) => {
    setSessions((prev) => {
      const next = [id, ...prev.filter((s) => s !== id)];
      saveJSON(LS_SESSIONS, next);
      return next;
    });
  }, []);

  const handleRename = useCallback((id: string, name: string) => {
    setNames((prev) => {
      const next = { ...prev, [id]: name };
      saveJSON(LS_NAMES, next);
      return next;
    });
  }, []);

  const switchSession = useCallback(
    (id: string) => {
      setThreadId(id);
      clearMessages();
      setCanvas({});
      addSession(id);
      connect(id);
    },
    [connect, clearMessages, setCanvas, addSession]
  );

  const handleDelete = useCallback((id: string) => {
    setSessions((prev) => {
      const next = prev.filter((s) => s !== id);
      saveJSON(LS_SESSIONS, next);
      if (id === threadId && next.length > 0) {
        switchSession(next[0]);
      }
      return next;
    });
    setNames((prev) => {
      const { [id]: _, ...rest } = prev;
      saveJSON(LS_NAMES, rest);
      return rest;
    });
  }, [threadId, switchSession]);

  useEffect(() => {
    if (!didInit.current) {
      didInit.current = true;
      connect(threadId);
      addSession(threadId);
    }
  }, [connect, threadId, addSession]);

  const handleNewSession = useCallback(() => {
    switchSession(newSessionId());
  }, [switchSession]);

  const handleSend = useCallback(
    (text: string) => {
      addMessage("user", text);
      const ok = send(text);
      if (!ok) {
        addMessage("agent", "未连接到后端服务，请先启动 backend");
        return;
      }
      setLoading(true);
      timerRef.current = setTimeout(() => {
        setLoading(false);
        addMessage("agent", "请求超时，请检查后端是否正常运行");
      }, 60_000);
    },
    [addMessage, send]
  );

  useEffect(() => {
    if (!loading) clearTimeout(timerRef.current ?? undefined);
  }, [loading]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header
        threadId={threadId}
        sessionName={names[threadId] || threadId}
        connected={connected}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onNewSession={handleNewSession}
      />
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {sidebarOpen && (
          <Sidebar
            sessions={sessions}
            current={threadId}
            names={names}
            onSwitch={switchSession}
            onRename={handleRename}
            onDelete={handleDelete}
          />
        )}
        {chatOpen ? (
          <ChatPanel
            messages={messages}
            onSend={handleSend}
            loading={loading}
            onToggleCollapse={() => setChatOpen(false)}
          />
        ) : (
          <button
            onClick={() => setChatOpen(true)}
            style={S.floatBtn}
            title="展开聊天"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 5h14M3 10h10M3 15h14" />
              <circle cx="15.5" cy="5" r="3" fill="#22c55e" stroke="none" />
            </svg>
          </button>
        )}
        <Canvas />
      </div>
    </div>
  );
}

const S = {
  floatBtn: {
    position: "absolute",
    bottom: 20,
    left: 20,
    width: 44,
    height: 44,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#18181b",
    color: "#fff",
    border: "none",
    borderRadius: 12,
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    zIndex: 10,
    transition: "transform 0.15s",
  } as React.CSSProperties,
};
