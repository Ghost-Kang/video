import { useEffect, useState } from "react";
import { COPY } from "../../lib/cardCopy";
import { useAnchors, type AnchorSort } from "../../hooks/useAnchors";
import { AnchorCard } from "./AnchorCard";
import { reuseAnchor, type Anchor } from "../../lib/anchorApi";
import { useToastStore } from "../../store/toastStore";

const SORT_STORAGE_KEY = "anchor_sort_preference";

function readStoredSort(): AnchorSort {
  if (typeof window === "undefined") return "reuse";
  const stored = window.localStorage.getItem(SORT_STORAGE_KEY);
  return stored === "recency" ? "recency" : "reuse";
}

export function AnchorSidebar() {
  const [open, setOpen] = useState(true);
  const [sortBy, setSortBy] = useState<AnchorSort>(() => readStoredSort());
  const characters = useAnchors("character", sortBy);
  const scenes = useAnchors("scene", sortBy);
  const pushToast = useToastStore((s) => s.push);

  // H4(审计 2026-06-06):此前 onPick 只 console.log —— 护城河(跨镜角色/场景一致性)
  // 的复用按钮是死的。接通后端 reuseAnchor(记 reuse_count + ANCHOR_REUSED 信号),并给
  // 用户明确下一步反馈。画布复用语义仍由 Director 执行,所以引导用户在对话里点名复用。
  const handlePick = (anchor: Anchor) => {
    void reuseAnchor(anchor.id, {
      user_id: "default",
      reused_in_run_id: "canvas",
      reused_in_shot_index: 0,
    });
    pushToast({
      kind: "info",
      title: `已选用「${anchor.label}」`,
      body: `在对话里告诉导演「用我的${anchor.label}」,跨镜保持一致。`,
    });
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SORT_STORAGE_KEY, sortBy);
    }
  }, [sortBy]);

  if (!open) {
    return (
      <button type="button" className="hidden md:block h-10 rounded-xl border border-stone-200 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200" onClick={() => setOpen(true)}>
        {COPY.anchor_picker_title}
      </button>
    );
  }

  const pillBase = "rounded-full px-3 py-1 text-xs transition-colors";
  const active = "bg-stone-900 text-white dark:bg-stone-200 dark:text-stone-900";
  const inactive = "bg-stone-100 text-stone-600 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700";

  return (
    <aside className="hidden md:block w-[240px] shrink-0 rounded-2xl bg-white shadow-sm border border-stone-200 p-4 h-fit dark:bg-stone-900 dark:border-stone-700">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-medium text-stone-900 dark:text-stone-100">{COPY.anchor_picker_title}</h2>
        <button type="button" className="text-stone-400 hover:text-stone-700 dark:text-stone-500 dark:hover:text-stone-300" onClick={() => setOpen(false)} aria-label="收起">
          x
        </button>
      </div>
      <div className="flex gap-2 mb-4" role="radiogroup" aria-label="排序方式">
        <button
          type="button"
          role="radio"
          aria-checked={sortBy === "reuse"}
          className={`${pillBase} ${sortBy === "reuse" ? active : inactive}`}
          onClick={() => setSortBy("reuse")}
        >
          按使用次数
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={sortBy === "recency"}
          className={`${pillBase} ${sortBy === "recency" ? active : inactive}`}
          onClick={() => setSortBy("recency")}
        >
          按时间
        </button>
      </div>
      <section className="mb-5">
        <h3 className="text-sm text-stone-500 mb-2 dark:text-stone-400">你的角色</h3>
        <div className="grid grid-cols-2 gap-2">
          {characters.anchors.map((anchor) => <AnchorCard key={anchor.id} anchor={anchor} onPick={handlePick} />)}
        </div>
      </section>
      <section>
        <h3 className="text-sm text-stone-500 mb-2 dark:text-stone-400">你的场景</h3>
        <div className="grid grid-cols-2 gap-2">
          {scenes.anchors.map((anchor) => <AnchorCard key={anchor.id} anchor={anchor} onPick={handlePick} />)}
        </div>
      </section>
    </aside>
  );
}
