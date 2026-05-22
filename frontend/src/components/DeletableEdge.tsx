import { useState } from "react";
import { BaseEdge, EdgeLabelRenderer, type EdgeProps } from "@xyflow/react";

export function DeletableEdge(props: EdgeProps) {
  const { id, sourceX, sourceY, targetX, targetY, style = {} } = props;
  const [hovered, setHovered] = useState(false);
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;

  return (
    <>
      <g
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <BaseEdge
          id={id}
          path={`M ${sourceX} ${sourceY} L ${targetX} ${targetY}`}
          style={{
            ...(style as Record<string, unknown>),
            stroke: hovered ? "#52525b" : (style as Record<string, string>)?.stroke || "#a1a1aa",
            strokeWidth: hovered ? 3 : 2,
            transition: "stroke 0.15s, stroke-width 0.15s",
          }}
        />
        {/* invisible wide path for easier hover targeting */}
        <path
          d={`M ${sourceX} ${sourceY} L ${targetX} ${targetY}`}
          fill="none"
          stroke="transparent"
          strokeWidth={20}
        />
      </g>
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${midX}px, ${midY}px)`,
            pointerEvents: "all",
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: "#ef4444",
            color: "#fff",
            border: "none",
            fontSize: 11,
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            opacity: hovered ? 1 : 0,
            transition: "opacity 0.15s",
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onClick={(e) => {
            e.stopPropagation();
            window.dispatchEvent(new CustomEvent("delete_edge", { detail: { edgeId: id } }));
          }}
        >
          ✕
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
