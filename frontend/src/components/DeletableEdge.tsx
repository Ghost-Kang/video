import { useState } from "react";
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, type EdgeProps } from "@xyflow/react";

export function DeletableEdge(props: EdgeProps) {
  const { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style = {}, markerEnd } = props;
  const [hovered, setHovered] = useState(false);
  const [path, midX, midY] = getSmoothStepPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, borderRadius: 14,
  });
  const baseStroke = (style as Record<string, string>)?.stroke || "rgba(124,45,18,0.4)";

  return (
    <>
      <g onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
        <BaseEdge
          id={id}
          path={path}
          markerEnd={markerEnd}
          style={{
            ...(style as Record<string, unknown>),
            stroke: hovered ? "#7c2d12" : baseStroke,
            strokeWidth: hovered ? 2.5 : 1.5,
            transition: "stroke 0.15s, stroke-width 0.15s",
          }}
        />
        {/* invisible wide path for easier hover targeting */}
        <path d={path} fill="none" stroke="transparent" strokeWidth={20} />
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
            background: "#b91c1c",
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
