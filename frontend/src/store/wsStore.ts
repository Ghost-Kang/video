import { create } from "zustand";
import { useCanvasStore } from "./canvasStore";
import { useSessionStore } from "./sessionStore";
import { useToastStore } from "./toastStore";
import type { WSEvent } from "../types/ws";


// 把后端 invalid_command code 映射成宝妈看得懂的中文标题。
// 未列的 code 一律 fallback 到通用 "请求出错"。
const ERROR_CODE_TITLES: Record<string, string> = {
  invalid_command: "请求格式不对",
  malformed_json: "数据格式不对",
};

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

interface ConnectionStatus {
  connected?: boolean;
  connecting?: boolean;
  reconnectAttempt?: number;
}

interface WSStore {
  currentThreadId: string;
  thinking: string[];
  loading: boolean;
  // W4D5-T1: WS 连接状态共享给根级 <ConnectionBanner/>。useWebSocket 是 App
  // 内部 hook,banner 是全局组件,中间靠 store 解耦。
  connected: boolean;
  connecting: boolean;
  reconnectAttempt: number;
  setCurrentThreadId: (threadId: string) => void;
  setLoading: (loading: boolean) => void;
  resetThinking: () => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  dispatch: (event: WSEvent, userId: string) => void;
}

export const useWSStore = create<WSStore>((set, get) => ({
  currentThreadId: "",
  thinking: [],
  loading: false,
  connected: false,
  connecting: false,
  reconnectAttempt: 0,

  setCurrentThreadId: (threadId) => set({ currentThreadId: threadId }),
  setLoading: (loading) => set({ loading }),
  resetThinking: () => set({ thinking: [] }),
  setConnectionStatus: (status) =>
    set((state) => ({
      connected: status.connected ?? state.connected,
      connecting: status.connecting ?? state.connecting,
      reconnectAttempt: status.reconnectAttempt ?? state.reconnectAttempt,
    })),

  dispatch: (event, userId) => {
    const canvas = useCanvasStore.getState();
    const sessions = useSessionStore.getState();

    if (event.type === "session_list") {
      const ids = event.sessions.map((s) => s.thread_id);
      const mergedNames: Record<string, string> = {};
      for (const id of ids) {
        if (sessions.names[id]) mergedNames[id] = sessions.names[id];
      }
      sessions.setUserId(userId);
      sessions.setSessions(ids);
      sessions.setNames(mergedNames);
      return;
    }

    const rid = "thread_id" in event ? event.thread_id : undefined;
    if (rid && rid !== get().currentThreadId) return;

    switch (event.type) {
      case "agent_response":
        set({ loading: false, thinking: [] });
        canvas.finalizeStreaming(event.content);
        if (event.canvas) queueMicrotask(() => canvas.setCanvas(event.canvas!));
        break;
      case "canvas_updated":
        if (event.canvas) queueMicrotask(() => canvas.setCanvas(event.canvas!));
        break;
      case "processing":
        break;
      case "session_state":
        canvas.setMessages(event.messages);
        if (event.canvas) queueMicrotask(() => canvas.setCanvas(event.canvas!));
        break;
      case "agent_stream":
        if (event.event === "tool_call") {
          set((state) => ({ thinking: [...state.thinking, labelToolCall(event.name ?? undefined)] }));
        } else if (event.event === "text" && event.content) {
          canvas.appendStreaming(event.content);
        }
        break;
      case "prompt_optimized":
        queueMicrotask(() => {
          useCanvasStore.setState((state) => ({
            nodes: state.nodes.map((node) =>
              node.id === event.node_id ? { ...node, description: event.optimized_prompt } : node
            ),
          }));
        });
        break;
      case "error": {
        // 仍保留 console 给开发期 debug。
        console.warn("[WS] error", event.code, event.message, event.bad_type);
        // 推到 toast 让用户实际看到 — 不然 Pydantic 校验失败完全静默。
        const title = ERROR_CODE_TITLES[event.code] ?? "请求出错";
        // body 用 bad_type 给开发者线索;不暴露 Pydantic 详细 message(那对宝妈无意义)。
        const body = event.bad_type ? `操作:${event.bad_type}` : undefined;
        useToastStore.getState().push({ kind: "error", title, body });
        break;
      }
    }
  },
}));
