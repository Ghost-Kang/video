import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

export function VideoNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  return (
    <div style={styles.wrapper}>
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
      <strong>{node.title}</strong>
      {node.result?.url ? (
        <video src={node.result.url as string} controls style={styles.video} />
      ) : (
        <div style={styles.placeholder}>🎬 等待生成</div>
      )}
      <span style={styles.badge(node.status)}>{node.status}</span>
    </div>
  );
}

const styles = {
  wrapper: {
    background: "#f9f0ff",
    border: "1px solid #b37feb",
    borderRadius: 8,
    padding: 12,
    minWidth: 220,
    fontSize: 13,
  },
  video: { width: "100%", borderRadius: 4, marginTop: 6 },
  placeholder: { color: "#999", fontSize: 12, margin: "8px 0", textAlign: "center" as const },
  badge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: s === "done" ? "#52c41a" : s === "executing" ? "#1890ff" : "#d9d9d9",
    color: s === "done" || s === "executing" ? "#fff" : "#666",
  }),
};
