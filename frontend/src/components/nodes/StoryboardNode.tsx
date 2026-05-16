import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CanvasNode } from "../../types";

interface Shot {
  no: number;
  description: string;
  duration?: number;
}

export function StoryboardNode({ data }: NodeProps) {
  const node = data.node as CanvasNode;
  const shots = node.result?.shots as Shot[] | undefined;
  return (
    <div style={styles.wrapper}>
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
      <strong>{node.title}</strong>
      {shots && (
        <ul style={styles.shots}>
          {shots.map((s) => (
            <li key={s.no}>镜{s.no}: {s.description.slice(0, 30)}</li>
          ))}
        </ul>
      )}
      <span style={styles.badge(node.status)}>{node.status}</span>
    </div>
  );
}

const styles = {
  wrapper: {
    background: "#fff7e6",
    border: "1px solid #faad14",
    borderRadius: 8,
    padding: 12,
    minWidth: 200,
    fontSize: 13,
  },
  shots: { margin: "4px 0", paddingLeft: 16, fontSize: 12, color: "#666" },
  badge: (s: string) => ({
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    background: s === "done" ? "#52c41a" : s === "executing" ? "#1890ff" : "#d9d9d9",
    color: s === "done" || s === "executing" ? "#fff" : "#666",
  }),
};
