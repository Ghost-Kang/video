import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

export function ImageNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  const isExecuting = node.status === "executing";

  return (
    <div style={S.wrapper}>
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
      <strong>{node.title}</strong>

      {node.result?.url ? (
        <img src={node.result.url as string} alt={node.title} style={S.img} />
      ) : isExecuting ? (
        <div className="img-loading" style={S.loading}>
          <span className="img-spinner" />
          <span>生成中...</span>
        </div>
      ) : (
        <div style={S.placeholder}>🖼 等待生成</div>
      )}

      <span style={S.badge(node.status)} className={isExecuting ? "badge-pulse" : ""}>{node.status}</span>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .badge-pulse { animation: pulse 2s ease-in-out infinite; }
        .img-spinner {
          display: inline-block; width: 12px; height: 12px;
          border: 2px solid #d9d9d9; border-top-color: #1890ff;
          border-radius: 50%; animation: spin 0.8s linear infinite;
          margin-right: 6px; vertical-align: middle;
        }
        .img-loading { display: flex; align-items: center; }
      `}</style>
    </div>
  );
}

const S = {
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
