import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

export function AudioNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  return (
    <div style={styles.wrapper}>
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
      <strong>🎵 {node.title}</strong>
      {node.description && <p style={styles.desc}>{node.description.slice(0, 80)}</p>}
      <span style={styles.badge(node.status)}>{node.status}</span>
    </div>
  );
}

const styles = {
  wrapper: {
    background: "#fff0f6",
    border: "1px solid #ff85c0",
    borderRadius: 8,
    padding: 12,
    minWidth: 180,
    fontSize: 13,
  },
  desc: { color: "#666", fontSize: 12, margin: "4px 0" },
  badge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: s === "done" ? "#52c41a" : s === "executing" ? "#1890ff" : "#d9d9d9",
    color: s === "done" || s === "executing" ? "#fff" : "#666",
  }),
};
