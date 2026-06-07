import { useEffect, useState } from "react";
import { useEditor, useValue } from "tldraw";
import { useProCanvasStore } from "../store/proCanvasStore";
import { PORT_COLOR, portOffset } from "./nodes/layout";
import { pronodeShapes } from "./graphIO";
import type { ProNodeTypeKey, ProPortType } from "../types/pro";

interface NodePos {
  x: number;
  y: number;
  type: ProNodeTypeKey;
}

function bezier(sx: number, sy: number, tx: number, ty: number): string {
  const dx = Math.max(40, Math.abs(tx - sx) / 2);
  return `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`;
}

/** 连线层 —— 经 tldraw components.OnTheCanvas 注入,渲染在画布坐标系(自动跟随平移/缩放)。
 *  连线住 proCanvasStore;节点坐标从 editor 反应式读取(拖动节点连线实时跟随)。 */
export function EdgeLayer() {
  const editor = useEditor();
  const edges = useProCanvasStore((s) => s.edges);
  const pending = useProCanvasStore((s) => s.pending);
  const removeEdge = useProCanvasStore((s) => s.removeEdge);

  // 反应式节点坐标(getCurrentPageShapes 是 reactive,拖动即重算)
  const nodes = useValue<Record<string, NodePos>>(
    "pro-node-positions",
    () => {
      const map: Record<string, NodePos> = {};
      for (const s of pronodeShapes(editor)) {
        map[s.id] = { x: s.x, y: s.y, type: s.props.nodeType };
      }
      return map;
    },
    [editor],
  );

  // pending 线跟随光标(editor.inputs.currentPagePoint 非 reactive,用 pointermove + screenToPage)
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  useEffect(() => {
    if (!pending) return;
    const onMove = (e: PointerEvent) => {
      const p = editor.screenToPage({ x: e.clientX, y: e.clientY });
      setCursor({ x: p.x, y: p.y });
    };
    window.addEventListener("pointermove", onMove);
    // reset 在 cleanup(pending 清空时本 effect 重跑,cleanup 先执行)—— 避免在 effect body
    // 同步 setState 触发 react-hooks/set-state-in-effect。
    return () => {
      window.removeEventListener("pointermove", onMove);
      setCursor(null);
    };
  }, [pending, editor]);

  return (
    <svg style={{ position: "absolute", left: 0, top: 0, width: 1, height: 1, overflow: "visible", pointerEvents: "none" }}>
      {edges.map((e) => {
        const src = nodes[e.source];
        const dst = nodes[e.target];
        if (!src || !dst) return null;
        const so = portOffset(src.type, e.sourceHandle, "out");
        const to = portOffset(dst.type, e.targetHandle, "in");
        if (!so || !to) return null;
        const sx = src.x + so.x;
        const sy = src.y + so.y;
        const tx = dst.x + to.x;
        const ty = dst.y + to.y;
        const mx = (sx + tx) / 2;
        const my = (sy + ty) / 2;
        return (
          <g key={e.id}>
            <path d={bezier(sx, sy, tx, ty)} fill="none" stroke="#7c2d12" strokeWidth={2} strokeOpacity={0.55} />
            <circle
              cx={mx}
              cy={my}
              r={7}
              fill="#fff"
              stroke="#dc2626"
              strokeWidth={1.5}
              style={{ pointerEvents: "all", cursor: "pointer" }}
              onPointerDown={(ev) => ev.stopPropagation()}
              onClick={(ev) => {
                ev.stopPropagation();
                removeEdge(e.id);
              }}
            >
              <title>删除连线</title>
            </circle>
            <text x={mx} y={my + 3} textAnchor="middle" fontSize={9} fill="#dc2626" style={{ pointerEvents: "none" }}>
              ×
            </text>
          </g>
        );
      })}

      {pending && cursor && nodes[pending.nodeId] && (() => {
        const src = nodes[pending.nodeId];
        const so = portOffset(src.type, pending.handle, "out");
        if (!so) return null;
        return (
          <path
            d={bezier(src.x + so.x, src.y + so.y, cursor.x, cursor.y)}
            fill="none"
            stroke={PORT_COLOR[pending.portType as ProPortType]}
            strokeWidth={2}
            strokeDasharray="5 4"
          />
        );
      })()}
    </svg>
  );
}
