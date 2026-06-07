import { PRO_NODE_SPECS, proPortsCompatible } from "../../types/pro";
import { useProCanvasStore } from "../../store/proCanvasStore";
import type { ProNodeShape } from "./NodeShape";
import { HEADER_H, NODE_W, PORT_COLOR, getPorts, type PortPos } from "./layout";

function paramSummary(shape: ProNodeShape): string {
  const spec = PRO_NODE_SPECS[shape.props.nodeType];
  const parts: string[] = [];
  for (const p of spec.params.slice(0, 2)) {
    const v = shape.props.params[p.name] ?? p.default;
    const sv = String(v);
    if (sv.trim()) parts.push(p.type === "str" && p.name !== "role" ? sv : `${p.label}:${sv}`);
  }
  return parts.join(" · ");
}

export function ProNodeCard({ shape }: { shape: ProNodeShape }) {
  const spec = PRO_NODE_SPECS[shape.props.nodeType];
  const ports = getPorts(shape.props.nodeType);
  const pending = useProCanvasStore((s) => s.pending);

  const onPortClick = (port: PortPos) => {
    const st = useProCanvasStore.getState();
    if (port.side === "out") {
      st.startConnection({ nodeId: shape.id, handle: port.name, portType: port.type, end: "source" });
      return;
    }
    const p = st.pending;
    if (p && p.end === "source" && p.nodeId !== shape.id && proPortsCompatible(p.portType, port.type)) {
      st.addEdge({ source: p.nodeId, sourceHandle: p.handle, target: shape.id, targetHandle: port.name });
      st.cancelConnection();
    }
  };

  const thumb = shape.props.resultUrl || shape.props.cachedUrl;
  const status = shape.props.status;

  return (
    <div
      data-testid={`pro-node-${shape.props.nodeType}`}
      style={{
        width: shape.props.w,
        height: shape.props.h,
        borderRadius: 14,
        background: "var(--color-paper, #faf8f3)",
        border: `1px solid ${spec.accent}33`,
        boxShadow: "0 4px 14px rgba(28,25,23,0.10)",
        position: "relative",
        overflow: "visible",
        fontFamily: "inherit",
      }}
    >
      {/* header */}
      <div
        style={{
          height: HEADER_H,
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "0 12px",
          borderRadius: "14px 14px 0 0",
          background: `${spec.accent}14`,
          borderBottom: `1px solid ${spec.accent}22`,
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: 99, background: spec.accent }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-ink, #1c1917)" }}>{spec.label}</span>
        <span style={{ marginLeft: "auto", fontSize: 11 }}>
          {shape.props.cached && <span title="命中缓存,不重渲染" style={{ color: "#16a34a" }}>♻︎</span>}
          {status === "running" && <span style={{ color: spec.accent }}>⏳</span>}
          {status === "done" && <span style={{ color: "#16a34a" }}>✓</span>}
          {status === "failed" && <span style={{ color: "#dc2626" }}>✕</span>}
        </span>
      </div>

      {/* body: param summary + thumbnail */}
      <div style={{ padding: "8px 12px", fontSize: 11, color: "var(--color-ink-soft, #44403c)", lineHeight: 1.4 }}>
        <div style={{ overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
          {paramSummary(shape) || <span style={{ opacity: 0.5 }}>(双击空白选中后在右侧编辑)</span>}
        </div>
        {thumb && (
          <img
            src={thumb}
            alt=""
            draggable={false}
            onPointerDown={(e) => e.stopPropagation()}
            style={{ marginTop: 6, width: "100%", height: 70, objectFit: "cover", borderRadius: 8, background: "#0001" }}
          />
        )}
      </div>

      {/* ports */}
      {ports.map((port) => {
        const droppable =
          port.side === "in" &&
          pending?.end === "source" &&
          pending.nodeId !== shape.id &&
          proPortsCompatible(pending.portType, port.type);
        const active = port.side === "out" && pending?.nodeId === shape.id && pending.handle === port.name;
        return (
          <div
            key={`${port.side}-${port.name}`}
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              onPortClick(port);
            }}
            title={`${port.name} (${port.type})`}
            style={{
              position: "absolute",
              left: port.x - 7,
              top: port.y - 7,
              width: 14,
              height: 14,
              borderRadius: 99,
              background: PORT_COLOR[port.type],
              border: `2px solid ${droppable || active ? "#1c1917" : "#fff"}`,
              cursor: "crosshair",
              boxShadow: droppable ? "0 0 0 4px rgba(22,163,74,0.25)" : undefined,
              zIndex: 2,
            }}
          >
            <span
              style={{
                position: "absolute",
                top: -3,
                [port.side === "in" ? "left" : "right"]: 18,
                fontSize: 9,
                color: "var(--color-ink-soft, #57534e)",
                whiteSpace: "nowrap",
                opacity: 0.75,
              }}
            >
              {port.name}
            </span>
          </div>
        );
      })}

      {/* width guard (so absolute ports at x=NODE_W align even if w changes) */}
      <span style={{ position: "absolute", left: NODE_W - 1, top: 0, width: 0, height: 0 }} />
    </div>
  );
}
