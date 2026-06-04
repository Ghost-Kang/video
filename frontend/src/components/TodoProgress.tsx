import { useCanvasStore } from "../store/canvasStore";
import type { Todo } from "../types/ws";
import type { CanvasNode } from "../types";

/**
 * 六步创作向导(StageRail,P2 画布 UX 重设计)。常驻画布顶部,让用户一眼看懂
 * 「现在到哪一步、下一步干啥」。双源:
 *  - Director 用 write_todos 规划了计划 → 用真 todos(实时状态)。
 *  - 还没计划(seed 态)→ 显示六步路线图,从画布节点反推状态,让用户先看懂流程。
 * 三态:completed(✓ 陶土)/ in_progress(● 暗橙,呼吸)/ pending(○ 暖灰)。
 */

// 六步规范流程 + 「这步干啥」一句话(让小白懂)。
const STEPS: { label: string; desc: string }[] = [
  { label: "策划书", desc: "为什么火 + 改成你的版本" },
  { label: "角色", desc: "定主角形象" },
  { label: "场景", desc: "拍摄场景" },
  { label: "分镜", desc: "每个镜头的画面" },
  { label: "视频", desc: "逐镜生成短片" },
  { label: "合成", desc: "拼成整片" },
];

interface Item {
  n: number;
  label: string;
  status: Todo["status"];
  desc?: string;
}

export function TodoProgress() {
  const todos = useCanvasStore((s) => s.todos);
  const nodes = useCanvasStore((s) => s.nodes);

  const usingTodos = todos.length > 0;
  const items: Item[] = usingTodos
    ? todos.map((t, i) => ({ n: i + 1, label: t.content, status: t.status }))
    : STEPS.map((s, i) => ({ n: i + 1, label: s.label, desc: s.desc, status: inferStep(i, nodes) }));

  const done = items.filter((t) => t.status === "completed").length;
  const current = items.find((t) => t.status === "in_progress") ?? items.find((t) => t.status === "pending");

  return (
    <div style={bar} className="nodrag nopan" data-testid="todo-progress">
      <div style={head}>{usingTodos ? "导演计划" : "创作流程"} · {done}/{items.length}</div>
      <div style={steps}>
        {items.map((t) => (
          <div key={t.n} style={step} title={t.desc ?? t.label} data-testid={`todo-${t.status}`}>
            <span style={numCircle(t.status)} className={t.status === "in_progress" ? "anim-cta-breathe" : ""}>
              {t.status === "completed" ? "✓" : t.n}
            </span>
            <span style={label(t.status)}>{t.label}</span>
          </div>
        ))}
      </div>
      {!usingTodos && current?.desc && (
        <div style={hint}>当前 · {current.label}:{current.desc}</div>
      )}
    </div>
  );
}

function inferStep(i: number, nodes: CanvasNode[]): Todo["status"] {
  const byType = (type: string) => nodes.filter((n) => n.type === type);
  const phase = (matched: CanvasNode[]): Todo["status"] => {
    if (!matched.length) return "pending";
    if (matched.some((n) => n.asset_status === "generating" || n.node_status === "reviewing")) return "in_progress";
    if (matched.every((n) => n.asset_status === "done")) return "completed";
    return "in_progress";
  };
  if (i === 0) {
    const s = byType("script");
    if (!s.length) return "pending";
    return s.every((n) => n.node_status === "confirmed") ? "completed" : "in_progress";
  }
  if (i >= 1 && i <= 3) return phase(byType("image")); // 角色/场景/分镜 = image 节点
  if (i === 4) return phase(byType("video"));
  if (i === 5) return phase(byType("composite"));
  return "pending";
}

const CLAY = "#7c2d12";
const AMBER = "#b45309";
const GREEN = "#15803d";

function statusColor(s: Todo["status"]): string {
  return s === "completed" ? GREEN : s === "in_progress" ? CLAY : "#a8a29e";
}

const bar: React.CSSProperties = {
  position: "absolute",
  top: 12,
  left: "50%",
  transform: "translateX(-50%)",
  zIndex: 20,
  maxWidth: "min(920px, 94vw)",
  display: "flex",
  alignItems: "center",
  gap: 12,
  background: "rgba(250,248,243,0.9)",
  backdropFilter: "blur(8px)",
  WebkitBackdropFilter: "blur(8px)",
  border: "1px solid rgba(124,45,18,0.16)",
  borderRadius: 14,
  padding: "8px 14px",
  boxShadow: "0 8px 26px -10px rgba(124,45,18,0.28)",
  overflowX: "auto",
};
const head: React.CSSProperties = { fontSize: 12, fontWeight: 600, color: CLAY, whiteSpace: "nowrap", flexShrink: 0 };
const steps: React.CSSProperties = { display: "flex", alignItems: "center", gap: 16 };
const step: React.CSSProperties = { display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" };
const numCircle = (s: Todo["status"]): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 18,
  height: 18,
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 600,
  color: s === "pending" ? statusColor(s) : "#fff",
  background: s === "pending" ? "transparent" : statusColor(s),
  border: s === "pending" ? "1.5px solid #d6d3d1" : "none",
});
const label = (s: Todo["status"]): React.CSSProperties => ({
  fontSize: 12,
  color: statusColor(s),
  fontWeight: s === "in_progress" ? 600 : 400,
});
const hint: React.CSSProperties = { fontSize: 11.5, color: AMBER, whiteSpace: "nowrap", flexShrink: 0, paddingLeft: 4, borderLeft: "1px solid rgba(124,45,18,0.12)" };
