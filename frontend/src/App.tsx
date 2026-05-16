import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { Canvas } from "./components/Canvas";
import { ChatPanel } from "./components/ChatPanel";
import { NodeDetail } from "./components/NodeDetail";
import { useWebSocket } from "./hooks/useWebSocket";
import { useCanvasStore } from "./store/canvasStore";
import type { WSIncoming } from "./types";

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
  const { threadId } = useParams<{ threadId: string }>();
  const navigate = useNavigate();
  const tid = threadId!;

  const [sessions, setSessions] = useState<string[]>(() => loadJSON<string[]>(LS_SESSIONS, []));
  const [names, setNames] = useState<Record<string, string>>(() => loadJSON<Record<string, string>>(LS_NAMES, {}));
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const messages = useCanvasStore((s) => s.messages);
  const setCanvas = useCanvasStore((s) => s.setCanvas);
  const addMessage = useCanvasStore((s) => s.addMessage);
  const setMessages = useCanvasStore((s) => s.setMessages);
  const clearMessages = useCanvasStore((s) => s.clear);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);

  const onMessage = useCallback(
    (res: WSIncoming) => {
      const rid = "thread_id" in res ? res.thread_id : undefined;
      if (rid && rid !== currentThreadIdRef.current) {
        console.log(`[WS] 忽略消息 thread=${rid} (当前=${currentThreadIdRef.current}) type=${res.type}`);
        return;
      }
      switch (res.type) {
        case "agent_response":
          console.log(`[WS] agent_response thread=${rid} content=${res.content?.slice(0, 50)}... nodes=${Object.keys(res.canvas?.nodes || {}).length}`);
          if (res.content) {
            setLoading(false);
            addMessage("agent", res.content);
          }
          if (res.canvas?.nodes) {
            setCanvas(res.canvas.nodes);
          }
          break;
        case "processing":
          console.log(`[WS] processing thread=${rid}`);
          break;
        case "session_state":
          console.log(`[WS] session_state thread=${rid} msgs=${res.messages.length} nodes=${Object.keys(res.canvas?.nodes || {}).length}`);
          setMessages(res.messages);
          if (res.canvas?.nodes) {
            setCanvas(res.canvas.nodes);
          }
          break;
      }
    },
    [addMessage, setMessages, setCanvas]
  );

  const { connect, sendMessage, sendPosition, sendGetSessionState, connected, connecting } =
    useWebSocket(onMessage);
  const didInit = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentThreadIdRef = useRef(tid);
  currentThreadIdRef.current = tid;

  const addSession = useCallback((id: string) => {
    setSessions((prev) => {
      if (prev.includes(id)) return prev;
      const next = [id, ...prev];
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
      if (id === tid) return;
      console.log(`[会话] 切换到 ${id}`);
      currentThreadIdRef.current = id;
      clearTimeout(timerRef.current ?? undefined);
      setLoading(false);
      clearMessages();
      setCanvas({});
      navigate(`/chat/${id}`);
    },
    [tid, navigate, clearMessages, setCanvas]
  );

  const handleDelete = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s !== id);
        saveJSON(LS_SESSIONS, next);
        if (id === tid && next.length > 0) {
          navigate(`/chat/${next[0]}`);
        }
        return next;
      });
      setNames((prev) => {
        const { [id]: _, ...rest } = prev;
        saveJSON(LS_NAMES, rest);
        return rest;
      });
    },
    [tid, navigate]
  );

  // 初始化 WS
  useEffect(() => {
    if (!didInit.current) {
      didInit.current = true;
      connect();
    }
  }, [connect]);

  // URL 变化时：同步会话列表 + 拉取状态
  useEffect(() => {
    addSession(tid);
    clearMessages();
    setCanvas({});
    sendGetSessionState(tid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tid]);

  // 当前会话被删时跳转
  useEffect(() => {
    if (sessions.length > 0 && !sessions.includes(tid)) {
      navigate(`/chat/${sessions[0]}`);
    }
  }, [sessions, tid, navigate]);

  const handleNewSession = useCallback(() => {
    navigate(`/chat/${newSessionId()}`);
  }, [navigate]);

  const handleSend = useCallback(
    (text: string) => {
      addMessage("user", text);
      sendMessage(tid, text);
      setLoading(true);
      timerRef.current = setTimeout(() => {
        setLoading(false);
        addMessage("agent", "请求超时，请检查后端是否正常运行");
      }, 60_000);
    },
    [addMessage, sendMessage, tid]
  );

  useEffect(() => {
    if (!loading) clearTimeout(timerRef.current ?? undefined);
  }, [loading]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header
        sessionName={names[tid] || tid}
        connected={connected}
        connecting={connecting}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onNewSession={handleNewSession}
      />
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {sidebarOpen && (
          <Sidebar
            sessions={sessions}
            current={tid}
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
        <Canvas onPositionChange={(pos) => sendPosition({ ...pos, thread_id: tid })} />
        {selectedNodeId && <NodeDetail />}
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
