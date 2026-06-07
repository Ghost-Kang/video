import { useState, useRef, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  MarkerType,
  applyNodeChanges,
  type Node,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type FitViewOptions,
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

import { useCanvasStore } from "../store/canvasStore";
import { ScriptNode } from "./nodes/ScriptNode";
import { ImageNode } from "./nodes/ImageNode";
import { VideoNode } from "./nodes/VideoNode";
import { CompositeNode } from "./nodes/CompositeNode";
import { ChapterGroupNode } from "./nodes/ChapterGroupNode";
import { DeletableEdge } from "./DeletableEdge";
import { CanvasEmptyState } from "./CanvasEmptyState";
import type { CanvasNode, WSPositionUpdate } from "../types";

const nodeTypes = {
  script: ScriptNode,
  image: ImageNode,
  video: VideoNode,
  composite: CompositeNode,
  group: ChapterGroupNode,
};

const edgeTypes = {
  default: DeletableEdge,
};

// MiniMap 节点配色:沿用四类节点的强调色,缩略图一眼分得清类型(暖色非阻挡版)。
const MINIMAP_NODE_COLOR: Record<string, string> = {
  script: "#7c2d12", image: "#ea580c", video: "#f59e0b", composite: "#d4a574",
};
function miniMapNodeColor(node: Node): string {
  if (node.type === "group") return "rgba(124,45,18,0.10)"; // 章节框淡显
  return MINIMAP_NODE_COLOR[node.type ?? ""] ?? "#a8a29e";
}

const NODE_W = 200;
const NODE_H = 120;

function getShotNo(node: CanvasNode): number {
  if (node.shot_no != null) {
    const n = parseInt(node.shot_no, 10);
    if (!isNaN(n)) return n;
  }
  return 0;
}

// ── P1-3 章节分组(ReactFlow sub-flows)──────────────────────────────────
// 只把 video 成片镜头按叙事章节框成 group;策划书/锚点/宫格留左侧 absolute 区,
// 参考链 edge 不被打断。章节当前按 shot_no 在总镜数中的位置推断(后续可由 Director 标注)。
const CHAPTERS = [
  { key: "open", label: "① 开场" },
  { key: "rise", label: "② 发展" },
  { key: "climax", label: "③ 高潮" },
  { key: "end", label: "④ 结尾" },
] as const;
const CHAPTER_X0 = 1500; // 章节区起点(在 composite 列 1200 之后)
const CHAPTER_W = 280;
const CHAPTER_GAP = 48;
const SHOT_SLOT_H = 210;

function chapterIndex(shotNo: number, maxShot: number): number {
  if (maxShot <= 1) return 0;
  const r = shotNo / maxShot;
  if (r <= 0.25) return 0;
  if (r <= 0.55) return 1;
  if (r <= 0.85) return 2;
  return 3;
}

/** chapter group 节点是前端虚拟的(不在 canvasStore),id 以 chapter- 前缀;持久化/同步时据此排除。 */
function isChapterGroupId(id: string): boolean {
  return id.startsWith("chapter-");
}

function defaultLayout(nodes: CanvasNode[]): Node[] {
  const typeX: Record<string, number> = { script: 0, image: 400, video: 800, composite: 1200 };
  const videos = nodes.filter((n) => n.type === "video" && getShotNo(n) > 0);
  const others = nodes.filter((n) => !(n.type === "video" && getShotNo(n) > 0));
  const maxShot = Math.max(1, ...videos.map(getShotNo));

  // 非镜头节点:沿用 type 列 absolute 布局。
  const result: Node[] = others.map((n, i) => ({
    id: n.id,
    type: n.type,
    position: { x: n.x ?? (typeX[n.type] ?? 100), y: n.y ?? (100 + i * 240) },
    data: { node: n },
  }));

  // video 按章节分桶,每桶一个 group 容器,镜头作为相对定位的子节点。
  const byChapter: CanvasNode[][] = [[], [], [], []];
  for (const v of videos) byChapter[chapterIndex(getShotNo(v), maxShot)].push(v);

  CHAPTERS.forEach((ch, ci) => {
    const members = byChapter[ci].slice().sort((a, b) => getShotNo(a) - getShotNo(b));
    if (members.length === 0) return;
    const groupId = `chapter-${ch.key}`;
    result.push({
      id: groupId,
      type: "group",
      position: { x: CHAPTER_X0 + ci * (CHAPTER_W + CHAPTER_GAP), y: 60 },
      style: { width: CHAPTER_W, height: members.length * SHOT_SLOT_H + 56 },
      data: { label: ch.label, count: members.length },
      selectable: false,
    });
    members.forEach((n, mi) => {
      result.push({
        id: n.id,
        type: n.type,
        parentId: groupId,
        extent: "parent",
        position: { x: 24, y: 44 + mi * SHOT_SLOT_H },
        data: { node: n },
      });
    });
  });

  return result;
}

function dagreLayout(nodes: CanvasNode[], edges: { source: string; target: string }[]): Map<string, { x: number; y: number }> {
  // 1. 全图跑一次 dagre LR，得到水平结构
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 120, ranksep: 300, marginx: 80, marginy: 80 });

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_W, height: NODE_H });
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target);
  }
  dagre.layout(g);

  // 2. 按 dagre x 坐标分列（同一横向层级）
  const COL_GAP = 150;
  const columns: Map<number, { id: string; x: number; y: number; shotNo: number }[]> = new Map();
  for (const n of nodes) {
    const pos = g.node(n.id);
    if (!pos) continue;
    const colKey = Math.round(pos.x / COL_GAP);
    const col = columns.get(colKey) || [];
    col.push({ id: n.id, x: pos.x - NODE_W / 2, y: pos.y, shotNo: getShotNo(n) });
    columns.set(colKey, col);
  }

  // 3. 每列内按 shot_no 重排 y
  const positions = new Map<string, { x: number; y: number }>();
  // 列按 x 从小到大处理（左→右）
  const sortedColKeys = [...columns.keys()].sort((a, b) => a - b);

  for (const colKey of sortedColKeys) {
    const col = columns.get(colKey)!;
    // 按 shot_no 排序（0 的排在后面）
    col.sort((a, b) => {
      if (a.shotNo === 0 && b.shotNo === 0) return 0;
      if (a.shotNo === 0) return 1;
      if (b.shotNo === 0) return -1;
      return a.shotNo - b.shotNo;
    });

    // 重新分配 y，shot 之间加间距
    let curY = 80;
    let prevShotNo = -1;
    for (const item of col) {
      if (item.shotNo > 0 && prevShotNo > 0 && item.shotNo !== prevShotNo) {
        curY += 120; // 不同分镜之间额外间距
      }
      positions.set(item.id, { x: item.x, y: curY });
      curY += NODE_H + 60;
      if (item.shotNo > 0) prevShotNo = item.shotNo;
    }
  }

  return positions;
}

interface Props {
  onPositionChange: (update: WSPositionUpdate) => void;
  onCreateEdge: (source: string, target: string) => void;
  onDeleteEdge: (edgeId: string) => void;
}

export function Canvas({ onPositionChange, onCreateEdge, onDeleteEdge }: Props) {
  const canvasNodes = useCanvasStore((s) => s.nodes);
  const edges = useCanvasStore((s) => s.edges);
  const updateNodePosition = useCanvasStore((s) => s.updateNodePosition);
  const addEdge = useCanvasStore((s) => s.addEdge);
  const removeEdge = useCanvasStore((s) => s.removeEdge);
  const selectNode = useCanvasStore((s) => s.selectNode);

  const [rfNodes, setRfNodes] = useState<Node[]>(() => defaultLayout(canvasNodes));
  // 只取我们用到的 fitView,结构化类型避开 ReactFlowInstance 的 Node/Edge 泛型与 store 边类型打架。
  const rfRef = useRef<{ fitView: (opts?: FitViewOptions) => unknown } | null>(null);

  // M7 — 「下一步」导航:大画布里用户得自己找该操作的节点。指向首个待确认(reviewing)节点,
  // 没有则指向首个待重生(needs_regen)节点。点按 → 居中放大 + 选中,打开右侧详情面板。
  // 跳过 seed 脚手架里那个空的「我的策划书」(reviewing 但还没内容)——「确认空节点」无意义。
  const nextNode =
    canvasNodes.find(
      (n) => n.node_status === "reviewing" && !(n.type === "script" && !(n.description || "").trim()),
    ) || canvasNodes.find((n) => n.needs_regen);
  const nextLabel = nextNode
    ? nextNode.node_status === "reviewing"
      ? "下一步 · 确认节点"
      : "下一步 · 待重生"
    : "";
  const focusNext = () => {
    if (!nextNode) return;
    selectNode(nextNode.id);
    rfRef.current?.fitView({ nodes: [{ id: nextNode.id }], duration: 500, maxZoom: 1.3, padding: 0.45 });
  };

  // H5 — 刚 seed 完(只有脚手架 script 节点、没有任何媒体、且「我的策划书」还空着):不让用户
  // 对着空策划书发懵,给一个「告诉导演开始」的明确 CTA(指向底部对话 dock,**不自动触发付费
  // Director**,留给用户主动开口)。和 M7 互斥(此时 nextNode 为空,不显「下一步」)。
  const myPlan = canvasNodes.find((n) => n.type === "script" && (n.title || "").includes("我的策划书"));
  const seededNotStarted =
    canvasNodes.length > 0 &&
    !canvasNodes.some((n) => n.type === "image" || n.type === "video" || n.type === "composite") &&
    !!myPlan && !(myPlan.description || "").trim();

  useEffect(() => {
    const handler = (e: Event) => {
      const { edgeId } = (e as CustomEvent).detail;
      removeEdge(edgeId);
      onDeleteEdge(edgeId);
    };
    window.addEventListener("delete_edge", handler);
    return () => window.removeEventListener("delete_edge", handler);
  }, [removeEdge, onDeleteEdge]);

  useEffect(() => {
    // 同步 canvasStore.nodes → 本地 rfNodes(ReactFlow 需本地 state 管位置 + 章节布局)。
    // store→local 镜像必须在 effect 里 setState,函数式更新读 prev 保留用户拖动,非 cascading render。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRfNodes((prev) => {
      const prevMap = new Map(prev.map((n) => [n.id, n]));
      return defaultLayout(canvasNodes).map((n) => {
        // 章节 group + 章节内镜头(parentId):始终用新布局(章节固定),不保留旧 absolute 坐标。
        if (n.type === "group" || n.parentId) return n;
        const existing = prevMap.get(n.id);
        if (existing) {
          return { ...n, position: existing.position, width: existing.width, height: existing.height };
        }
        return n;
      });
    });
  }, [canvasNodes]);

  const persistRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      setRfNodes((nds) => {
        const updated = applyNodeChanges(changes, nds);
        for (const c of changes) {
          if (c.type === "position" && c.position) {
            // 章节 group(前端虚拟,不在后端)+ 章节内镜头(相对坐标,每次按章节重算)
            // 都不持久化,避免污染后端 node 坐标。
            if (isChapterGroupId(c.id)) continue;
            if (updated.find((n) => n.id === c.id)?.parentId) continue;
            const x = Math.round(c.position.x);
            const y = Math.round(c.position.y);
            updateNodePosition(c.id, x, y);
            if (persistRef.current[c.id]) clearTimeout(persistRef.current[c.id]);
            persistRef.current[c.id] = setTimeout(() => {
              onPositionChange({ type: "update_position", thread_id: "", node_id: c.id, x, y });
              delete persistRef.current[c.id];
            }, 300);
          }
        }
        return updated;
      });
    },
    [updateNodePosition, onPositionChange]
  );

  const handleConnect: OnConnect = useCallback(
    (connection) => {
      if (!connection.source || !connection.target) return;
      const edgeId = `e-${connection.source}-${connection.target}`;
      // 检查重复
      if (edges.some((e) => e.source === connection.source && e.target === connection.target)) return;
      addEdge({ id: edgeId, source: connection.source, target: connection.target });
      onCreateEdge(connection.source, connection.target);
    },
    [edges, addEdge, onCreateEdge]
  );

  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      for (const c of changes) {
        if (c.type === "remove") {
          removeEdge(c.id);
          onDeleteEdge(c.id);
        }
      }
    },
    [removeEdge, onDeleteEdge]
  );

  const handleAutoLayout = useCallback(() => {
    const positions = dagreLayout(canvasNodes, edges);
    // 章节内镜头(video,有 shot_no)不参与 dagre 自动排版,保持章节 group 布局。
    const inChapter = new Set(
      canvasNodes.filter((n) => n.type === "video" && getShotNo(n) > 0).map((n) => n.id),
    );
    for (const [id, pos] of positions) {
      if (inChapter.has(id)) continue;
      updateNodePosition(id, pos.x, pos.y);
      onPositionChange({ type: "update_position", thread_id: "", node_id: id, x: pos.x, y: pos.y });
    }
    setRfNodes((prev) =>
      prev.map((n) => {
        if (n.type === "group" || n.parentId) return n;
        const pos = positions.get(n.id);
        return pos ? { ...n, position: pos } : n;
      })
    );
  }, [canvasNodes, edges, updateNodePosition, onPositionChange]);

  return (
    <div style={{ flex: 1, minWidth: 0, height: "100%", position: "relative", overflow: "hidden" }}>
      {/* aurora 底:两团暖色光晕缓慢漂移(陶土 + 琥珀),藏在点阵之下,给空旷画布一点高级的呼吸感。
          位于 z0,ReactFlow 透明叠在上面;anim-aurora-* 已在 reduced-motion 注册(铁律⑧)。 */}
      <div style={S.aurora} aria-hidden>
        <div style={S.blob1} className="anim-aurora-1" />
        <div style={S.blob2} className="anim-aurora-2" />
      </div>
      <ReactFlow
        nodes={rfNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onInit={(inst) => { rfRef.current = inst; }}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onNodeClick={(_e, node) => selectNode(node.id)}
        defaultEdgeOptions={{
          deletable: true,
          style: { stroke: "rgba(124,45,18,0.4)", strokeWidth: 1.5 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(124,45,18,0.55)", width: 16, height: 16 },
        }}
        proOptions={{ hideAttribution: true }}
        style={{ background: "transparent" }}
        fitView
      >
        {/* 暖色科技底:极淡陶土点阵(替默认黑网格)。 */}
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="rgba(124,45,18,0.10)" />
        <Controls className="cascade-rf-controls" />
        {/* 暖色非阻挡版小地图(bottom-right,与 bottom-left 的 Controls 错开)。半透玻璃 +
            类型配色 + pannable/zoomable 当导航用;主题色走 CSS 变量(亮/暗都不会变白块)。
            **门控 >=8**:画布够忙(导演搭出角色/场景/分镜后)才需要缩略图导航;稀疏的种子
            画布(2 节点)不显示 —— 否则 fitView 会把它正好扣在策划书节点上,重蹈创始人最初
            「白块挡操作」的覆辙。够忙时画布溢出视口,缩略图才真有用且不再是死块。 */}
        {canvasNodes.length >= 8 && (
          <MiniMap
            className="cascade-rf-minimap"
            position="bottom-right"
            pannable
            zoomable
            nodeColor={miniMapNodeColor}
            nodeStrokeColor="rgba(124,45,18,0.28)"
            nodeStrokeWidth={2}
            nodeBorderRadius={3}
            style={{ width: 168, height: 116 }}
            ariaLabel="画布缩略图"
          />
        )}
      </ReactFlow>
      {/* 空画布引导(0 节点时):告诉用户这是创作画布 + 一键唤起导演。 */}
      {canvasNodes.length === 0 && <CanvasEmptyState />}
      <button onClick={handleAutoLayout} style={S.layoutBtn}>自动排版</button>
      {/* M7 — 「下一步」导航:有待确认/待重生节点时出现,点按居中放大 + 选中(打开详情)。 */}
      {nextNode && (
        <button onClick={focusNext} style={S.nextBtn} title={nextNode.title}>
          {nextLabel}
        </button>
      )}
      {/* H5 — 刚 seed 完的冷启动 CTA(与 M7 互斥):指向底部对话,让用户开口,导演才开始(不自动烧钱)。 */}
      {seededNotStarted && (
        <button
          onClick={() => window.dispatchEvent(new CustomEvent("open_canvas_chat"))}
          style={S.seedCta}
          className="anim-cta-breathe"
        >
          ✦ 告诉导演你想做的方向,他就开始搭这条片子
        </button>
      )}
    </div>
  );
}

const S = {
  aurora: {
    position: "absolute",
    inset: 0,
    zIndex: 0,
    overflow: "hidden",
    pointerEvents: "none",
  } as React.CSSProperties,
  blob1: {
    position: "absolute",
    top: "-12%",
    left: "-8%",
    width: "55%",
    height: "60%",
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(234,88,12,0.10) 0%, rgba(234,88,12,0) 68%)",
    filter: "blur(40px)",
  } as React.CSSProperties,
  blob2: {
    position: "absolute",
    bottom: "-15%",
    right: "-10%",
    width: "60%",
    height: "62%",
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(124,45,18,0.08) 0%, rgba(124,45,18,0) 70%)",
    filter: "blur(44px)",
  } as React.CSSProperties,
  nextBtn: {
    position: "absolute",
    bottom: 20,
    left: "50%",
    transform: "translateX(-50%)",
    height: 38,
    display: "flex",
    alignItems: "center",
    gap: 6,
    background: "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
    border: "none",
    borderRadius: 19,
    cursor: "pointer",
    color: "#fff",
    fontWeight: 600,
    fontSize: 13,
    padding: "0 20px",
    zIndex: 12,
    boxShadow: "0 4px 16px rgba(234,88,12,0.32)",
  } as React.CSSProperties,
  seedCta: {
    position: "absolute",
    bottom: 20,
    left: "50%",
    transform: "translateX(-50%)",
    height: 40,
    display: "flex",
    alignItems: "center",
    gap: 6,
    background: "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
    border: "none",
    borderRadius: 20,
    cursor: "pointer",
    color: "#fff",
    fontWeight: 600,
    fontSize: 13,
    padding: "0 22px",
    zIndex: 12,
    maxWidth: "90%",
    boxShadow: "0 8px 24px -6px rgba(234,88,12,0.45)",
  } as React.CSSProperties,
  layoutBtn: {
    position: "absolute",
    top: 12,
    right: 12,
    height: 32,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(250,248,243,0.82)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    border: "1px solid rgba(124,45,18,0.18)",
    borderRadius: 12,
    cursor: "pointer",
    color: "#7c2d12",
    fontWeight: 500,
    fontSize: 13,
    padding: "0 14px",
    zIndex: 10,
    boxShadow: "0 2px 10px rgba(124,45,18,0.08)",
  } as React.CSSProperties,
};
