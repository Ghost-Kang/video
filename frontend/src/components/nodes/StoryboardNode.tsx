import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode, Shot } from "../../types";

export function StoryboardNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  const shots = node.result?.shots as Shot[] | undefined;

  return (
    <div style={S.wrapper}>
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
      <strong style={S.title}>{node.title}</strong>
      {shots && shots.length > 0 ? (
        <div style={S.shots}>
          {shots.slice(0, 5).map((s, i) => (
            <div key={i} style={S.row}>
              <span style={S.no}>{s.no}</span>
              <span style={S.desc}>{s.description.slice(0, 40)}</span>
              {s.duration && <span style={S.meta}>{s.duration}</span>}
            </div>
          ))}
          {shots.length > 5 && <span style={S.more}>+{shots.length - 5} 镜</span>}
        </div>
      ) : (
        <p style={S.desc}>{(node.result?.content as string)?.slice(0, 100) || node.description?.slice(0, 100)}</p>
      )}
      <span style={S.badge(node.status)}>{node.status}</span>
    </div>
  );
}

const S = {
  wrapper: {
    background: "#fff7e6",
    border: "1px solid #faad14",
    borderRadius: 8,
    padding: 12,
    minWidth: 240,
    maxWidth: 320,
    fontSize: 13,
  },
  title: { display: "block", marginBottom: 4 },
  shots: { margin: "6px 0", display: "flex", flexDirection: "column", gap: 4 } as React.CSSProperties,
  row: { display: "flex", alignItems: "center", gap: 6, fontSize: 12 },
  no: { fontWeight: 600, color: "#b45309", flexShrink: 0, minWidth: 20 },
  desc: { color: "#3f3f46", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  meta: { color: "#a1a1aa", fontSize: 11, flexShrink: 0 },
  more: { color: "#a1a1aa", fontSize: 11, paddingLeft: 4 },
  badge: (status: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: status === "done" ? "#52c41a" : status === "awaiting_review" ? "#faad14" : status === "executing" ? "#1890ff" : "#d9d9d9",
    color: status === "done" || status === "executing" ? "#fff" : "#666",
  }),
};
