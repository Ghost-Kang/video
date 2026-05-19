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
  const tid = threadId!;

  const [sessions, setSessions] = useState<string[]>(() => loadJSON<string[]>(lsKey("sessions", userId), []));
  const [names, setNames] = useState<Record<string, string>>(() => loadJSON<Record<string, string>>(lsKey("names", userId), {}));
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(true);
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

  const onMessage = useCallback(
    (res: WSIncoming) => {
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
            setThinking((t) => [...t, `${res.name}(${res.args?.slice(0, 80) || ""})`]);
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
    [addMessage, setMessages, setCanvas, appendStreaming, finalizeStreaming]
  );

  const { connect, sendMessage, sendPosition, sendGetSessionState, sendReviewNode, sendExecuteNode, sendUpdateNodeStatus, sendOptimizePrompt, sendCreateEdge, sendDeleteEdge, sendReorderEdge, connected, connecting } =
    useWebSocket(userId, onMessage);
  const didInit = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentThreadIdRef = useRef(tid);
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
      currentThreadIdRef.current = id;
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
    },
    []
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
    setCanvas({ nodes: {}, edges: [] });
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
    (nodeId: string, nodeType: string, description: string, provider?: string, duration?: number, resolution?: string, generateAudio?: boolean) => {
      sendExecuteNode({ type: "execute_node", thread_id: tid, node_id: nodeId, node_type: nodeType as any, description, image_gen_provider: provider, duration, resolution, generate_audio: generateAudio });
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
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header
        userId={userId}
        sessionName={names[tid] || "新会话"}
        connected={connected}
        connecting={connecting}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onNewSession={handleNewSession}
        onLogout={onLogout}
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
            streaming={streamingContent}
            thinking={thinking}
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
        <Canvas onPositionChange={(pos) => sendPosition({ ...pos, thread_id: tid })} onCreateEdge={handleCreateEdge} onDeleteEdge={handleDeleteEdge} />
        {selectedNodeId && <NodeDetail onReview={handleReview} onExecuteNode={handleExecuteNode} onUpdateNodeStatus={handleUpdateNodeStatus} onOptimizePrompt={handleOptimizePrompt} onDeleteEdge={handleDeleteEdge} onReorderEdge={handleReorderEdge} />}
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
