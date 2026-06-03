import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { NeedsRegenBadge } from "./NeedsRegenBadge";

export function CompositeNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const asset = node.asset_status || "idle";

  return (
    <div style={S.wrapper}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <strong>{node.title}</strong>

      {node.result?.url ? (
        <video src={node.result.url as string} controls style={S.video} />
      ) : asset === "generating" ? (
        <div style={S.loading}>🎬 合成中...</div>
      ) : (
        <div style={S.placeholder}>🎬 等待合成</div>
      )}

      <span style={S.badge(node.node_status)}>{node.node_status}</span>
      {asset !== "idle" && <span style={S.assetBadge(asset)}>{asset}</span>}
      <NeedsRegenBadge node={node} />
    </div>
  );
}

const S = {
  wrapper: {
    background: "#fefce8",
    border: "2px solid #eab308",
    borderRadius: 8,
    padding: 12,
    minWidth: 220,
    fontSize: 13,
  },
  video: { width: "100%", borderRadius: 4, marginTop: 6 },
  placeholder: { color: "#999", fontSize: 12, margin: "8px 0", textAlign: "center" as const },
  loading: { color: "#eab308", fontSize: 12, margin: "8px 0", padding: "8px 0" },
  badge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: s === "confirmed" ? "#18181b" : "#f4f4f5",
    color: s === "confirmed" ? "#fff" : "#71717a",
  }),
  assetBadge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    marginLeft: 4,
    background: s === "done" ? "#eab308" : s === "generating" ? "#fefce8" : "#f4f4f5",
    color: s === "done" ? "#fff" : "#71717a",
  }),
};
