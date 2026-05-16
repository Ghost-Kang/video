import { useMemo, useRef, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
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
  const nodes = useCanvasStore((s) => s.nodes);
  const updateNodePosition = useCanvasStore((s) => s.updateNodePosition);
  const selectNode = useCanvasStore((s) => s.selectNode);
  const rfNodes = useMemo(() => defaultLayout(nodes), [nodes]);

  const persistRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const handleDrag = useCallback(
    (_evt: unknown, node: Node) => {
      const id = node.id;
      const x = Math.round(node.position.x);
      const y = Math.round(node.position.y);
      // 本地即时更新
      updateNodePosition(id, x, y);
      // 写文件 300ms 防抖
      if (persistRef.current[id]) clearTimeout(persistRef.current[id]);
      persistRef.current[id] = setTimeout(() => {
        onPositionChange({ type: "update_position", thread_id: "", node_id: id, x, y });
        delete persistRef.current[id];
      }, 300);
    },
    [updateNodePosition, onPositionChange]
  );

  return (
    <div style={{ flex: 1, height: "100%" }}>
      <ReactFlow
        nodes={rfNodes}
        nodeTypes={nodeTypes}
        onNodeDrag={handleDrag}
        onNodeClick={(_e, node) => selectNode(node.id)}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
