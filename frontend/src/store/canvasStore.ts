import { create } from "zustand";
import type { CanvasNode } from "../types";

interface Edge {
  id: string;
  source: string;
  target: string;
  position?: number;
}

interface CanvasStore {
  nodes: CanvasNode[];
  edges: Edge[];
  messages: { role: "user" | "agent"; content: string }[];
  selectedNodeId: string | null;
  streamingContent: string;
  setCanvas: (data: { nodes: Record<string, CanvasNode>; edges?: unknown[] }) => void;
  updateNodePosition: (id: string, x: number, y: number) => void;
  addEdge: (edge: Edge) => void;
  removeEdge: (id: string) => void;
  addMessage: (role: "user" | "agent", content: string) => void;
  setMessages: (msgs: { role: "user" | "agent"; content: string }[]) => void;
  selectNode: (id: string | null) => void;
  appendStreaming: (text: string) => void;
  finalizeStreaming: (content: string) => void;
  clear: () => void;
}

export const useCanvasStore = create<CanvasStore>((set) => ({
  nodes: [],
  edges: [],
  messages: [],
  selectedNodeId: null,
  streamingContent: "",

  setCanvas: (data) =>
    set({
      nodes: Object.values(data.nodes),
      edges: (data.edges || []) as Edge[],
    }),

  updateNodePosition: (id, x, y) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, x, y } : n)),
    })),

  addEdge: (edge) =>
    set((s) => {
      if (s.edges.some((e) => e.source === edge.source && e.target === edge.target)) return s;
      return { edges: [...s.edges, edge] };
    }),

  removeEdge: (id) =>
    set((s) => ({ edges: s.edges.filter((e) => e.id !== id) })),

  addMessage: (role, content) =>
    set((s) => ({ messages: [...s.messages, { role, content }] })),

  setMessages: (msgs) => set({ messages: msgs }),

  selectNode: (id) => set({ selectedNodeId: id }),

  appendStreaming: (text) =>
    set((s) => ({ streamingContent: s.streamingContent + text })),

  finalizeStreaming: (content) =>
    set((s) => ({
      messages: [...s.messages, { role: "agent" as const, content }],
      streamingContent: "",
    })),

  clear: () => set({ nodes: [], edges: [], messages: [], selectedNodeId: null, streamingContent: "" }),
}));
