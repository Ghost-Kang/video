import { useState } from "react";
import { useEditor, useValue } from "tldraw";
import { loadGraph, pronodeShapes } from "./graphIO";
import { ProApiError, proErrorTitle, seedFromTheme } from "./proExecution";
import { useToastStore } from "../store/toastStore";

/** 空白画布中央的「主题→创作」入口(plan 创作流愿景)。画布有节点时自动隐藏。
 *  提交 → 后端 Doubao 从主题生成脚本+分镜 → loadGraph 铺满画布(脚本卡 + 每分镜 提示词→图→视频→预览)。 */
export function ProThemeInput({ threadId, ready }: { threadId: string; ready: boolean }) {
  const editor = useEditor();
  const [theme, setTheme] = useState("");
  const [busy, setBusy] = useState(false);
  const empty = useValue("pro-empty-canvas", () => pronodeShapes(editor).length === 0, [editor]);

  if (!ready || !empty) return null;

  const go = async () => {
    const t = theme.trim();
    if (!t || busy) return;
    setBusy(true);
    try {
      loadGraph(editor, await seedFromTheme(t, threadId));
    } catch (e) {
      const err = e as ProApiError;
      useToastStore.getState().push({ kind: "error", title: proErrorTitle(err.code), body: err.detail });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none", zIndex: 20 }}
    >
      <div
        onPointerDown={(e) => e.stopPropagation()}
        style={{ pointerEvents: "all" }}
        className="w-[min(92vw,520px)] rounded-2xl border border-[var(--color-clay)]/20 bg-[var(--color-paper)]/95 p-6 text-center shadow-2xl backdrop-blur"
        data-testid="pro-theme-input"
      >
        <h2 className="text-lg font-semibold text-[var(--color-ink)]">⚡ 用主题开始创作</h2>
        <p className="mx-auto mt-1 max-w-[40ch] text-sm text-[var(--color-ink-soft)]">
          输入你想创作的短视频主题,自动生成「脚本卡 + 每个分镜(提示词→生成图→图生视频→预览)」,全部可改、可增删、可连线。
        </p>
        <textarea
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) go();
          }}
          rows={2}
          placeholder="例如:3 分钟教新手做宝宝辅食南瓜泥,温馨厨房"
          disabled={busy}
          className="mt-4 w-full resize-none rounded-xl border border-[var(--color-ink)]/15 bg-white px-3 py-2.5 text-sm outline-none focus:border-[var(--color-clay)]/50"
        />
        <button
          type="button"
          onClick={go}
          disabled={busy || !theme.trim()}
          data-testid="pro-theme-submit"
          className="mt-3 w-full rounded-xl bg-[var(--color-clay)] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--color-clay-soft)] disabled:opacity-50"
        >
          {busy ? "正在生成脚本与分镜…" : "生成脚本与分镜"}
        </button>
        <p className="mt-2 text-[11px] text-[var(--color-ink-soft)]/60">⌘/Ctrl + Enter 快捷生成 · 生成后点 ▶运行 出图/出片</p>
      </div>
    </div>
  );
}
