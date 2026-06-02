import { useContext } from "react";
import { NodeToolbar, Position } from "@xyflow/react";
import type { CanvasNode } from "../../types";
import { NodeActionsContext } from "../../lib/nodeActionsContext";

/**
 * 画布节点上的浮动操作条(NodeToolbar)—— 选中节点时在其上方弹出「确认 / 生成」。
 *
 * 此前节点操作只能点开 NodeDetail 侧面板(781 行)再操作;锚点级联创作里每个节点都要
 * 「确认→解锁下游」「生成图/视频」,挂在节点上比开侧面板快得多(CANVAS_DESIGN「节点为主体」)。
 *
 * actions 通过 NodeActionsContext(lib/nodeActionsContext)注入,节点组件 useContext 取,
 * 避免把 actions 一路 props 钻到每个自定义节点。删除/精细调参(provider/时长/分辨率)仍走 NodeDetail。
 */
export function NodeActionBar({ node, selected }: { node: CanvasNode; selected?: boolean }) {
  const actions = useContext(NodeActionsContext);
  if (!actions) return null;

  const asset = node.asset_status || "idle";
  const isMedia = node.type === "image" || node.type === "video" || node.type === "composite";
  const reviewing = node.node_status === "reviewing";
  const confirmed = node.node_status === "confirmed";
  const desc = node.description || (node.result?.prompt as string) || "";

  const genLabel =
    asset === "done" ? "↻ 重生" : node.type === "composite" ? "🎬 合成" : "⚡ 生成";

  return (
    <NodeToolbar isVisible={!!selected} position={Position.Top}>
      <div style={S.bar}>
        {reviewing && (
          <button
            type="button"
            style={S.btn}
            title="确认此节点,解锁下游创建"
            onClick={() => actions.handleUpdateNodeStatus(node.id, "confirmed")}
          >
            ✓ 确认
          </button>
        )}
        {isMedia && confirmed && asset !== "generating" && (
          <button
            type="button"
            style={S.btnPrimary}
            title="生成此节点的图 / 视频"
            onClick={() => actions.handleExecuteNode(node.id, node.type, desc)}
          >
            {genLabel}
          </button>
        )}
      </div>
    </NodeToolbar>
  );
}

const S: Record<string, React.CSSProperties> = {
  bar: {
    display: "flex",
    gap: 6,
    background: "#fff",
    border: "1px solid #d4d4d8",
    borderRadius: 8,
    padding: 4,
    boxShadow: "0 2px 10px rgba(0,0,0,0.10)",
  },
  btn: {
    fontSize: 11,
    padding: "3px 9px",
    borderRadius: 6,
    border: "1px solid #e4e4e7",
    background: "#fafafa",
    cursor: "pointer",
    color: "#18181b",
  },
  btnPrimary: {
    fontSize: 11,
    padding: "3px 9px",
    borderRadius: 6,
    border: "1px solid #7c2d12",
    background: "#7c2d12",
    cursor: "pointer",
    color: "#faf8f3",
  },
};
