import { useState } from "react";
import { useEditor } from "tldraw";
import { compileGraph, loadGraph } from "./graphIO";
import { deleteTemplate, listTemplates, loadTemplate, saveTemplate, type ProTemplateMeta } from "./proExecution";
import { useToastStore } from "../store/toastStore";

/** 模板:另存当前图 / 套用已存模板(plan §7 P2 graph 模板存取)。child of <Tldraw> → useEditor 可用。 */
export function ProTemplates() {
  const editor = useEditor();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<ProTemplateMeta[]>([]);

  const refresh = async () => setItems(await listTemplates());
  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) void refresh();
  };

  const onSave = async () => {
    const name = window.prompt("模板名称", "我的模板");
    if (!name) return;
    try {
      await saveTemplate(name, compileGraph(editor));
      await refresh();
      useToastStore.getState().push({ kind: "info", title: "已存为模板", ttlMs: 2000 });
    } catch {
      useToastStore.getState().push({ kind: "error", title: "保存模板失败" });
    }
  };

  const onApply = async (id: string) => {
    try {
      loadGraph(editor, await loadTemplate(id));
      setOpen(false);
    } catch {
      useToastStore.getState().push({ kind: "error", title: "套用模板失败" });
    }
  };

  const onDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteTemplate(id);
    await refresh();
  };

  return (
    <div style={{ position: "relative", pointerEvents: "all" }} onPointerDown={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={toggle}
        data-testid="pro-templates-toggle"
        className="rounded-lg border border-[var(--color-ink)]/15 px-2.5 py-1.5 text-xs font-medium text-[var(--color-ink-soft)] transition hover:bg-[var(--color-paper-deeper)]"
      >
        💾 模板
      </button>
      {open && (
        <div className="absolute right-0 top-9 z-40 w-56 rounded-xl border border-[var(--color-clay)]/20 bg-[var(--color-paper)] p-1.5 shadow-xl">
          <button
            type="button"
            onClick={onSave}
            className="w-full rounded-lg px-2.5 py-1.5 text-left text-xs font-medium text-[var(--color-clay)] hover:bg-[var(--color-paper-deeper)]"
          >
            + 另存当前为模板
          </button>
          <div className="my-1 h-px bg-[var(--color-ink)]/10" />
          {items.length === 0 ? (
            <div className="px-2.5 py-2 text-xs text-[var(--color-ink-soft)]/60">暂无模板</div>
          ) : (
            items.map((t) => (
              <div
                key={t.template_id}
                onClick={() => onApply(t.template_id)}
                className="group flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-1.5 text-xs text-[var(--color-ink-soft)] hover:bg-[var(--color-paper-deeper)]"
              >
                <span className="truncate">{t.name}</span>
                <button
                  type="button"
                  onClick={(e) => onDelete(t.template_id, e)}
                  className="ml-2 shrink-0 text-[var(--color-ink-soft)]/40 hover:text-red-500"
                  title="删除模板"
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
