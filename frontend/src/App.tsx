import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Canvas } from "./components/Canvas";
import { CardStack } from "./components/CardStack";
import { ChatPanel } from "./components/ChatPanel";
import { CanvasChatDock } from "./components/CanvasChatDock";
import { Header } from "./components/Header";
import { DarkModeToggle } from "./components/landing/DarkModeToggle";
import { NodeDetail } from "./components/NodeDetail";
import { NodeActionsContext } from "./lib/nodeActionsContext";
import { Sidebar } from "./components/Sidebar";
import { useLayoutState } from "./hooks/useLayoutState";
import { useNodeActions } from "./hooks/useNodeActions";
import { useWebSocket } from "./hooks/useWebSocket";
import { shouldHideProToggle, isAdminUser } from "./lib/proViewAccess";
import { resolveRewriteEnabled } from "./lib/rewriteAccess";
import { sessionDisplayName } from "./lib/sessionTitle";
import { trackEvent } from "./lib/eventsApi";
import { useCanvasStore } from "./store/canvasStore";
import { useNicheStore } from "./store/nicheStore";
import { useSessionStore } from "./store/sessionStore";
import { usePendingCaseStore } from "./store/pendingCaseStore";
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
  // W4 redesign: 自动改写守卫。只有用户在本会话真提交过一条 URL(justSubmitted)
  // 后分析回来,才自动触发改写 —— 冷加载历史会话的 replay 不会误触发(那时
  // justSubmitted 始终 false)。autoRewriteFiredFor 再加一层:每个 analysis_id 只发一次。
  const justSubmittedRef = useRef(false);
  const autoRewriteFiredFor = useRef<string | null>(null);
  // 等待态遥测:waitStart = 本次分析开始的毫秒戳(null = 当前没有在等);
  // abandonedFired 保证每次等待最多记一次「中途跳出」(切走/隐藏页面)。
  const waitStartRef = useRef<number | null>(null);
  const abandonedFiredRef = useRef(false);
  const isProView = searchParams.get("view") === "pro";
  const { sidebarOpen, chatOpen, setSidebarOpen, setChatOpen } = useLayoutState();
  const sessions = useSessionStore((s) => s.sessions);
  const names = useSessionStore((s) => s.names);
  const sessionMeta = useSessionStore((s) => s.meta);
  const setSessionUserId = useSessionStore((s) => s.setUserId);
  const addSession = useSessionStore((s) => s.addSession);
  const renameSession = useSessionStore((s) => s.rename);
  const deleteSessionLocal = useSessionStore((s) => s.deleteSession);
  const messages = useCanvasStore((s) => s.messages);
  const streaming = useCanvasStore((s) => s.streamingContent);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const analysis = useCanvasStore((s) => s.analysis);
  const rewriteShots = useCanvasStore((s) => s.rewriteShots);
  // 分析中沉浸态用:本 thread「用户刚点的那条」案例素材(粘陌生链接时为 null)。
  const pendingCase = usePendingCaseStore((s) => s.byThread[tid] ?? null);
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
    // 标记「本会话刚提交了一条链接」——分析回来后据此判断是否自动改写。
    if (/https?:\/\//i.test(text)) {
      justSubmittedRef.current = true;
      // 失败后换样本重试(同 thread):若新链接与暂存案例不是同一条,清掉暂存,
      // 别让旧案例封面在沉浸态里冒充「你刚点的这条」。
      const pc = usePendingCaseStore.getState().byThread[tid];
      if (pc && pc.source_url !== text) usePendingCaseStore.getState().clearPendingCase(tid);
      // 等待态遥测起点。
      waitStartRef.current = Date.now();
      abandonedFiredRef.current = false;
      trackEvent(
        "analysis_wait_started",
        { has_case: Boolean(usePendingCaseStore.getState().byThread[tid]) },
        tid,
      );
    }
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
      if (waitStartRef.current != null) {
        trackEvent("analysis_wait_timeout", { elapsed_ms: Date.now() - waitStartRef.current }, tid);
        waitStartRef.current = null;
      }
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
  // 图生视频(单镜)/ 合成整片 —— bracket 标记由 Director §0.7b/§0.7c 解析,异步生成,
  // 完成后端推帧自动渲染(视频要几分钟,合成几十秒)。
  const onGenerateShotVideo = useCallback((idx: number) => {
    sendChatMessage(`[generate_shot_video: shot_index=${idx}]`);
  }, [sendChatMessage]);
  const onComposeFilm = useCallback(() => {
    sendChatMessage(`[compose_film]`);
  }, [sendChatMessage]);
  // 「改成你自己的版本」CTA(去 niche 后通用代笔)。bracket 标记由 Director §0.6
  // 解析:`[selected_niche: generic]` → 立即 cascade_rewrite;可选的
  // `[rewrite_topic: ...]` 把一句话主题作为 topic 导向题材。topic 留空 = 纯按源片
  // 骨架改写。不再写 nicheStore(去 niche 后 niche 恒 null,发布包按分析 theme 派生)。
  const onTriggerRewrite = useCallback((topic?: string) => {
    justSubmittedRef.current = false; // 手动触发 = 消费掉自动改写信号
    if (analysis) autoRewriteFiredFor.current = analysis.analysis_id;
    const t = topic?.trim();
    const topicMarker = t ? `[rewrite_topic: ${t}]` : "";
    sendChatMessage(`[selected_niche: generic]${topicMarker} 改成我的版本`);
  }, [sendChatMessage, analysis]);
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
  // W4 redesign — 自动改写:分析回来后,若 niche 已知且本会话刚提交过链接,
  // 自动把改写跑起来(别把唯一的价值「你的版本」锁在用户手动点 CTA 后面)。
  // 三重守卫:justSubmitted(冷 replay 不触发)/ 每 analysis_id 只发一次 /
  // 已有 rewrite 或正在 loading 则跳过。niche 未知时不发,交给卡片里的醒目 CTA。
  // 2026-05-30 toprador 对齐:改写「你的版本」本轮暂挂,自动改写关闭。
  // 代码保留(rewrite_service / wsStore rewrite_returned 仍在)。
  // D2 灰度铺路(phase2_kickoff_synthesis_2026-05-31 §3):REWRITE_ENABLED 不再是
  // 源码硬常量,改成运行时可控(后端 cohort flag > VITE_REWRITE_ENABLED > false)。
  // 本轮**保持关闭**:无 cohort flag 下发、不设 env → 恒为 false,行为不变。
  // TODO: 后端在握手/session_state 下发 per-cohort rewrite_enabled 后,把它取出
  // 传入 resolveRewriteEnabled(cohortFlag) 即可切到按 cohort 灰度。
  const REWRITE_ENABLED = useMemo(() => resolveRewriteEnabled(), []);
  useEffect(() => {
    if (!REWRITE_ENABLED) return;
    if (!analysis || loading) return;
    if (!justSubmittedRef.current) return;
    if (rewriteShots.length > 0) return;
    if (autoRewriteFiredFor.current === analysis.analysis_id) return;
    // 去 niche 后无 niche onboarding,改写改由 CardStack 的「改成你的版本」CTA
    // 显式触发(可填一句话主题)。不在此自动改写——避免无主题的低质 auto 改写 +
    // 不擅自替用户花钱。保留 effect 骨架(REWRITE_ENABLED + 守卫)以便将来按 cohort
    // 接回自动改写。
    return;
  }, [REWRITE_ENABLED, analysis, loading, rewriteShots, onTriggerRewrite]);
  // 等待完成遥测:analysis 到达 = 这次等待成功收尾,记端到端耗时。冷加载历史会话
  // (replay)时 waitStart 为 null,不会误记 —— 只统计用户主动发起的那次等待。
  useEffect(() => {
    if (analysis && waitStartRef.current != null) {
      trackEvent(
        "analysis_wait_completed",
        { elapsed_ms: Date.now() - waitStartRef.current, analysis_id: analysis.analysis_id },
        tid,
      );
      waitStartRef.current = null;
    }
  }, [analysis, tid]);
  // 中途跳出遥测:分析进行中页面被切到后台(切 tab / 锁屏 / 关页前多半先 hidden)。
  // 用 visibilitychange 而非 beforeunload —— 此刻页面仍存活,埋点 fetch 能发出去。
  // 每次等待最多记一次(abandonedFiredRef)。
  useEffect(() => {
    const onVis = () => {
      if (
        document.visibilityState === "hidden" &&
        loading &&
        waitStartRef.current != null &&
        !abandonedFiredRef.current
      ) {
        abandonedFiredRef.current = true;
        trackEvent(
          "analysis_wait_abandoned",
          { reason: "hidden", elapsed_ms: Date.now() - waitStartRef.current },
          tid,
        );
      }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [loading, tid]);
  const switchSession = useCallback((id: string) => {
    if (id === tid) return;
    // 离开仍在分析的会话也算一次中途跳出(此刻 loading 还是 true)。
    if (loading && waitStartRef.current != null && !abandonedFiredRef.current) {
      abandonedFiredRef.current = true;
      trackEvent(
        "analysis_wait_abandoned",
        { reason: "switch_session", elapsed_ms: Date.now() - waitStartRef.current },
        tid,
      );
    }
    waitStartRef.current = null;
    clearTimeout(timerRef.current ?? undefined);
    setLoading(false);
    resetThinking();
    clearCanvas();
    setCanvas({ nodes: {}, edges: [] });
    navigate(`/chat/${id}`);
  }, [clearCanvas, navigate, resetThinking, setCanvas, setLoading, tid, loading]);
  const deleteSession = useCallback((id: string) => {
    usePendingCaseStore.getState().clearPendingCase(id);
    deleteSessionLocal(id);
    sendCommand({ type: "delete_session", thread_id: id });
  }, [deleteSessionLocal, sendCommand]);
  // 清理「空会话」:未拆解(无 meta)且未被用户重命名、且非当前会话的。本地全删 +
  // 一条 delete_sessions 批量软删命令。用「一条命令」而非 N 条 delete_session,
  // 是因为 N 条会触发 N 个 session_list 回推,中间态的 union 会把还没删完的会话
  // 重新加回 localStorage(刷新后又冒出来)。批量 = 一次事务 + 一次最终 session_list。
  const clearEmptySessions = useCallback(() => {
    const { sessions: all, names: nm, meta: mt } = useSessionStore.getState();
    const empties = all.filter((id) => id !== tid && !mt[id] && !nm[id]?.trim());
    if (empties.length === 0) return;
    empties.forEach((id) => deleteSessionLocal(id));
    sendCommand({ type: "delete_sessions", thread_ids: empties });
  }, [tid, deleteSessionLocal, sendCommand]);
  const toggleProView = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (next.get("view") === "pro") next.delete("view");
      else next.set("view", "pro");
      return next;
    });
  }, [setSearchParams]);
  const proToggle = useMemo(() => isAdminUser(userId) ? toggleProView : undefined, [toggleProView, userId]);
  // W5D3 layout reform — chat from right rail → bottom dock.
  // 非 pro-view 用 ChatPanel(CardStack 拆解配套的 5 状态机);pro-view 用
  // CanvasChatDock(自由对话驱动 Director 在画布编排锚点级联)。两者都走底部
  // dock,fab 收起/展开共用 chatOpen。
  return (
    <div className="relative flex flex-col h-screen bg-[var(--color-paper)] dark:bg-stone-950 text-stone-900 dark:text-stone-100 transition-colors duration-500">
      <DarkModeToggle />
      <Header userId={userId} sessionName={sessionDisplayName(names, sessionMeta, tid)} connected={connected} connecting={connecting} sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen((v) => !v)} onNewSession={() => navigate(`/chat/${newSessionId()}`)} onLogout={onLogout} isProView={isProView} onToggleProView={proToggle} hideProToggle={shouldHideProToggle(userId)} />
      <div className="flex flex-1 overflow-hidden flex-col" data-testid="app-shell">
        <div className="flex flex-1 overflow-hidden" data-testid="app-main-row">
          {sidebarOpen && <Sidebar sessions={sessions} current={tid} names={names} meta={sessionMeta} onSwitch={switchSession} onRename={renameSession} onDelete={deleteSession} onClearEmpty={clearEmptySessions} />}
          {isProView ? (
            <NodeActionsContext.Provider value={actions}>
              <Canvas onPositionChange={(pos) => sendCommand({ ...pos, thread_id: tid })} onCreateEdge={actions.handleCreateEdge} onDeleteEdge={actions.handleDeleteEdge} />
              {selectedNodeId && <NodeDetail actions={actions} />}
            </NodeActionsContext.Provider>
          ) : <CardStack onGenerateFirstFrame={onGenerateFirstFrame} onTriggerRewrite={onTriggerRewrite} onGenerateShotVideo={onGenerateShotVideo} onComposeFilm={onComposeFilm} pendingCase={pendingCase} thinking={thinking} />}
        </div>
        {chatOpen ? (
          isProView ? (
            <CanvasChatDock messages={messages} streaming={streaming} thinking={thinking} onSend={sendChatMessage} loading={loading} onToggleCollapse={() => setChatOpen(false)} />
          ) : (
            <ChatPanel messages={messages} streaming={streaming} thinking={thinking} onSend={sendChatMessage} loading={loading} onToggleCollapse={() => setChatOpen(false)} />
          )
        ) : (
          <button onClick={() => setChatOpen(true)} className="absolute bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-stone-900 dark:bg-[#7c2d12] text-[#faf8f3] shadow-[0_6px_20px_-4px_rgba(28,25,23,0.25)] dark:shadow-[0_6px_20px_-4px_rgba(124,45,18,0.5)] hover:scale-105 active:scale-95 transition-transform duration-200" title="问导演" aria-label="问导演" type="button" data-testid="dock-fab">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 4h12M3 9h12M3 14h8" strokeLinecap="round" /></svg>
          </button>
        )}
      </div>
    </div>
  );
}
