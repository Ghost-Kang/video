import { useEditor, useValue } from "tldraw";
import { PRO_NODE_SPECS } from "../types/pro";
import { useProCanvasStore } from "../store/proCanvasStore";
import { getProNode, updateProNode } from "./graphIO";
import type { ProNodeShape } from "./nodes/NodeShape";

/** 选中单个节点时,右侧参数编辑面板。改参数 → editor.updateShape(单一真相在 editor)。 */
export function NodeParamPanel() {
  const editor = useEditor();
  const removeEdgesForNodes = useProCanvasStore((s) => s.removeEdgesForNodes);

  const selected = useValue<ProNodeShape | null>(
    "pro-selected-node",
    () => {
      const ids = editor.getSelectedShapeIds();
      if (ids.length !== 1) return null;
      return getProNode(editor, ids[0]);
    },
    [editor],
  );

  if (!selected) return null;
  const spec = PRO_NODE_SPECS[selected.props.nodeType];

  const setParam = (name: string, value: string | number) => {
    updateProNode(editor, selected.id, { params: { ...selected.props.params, [name]: value } });
  };

  const remove = () => {
    removeEdgesForNodes([selected.id]);
    editor.deleteShape(selected.id);
  };

  return (
    <div
      style={{
        position: "absolute",
        top: 64,
        right: 12,
        width: 280,
        maxHeight: "calc(100% - 88px)",
        overflowY: "auto",
        pointerEvents: "all",
        zIndex: 30,
      }}
      className="rounded-2xl border border-[var(--color-clay)]/20 bg-[var(--color-paper)] p-4 shadow-xl"
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="mb-3 flex items-center gap-2">
        <span style={{ width: 8, height: 8, borderRadius: 99, background: spec.accent }} />
        <span className="text-sm font-semibold text-[var(--color-ink)]">{spec.label}</span>
        {spec.billable && <span className="ml-auto text-[10px] text-[var(--color-clay)]">计费</span>}
      </div>

      {spec.params.length === 0 && (
        <p className="text-xs text-[var(--color-ink-soft)]">该节点没有可调参数。</p>
      )}

      <div className="flex flex-col gap-3">
        {spec.params.map((p) => {
          const val = selected.props.params[p.name] ?? p.default;
          return (
            <label key={p.name} className="flex flex-col gap-1">
              <span className="text-xs text-[var(--color-ink-soft)]">{p.label}</span>
              {p.choices ? (
                <select
                  value={String(val)}
                  onChange={(e) => setParam(p.name, e.target.value)}
                  className="rounded-lg border border-[var(--color-ink)]/15 bg-white px-2 py-1.5 text-sm"
                >
                  {p.choices.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              ) : p.type === "str" ? (
                p.name === "text" || p.name === "script_markdown" ? (
                  <textarea
                    value={String(val)}
                    rows={p.name === "script_markdown" ? 8 : 3}
                    onChange={(e) => setParam(p.name, e.target.value)}
                    className="rounded-lg border border-[var(--color-ink)]/15 bg-white px-2 py-1.5 text-sm"
                  />
                ) : (
                  <input
                    value={String(val)}
                    onChange={(e) => setParam(p.name, e.target.value)}
                    className="rounded-lg border border-[var(--color-ink)]/15 bg-white px-2 py-1.5 text-sm"
                  />
                )
              ) : (
                <input
                  type="number"
                  value={Number(val)}
                  min={p.min}
                  max={p.max}
                  step={p.type === "float" ? 0.1 : 1}
                  onChange={(e) => setParam(p.name, p.type === "float" ? parseFloat(e.target.value) : parseInt(e.target.value || "0", 10))}
                  className="rounded-lg border border-[var(--color-ink)]/15 bg-white px-2 py-1.5 text-sm"
                />
              )}
            </label>
          );
        })}
      </div>

      <button
        type="button"
        onClick={remove}
        className="mt-4 w-full rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50"
      >
        删除此节点
      </button>
    </div>
  );
}
