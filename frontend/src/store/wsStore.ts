import { create } from "zustand";
import { useCanvasStore } from "./canvasStore";
import { useSessionStore } from "./sessionStore";
import type { WSEvent } from "../types/ws";

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

interface WSStore {
  currentThreadId: string;
  thinking: string[];
  loading: boolean;
  setCurrentThreadId: (threadId: string) => void;
  setLoading: (loading: boolean) => void;
  resetThinking: () => void;
  dispatch: (event: WSEvent, userId: string) => void;
}

export const useWSStore = create<WSStore>((set, get) => ({
  currentThreadId: "",
  thinking: [],
  loading: false,

  setCurrentThreadId: (threadId) => set({ currentThreadId: threadId }),
  setLoading: (loading) => set({ loading }),
  resetThinking: () => set({ thinking: [] }),

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
      case "error":
        console.warn("[WS] error", event.code, event.message);
        break;
    }
  },
}));
