import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode, AssetStatus } from "../../types";
import { NodeActionBar } from "./NodeActionBar";

export function ImageNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const asset = node.asset_status || "idle";
  const isGenerating = asset === "generating";

  return (
    <div style={S.wrapper}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong>{node.title}</strong>

      {node.result?.url ? (
        <img src={node.result.url as string} alt={node.title} style={S.img} />
      ) : isGenerating ? (
        <div className="img-loading" style={S.loading}>
          <span className="img-spinner" />
          <span>生成中...</span>
        </div>
      ) : (
        <div style={S.placeholder}>🖼 等待生成</div>
      )}

      <span style={S.badge(node.node_status)}>{node.node_status}</span>
      {asset !== "idle" && <span style={S.assetBadge(asset)} className={isGenerating ? "badge-pulse" : ""}>{asset}</span>}

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
    background: "#fff",
    border: "1px solid #d4d4d8",
    borderRadius: 8,
    padding: 8,
    minWidth: 140,
    maxWidth: 180,
    fontSize: 11,
  },
  img: { width: "100%", maxHeight: 100, borderRadius: 4, marginTop: 4, objectFit: "cover" as const },
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
  assetBadge: (s: AssetStatus) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    marginLeft: 4,
    background: s === "done" ? "#18181b" : s === "generating" ? "#f4f4f5" : s === "failed" ? "#f4f4f5" : s === "timeout" ? "#fef2f2" : "transparent",
    color: s === "done" ? "#fff" : s === "generating" ? "#71717a" : s === "failed" ? "#a1a1aa" : s === "timeout" ? "#dc2626" : "#a1a1aa",
    border: s === "failed" || s === "timeout" ? "1px solid #d4d4d8" : "none",
  }),
};
