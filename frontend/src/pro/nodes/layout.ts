/**
 * 节点卡片尺寸 + 端口几何 —— 卡片渲染(ProNodeCard)与连线层(EdgeLayer)共用同一份,
 * 保证端口圆点与连线端点对齐。坐标是相对节点原点的偏移(x ∈ {0, NODE_W})。
 */

import { PRO_NODE_SPECS, type ProNodeTypeKey, type ProPortType } from "../../types/pro";

export const NODE_W = 210;
export const HEADER_H = 34;
const PORT_TOP = HEADER_H + 18;
const PORT_GAP = 26;
const THUMB_H = 92;
const BODY_PAD = 12;

export const PORT_COLOR: Record<ProPortType, string> = {
  image: "#a16207",
  text: "#0f766e",
  model: "#7c2d12",
  video: "#be185d",
  audio: "#0d9488",
  any: "#78716c",
};

export function hasThumb(t: ProNodeTypeKey): boolean {
  return (
    t === "Generate" ||
    t === "Preview" ||
    t === "LoadImage" ||
    t === "Anchor" ||
    t === "Upscale" ||
    t === "Video" ||
    t === "Compose" ||
    t === "Subtitle" ||
    t === "BGM" ||
    t === "TTS"
  );
}

export function nodeHeight(t: ProNodeTypeKey): number {
  const spec = PRO_NODE_SPECS[t];
  const portRows = Math.max(spec.inputs.length, spec.outputs.length, 1);
  let h = PORT_TOP + portRows * PORT_GAP + BODY_PAD;
  if (hasThumb(t)) h += THUMB_H;
  return h;
}

export interface PortPos {
  name: string;
  type: ProPortType;
  side: "in" | "out";
  required: boolean;
  multi: boolean;
  x: number;
  y: number;
}

export function getPorts(t: ProNodeTypeKey): PortPos[] {
  const spec = PRO_NODE_SPECS[t];
  const out: PortPos[] = [];
  spec.inputs.forEach((p, i) =>
    out.push({ name: p.name, type: p.type, side: "in", required: !!p.required, multi: !!p.multi, x: 0, y: PORT_TOP + i * PORT_GAP }),
  );
  spec.outputs.forEach((p, i) =>
    out.push({ name: p.name, type: p.type, side: "out", required: false, multi: false, x: NODE_W, y: PORT_TOP + i * PORT_GAP }),
  );
  return out;
}

/** 节点上某具名端口相对原点的中心坐标(连线层用)。找不到回 null。 */
export function portOffset(t: ProNodeTypeKey, handle: string, side: "in" | "out"): { x: number; y: number } | null {
  const p = getPorts(t).find((pp) => pp.name === handle && pp.side === side);
  return p ? { x: p.x, y: p.y } : null;
}
