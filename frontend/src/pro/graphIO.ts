/**
 * Pro 图序列化:tldraw editor 的 pronode shapes + proCanvasStore 的 edges ↔ ProGraph JSON。
 * 节点本体住 editor;连线住 store。compileGraph = 拼成发后端的 ProGraph(校验在后端 compiler)。
 *
 * tldraw v5 的 TLShape / createShape / updateShape 都是对内置封闭联合类型化的,自定义 "pronode"
 * shape 不在其中 → 在 editor 边界用 cast helpers(pronodeShapes/getProNode/updateProNode/createNode)
 * 集中处理,其余文件不再各自 cast。
 */

import { createShapeId, type Editor, type TLShapeId } from "tldraw";
import { PRO_NODE_SPECS, type ProGraph, type ProNode, type ProNodeTypeKey } from "../types/pro";
import { useProCanvasStore } from "../store/proCanvasStore";
import { NODE_W, nodeHeight } from "./nodes/layout";
import type { ProNodeProps, ProNodeShape } from "./nodes/NodeShape";

export function defaultParams(t: ProNodeTypeKey): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  for (const p of PRO_NODE_SPECS[t].params) out[p.name] = p.default;
  return out;
}

/** 当前页所有 pronode shape(经 TLGlobalShapePropsMap 注册,s.type 守卫原生类型安全)。 */
export function pronodeShapes(editor: Editor): ProNodeShape[] {
  return editor.getCurrentPageShapes().filter((s): s is ProNodeShape => s.type === "pronode");
}

export function getProNode(editor: Editor, id: TLShapeId): ProNodeShape | null {
  const s = editor.getShape(id);
  return s && s.type === "pronode" ? s : null;
}

export function updateProNode(editor: Editor, id: TLShapeId, props: Partial<ProNodeProps>): void {
  editor.updateShape<ProNodeShape>({ id, type: "pronode", props });
}

interface CreateOpts {
  id?: string;
  params?: Record<string, string | number>;
  cached?: boolean;
  cachedUrl?: string | null;
  label?: string;
}

export function createNode(editor: Editor, t: ProNodeTypeKey, x: number, y: number, opts: CreateOpts = {}): TLShapeId {
  const id = opts.id ? createShapeId(opts.id) : createShapeId();
  const cachedUrl = opts.cachedUrl ?? null;
  const cached = !!(opts.cached && cachedUrl);
  const props: ProNodeProps = {
    w: NODE_W,
    h: nodeHeight(t),
    nodeType: t,
    params: { ...defaultParams(t), ...(opts.params ?? {}) },
    cached,
    cachedUrl,
    status: "idle",
    resultUrl: cached ? cachedUrl : null,
    label: opts.label ?? "",
    needsRegen: false,
  };
  editor.createShape<ProNodeShape>({ id, type: "pronode", x, y, props });
  return id;
}

export function nodesFromEditor(editor: Editor): ProNode[] {
  return pronodeShapes(editor).map((s) => ({
    id: s.id,
    type: s.props.nodeType,
    params: s.props.params,
    cached: s.props.cached,
    cached_url: s.props.cachedUrl,
    label: s.props.label,
    x: s.x,
    y: s.y,
  }));
}

/** 纯函数:节点 + 连线 → ProGraph(可单测)。 */
export function assembleGraph(nodes: ProNode[], edges: ProGraph["edges"]): ProGraph {
  return { version: 1, nodes, edges };
}

export function compileGraph(editor: Editor): ProGraph {
  return assembleGraph(nodesFromEditor(editor), useProCanvasStore.getState().edges);
}

/** seed/导入的 ProGraph → editor + store(替换现有)。节点 id 经 createShapeId 规范化,连线同步重映射。 */
export function loadGraph(editor: Editor, graph: ProGraph): void {
  const existing = pronodeShapes(editor).map((s) => s.id);
  editor.run(() => {
    if (existing.length) editor.deleteShapes(existing);
    for (const n of graph.nodes) {
      createNode(editor, n.type, n.x ?? 0, n.y ?? 0, {
        id: n.id,
        params: n.params,
        cached: n.cached,
        cachedUrl: n.cached_url,
        label: n.label,
      });
    }
  });
  const edges = graph.edges.map((e) => ({
    id: e.id,
    source: String(createShapeId(e.source)),
    sourceHandle: e.sourceHandle,
    target: String(createShapeId(e.target)),
    targetHandle: e.targetHandle,
  }));
  useProCanvasStore.getState().setEdges(edges);
  editor.zoomToFit({ animation: { duration: 200 } });
}

const _GENERATED = ["Generate", "Video", "Compose"];

/** 单节点重生:目标节点 + 其当前上游链(生成型上游用上次产物 cached,静态上游读最新) + 合成 Preview。
 *  读 live editor + store edges,所以上游改了/加了内容都吃进去(见与 founder 的语义确认)。 */
export function buildRegenSubgraph(editor: Editor, targetId: string): ProGraph {
  const shapes = pronodeShapes(editor);
  const byId = new Map(shapes.map((s) => [String(s.id), s]));
  const edges = useProCanvasStore.getState().edges;

  // BFS 上游(沿当前连线)
  const keep = new Set<string>([targetId]);
  const q = [targetId];
  while (q.length) {
    const cur = q.shift() as string;
    for (const e of edges) if (e.target === cur && !keep.has(e.source)) { keep.add(e.source); q.push(e.source); }
  }

  const nodes: ProNode[] = [];
  for (const id of keep) {
    const s = byId.get(id);
    if (!s) continue;
    const p = s.props;
    if (id === targetId) {
      nodes.push({ id, type: p.nodeType, params: p.params, cached: false, cached_url: null, label: p.label, x: s.x, y: s.y });
    } else {
      const out = p.resultUrl || p.cachedUrl;
      const isGen = _GENERATED.includes(p.nodeType);
      nodes.push({
        id, type: p.nodeType, params: p.params,
        cached: isGen ? !!out : p.cached,
        cached_url: isGen ? out : p.cachedUrl,
        label: p.label, x: s.x, y: s.y,
      });
    }
  }

  // 合成 Preview 接目标产出(让 run 有出口)
  const targetType = byId.get(targetId)?.props.nodeType;
  const outHandle = targetType === "Video" || targetType === "Compose" ? "video" : "image";
  const previewId = `regen_preview_${targetId}`;
  nodes.push({ id: previewId, type: "Preview", params: {}, x: 0, y: 0 });

  const subEdges = edges.filter((e) => keep.has(e.source) && keep.has(e.target)).map((e) => ({ ...e }));
  subEdges.push({ id: `regen_e_${targetId}`, source: targetId, sourceHandle: outHandle, target: previewId, targetHandle: "image" });

  return { version: 1, nodes, edges: subEdges };
}

/** 重生目标的下游(沿出边)生成型节点 id —— 重生后给它们标脏「需重生」。 */
export function downstreamGeneratedIds(targetId: string): string[] {
  const edges = useProCanvasStore.getState().edges;
  const out = new Set<string>();
  const q = [targetId];
  while (q.length) {
    const cur = q.shift() as string;
    for (const e of edges) if (e.source === cur && !out.has(e.target)) { out.add(e.target); q.push(e.target); }
  }
  return [...out];
}
