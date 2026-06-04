import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionBar } from "./NodeActionBar";
import { NeedsRegenBadge } from "./NeedsRegenBadge";

const STATUS_CN: Record<string, string> = { reviewing: "待确认", confirmed: "已确认" };

export function VideoNode({ data, selected }: NodeProps) {
  const node = data.node as CanvasNode;
  const isGenerating = node.asset_status === "generating";
  return (
    <div style={styles.wrapper(selected)}>
      <NodeActionBar node={node} selected={selected} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong style={styles.title}>{node.title}</strong>
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
      ) : isGenerating ? (
        <div style={styles.media} className="anim-cta-breathe">生成视频中…（约几分钟）</div>
      ) : (
        <div style={styles.placeholder}>🎬 等待生成</div>
      )}
      <div style={styles.badgeRow}>
        <span style={styles.badge(node.node_status)}>{STATUS_CN[node.node_status] ?? node.node_status}</span>
      </div>
      <NeedsRegenBadge node={node} />
    </div>
  );
}

const CLAY = "#7c2d12";
const AMBER = "#b45309";

const styles = {
  wrapper: (selected?: boolean): React.CSSProperties => ({
    background: "rgba(255,255,255,0.86)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    border: `1px solid ${selected ? "rgba(124,45,18,0.55)" : "rgba(124,45,18,0.16)"}`,
    borderLeft: "4px solid #f59e0b",
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
    display: "flex", alignItems: "center", justifyContent: "center",
    color: CLAY, fontSize: 12,
  } as React.CSSProperties,
  placeholder: {
    width: "100%", aspectRatio: "16/9", borderRadius: 8, marginTop: 6,
    display: "flex", alignItems: "center", justifyContent: "center",
    color: "#9a3412", fontSize: 12,
    background: "rgba(124,45,18,0.04)", border: "1px dashed rgba(124,45,18,0.20)",
  } as React.CSSProperties,
  badgeRow: { marginTop: 8 },
  badge: (s: string): React.CSSProperties => ({
    display: "inline-block", padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 500,
    background: s === "confirmed" ? "rgba(124,45,18,0.10)" : "rgba(180,83,9,0.12)",
    color: s === "confirmed" ? CLAY : AMBER,
  }),
};
