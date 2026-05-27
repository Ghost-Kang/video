import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { Canvas } from "./components/Canvas";
import { CardStack } from "./components/CardStack";
import { ChatPanel } from "./components/ChatPanel";
import { NodeDetail } from "./components/NodeDetail";
import { useWebSocket } from "./hooks/useWebSocket";
import { useCanvasStore } from "./store/canvasStore";
import { shouldHideProToggle, isAdminUser } from "./lib/proViewAccess";
import { DarkModeToggle } from "./components/landing/DarkModeToggle";
import type { NodeType, WSIncoming } from "./types";

// 把后端 tool_call 名映射成宝妈看得懂的中文进度词;未知 tool 默认 "整理中"。
const TOOL_LABELS: Record<string, string> = {
  script_writer: "🍳 在写开头脚本…",
  image_generate: "✨ 在生成画面参考…",
  analyze_source: "🔍 在拆解视频…",
  request_shallow_analysis: "🔍 在拆解视频…",
  rewrite_to_niche: "📝 在改写成你的版本…",
  storyboard: "🎬 在排分镜…",
  publish_pack: "📦 在准备发布包…",
};
function labelToolCall(name: string | undefined): string {
  if (!name) return "✨ 整理中…";
  return TOOL_LABELS[name] || "✨ 整理中…";
}

function lsKey(key: string, userId: string) { return `openrhtv_${userId}_${key}`; }

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

interface AppProps {
  userId: string;
  onLogout: () => void;
}

export default function App({ userId, onLogout }: AppProps) {
  const { threadId } = useParams<{ threadId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tid = threadId!;
  const isProView = searchParams.get("view") === "pro";

  const toggleProView = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (next.get("view") === "pro") {
        next.delete("view");
      } else {
        next.set("view", "pro");
      }
      return next;
    });
  }, [setSearchParams]);

  const [sessions, setSessions] = useState<string[]>(() => loadJSON<string[]>(lsKey("sessions", userId), []));
  const [names, setNames] = useState<Record<string, string>>(() => loadJSON<Record<string, string>>(lsKey("names", userId), {}));
  const isMobileInitial = typeof window !== "undefined" && window.matchMedia("(max-width: 768px)").matches;
  const [sidebarOpen, setSidebarOpen] = useState(!isMobileInitial);
  const [chatOpen, setChatOpen] = useState(!isMobileInitial);
  const showProToggle = isAdminUser(userId);

  // 监听 viewport 跨阈值变化(横竖屏切换 / 拉宽窗口),自动展开/收起 panel
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 768px)");
    const onChange = (e: MediaQueryListEvent) => {
      setSidebarOpen(!e.matches);
      setChatOpen(!e.matches);
    };
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);
  const [thinking, setThinking] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const messages = useCanvasStore((s) => s.messages);
  const streamingContent = useCanvasStore((s) => s.streamingContent);
  const setCanvas = useCanvasStore((s) => s.setCanvas);
  const addMessage = useCanvasStore((s) => s.addMessage);
  const setMessages = useCanvasStore((s) => s.setMessages);
  const appendStreaming = useCanvasStore((s) => s.appendStreaming);
  const finalizeStreaming = useCanvasStore((s) => s.finalizeStreaming);
  const clearMessages = useCanvasStore((s) => s.clear);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const didInit = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentThreadIdRef = useRef(tid);

  const onMessage = useCallback(
    (res: WSIncoming) => {
      // session_list 是用户级别消息，不经过 thread_id 过滤
      // 数据库是真相源头，本地只保留用户自定义的名称
      if (res.type === "session_list") {
        console.log(`[WS] session_list 收到 ${res.sessions.length} 个会话`);
        const ids = res.sessions.map(s => s.thread_id);
        const localNames = loadJSON<Record<string, string>>(lsKey("names", userId), {});
        const mergedNames: Record<string, string> = {};
        for (const id of ids) {
          if (localNames[id]) mergedNames[id] = localNames[id];
        }
        setSessions(ids);
        setNames(mergedNames);
        saveJSON(lsKey("sessions", userId), ids);
        saveJSON(lsKey("names", userId), mergedNames);
        return;
      }

      const rid = "thread_id" in res ? res.thread_id : undefined;
      if (rid && rid !== currentThreadIdRef.current) {
        console.log(`[WS] 忽略消息 thread=${rid} (当前=${currentThreadIdRef.current}) type=${res.type}`);
        return;
      }
      switch (res.type) {
        case "agent_response":
          console.log(`[WS] agent_response thread=${rid} content=${res.content?.slice(0, 50)}...`);
          setLoading(false);
          setThinking([]);
          finalizeStreaming(res.content);
          if (res.canvas) {
            queueMicrotask(() => setCanvas(res.canvas!));
          }
          break;
        case "canvas_updated":
          if (res.canvas) {
            queueMicrotask(() => setCanvas(res.canvas!));
          }
          break;
        case "processing":
          console.log(`[WS] processing thread=${rid}`);
          break;
        case "session_state":
          console.log(`[WS] session_state thread=${rid} msgs=${res.messages.length} nodes=${Object.keys(res.canvas?.nodes || {}).length}`);
          setMessages(res.messages);
          if (res.canvas) {
            queueMicrotask(() => setCanvas(res.canvas!));
          }
          break;
        case "agent_stream":
          if (res.event === "tool_call") {
            setThinking((t) => [...t, labelToolCall(res.name)]);
          } else if (res.event === "text" && res.content) {
            appendStreaming(res.content);
          }
          break;
        case "prompt_optimized":
          console.log(`[WS] prompt_optimized node=${res.node_id}`);
          queueMicrotask(() => {
            useCanvasStore.setState((s) => ({
              nodes: s.nodes.map((n) =>
                n.id === res.node_id ? { ...n, description: res.optimized_prompt } : n
              ),
            }));
          });
          break;
      }
    },
    [addMessage, setMessages, setCanvas, appendStreaming, finalizeStreaming, userId]
  );

  const { connect, sendMessage, sendPosition, sendGetSessionState, sendReviewNode, sendExecuteNode, sendUpdateNodeStatus, sendOptimizePrompt, sendCreateEdge, sendDeleteEdge, sendReorderEdge, sendDeleteSession, connected, connecting } =
    useWebSocket(userId, onMessage);
  currentThreadIdRef.current = tid;

  const addSession = useCallback((id: string) => {
    setSessions((prev) => {
      if (prev.includes(id)) return prev;
      const next = [id, ...prev];
      saveJSON(lsKey("sessions", userId), next);
      return next;
    });
  }, []);

  const handleRename = useCallback((id: string, name: string) => {
    setNames((prev) => {
      const next = { ...prev, [id]: name };
      saveJSON(lsKey("names", userId), next);
      return next;
    });
  }, []);

  const switchSession = useCallback(
    (id: string) => {
      if (id === tid) return;
      console.log(`[会话] 切换到 ${id}`);
      clearTimeout(timerRef.current ?? undefined);
      setLoading(false);
      setThinking([]);
      clearMessages();
      setCanvas({ nodes: {}, edges: [] });
      navigate(`/chat/${id}`);
    },
    [tid, navigate, clearMessages, setCanvas]
  );

  const handleDelete = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s !== id);
        saveJSON(lsKey("sessions", userId), next);
        return next;
      });
      setNames((prev) => {
        const { [id]: _, ...rest } = prev;
        saveJSON(lsKey("names", userId), rest);
        return rest;
      });
      sendDeleteSession(id);
    },
    [sendDeleteSession]
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
    currentThreadIdRef.current = tid;
    queueMicrotask(() => {
      addSession(tid);
      clearMessages();
      setCanvas({ nodes: {}, edges: [] });
      sendGetSessionState(tid);
    });
  }, [tid, addSession, clearMessages, setCanvas, sendGetSessionState]);

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
      }, 300_000);
    },
    [addMessage, sendMessage, tid]
  );

  const handleReview = useCallback(
    (nodeId: string, action: "approve" | "reject", feedback?: string) => {
      sendReviewNode({ type: "review_node", thread_id: tid, node_id: nodeId, action, feedback });
      if (action === "reject") {
        const f = feedback ? `，反馈意见：${feedback}` : "";
        handleSend(`驳回节点「${nodeId}」${f}\n节点 ${nodeId} 审核未通过，请根据反馈重新生成。`);
      }
      // approve 不自动发消息，由用户自己决定何时推进
    },
    [sendReviewNode, tid, handleSend]
  );

  const handleExecuteNode = useCallback(
    (nodeId: string, nodeType: NodeType, description: string, provider?: string, duration?: number, resolution?: string, generateAudio?: boolean) => {
      sendExecuteNode({ type: "execute_node", thread_id: tid, node_id: nodeId, node_type: nodeType, description, image_gen_provider: provider, duration, resolution, generate_audio: generateAudio });
    },
    [sendExecuteNode, tid]
  );

  const handleUpdateNodeStatus = useCallback(
    (nodeId: string, nodeStatus: "reviewing" | "confirmed") => {
      // 乐观更新本地 store（推迟到微任务避免跨渲染冲突）
      queueMicrotask(() => {
        useCanvasStore.setState((s) => ({
          nodes: s.nodes.map((n) =>
            n.id === nodeId ? { ...n, node_status: nodeStatus } : n
          ),
        }));
      });
      sendUpdateNodeStatus(tid, nodeId, nodeStatus);
    },
    [sendUpdateNodeStatus, tid]
  );

  const handleCreateEdge = useCallback(
    (source: string, target: string) => {
      sendCreateEdge(tid, source, target);
    },
    [sendCreateEdge, tid]
  );

  const handleReorderEdge = useCallback(
    (edgeId: string, direction: "up" | "down") => {
      sendReorderEdge(tid, edgeId, direction);
    },
    [sendReorderEdge, tid]
  );

  const handleDeleteEdge = useCallback(
    (edgeId: string) => {
      sendDeleteEdge(tid, edgeId);
    },
    [sendDeleteEdge, tid]
  );

  const handleOptimizePrompt = useCallback(
    (nodeId: string, prompt: string, feedback: string) => {
      sendOptimizePrompt({ type: "optimize_prompt", thread_id: tid, node_id: nodeId, prompt, feedback });
    },
    [sendOptimizePrompt, tid]
  );

  useEffect(() => {
    if (!loading) clearTimeout(timerRef.current ?? undefined);
  }, [loading]);

  return (
    <div className="relative flex flex-col h-screen bg-[var(--color-paper)] dark:bg-stone-950 text-stone-900 dark:text-stone-100 transition-colors duration-500">
      <DarkModeToggle />
      <Header
        userId={userId}
        sessionName={names[tid] || "新会话"}
        connected={connected}
        connecting={connecting}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onNewSession={handleNewSession}
        onLogout={onLogout}
        isProView={isProView}
        onToggleProView={showProToggle ? toggleProView : undefined}
        hideProToggle={shouldHideProToggle(userId)}
      />
      <div className="flex flex-1 overflow-hidden">
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
        {isProView ? (
          <>
            <Canvas onPositionChange={(pos) => sendPosition({ ...pos, thread_id: tid })} onCreateEdge={handleCreateEdge} onDeleteEdge={handleDeleteEdge} />
            {selectedNodeId && (
              <NodeDetail
                onReview={handleReview}
                onExecuteNode={handleExecuteNode}
                onUpdateNodeStatus={handleUpdateNodeStatus}
                onOptimizePrompt={handleOptimizePrompt}
                onDeleteEdge={handleDeleteEdge}
                onReorderEdge={handleReorderEdge}
              />
            )}
          </>
        ) : (
          <CardStack />
        )}
        {chatOpen ? (
          <ChatPanel
            messages={messages}
            streaming={streamingContent}
            thinking={thinking}
            onSend={handleSend}
            loading={loading}
            onToggleCollapse={() => setChatOpen(false)}
          />
        ) : (
          <button
            onClick={() => setChatOpen(true)}
            className="absolute bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-stone-900 dark:bg-[#7c2d12] text-[#faf8f3] shadow-[0_6px_20px_-4px_rgba(28,25,23,0.25)] dark:shadow-[0_6px_20px_-4px_rgba(124,45,18,0.5)] hover:scale-105 active:scale-95 transition-transform duration-200"
            title="问导演"
            type="button"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 4h12M3 9h12M3 14h8" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

