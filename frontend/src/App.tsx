import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Canvas } from "./components/Canvas";
import { CardStack } from "./components/CardStack";
import { ChatPanel } from "./components/ChatPanel";
import { Header } from "./components/Header";
import { DarkModeToggle } from "./components/landing/DarkModeToggle";
import { NodeDetail } from "./components/NodeDetail";
import { Sidebar } from "./components/Sidebar";
import { useLayoutState } from "./hooks/useLayoutState";
import { useNodeActions } from "./hooks/useNodeActions";
import { useWebSocket } from "./hooks/useWebSocket";
import { shouldHideProToggle, isAdminUser } from "./lib/proViewAccess";
import { useCanvasStore } from "./store/canvasStore";
import { useSessionStore } from "./store/sessionStore";
import { useWSStore } from "./store/wsStore";
import type { WSEvent } from "./types/ws";
function newSessionId() {
  return `session-${Date.now().toString(36)}`;
}
interface AppProps { userId: string; onLogout: () => void; }
export default function App({ userId, onLogout }: AppProps) {
  const { threadId } = useParams<{ threadId: string }>();
  const tid = threadId!;
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isProView = searchParams.get("view") === "pro";
  const { sidebarOpen, chatOpen, setSidebarOpen, setChatOpen } = useLayoutState();
  const sessions = useSessionStore((s) => s.sessions);
  const names = useSessionStore((s) => s.names);
  const setSessionUserId = useSessionStore((s) => s.setUserId);
  const addSession = useSessionStore((s) => s.addSession);
  const renameSession = useSessionStore((s) => s.rename);
  const deleteSessionLocal = useSessionStore((s) => s.deleteSession);
  const messages = useCanvasStore((s) => s.messages);
  const streaming = useCanvasStore((s) => s.streamingContent);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const addMessage = useCanvasStore((s) => s.addMessage);
  const clearCanvas = useCanvasStore((s) => s.clear);
  const setCanvas = useCanvasStore((s) => s.setCanvas);
  const thinking = useWSStore((s) => s.thinking);
  const loading = useWSStore((s) => s.loading);
  const dispatchWSEvent = useWSStore((s) => s.dispatch);
  const setCurrentThreadId = useWSStore((s) => s.setCurrentThreadId);
  const setLoading = useWSStore((s) => s.setLoading);
  const resetThinking = useWSStore((s) => s.resetThinking);
  const setConnectionStatus = useWSStore((s) => s.setConnectionStatus);
  const onMessage = useCallback((event: WSEvent) => dispatchWSEvent(event, userId), [dispatchWSEvent, userId]);
  const { connect, sendCommand, connected, connecting, reconnectAttempt } = useWebSocket(userId, onMessage);
  // W4D5-T1: 把 useWebSocket 的连接状态镜像到 wsStore,让根级 <ConnectionBanner/>
  // (在 main.tsx mount,App 之外)能直接订阅。useWebSocket 自身保持 store-agnostic。
  useEffect(() => {
    setConnectionStatus({ connected, connecting, reconnectAttempt });
  }, [connected, connecting, reconnectAttempt, setConnectionStatus]);
  const sendChatMessage = useCallback((text: string) => {
    addMessage("user", text);
    sendCommand({ type: "user_message", thread_id: tid, content: text });
    setLoading(true);
    timerRef.current = setTimeout(() => {
      setLoading(false);
      addMessage("agent", "请求超时，请检查后端是否正常运行");
    }, 300_000);
  }, [addMessage, sendCommand, setLoading, tid]);
  const actions = useNodeActions(tid, sendCommand, sendChatMessage);
  useEffect(() => {
    setSessionUserId(userId);
  }, [setSessionUserId, userId]);
  useEffect(() => {
    connect();
  }, [connect]);
  useEffect(() => {
    setCurrentThreadId(tid);
    addSession(tid);
    clearCanvas();
    setCanvas({ nodes: {}, edges: [] });
    sendCommand({ type: "get_session_state", thread_id: tid });
  }, [addSession, clearCanvas, sendCommand, setCanvas, setCurrentThreadId, tid]);
  useEffect(() => {
    if (sessions.length > 0 && !sessions.includes(tid)) navigate(`/chat/${sessions[0]}`);
  }, [navigate, sessions, tid]);
  useEffect(() => {
    if (!loading) clearTimeout(timerRef.current ?? undefined);
  }, [loading]);
  const switchSession = useCallback((id: string) => {
    if (id === tid) return;
    clearTimeout(timerRef.current ?? undefined);
    setLoading(false);
    resetThinking();
    clearCanvas();
    setCanvas({ nodes: {}, edges: [] });
    navigate(`/chat/${id}`);
  }, [clearCanvas, navigate, resetThinking, setCanvas, setLoading, tid]);
  const deleteSession = useCallback((id: string) => {
    deleteSessionLocal(id);
    sendCommand({ type: "delete_session", thread_id: id });
  }, [deleteSessionLocal, sendCommand]);
  const toggleProView = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.get("view") === "pro" ? next.delete("view") : next.set("view", "pro");
      return next;
    });
  }, [setSearchParams]);
  const proToggle = useMemo(() => isAdminUser(userId) ? toggleProView : undefined, [toggleProView, userId]);
  return (
    <div className="relative flex flex-col h-screen bg-[var(--color-paper)] dark:bg-stone-950 text-stone-900 dark:text-stone-100 transition-colors duration-500">
      <DarkModeToggle />
      <Header userId={userId} sessionName={names[tid] || "新会话"} connected={connected} connecting={connecting} sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen((v) => !v)} onNewSession={() => navigate(`/chat/${newSessionId()}`)} onLogout={onLogout} isProView={isProView} onToggleProView={proToggle} hideProToggle={shouldHideProToggle(userId)} />
      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen && <Sidebar sessions={sessions} current={tid} names={names} onSwitch={switchSession} onRename={renameSession} onDelete={deleteSession} />}
        {isProView ? (
          <>
            <Canvas onPositionChange={(pos) => sendCommand({ ...pos, thread_id: tid })} onCreateEdge={actions.handleCreateEdge} onDeleteEdge={actions.handleDeleteEdge} />
            {selectedNodeId && <NodeDetail actions={actions} />}
          </>
        ) : <CardStack />}
        {chatOpen ? <ChatPanel messages={messages} streaming={streaming} thinking={thinking} onSend={sendChatMessage} loading={loading} onToggleCollapse={() => setChatOpen(false)} /> : (
          <button onClick={() => setChatOpen(true)} className="absolute bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-stone-900 dark:bg-[#7c2d12] text-[#faf8f3] shadow-[0_6px_20px_-4px_rgba(28,25,23,0.25)] dark:shadow-[0_6px_20px_-4px_rgba(124,45,18,0.5)] hover:scale-105 active:scale-95 transition-transform duration-200" title="问导演" type="button">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 4h12M3 9h12M3 14h8" strokeLinecap="round" /></svg>
          </button>
        )}
      </div>
    </div>
  );
}
