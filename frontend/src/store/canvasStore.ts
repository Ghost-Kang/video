import { create } from "zustand";
import type { CanvasNode } from "../types";

interface CanvasStore {
  nodes: CanvasNode[];
  messages: { role: "user" | "agent"; content: string }[];
  selectedNodeId: string | null;
  setCanvas: (data: Record<string, CanvasNode>) => void;
  updateNodePosition: (id: string, x: number, y: number) => void;
  addMessage: (role: "user" | "agent", content: string) => void;
  setMessages: (msgs: { role: "user" | "agent"; content: string }[]) => void;
  selectNode: (id: string | null) => void;
  clear: () => void;
}

export const useCanvasStore = create<CanvasStore>((set) => ({
  nodes: [],
  messages: [],
  selectedNodeId: null,

  setCanvas: (data) =>
    set({ nodes: Object.values(data) }),

  updateNodePosition: (id, x, y) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, x, y } : n)),
    })),

  addMessage: (role, content) =>
    set((s) => ({ messages: [...s.messages, { role, content }] })),

  setMessages: (msgs) => set({ messages: msgs }),

  selectNode: (id) => set({ selectedNodeId: id }),

  clear: () => set({ nodes: [], messages: [], selectedNodeId: null }),
}));
