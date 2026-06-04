import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { NeedsRegenBadge } from "./NeedsRegenBadge";

const STATUS_CN: Record<string, string> = { reviewing: "待确认", confirmed: "已确认" };

export function ScriptNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const content = node.result?.content as string | undefined;
  return (
    <div style={styles.wrapper(selected)}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong style={styles.title} className="font-serif-cn">{node.title}</strong>
      {content ? (
        <p style={styles.content}>{content.slice(0, 200)}</p>
      ) : node.description ? (
        <p style={styles.desc}>{node.description.slice(0, 100)}</p>
      ) : null}
      <span style={styles.badge(node.node_status)}>{STATUS_CN[node.node_status] ?? node.node_status}</span>
      <NeedsRegenBadge node={node} />
    </div>
  );
}

const CLAY = "#7c2d12";
const AMBER = "#b45309";

const styles = {
  wrapper: (selected?: boolean): React.CSSProperties => ({
    background: "rgba(255,255,255,0.88)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    border: `1px solid ${selected ? "rgba(124,45,18,0.55)" : "rgba(124,45,18,0.18)"}`,
    borderLeft: "4px solid #7c2d12",
    borderRadius: 14,
    padding: 14,
    minWidth: 260,
    maxWidth: 320,
    fontSize: 13,
    boxShadow: selected ? "0 6px 22px rgba(124,45,18,0.16)" : "0 2px 12px rgba(124,45,18,0.07)",
  }),
  title: { display: "block", marginBottom: 6, color: "#1c1917", fontSize: 14 } as React.CSSProperties,
  content: {
    color: "#3f3f46",
    fontSize: 12,
    lineHeight: 1.55,
    margin: "4px 0",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    maxHeight: 120,
    overflow: "hidden",
  } as React.CSSProperties,
  desc: { color: "#78716c", fontSize: 12, margin: "4px 0" },
  badge: (s: string): React.CSSProperties => ({
    display: "inline-block",
    marginTop: 8,
    padding: "2px 8px",
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 500,
    background: s === "confirmed" ? "rgba(124,45,18,0.10)" : "rgba(180,83,9,0.12)",
    color: s === "confirmed" ? CLAY : AMBER,
  }),
};
