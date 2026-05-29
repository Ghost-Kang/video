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
import { useNicheStore, type NicheId } from "./store/nicheStore";
import { useSessionStore } from "./store/sessionStore";
import { useWSStore, synthesizeClientTimeout } from "./store/wsStore";
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
  const setFailure = useCanvasStore((s) => s.setFailure);
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
    // Niche is now a proper WS field (codegen'd from backend Pydantic). undefined
    // when the user hasn't picked one yet — backend treats it as "ask the user".
    const niche = useNicheStore.getState().niche;
    sendCommand({ type: "user_message", thread_id: tid, content: text, selected_niche: niche ?? undefined });
    setLoading(true);
    timerRef.current = setTimeout(() => {
      // W5D3 Bug #6 — 超时时必须同时清掉 loading 和 progress 残留,否则
      // ChatPanel 收到 failed banner 后,后台还在播 "85% running..."。
      setLoading(false);
      useWSStore.setState({
        progressStage: null,
        progressPercent: null,
        progressEta: null,
        progressDetail: "",
      });
      setFailure(synthesizeClientTimeout());
    }, 300_000);
  }, [addMessage, sendCommand, setFailure, setLoading, tid]);
  const actions = useNodeActions(tid, sendCommand, sendChatMessage);
  // Per-shot first-frame trigger. The bracket-prefix convention mirrors
  // `[selected_niche: ...]` — Director's §0.6 prompt picks up the cue and
  // calls `cascade_generate_first_frame`. ShotCard owns the local "generating"
  // spinner; the WS frame `shot_first_frame_returned` patches the image in.
  const onGenerateFirstFrame = useCallback((idx: number) => {
    sendChatMessage(`[generate_first_frame: shot_index=${idx}]`);
  }, [sendChatMessage]);
  // Niche CTA on the ScriptCard. The bracket-prefix is picked up by
  // Director §0.6 — it sees the `[selected_niche: ...]` and immediately
  // calls `cascade_rewrite`. We also persist the choice in nicheStore so
  // subsequent natural-language follow-ups inherit the same niche.
  const onTriggerRewrite = useCallback((niche: NicheId) => {
    useNicheStore.getState().setNiche(niche);
    sendChatMessage(`[selected_niche: ${niche}] 改成这个方向`);
  }, [sendChatMessage]);
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
    // Redirect to the newest session only when the current thread is genuinely
    // unknown AND nothing is running on it. W5D4: the old unconditional version
    // fired mid-run — a freshly-created session (landing → 拆解) isn't in the
    // backend session_list yet, so `!sessions.includes(tid)` was briefly true,
    // and navigating away changed currentThreadId, causing the running session's
    // WS frames to be discarded (blank 拆解中 screen). The session_list handler
    // now unions local sessions in, but we also hard-guard here: never yank the
    // user off a session that is actively loading.
    if (loading) return;
    if (sessions.length > 0 && !sessions.includes(tid)) navigate(`/chat/${sessions[0]}`);
  }, [navigate, sessions, tid, loading]);
  useEffect(() => {
    if (!loading) clearTimeout(timerRef.current ?? undefined);
  }, [loading]);
  // Landing 上 quick-pick / URL 提交把链接放在 ?source_url= 里跳过来; 等 WS 连通后
  // 自动发出 user_message 触发 cascade,并清掉 query 避免回退时重发。
  const autosentRef = useRef(false);
  useEffect(() => {
    if (autosentRef.current || !connected) return;
    const sourceUrl = searchParams.get("source_url");
    if (!sourceUrl) return;
    autosentRef.current = true;
    sendChatMessage(decodeURIComponent(sourceUrl));
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("source_url");
      return next;
    }, { replace: true });
  }, [connected, searchParams, sendChatMessage, setSearchParams]);
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
  // W5D3 layout reform — chat from right rail → bottom dock.
  // Pro view (`?view=pro`) skips the dock entirely: it has its own Canvas
  // and the dock would just stuff the screen. Mobile keeps the dock at
  // bottom (full-width, collapsed-by-default toggle via `chatOpen`).
  const showDock = !isProView;
  return (
    <div className="relative flex flex-col h-screen bg-[var(--color-paper)] dark:bg-stone-950 text-stone-900 dark:text-stone-100 transition-colors duration-500">
      <DarkModeToggle />
      <Header userId={userId} sessionName={names[tid] || "新会话"} connected={connected} connecting={connecting} sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen((v) => !v)} onNewSession={() => navigate(`/chat/${newSessionId()}`)} onLogout={onLogout} isProView={isProView} onToggleProView={proToggle} hideProToggle={shouldHideProToggle(userId)} />
      <div className="flex flex-1 overflow-hidden flex-col" data-testid="app-shell">
        <div className="flex flex-1 overflow-hidden" data-testid="app-main-row">
          {sidebarOpen && <Sidebar sessions={sessions} current={tid} names={names} onSwitch={switchSession} onRename={renameSession} onDelete={deleteSession} />}
          {isProView ? (
            <>
              <Canvas onPositionChange={(pos) => sendCommand({ ...pos, thread_id: tid })} onCreateEdge={actions.handleCreateEdge} onDeleteEdge={actions.handleDeleteEdge} />
              {selectedNodeId && <NodeDetail actions={actions} />}
            </>
          ) : <CardStack onGenerateFirstFrame={onGenerateFirstFrame} onTriggerRewrite={onTriggerRewrite} />}
        </div>
        {showDock && (chatOpen ? (
          <ChatPanel messages={messages} streaming={streaming} thinking={thinking} onSend={sendChatMessage} loading={loading} onToggleCollapse={() => setChatOpen(false)} />
        ) : (
          <button onClick={() => setChatOpen(true)} className="absolute bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-stone-900 dark:bg-[#7c2d12] text-[#faf8f3] shadow-[0_6px_20px_-4px_rgba(28,25,23,0.25)] dark:shadow-[0_6px_20px_-4px_rgba(124,45,18,0.5)] hover:scale-105 active:scale-95 transition-transform duration-200" title="问导演" aria-label="问导演" type="button" data-testid="dock-fab">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 4h12M3 9h12M3 14h8" strokeLinecap="round" /></svg>
          </button>
        ))}
      </div>
    </div>
  );
}
