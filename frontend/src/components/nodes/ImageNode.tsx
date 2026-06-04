import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode, AssetStatus } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { NeedsRegenBadge } from "./NeedsRegenBadge";

const STATUS_CN: Record<string, string> = { reviewing: "待确认", confirmed: "已确认" };
const ASSET_CN: Record<string, string> = {
  generating: "生成中", done: "已生成", failed: "失败重试", timeout: "超时重试", pending: "排队中",
};

export function ImageNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const asset = node.asset_status || "idle";
  const isGenerating = asset === "generating";

  return (
    <div style={S.wrapper(selected)}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong style={S.title}>{node.title}</strong>

      {node.result?.url ? (
        <img
          src={node.result.url as string}
          alt={node.title}
          style={S.img}
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
        />
      ) : isGenerating ? (
        <div style={S.media}>生成草稿图中…</div>
      ) : (
        <div style={S.placeholder}>🖼 等待生成</div>
      )}

      <div style={S.badgeRow}>
        <span style={S.badge(node.node_status)}>{STATUS_CN[node.node_status] ?? node.node_status}</span>
        {asset !== "idle" && (
          <span style={S.assetBadge(asset)} className={isGenerating ? "anim-cta-breathe" : ""}>
            {ASSET_CN[asset] ?? asset}
          </span>
        )}
      </div>
      <NeedsRegenBadge node={node} />
    </div>
  );
}

const CLAY = "#7c2d12";
const AMBER = "#b45309";
const GREEN = "#15803d";
const RED = "#b91c1c";

const S = {
  wrapper: (selected?: boolean): React.CSSProperties => ({
    background: "rgba(255,255,255,0.86)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    border: `1px solid ${selected ? "rgba(124,45,18,0.55)" : "rgba(124,45,18,0.16)"}`,
    borderLeft: "4px solid #ea580c",
    borderRadius: 14,
    padding: 10,
    minWidth: 150,
    maxWidth: 190,
    fontSize: 11,
    boxShadow: selected ? "0 6px 22px rgba(124,45,18,0.16)" : "0 2px 10px rgba(124,45,18,0.06)",
  }),
  title: { color: "#1c1917", fontWeight: 600, fontSize: 12 } as React.CSSProperties,
  img: { width: "100%", aspectRatio: "16/9", borderRadius: 8, marginTop: 6, objectFit: "cover" as const },
  media: {
    width: "100%", aspectRatio: "16/9", borderRadius: 8, marginTop: 6,
    display: "flex", alignItems: "center", justifyContent: "center",
    color: CLAY, fontSize: 11,
  } as React.CSSProperties,
  placeholder: {
    width: "100%", aspectRatio: "16/9", borderRadius: 8, marginTop: 6,
    display: "flex", alignItems: "center", justifyContent: "center",
    color: "#9a3412", fontSize: 12,
    background: "rgba(124,45,18,0.04)", border: "1px dashed rgba(124,45,18,0.20)",
  } as React.CSSProperties,
  badgeRow: { display: "flex", gap: 4, marginTop: 8, flexWrap: "wrap" as const },
  badge: (s: string): React.CSSProperties => ({
    padding: "2px 8px", borderRadius: 999, fontSize: 10.5, fontWeight: 500,
    background: s === "confirmed" ? "rgba(124,45,18,0.10)" : "rgba(180,83,9,0.12)",
    color: s === "confirmed" ? CLAY : AMBER,
  }),
  assetBadge: (s: AssetStatus): React.CSSProperties => {
    const tone = s === "done" ? GREEN : s === "failed" || s === "timeout" ? RED : AMBER;
    return {
      padding: "2px 8px", borderRadius: 999, fontSize: 10.5, fontWeight: 500,
      background: `${tone}1a`, color: tone,
    };
  },
};
