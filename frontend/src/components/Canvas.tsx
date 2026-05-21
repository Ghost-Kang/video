import { useState, useRef, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  applyNodeChanges,
  type Node,
  type OnNodesChange,
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

import { useCanvasStore } from "../store/canvasStore";
import { ScriptNode } from "./nodes/ScriptNode";
import { ImageNode } from "./nodes/ImageNode";
import { VideoNode } from "./nodes/VideoNode";
import { AudioNode } from "./nodes/AudioNode";
import type { CanvasNode, WSPositionUpdate } from "../types";

const nodeTypes = {
  script: ScriptNode,
  image: ImageNode,
  video: VideoNode,
  audio: AudioNode,
};

const NODE_W = 200;
const NODE_H = 120;

function defaultLayout(nodes: CanvasNode[]): Node[] {
  return nodes.map((n) => ({
    id: n.id, type: n.type,
    position: { x: n.x ?? 100, y: n.y ?? 100 },
    data: { node: n },
  }));
}

function dagreLayout(nodes: CanvasNode[], edges: { source: string; target: string }[]): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 60, ranksep: 200, marginx: 40, marginy: 40 });

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_W, height: NODE_H });
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target);
  }
  dagre.layout(g);

  const positions = new Map<string, { x: number; y: number }>();
  for (const n of nodes) {
    const pos = g.node(n.id);
    if (pos) positions.set(n.id, { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 });
  }
  return positions;
}

interface Props {
  onPositionChange: (update: WSPositionUpdate) => void;
}

export function Canvas({ onPositionChange }: Props) {
  const canvasNodes = useCanvasStore((s) => s.nodes);
  const edges = useCanvasStore((s) => s.edges);
  const updateNodePosition = useCanvasStore((s) => s.updateNodePosition);
  const selectNode = useCanvasStore((s) => s.selectNode);

  const [rfNodes, setRfNodes] = useState<Node[]>(() => defaultLayout(canvasNodes));

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
        onNodesChange={handleNodesChange}
        onNodeClick={(_e, node) => selectNode(node.id)}
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
