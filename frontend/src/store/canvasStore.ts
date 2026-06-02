import { create } from "zustand";
import type { CanvasNode } from "../types";
import type { CascadeAnalysisContract, FailurePayload, Scene } from "../types/cascade";
import type { RewriteShot } from "../lib/cascadeMapper";

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
  updateRewriteShotFirstFrame: (shot_index: number, url: string) => void;
  setRewriteShotFirstFrameError: (shot_index: number, error: string | null) => void;
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

  // 生成草稿图 leg:把首帧 URL 打到对应 shot_index 的改写镜头上(成功 → 清除任何旧错误)。
  updateRewriteShotFirstFrame: (shot_index, url) =>
    set((s) => ({
      rewriteShots: s.rewriteShots.map((sh) =>
        sh.shot_index === shot_index
          ? { ...sh, firstFrameUrl: url, firstFrameError: undefined }
          : sh
      ),
    })),

  // 生成失败/重试:置(error 字符串)或清(null)对应镜头的错误态。
  setRewriteShotFirstFrameError: (shot_index, error) =>
    set((s) => ({
      rewriteShots: s.rewriteShots.map((sh) =>
        sh.shot_index === shot_index
          ? { ...sh, firstFrameError: error ?? undefined }
          : sh
      ),
    })),

  setFailure: (failure) => set({ failure }),

  loadFromAnalysis: (analysis) =>
    set((state) => {
      // W5D3 Bug #7 — re-applying the same analysis (e.g. duplicate WS frame
      // on reconnect, or a snapshot replay) must not nuke the rewrite the
      // user just spent 60s producing. Only reset script/rewriteShots when
      // the analysis_id actually changed.
      //
      // W5D3 CR-P1 follow-up — `analysis_id` is deterministic
      // hash(user_id + source_url); a re-analysis of the same URL returns the
      // SAME id even if Doubao produced different scenes. Comparing by id
      // alone risks leaving rewriteShots indexed against the OLD scenes when
      // the new analysis has rearranged them. Compare a coarse scenes
      // signature (count + every timestamp pair) so true re-analysis with
      // mutated scenes triggers a full reset of dependent state.
      const sceneSignature = (a: CascadeAnalysisContract) =>
        `${a.scenes.length}|` +
        a.scenes
          .map((s) => `${s.timestamp_start}-${s.timestamp_end}`)
          .join(",");
      const sameAnalysis =
        state.analysis !== null &&
        state.analysis.analysis_id === analysis.analysis_id &&
        sceneSignature(state.analysis) === sceneSignature(analysis);
      // W4 redesign + 缺陷 ① 修复:分析阶段 script 留空,不再预填源逐字稿
      // (buildDefaultScript)。「改完的版本」/「拿去发」是改写产物(幕2/3),
      // 由 rewrite_returned 的 setScript 填入;分析回来只显示幕1(为什么火+选方向)。
      // 否则改写在途的 ~30s 窗口里,源逐字稿会被误显示成「改完的版本」+ 过早冒出发布包。
      return sameAnalysis
        ? {
            analysis,
            shots: analysis.scenes,
            failure: null,
          }
        : {
            analysis,
            script: "",
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
