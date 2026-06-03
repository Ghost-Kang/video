import type { CanvasNode } from "../../types";

/**
 * time-travel 回溯(P2 slice-2)徽标 —— 上游被重生后,下游产物已过时(needs_regen=true)。
 *
 * 语义:此节点参考的某个上游被重生了,它现在显示的图/视频/文字是「旧上游」的产物,已过时。
 * 媒体节点(image/video/composite)选中后,NodeActionBar 会给出琥珀「↻ 重生」按钮按新上游
 * 刷新(重生顺带把它自己的下游也标脏,级联下传,见后端 _mark_descendants_stale);script
 * 节点画布侧暂无重生 worker,徽标为纯状态提示,刷新经重新对话驱动 Director。needs_regen=false
 * 时不渲染。
 *
 * 单独成组件:徽标在 4 个内容节点(script/image/video/composite)复用,集中一处保证文案/
 * 配色一致(暖色琥珀=待办提醒)。文案只陈述「状态」不指定按钮,避免对无重生按钮的 script 食言。
 */
export function NeedsRegenBadge({ node }: { node: CanvasNode }) {
  if (!node.needs_regen) return null;
  return (
    <span
      style={S.badge}
      title="上游已重生,此节点产物已过时,需按新上游重新生成"
      data-testid="needs-regen-badge"
    >
      ⚠ 需重生
    </span>
  );
}

const S: Record<string, React.CSSProperties> = {
  badge: {
    display: "inline-block",
    marginLeft: 4,
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
    background: "#fef3c7", // amber-100 — 待办提醒,区别于状态徽标的中性灰
    color: "#b45309", // amber-700
    border: "1px solid #fcd34d", // amber-300
  },
};
