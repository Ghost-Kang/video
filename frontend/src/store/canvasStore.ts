import { create } from "zustand";
import type { CanvasNode } from "../types";
import type { CascadeAnalysisContract, FailurePayload, Scene } from "../types/cascade";
import {
  MOCK_BAOMAM_ANALYSIS,
  buildDefaultScript,
} from "../fixtures/baomamFushi001";

interface Edge {
  id: string;
  source: string;
  target: string;
}

interface CanvasStore {
  nodes: CanvasNode[];
  edges: Edge[];
  messages: { role: "user" | "agent"; content: string }[];
  selectedNodeId: string | null;
  streamingContent: string;
  analysis: CascadeAnalysisContract | null;
  script: string;
  shots: Scene[];
  failure: FailurePayload | null;
  setCanvas: (data: { nodes: Record<string, CanvasNode>; edges?: unknown[] }) => void;
  updateNodePosition: (id: string, x: number, y: number) => void;
  addMessage: (role: "user" | "agent", content: string) => void;
  setMessages: (msgs: { role: "user" | "agent"; content: string }[]) => void;
  selectNode: (id: string | null) => void;
  appendStreaming: (text: string) => void;
  finalizeStreaming: (content: string) => void;
  setAnalysis: (analysis: CascadeAnalysisContract | null) => void;
  setScript: (script: string) => void;
  setShots: (shots: Scene[]) => void;
  setFailure: (failure: FailurePayload | null) => void;
  loadFromAnalysis: (analysis: CascadeAnalysisContract) => void;
  clear: () => void;
}

export const useCanvasStore = create<CanvasStore>((set) => ({
  nodes: [],
  edges: [],
  messages: [],
  selectedNodeId: null,
  streamingContent: "",
  analysis: MOCK_BAOMAM_ANALYSIS,
  script: buildDefaultScript(MOCK_BAOMAM_ANALYSIS),
  shots: MOCK_BAOMAM_ANALYSIS.scenes,
  failure: null,

  setCanvas: (data) =>
    set({
      nodes: Object.values(data.nodes),
      edges: (data.edges || []) as Edge[],
    }),

  updateNodePosition: (id, x, y) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, x, y } : n)),
    })),

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

  setAnalysis: (analysis) => set({ analysis }),

  setScript: (script) => set({ script }),

  setShots: (shots) => set({ shots }),

  setFailure: (failure) => set({ failure }),

  loadFromAnalysis: (analysis) =>
    set({
      analysis,
      script: buildDefaultScript(analysis),
      shots: analysis.scenes,
      failure: null,
    }),

  clear: () =>
    set({
      nodes: [],
      edges: [],
      messages: [],
      selectedNodeId: null,
      streamingContent: "",
      analysis: MOCK_BAOMAM_ANALYSIS,
      script: buildDefaultScript(MOCK_BAOMAM_ANALYSIS),
      shots: MOCK_BAOMAM_ANALYSIS.scenes,
      failure: null,
    }),
}));
