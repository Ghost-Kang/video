import { Link } from "react-router-dom";
import { useEditor } from "tldraw";
import { PRO_NODE_ORDER, PRO_NODE_SPECS } from "../types/pro";
import { useProCanvasStore } from "../store/proCanvasStore";
import { createNode } from "./graphIO";
import { NODE_W } from "./nodes/layout";
import { ProTemplates } from "./ProTemplates";

let _addCount = 0;

const STATUS_LABEL: Record<string, string> = {
  idle: "",
  queued: "已排队…",
  submitting: "提交中…",
  running: "生成中…",
  done: "完成 ✓",
  failed: "失败 ✕",
  cancelled: "已取消",
};

export function ProToolbar({ onRun, threadId }: { onRun: () => void; threadId: string }) {
  const editor = useEditor();
  const run = useProCanvasStore((s) => s.run);
  const pending = useProCanvasStore((s) => s.pending);
  const cancelConnection = useProCanvasStore((s) => s.cancelConnection);
  const busy = run.status === "queued" || run.status === "submitting" || run.status === "running";

  const add = (t: (typeof PRO_NODE_ORDER)[number]) => {
    const c = editor.getViewportPageBounds().center;
    const k = _addCount++ % 6;
    createNode(editor, t, c.x - NODE_W / 2 + k * 26, c.y - 60 + k * 26);
  };

  return (
    <div
      style={{ position: "absolute", top: 0, left: 0, right: 0, zIndex: 25, pointerEvents: "none" }}
      className="flex flex-wrap items-center gap-2 p-2"
    >
      <div
        className="flex items-center gap-1.5 rounded-2xl border border-[var(--color-clay)]/15 bg-[var(--color-paper)]/95 px-2 py-1.5 shadow-lg backdrop-blur"
        style={{ pointerEvents: "all" }}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <Link to={`/chat/${threadId}`} className="px-2 text-sm text-[var(--color-ink-soft)] hover:text-[var(--color-clay)]" title="返回 Agent 模式">
          ←
        </Link>
        <span className="mr-1 text-xs font-semibold text-[var(--color-clay)]">⚡ Pro 画布</span>
        {PRO_NODE_ORDER.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => add(t)}
            className="rounded-lg px-2 py-1 text-xs font-medium text-[var(--color-ink-soft)] transition hover:bg-[var(--color-paper-deeper)]"
            style={{ borderLeft: `3px solid ${PRO_NODE_SPECS[t].accent}` }}
          >
            +{PRO_NODE_SPECS[t].label}
          </button>
        ))}
      </div>

      <div
        className="ml-auto flex items-center gap-2 rounded-2xl border border-[var(--color-clay)]/15 bg-[var(--color-paper)]/95 px-3 py-1.5 shadow-lg backdrop-blur"
        style={{ pointerEvents: "all" }}
        onPointerDown={(e) => e.stopPropagation()}
      >
        {run.status !== "idle" && (
          <span className="text-xs text-[var(--color-ink-soft)]">
            {STATUS_LABEL[run.status]}
            {run.status === "running" && run.pct ? ` ${run.pct}%` : ""}
          </span>
        )}
        <ProTemplates />
        <button
          type="button"
          onClick={onRun}
          disabled={busy}
          data-testid="pro-run-button"
          className="rounded-xl bg-[var(--color-clay)] px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-[var(--color-clay-soft)] disabled:opacity-50"
        >
          {busy ? "运行中…" : "▶ 运行"}
        </button>
      </div>

      {pending && (
        <div
          className="absolute left-1/2 top-14 -translate-x-1/2 rounded-full bg-[var(--color-ink)]/85 px-3 py-1 text-xs text-white shadow-lg"
          style={{ pointerEvents: "all" }}
          onClick={cancelConnection}
        >
          点目标输入口完成连线 · 点此 / Esc 取消
        </div>
      )}
    </div>
  );
}
