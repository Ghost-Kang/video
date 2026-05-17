import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

export function ScriptNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  const content = node.result?.content as string | undefined;
  return (
    <div style={styles.wrapper}>
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
      <strong style={styles.title}>{node.title}</strong>
      {content ? (
        <p style={styles.content}>{content.slice(0, 200)}</p>
      ) : node.description ? (
        <p style={styles.desc}>{node.description.slice(0, 100)}</p>
      ) : null}
      <span style={styles.badge(node.status)}>{node.status}</span>
    </div>
  );
}

const styles = {
  wrapper: {
    background: "#f0f4ff",
    border: "1px solid #bae",
    borderRadius: 8,
    padding: 12,
    minWidth: 260,
    maxWidth: 320,
    fontSize: 13,
  },
  title: { display: "block", marginBottom: 4 },
  content: {
    color: "#3f3f46",
    fontSize: 12,
    lineHeight: 1.5,
    margin: "4px 0",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    maxHeight: 120,
    overflow: "hidden",
  } as React.CSSProperties,
  desc: { color: "#666", fontSize: 12, margin: "4px 0" },
  badge: (status: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background:
      status === "done" ? "#52c41a"
      : status === "awaiting_review" ? "#faad14"
      : status === "executing" ? "#1890ff"
      : "#d9d9d9",
    color: status === "done" || status === "executing" ? "#fff" : "#666",
  }),
};
