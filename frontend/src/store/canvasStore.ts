import { create } from "zustand";
import type { CanvasNode } from "../types";
import type { CascadeAnalysisContract, FailurePayload, Scene } from "../types/cascade";
import type { RewriteShot } from "../lib/cascadeMapper";
import { buildDefaultScript } from "../fixtures/baomamFushi001";

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
  analysis: CascadeAnalysisContract | null;
  script: string;
  /** 源视频每一幕 — 永远绑 analysis.scenes,不被 rewrite 覆盖。 */
  shots: Scene[];
  /** 改写后的镜头 — 跟 shots 共存,空时不渲染对应区域。 */
  rewriteShots: RewriteShot[];
  failure: FailurePayload | null;
  setCanvas: (data: { nodes: Record<string, CanvasNode>; edges?: unknown[] }) => void;
  updateNodePosition: (id: string, x: number, y: number) => void;
  addEdge: (edge: Edge) => void;
  removeEdge: (id: string) => void;
  addMessage: (role: "user" | "agent", content: string) => void;
  setMessages: (msgs: { role: "user" | "agent"; content: string }[]) => void;
  selectNode: (id: string | null) => void;
  appendStreaming: (text: string) => void;
  finalizeStreaming: (content: string) => void;
  setAnalysis: (analysis: CascadeAnalysisContract | null) => void;
  setScript: (script: string) => void;
  setShots: (shots: Scene[]) => void;
  setRewriteShots: (shots: RewriteShot[]) => void;
  updateShotFirstFrame: (scene_index: number, url: string) => void;
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
  // W4D5: initial state is empty — no mock fixture. Real analysis lands
  // via WS `analysis_returned` and flips the CardStack into render mode.
  analysis: null,
  script: "",
  shots: [],
  rewriteShots: [],
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

  setAnalysis: (analysis) => set({ analysis }),

  setScript: (script) => set({ script }),

  setShots: (shots) => set({ shots }),

  setRewriteShots: (rewriteShots) => set({ rewriteShots }),

  updateShotFirstFrame: (scene_index, url) =>
    set((s) => ({
      shots: s.shots.map((sh) =>
        sh.scene_index === scene_index ? { ...sh, first_frame_url: url } : sh
      ),
    })),

  setFailure: (failure) => set({ failure }),

  loadFromAnalysis: (analysis) =>
    set((state) => {
      // W5D3 Bug #7 — re-applying the same analysis (e.g. duplicate WS frame
      // on reconnect, or a snapshot replay) must not nuke the rewrite the
      // user just spent 60s producing. Only reset script/rewriteShots when
      // the analysis_id actually changed.
      const sameAnalysis =
        state.analysis !== null && state.analysis.analysis_id === analysis.analysis_id;
      return sameAnalysis
        ? {
            analysis,
            shots: analysis.scenes,
            failure: null,
          }
        : {
            analysis,
            script: buildDefaultScript(analysis),
            shots: analysis.scenes,
            rewriteShots: [],
            failure: null,
          };
    }),

  clear: () =>
    set({
      nodes: [],
      edges: [],
      messages: [],
      selectedNodeId: null,
      streamingContent: "",
      analysis: null,
      script: "",
      shots: [],
      rewriteShots: [],
      failure: null,
    }),
}));
