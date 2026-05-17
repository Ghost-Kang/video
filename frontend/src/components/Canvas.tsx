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
import "@xyflow/react/dist/style.css";

import { useCanvasStore } from "../store/canvasStore";
import { ScriptNode } from "./nodes/ScriptNode";
import { StoryboardNode } from "./nodes/StoryboardNode";
import { ImageNode } from "./nodes/ImageNode";
import { VideoNode } from "./nodes/VideoNode";
import { AudioNode } from "./nodes/AudioNode";
import type { CanvasNode, WSPositionUpdate } from "../types";

const nodeTypes = {
  script: ScriptNode,
  storyboard: StoryboardNode,
  image: ImageNode,
  video: VideoNode,
  audio: AudioNode,
};

function defaultLayout(nodes: CanvasNode[]): Node[] {
  const order = ["script", "storyboard", "image", "video", "audio"];
  const gap = 200;
  return nodes.map((n, i) => {
    const col = order.indexOf(n.type);
    const x = n.x ?? 100 + (col >= 0 ? col : 0) * 320;
    const y = n.y ?? (i + 1) * gap;
    return { id: n.id, type: n.type, position: { x, y }, data: { node: n } };
  });
}

interface Props {
  onPositionChange: (update: WSPositionUpdate) => void;
}

export function Canvas({ onPositionChange }: Props) {
  const canvasNodes = useCanvasStore((s) => s.nodes);
  const edges = useCanvasStore((s) => s.edges);
  const updateNodePosition = useCanvasStore((s) => s.updateNodePosition);
  const selectNode = useCanvasStore((s) => s.selectNode);

  // 内部节点状态（包含 React Flow 管理的尺寸信息，MiniMap 需要）
  const [rfNodes, setRfNodes] = useState<Node[]>(() => defaultLayout(canvasNodes));

  // 当 store 中的节点数据变化时，同步位置（保留已有尺寸）
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
        // 持久化位置变更
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

  return (
    <div style={{ flex: 1, height: "100%" }}>
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
            return t === "script" ? "#c4b5fd" : t === "storyboard" ? "#fcd34d" : t === "image" ? "#86efac" : t === "video" ? "#c084fc" : t === "audio" ? "#fda4af" : "#d4d4d8";
          }}
        />
      </ReactFlow>
    </div>
  );
}
