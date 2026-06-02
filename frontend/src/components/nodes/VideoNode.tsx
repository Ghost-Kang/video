import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";

export function VideoNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  return (
    <div style={styles.wrapper}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong>{node.title}</strong>
      {node.result?.url ? (
        <video
          src={node.result.url as string}
          controls
          style={styles.video}
          onPlay={(e) => {
            document.querySelectorAll("video").forEach((v) => {
              if (v !== e.currentTarget) v.pause();
            });
          }}
        />
      ) : node.asset_status === "generating" ? (
        <div style={styles.loading}><span className="img-spinner" />生成中...</div>
      ) : (
        <div style={styles.placeholder}>🎬 等待生成</div>
      )}
      <span style={styles.badge(node.node_status)}>{node.node_status}</span>
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
    background: "#fff",
    border: "1px solid #a1a1aa",
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
    background: s === "confirmed" ? "#18181b" : "#f4f4f5",
    color: s === "confirmed" ? "#fff" : "#71717a",
  }),
};
