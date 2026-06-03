import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { NeedsRegenBadge } from "./NeedsRegenBadge";

export function ScriptNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const content = node.result?.content as string | undefined;
  return (
    <div style={styles.wrapper}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong style={styles.title}>{node.title}</strong>
      {content ? (
        <p style={styles.content}>{content.slice(0, 200)}</p>
      ) : node.description ? (
        <p style={styles.desc}>{node.description.slice(0, 100)}</p>
      ) : null}
      <span style={styles.badge(node.node_status)}>{node.node_status}</span>
      <NeedsRegenBadge node={node} />
    </div>
  );
}

const styles = {
  wrapper: {
    background: "#fff",
    border: "2px solid #18181b",
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
  badge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: s === "confirmed" ? "#18181b" : "#f4f4f5",
    color: s === "confirmed" ? "#fff" : "#71717a",
  }),
};
