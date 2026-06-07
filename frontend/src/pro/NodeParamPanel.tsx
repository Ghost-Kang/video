import { useState } from "react";
import { useEditor, useValue } from "tldraw";
import { PRO_NODE_SPECS } from "../types/pro";
import { useProCanvasStore } from "../store/proCanvasStore";
import { useToastStore } from "../store/toastStore";
import { getProNode, loadGraph, updateProNode } from "./graphIO";
import { ProApiError, proErrorTitle, regenFromScript, seedFromTheme } from "./proExecution";
import type { ProNodeShape } from "./nodes/NodeShape";

/** 选中单个节点时,右侧参数编辑面板。改参数 → editor.updateShape(单一真相在 editor)。 */
export function NodeParamPanel({ threadId, onRegen }: { threadId: string; onRegen?: (nodeId: string) => void }) {
  const editor = useEditor();
  const removeEdgesForNodes = useProCanvasStore((s) => s.removeEdgesForNodes);
  const [regenBusy, setRegenBusy] = useState(false);

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

  // 脚本卡重生:用当前(可能已编辑的)脚本重拆分镜 → 替换画布。
  const regenFromScriptCard = async () => {
    const script = String(selected.props.params.script_markdown ?? "").trim();
    if (!script || regenBusy) return;
    if (!window.confirm("根据当前脚本重新生成分镜?会替换画布上现有的分镜/图/视频节点。")) return;
    setRegenBusy(true);
    try {
      loadGraph(editor, await regenFromScript(script, threadId));
    } catch (e) {
      const err = e as ProApiError;
      useToastStore.getState().push({ kind: "error", title: proErrorTitle(err.code), body: err.detail });
    } finally {
      setRegenBusy(false);
    }
  };

  // 改主题→重生整篇:用主题重新生成脚本+分镜 → 替换画布。
  const regenFromThemeCard = async () => {
    const theme = String(selected.props.params.theme ?? "").trim();
    if (regenBusy) return;
    if (!theme) {
      useToastStore.getState().push({ kind: "warning", title: "请先在「主题」里填写主题" });
      return;
    }
    if (!window.confirm("根据主题重新生成整篇脚本与分镜?会替换画布上现有节点。")) return;
    setRegenBusy(true);
    try {
      loadGraph(editor, await seedFromTheme(theme, threadId));
    } catch (e) {
      const err = e as ProApiError;
      useToastStore.getState().push({ kind: "error", title: proErrorTitle(err.code), body: err.detail });
    } finally {
      setRegenBusy(false);
    }
  };

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

      {selected.props.nodeType === "Script" && (
        <div className="mt-4 flex flex-col gap-2">
          <button
            type="button"
            onClick={regenFromThemeCard}
            disabled={regenBusy}
            data-testid="pro-theme-regen"
            className="w-full rounded-lg bg-[var(--color-clay)] px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[var(--color-clay-soft)] disabled:opacity-50"
          >
            {regenBusy ? "重新生成中…" : "🎬 改主题·重生整篇"}
          </button>
          <button
            type="button"
            onClick={regenFromScriptCard}
            disabled={regenBusy}
            data-testid="pro-script-regen"
            className="w-full rounded-lg border border-[var(--color-clay)]/40 px-3 py-1.5 text-xs font-semibold text-[var(--color-clay)] transition hover:bg-[var(--color-paper-deeper)] disabled:opacity-50"
          >
            {regenBusy ? "重新生成中…" : "🔄 按脚本重拆分镜"}
          </button>
        </div>
      )}

      {(selected.props.nodeType === "Generate" || selected.props.nodeType === "Video") && onRegen && (
        <button
          type="button"
          onClick={() => onRegen(String(selected.id))}
          data-testid="pro-node-regen"
          className="mt-4 w-full rounded-lg bg-[var(--color-clay)] px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[var(--color-clay-soft)]"
        >
          🔄 重新生成{selected.props.needsRegen ? "(上游已变)" : ""}
        </button>
      )}

      <button
        type="button"
        onClick={remove}
        className="mt-3 w-full rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50"
      >
        删除此节点
      </button>
    </div>
  );
}
