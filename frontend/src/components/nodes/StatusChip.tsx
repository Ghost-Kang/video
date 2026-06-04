import type { CanvasNode } from "../../types";

/**
 * 单一状态芯片(P2 画布 polish)。把原本散落的三枚徽标(node_status「待确认/已确认」×
 * asset_status「生成中/已生成/失败…」× needs_regen「⚠需重生」)折叠成**一枚**最能代表
 * 该节点当前状态的中文芯片,降噪 + 一眼可读。
 *
 * 优先级(高→低,只显示最该让用户看到的那一个):
 *  1. needs_regen   → 上游变了,产物过时,最该提醒 → 琥珀告警「待重生」
 *  2. generating    → 正在出活 → 琥珀呼吸「生成中/合成中」
 *  3. failed/timeout→ 出错了 → 红「失败重试/超时重试」
 *  4. asset done    → 有成品 → 绿「已确认 / 已生成」(看 node_status)
 *  5. 无成品(idle/script) → node_status:已确认(陶土)/ 待确认(琥珀)
 */

const CLAY = "#7c2d12";
const AMBER = "#b45309";
const GREEN = "#15803d";
const RED = "#b91c1c";

interface Chip {
  label: string;
  tone: string;
  breathing?: boolean;
  alert?: boolean;
  testid: string;
}

function deriveChip(node: CanvasNode): Chip {
  const asset = node.asset_status || "idle";
  const confirmed = node.node_status === "confirmed";
  const composite = node.type === "composite";
  const verb = composite ? "合成" : "生成";

  if (node.needs_regen) return { label: "⚠ 待重生", tone: AMBER, alert: true, testid: "needs-regen" };
  if (asset === "generating") return { label: `${verb}中`, tone: AMBER, breathing: true, testid: "generating" };
  if (asset === "failed") return { label: "✕ 失败重试", tone: RED, testid: "failed" };
  if (asset === "timeout") return { label: "✕ 超时重试", tone: RED, testid: "timeout" };
  if (asset === "done") return { label: confirmed ? "✓ 已确认" : `已${verb}`, tone: GREEN, testid: "done" };
  // 无成品(idle):纯 node_status
  return confirmed
    ? { label: "✓ 已确认", tone: CLAY, testid: "confirmed" }
    : { label: "● 待确认", tone: AMBER, testid: "reviewing" };
}

export function StatusChip({ node }: { node: CanvasNode }) {
  const chip = deriveChip(node);
  return (
    <span
      data-testid="status-chip"
      data-state={chip.testid}
      className={chip.breathing ? "anim-cta-breathe" : ""}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 9px",
        borderRadius: 999,
        fontSize: 10.5,
        fontWeight: 600,
        letterSpacing: "0.01em",
        color: chip.tone,
        background: `${chip.tone}14`,
        border: chip.alert ? `1px solid ${chip.tone}66` : "1px solid transparent",
        whiteSpace: "nowrap",
      }}
      title={chip.alert ? "上游已重生,此节点产物已过时,需按新上游重新生成" : undefined}
    >
      {chip.label}
    </span>
  );
}
