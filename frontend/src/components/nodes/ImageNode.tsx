import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

export function ImageNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  return (
    <div style={styles.wrapper}>
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
      <strong>{node.title}</strong>
      {node.result?.url ? (
        <img src={node.result.url as string} alt={node.title} style={styles.img} />
      ) : (
        <div style={styles.placeholder}>🖼 等待生成</div>
      )}
      <span style={styles.badge(node.status)}>{node.status}</span>
    </div>
  );
}

const styles = {
  wrapper: {
    background: "#f6ffed",
    border: "1px solid #73d13d",
    borderRadius: 8,
    padding: 12,
    minWidth: 200,
    fontSize: 13,
  },
  img: { width: "100%", borderRadius: 4, marginTop: 6 },
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
