import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

export function AudioNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  return (
    <div style={styles.wrapper}>
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong>🎵 {node.title}</strong>
      {node.description && <p style={styles.desc}>{node.description.slice(0, 80)}</p>}
      {node.asset_status === "generating" && <div style={styles.loading}>生成中...</div>}
      <span style={styles.badge(node.node_status)}>{node.node_status}</span>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .badge-pulse { animation: pulse 2s ease-in-out infinite; }
      `}</style>
    </div>
  );
}

const styles = {
  wrapper: {
    background: "#fff",
    border: "1px solid #d4d4d8",
    borderRadius: 8,
    padding: 12,
    minWidth: 180,
    fontSize: 13,
  },
  desc: { color: "#666", fontSize: 12, margin: "4px 0" },
  loading: { color: "#1890ff", fontSize: 12, margin: "4px 0" },
  badge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: s === "confirmed" ? "#18181b" : "#f4f4f5",
    color: s === "confirmed" ? "#fff" : "#71717a",
  }),
};
