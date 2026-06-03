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

  // time-travel 回溯(P2 slice-2):确有产物可取代时(asset done,或被上游重生标脏且仍存旧
  // result)→ 走 regenerate_node(快照旧版 → 清 + 入队 → 标脏下游)。首次生成走 execute_node
  // (无旧版可存;下游此时本就没产物,标脏无意义)。此前两条路都错调 execute_node,
  // 「↻ 重生」既不快照也不标脏下游。
  //
  // `!!node.result` 守卫:后端 _mark_descendants_stale 的 has_asset 把「首次生成就失败」
  // (result=null、asset=failed/timeout)的节点也标 needs_regen —— 那种节点没有旧版可存,
  // 当它「重生」会写一条 result=null 的垃圾版本快照;此处当首次生成(execute 重试)更对。
  const isRegen = !!node.result && (asset === "done" || node.needs_regen);
  const genLabel = isRegen ? "↻ 重生" : node.type === "composite" ? "🎬 合成" : "⚡ 生成";
  const onGen = () =>
    isRegen
      ? actions.handleRegenerateNode(node.id)
      : actions.handleExecuteNode(node.id, node.type, desc);
  // tooltip 跟 label/action 一致:isRegen 才说「重生」,否则说「生成」(stale 但无旧产物的
  // 节点走生成,不能食言说重生)。
  const genTitle = isRegen
    ? node.needs_regen
      ? "上游已变,产物过时 —— 重生按新上游刷新(旧版自动存档,下游连带标记需重生)"
      : "重生此节点(旧版自动存档,下游连带标记需重生)"
    : node.needs_regen
      ? "上游已变,此节点尚无产物 —— 生成即按新上游"
      : "生成此节点的图 / 视频";

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
            style={node.needs_regen ? S.btnStale : S.btnPrimary}
            title={genTitle}
            onClick={onGen}
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
  // 节点被标脏(needs_regen)时,重生 CTA 用琥珀强调,呼应 NeedsRegenBadge。
  btnStale: {
    fontSize: 11,
    padding: "3px 9px",
    borderRadius: 6,
    border: "1px solid #b45309",
    background: "#f59e0b",
    cursor: "pointer",
    color: "#fff",
    fontWeight: 600,
  },
};
