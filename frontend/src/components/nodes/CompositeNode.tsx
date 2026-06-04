import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { StatusChip } from "./StatusChip";

export function CompositeNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const isGenerating = node.asset_status === "generating";

  return (
    <div style={S.wrapper(selected)} className={isGenerating ? "anim-active-ring" : undefined}>
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
        <StatusChip node={node} />
      </div>
    </div>
  );
}

const CLAY = "#7c2d12";

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
};
