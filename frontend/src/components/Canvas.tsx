import { useMemo } from "react";
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
import type { CanvasNode } from "../types";

const nodeTypes = {
  script: ScriptNode,
  storyboard: StoryboardNode,
  image: ImageNode,
  video: VideoNode,
  audio: AudioNode,
};

/** 将画布节点按类型分组，从上到下排列 */
function layout(nodes: CanvasNode[]): Node[] {
  const order = ["script", "storyboard", "image", "video", "audio"];
  const gap = 200;

  return nodes.map((n, i) => {
    const col = order.indexOf(n.type);
    const x = 100 + (col >= 0 ? col : 0) * 320;
    const yPos = (i + 1) * gap;
    return {
      id: n.id,
      type: n.type,
      position: { x, y: yPos },
      data: { node: n },
    };
  });
}

export function Canvas() {
  const canvasNodes = useCanvasStore((s) => s.nodes);
  const rfNodes = useMemo(() => layout(canvasNodes), [canvasNodes]);

  return (
    <div style={{ flex: 1, height: "100%" }}>
      <ReactFlow nodes={rfNodes} nodeTypes={nodeTypes} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
