import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { StatusChip } from "./StatusChip";

export function ImageNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const isGenerating = node.asset_status === "generating";

  return (
    <div style={S.wrapper(selected)} className={isGenerating ? "anim-active-ring" : undefined}>
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
        <StatusChip node={node} />
      </div>
    </div>
  );
}

const CLAY = "#7c2d12";

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
};
