import { create } from "zustand";
import type { ProEdge, ProEstimate, ProPortType, ProRunEvent } from "../types/pro";

/**
 * Pro 高级子画布状态。**节点本体住在 tldraw editor**(自定义 shape,源真相);这里只管:
 * 连线(edges,以 InFrontOfTheCanvas overlay 渲染)、连线进行态(pending,点输出→点输入)、
 * Run 运行态(runId/status/outputs/error)、成本估算 + 确认弹窗、当前选中节点(参数面板)。
 * 纯状态、不 import tldraw → 可单测。
 */

export type ProRunStatus =
  | "idle"
  | "queued"
  | "submitting"
  | "running"
  | "done"
  | "failed"
  | "cancelled";

export interface PendingConnection {
  nodeId: string;
  handle: string;
  portType: ProPortType;
  /** 从输出口拉(out)还是从输入口拉(in)—— MVP 只支持 out→in。 */
  end: "source" | "target";
}

export interface ProRunState {
  runId: string | null;
  status: ProRunStatus;
  outputs: string[];
  error: string | null;
  pct: number;
}

const IDLE_RUN: ProRunState = { runId: null, status: "idle", outputs: [], error: null, pct: 0 };

interface ProCanvasStore {
  edges: ProEdge[];
  pending: PendingConnection | null;
  selectedNodeId: string | null;
  estimate: ProEstimate | null;
  costModalOpen: boolean;
  run: ProRunState;

  setEdges: (edges: ProEdge[]) => void;
  addEdge: (edge: Omit<ProEdge, "id"> & { id?: string }, opts?: { multi?: boolean }) => void;
  removeEdge: (edgeId: string) => void;
  removeEdgesForNodes: (nodeIds: string[]) => void;
  startConnection: (c: PendingConnection) => void;
  cancelConnection: () => void;
  setSelectedNodeId: (id: string | null) => void;

  openCostModal: (estimate: ProEstimate) => void;
  closeCostModal: () => void;

  setRun: (patch: Partial<ProRunState>) => void;
  resetRun: () => void;
  applyProRunEvent: (ev: ProRunEvent) => void;

  reset: () => void;
}

let _edgeSeq = 0;
function nextEdgeId(): string {
  _edgeSeq += 1;
  return `pe_${_edgeSeq}_${Math.random().toString(36).slice(2, 8)}`;
}

export const useProCanvasStore = create<ProCanvasStore>((set, get) => ({
  edges: [],
  pending: null,
  selectedNodeId: null,
  estimate: null,
  costModalOpen: false,
  run: IDLE_RUN,

  setEdges: (edges) => set({ edges }),

  addEdge: (edge, opts) => {
    // 单值输入:同一 (target, targetHandle) 只保留一条 —— 新连替换旧连(与后端 multi_input 守卫一致)。
    // multi 输入(如 Compose.videos):保留多条,只去掉完全相同的重复边。
    const multi = !!opts?.multi;
    const filtered = get().edges.filter((e) =>
      multi
        ? !(e.source === edge.source && e.sourceHandle === edge.sourceHandle && e.target === edge.target && e.targetHandle === edge.targetHandle)
        : !(e.target === edge.target && e.targetHandle === edge.targetHandle),
    );
    filtered.push({ id: edge.id ?? nextEdgeId(), source: edge.source, sourceHandle: edge.sourceHandle, target: edge.target, targetHandle: edge.targetHandle });
    set({ edges: filtered });
  },

  removeEdge: (edgeId) => set((s) => ({ edges: s.edges.filter((e) => e.id !== edgeId) })),

  removeEdgesForNodes: (nodeIds) => {
    const drop = new Set(nodeIds);
    set((s) => ({ edges: s.edges.filter((e) => !drop.has(e.source) && !drop.has(e.target)) }));
  },

  startConnection: (c) => set({ pending: c }),
  cancelConnection: () => set({ pending: null }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  openCostModal: (estimate) => set({ estimate, costModalOpen: true }),
  closeCostModal: () => set({ costModalOpen: false }),

  setRun: (patch) => set((s) => ({ run: { ...s.run, ...patch } })),
  resetRun: () => set({ run: IDLE_RUN }),

  applyProRunEvent: (ev) => {
    const cur = get().run;
    // 只认当前 run(runId 由后端首帧 queued 铸造并下发)。runId 未定 → 接纳首帧。
    if (cur.runId && "run_id" in ev && ev.run_id !== cur.runId) return;
    switch (ev.type) {
      case "pro_run_progress": {
        const status: ProRunStatus =
          ev.status === "cancelled"
            ? "cancelled"
            : ev.status === "queued"
              ? "queued"
              : ev.status === "submitting"
                ? "submitting"
                : "running";
        set({ run: { ...cur, runId: ev.run_id, status, pct: ev.pct ?? cur.pct } });
        break;
      }
      case "pro_run_node_done":
        set({ run: { ...cur, runId: ev.run_id, outputs: [...cur.outputs, ev.output_url] } });
        break;
      case "pro_run_done":
        set({ run: { ...cur, runId: ev.run_id, status: "done", pct: 100, outputs: ev.outputs ?? cur.outputs } });
        break;
      case "pro_run_failed":
        set({ run: { ...cur, runId: ev.run_id, status: "failed", error: ev.error } });
        break;
    }
  },

  reset: () => set({ edges: [], pending: null, selectedNodeId: null, estimate: null, costModalOpen: false, run: IDLE_RUN }),
}));
