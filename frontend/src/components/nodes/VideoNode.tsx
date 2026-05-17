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
      ) : node.status === "executing" ? (
        <div style={styles.loading}><span className="img-spinner" />生成中...</div>
      ) : (
        <div style={styles.placeholder}>🎬 等待生成</div>
      )}
      <span style={styles.badge(node.status)} className={node.status === "executing" ? "badge-pulse" : ""}>{node.status}</span>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .badge-pulse { animation: pulse 2s ease-in-out infinite; }
        .img-spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid #d9d9d9; border-top-color: #1890ff; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 6px; vertical-align: middle; }
      `}</style>
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
  loading: { color: "#1890ff", fontSize: 12, margin: "8px 0", padding: "8px 0" },
  badge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: s === "done" ? "#52c41a" : s === "executing" ? "#1890ff" : "#d9d9d9",
    color: s === "done" || s === "executing" ? "#fff" : "#666",
  }),
};
