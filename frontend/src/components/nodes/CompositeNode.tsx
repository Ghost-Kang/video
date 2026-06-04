import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { NeedsRegenBadge } from "./NeedsRegenBadge";

const STATUS_CN: Record<string, string> = { reviewing: "待确认", confirmed: "已确认" };
const ASSET_CN: Record<string, string> = {
  generating: "合成中", done: "已合成", failed: "失败重试", timeout: "超时重试", pending: "排队中",
};

export function CompositeNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const asset = node.asset_status || "idle";
  const isGenerating = asset === "generating";

  return (
    <div style={S.wrapper(selected)}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <strong style={S.title}>{node.title}</strong>

      {node.result?.url ? (
        <video src={node.result.url as string} controls style={S.video} />
      ) : isGenerating ? (
        <div style={S.media} className="anim-cta-breathe">合成整片中…</div>
      ) : (
        <div style={S.placeholder}>🎬 等待合成</div>
      )}

      <div style={S.badgeRow}>
        <span style={S.badge(node.node_status)}>{STATUS_CN[node.node_status] ?? node.node_status}</span>
        {asset !== "idle" && <span style={S.assetBadge(asset)}>{ASSET_CN[asset] ?? asset}</span>}
      </div>
      <NeedsRegenBadge node={node} />
    </div>
  );
}

const CLAY = "#7c2d12";
const AMBER = "#b45309";
const GREEN = "#15803d";

const S = {
  wrapper: (selected?: boolean): React.CSSProperties => ({
    background: "rgba(255,250,243,0.9)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    border: `1px solid ${selected ? "rgba(124,45,18,0.55)" : "rgba(124,45,18,0.18)"}`,
    borderLeft: "4px solid #d4a574",
    borderRadius: 14,
    padding: 12,
    minWidth: 220,
    fontSize: 13,
    boxShadow: selected ? "0 6px 22px rgba(124,45,18,0.16)" : "0 2px 10px rgba(124,45,18,0.06)",
  }),
  title: { color: "#1c1917", fontWeight: 600 } as React.CSSProperties,
  video: { width: "100%", borderRadius: 8, marginTop: 6 },
  media: {
    width: "100%", aspectRatio: "16/9", borderRadius: 8, marginTop: 6,
    display: "flex", alignItems: "center", justifyContent: "center", color: CLAY, fontSize: 12,
  } as React.CSSProperties,
  placeholder: {
    width: "100%", aspectRatio: "16/9", borderRadius: 8, marginTop: 6,
    display: "flex", alignItems: "center", justifyContent: "center",
    color: "#9a3412", fontSize: 12,
    background: "rgba(124,45,18,0.04)", border: "1px dashed rgba(124,45,18,0.20)",
  } as React.CSSProperties,
  badgeRow: { display: "flex", gap: 4, marginTop: 8, flexWrap: "wrap" as const },
  badge: (s: string): React.CSSProperties => ({
    padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 500,
    background: s === "confirmed" ? "rgba(124,45,18,0.10)" : "rgba(180,83,9,0.12)",
    color: s === "confirmed" ? CLAY : AMBER,
  }),
  assetBadge: (s: string): React.CSSProperties => {
    const tone = s === "done" ? GREEN : AMBER;
    return { padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 500, background: `${tone}1a`, color: tone };
  },
};
