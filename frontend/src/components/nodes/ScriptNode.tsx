import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

export function ScriptNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  return (
    <div style={styles.wrapper("script")}>
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
      <strong>{node.title}</strong>
      {node.description && <p style={styles.desc}>{node.description.slice(0, 100)}</p>}
      <span style={styles.badge(node.status)}>{node.status}</span>
    </div>
  );
}

const COLORS: Record<string, string> = {
  script: "#f0f4ff",
  storyboard: "#fff7e6",
  image: "#f6ffed",
  video: "#f9f0ff",
  audio: "#fff0f6",
};

const styles = {
  wrapper: (type: string) => ({
    background: COLORS[type] || "#fff",
    border: "1px solid #ddd",
    borderRadius: 8,
    padding: 12,
    minWidth: 180,
    fontSize: 13,
  }),
  desc: { color: "#666", fontSize: 12, margin: "4px 0" },
  badge: (status: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: status === "done" ? "#52c41a" : status === "executing" ? "#1890ff" : "#d9d9d9",
    color: status === "done" || status === "executing" ? "#fff" : "#666",
  }),
};
