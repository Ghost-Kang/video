import { useCanvasStore } from "../store/canvasStore";
import type { Todo } from "../types/ws";

/**
 * write_todos→画布进度(P2 ③):Director 用 deepagents 的 `write_todos` 规划的多步创作进度
 * (策划书 → 角色三视图 → 场景图 → 宫格图 → 逐镜视频 → 合成)。渲染成画布顶部的进度条:
 * 每步显示 pending(○)/ in_progress(● 陶土)/ completed(✓ 绿)。todos 空时不渲染。
 *
 * 数据来自 canvasStore.todos(后端每轮 agent 跑完读 state["todos"] 推 todos_updated)。
 */
export function TodoProgress() {
  const todos = useCanvasStore((s) => s.todos);
  if (!todos.length) return null;
  const done = todos.filter((t) => t.status === "completed").length;
  return (
    <div style={bar} className="nodrag nopan" data-testid="todo-progress">
      <div style={head}>
        导演计划 · {done}/{todos.length}
      </div>
      <div style={steps}>
        {todos.map((t, i) => (
          <div key={i} style={step} title={t.content} data-testid={`todo-${t.status}`}>
            <span style={dot(t.status)}>{glyph(t.status)}</span>
            <span style={label(t.status)}>{t.content}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function glyph(status: Todo["status"]): string {
  return status === "completed" ? "✓" : status === "in_progress" ? "●" : "○";
}

function color(status: Todo["status"]): string {
  return status === "completed" ? "#16a34a" : status === "in_progress" ? "#7c2d12" : "#a1a1aa";
}

const bar: React.CSSProperties = {
  position: "absolute",
  top: 12,
  left: "50%",
  transform: "translateX(-50%)",
  zIndex: 20,
  maxWidth: "min(880px, 92vw)",
  display: "flex",
  alignItems: "center",
  gap: 12,
  background: "rgba(255,255,255,0.92)",
  backdropFilter: "blur(6px)",
  border: "1px solid #e7e5e4",
  borderRadius: 12,
  padding: "7px 12px",
  boxShadow: "0 6px 20px -8px rgba(28,25,23,0.25)",
  overflowX: "auto",
};
const head: React.CSSProperties = { fontSize: 12, fontWeight: 600, color: "#7c2d12", whiteSpace: "nowrap", flexShrink: 0 };
const steps: React.CSSProperties = { display: "flex", alignItems: "center", gap: 14 };
const step: React.CSSProperties = { display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap" };
const dot = (status: Todo["status"]): React.CSSProperties => ({ fontSize: 12, color: color(status) });
const label = (status: Todo["status"]): React.CSSProperties => ({
  fontSize: 12,
  color: color(status),
  fontWeight: status === "in_progress" ? 600 : 400,
  textDecoration: status === "completed" ? "line-through" : "none",
});
