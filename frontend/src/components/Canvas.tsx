import { useState, useRef, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  applyNodeChanges,
  applyEdgeChanges,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

import { useCanvasStore } from "../store/canvasStore";
import { ScriptNode } from "./nodes/ScriptNode";
import { ImageNode } from "./nodes/ImageNode";
import { VideoNode } from "./nodes/VideoNode";
import { AudioNode } from "./nodes/AudioNode";
import { DeletableEdge } from "./DeletableEdge";
import type { CanvasNode, WSPositionUpdate } from "../types";

const nodeTypes = {
  script: ScriptNode,
  image: ImageNode,
  video: VideoNode,
  audio: AudioNode,
};

const edgeTypes = {
  default: DeletableEdge,
};

const NODE_W = 200;
const NODE_H = 120;

function defaultLayout(nodes: CanvasNode[]): Node[] {
  const typeX: Record<string, number> = { script: 0, image: 400, video: 800, audio: 1200 };
  return nodes.map((n, i) => ({
    id: n.id, type: n.type,
    position: {
      x: n.x ?? (typeX[n.type] ?? 100),
      y: n.y ?? (100 + i * 240),
    },
    data: { node: n },
  }));
}

function getShotNo(node: CanvasNode): number {
  if (node.shot_no != null) {
    const n = parseInt(node.shot_no, 10);
    if (!isNaN(n)) return n;
  }
  return 0;
}

function dagreLayout(nodes: CanvasNode[], edges: { source: string; target: string }[]): Map<string, { x: number; y: number }> {
  // 1. 全图跑一次 dagre LR，得到水平结构
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 120, ranksep: 300, marginx: 80, marginy: 80 });

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_W, height: NODE_H });
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target);
  }
  dagre.layout(g);

  // 2. 按 dagre x 坐标分列（同一横向层级）
  const COL_GAP = 150;
  const columns: Map<number, { id: string; x: number; y: number; shotNo: number }[]> = new Map();
  for (const n of nodes) {
    const pos = g.node(n.id);
    if (!pos) continue;
    const colKey = Math.round(pos.x / COL_GAP);
    const col = columns.get(colKey) || [];
    col.push({ id: n.id, x: pos.x - NODE_W / 2, y: pos.y, shotNo: getShotNo(n) });
    columns.set(colKey, col);
  }

  // 3. 每列内按 shot_no 重排 y
  const positions = new Map<string, { x: number; y: number }>();
  // 列按 x 从小到大处理（左→右）
  const sortedColKeys = [...columns.keys()].sort((a, b) => a - b);

  for (const colKey of sortedColKeys) {
    const col = columns.get(colKey)!;
    // 按 shot_no 排序（0 的排在后面）
    col.sort((a, b) => {
      if (a.shotNo === 0 && b.shotNo === 0) return 0;
      if (a.shotNo === 0) return 1;
      if (b.shotNo === 0) return -1;
      return a.shotNo - b.shotNo;
    });

    // 重新分配 y，shot 之间加间距
    let curY = 80;
    let prevShotNo = -1;
    for (const item of col) {
      if (item.shotNo > 0 && prevShotNo > 0 && item.shotNo !== prevShotNo) {
        curY += 120; // 不同分镜之间额外间距
      }
      positions.set(item.id, { x: item.x, y: curY });
      curY += NODE_H + 60;
      if (item.shotNo > 0) prevShotNo = item.shotNo;
    }
  }

  return positions;
}

interface Props {
  onPositionChange: (update: WSPositionUpdate) => void;
  onCreateEdge: (source: string, target: string) => void;
  onDeleteEdge: (edgeId: string) => void;
}

export function Canvas({ onPositionChange, onCreateEdge, onDeleteEdge }: Props) {
  const canvasNodes = useCanvasStore((s) => s.nodes);
  const edges = useCanvasStore((s) => s.edges);
  const updateNodePosition = useCanvasStore((s) => s.updateNodePosition);
  const addEdge = useCanvasStore((s) => s.addEdge);
  const removeEdge = useCanvasStore((s) => s.removeEdge);
  const selectNode = useCanvasStore((s) => s.selectNode);

  const [rfNodes, setRfNodes] = useState<Node[]>(() => defaultLayout(canvasNodes));

  useEffect(() => {
    const handler = (e: Event) => {
      const { edgeId } = (e as CustomEvent).detail;
      removeEdge(edgeId);
      onDeleteEdge(edgeId);
    };
    window.addEventListener("delete_edge", handler);
    return () => window.removeEventListener("delete_edge", handler);
  }, [removeEdge, onDeleteEdge]);

  useEffect(() => {
    setRfNodes((prev) => {
      const prevMap = new Map(prev.map((n) => [n.id, n]));
      return defaultLayout(canvasNodes).map((n) => {
        const existing = prevMap.get(n.id);
        if (existing) {
          return { ...n, position: n.position, width: existing.width, height: existing.height };
        }
        return n;
      });
    });
  }, [canvasNodes]);

  const persistRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      setRfNodes((nds) => {
        const updated = applyNodeChanges(changes, nds);
        for (const c of changes) {
          if (c.type === "position" && c.position) {
            const x = Math.round(c.position.x);
            const y = Math.round(c.position.y);
            updateNodePosition(c.id, x, y);
            if (persistRef.current[c.id]) clearTimeout(persistRef.current[c.id]);
            persistRef.current[c.id] = setTimeout(() => {
              onPositionChange({ type: "update_position", thread_id: "", node_id: c.id, x, y });
              delete persistRef.current[c.id];
            }, 300);
          }
        }
        return updated;
      });
    },
    [updateNodePosition, onPositionChange]
  );

  const handleConnect: OnConnect = useCallback(
    (connection) => {
      if (!connection.source || !connection.target) return;
      const edgeId = `e-${connection.source}-${connection.target}`;
      // 检查重复
      if (edges.some((e) => e.source === connection.source && e.target === connection.target)) return;
      addEdge({ id: edgeId, source: connection.source, target: connection.target });
      onCreateEdge(connection.source, connection.target);
    },
    [edges, addEdge, onCreateEdge]
  );

  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      for (const c of changes) {
        if (c.type === "remove") {
          removeEdge(c.id);
          onDeleteEdge(c.id);
        }
      }
    },
    [removeEdge, onDeleteEdge]
  );

  const handleAutoLayout = useCallback(() => {
    const positions = dagreLayout(canvasNodes, edges);
    for (const [id, pos] of positions) {
      updateNodePosition(id, pos.x, pos.y);
      onPositionChange({ type: "update_position", thread_id: "", node_id: id, x: pos.x, y: pos.y });
    }
    setRfNodes((prev) =>
      prev.map((n) => {
        const pos = positions.get(n.id);
        return pos ? { ...n, position: pos } : n;
      })
    );
  }, [canvasNodes, edges, updateNodePosition, onPositionChange]);

  return (
    <div style={{ flex: 1, height: "100%", position: "relative" }}>
      <ReactFlow
        nodes={rfNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onNodeClick={(_e, node) => selectNode(node.id)}
        defaultEdgeOptions={{ deletable: true, style: { stroke: "#a1a1aa", strokeWidth: 2 } }}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap
          position="bottom-right"
          style={{ background: "#fafafa", border: "1px solid #e4e4e7", borderRadius: 8 }}
          nodeColor={(n) => {
            const t = (n.data?.node as { type?: string })?.type;
            return t === "script" ? "#18181b" : t === "image" ? "#52525b" : t === "video" ? "#a1a1aa" : t === "audio" ? "#d4d4d8" : "#e4e4e7";
          }}
        />
      </ReactFlow>
      <button onClick={handleAutoLayout} style={S.layoutBtn} title="自动排版">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      </button>
    </div>
  );
}

const S = {
  layoutBtn: {
    position: "absolute",
    top: 12,
    right: 12,
    width: 36,
    height: 36,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#fff",
    border: "1px solid #e4e4e7",
    borderRadius: 8,
    cursor: "pointer",
    color: "#71717a",
    zIndex: 10,
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  } as React.CSSProperties,
};
