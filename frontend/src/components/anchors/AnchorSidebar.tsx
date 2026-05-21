import { useEffect, useState } from "react";
import { COPY } from "../../lib/cardCopy";
import { useAnchors, type AnchorSort } from "../../hooks/useAnchors";
import { AnchorCard } from "./AnchorCard";

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

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SORT_STORAGE_KEY, sortBy);
    }
  }, [sortBy]);

  if (!open) {
    return (
      <button type="button" className="hidden md:block h-10 rounded-xl border border-stone-200 bg-white px-3 text-sm" onClick={() => setOpen(true)}>
        {COPY.anchor_picker_title}
      </button>
    );
  }

  const pillBase = "rounded-full px-3 py-1 text-xs transition-colors";
  const active = "bg-stone-900 text-white";
  const inactive = "bg-stone-100 text-stone-600 hover:bg-stone-200";

  return (
    <aside className="hidden md:block w-[240px] shrink-0 rounded-2xl bg-white shadow-sm border border-stone-200 p-4 h-fit">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-medium text-stone-900">{COPY.anchor_picker_title}</h2>
        <button type="button" className="text-stone-400 hover:text-stone-700" onClick={() => setOpen(false)} aria-label="收起">
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
        <h3 className="text-sm text-stone-500 mb-2">你的角色</h3>
        <div className="grid grid-cols-2 gap-2">
          {characters.anchors.map((anchor) => <AnchorCard key={anchor.id} anchor={anchor} onPick={() => console.log("reuse intent", anchor.id)} />)}
        </div>
      </section>
      <section>
        <h3 className="text-sm text-stone-500 mb-2">你的场景</h3>
        <div className="grid grid-cols-2 gap-2">
          {scenes.anchors.map((anchor) => <AnchorCard key={anchor.id} anchor={anchor} onPick={() => console.log("reuse intent", anchor.id)} />)}
        </div>
      </section>
    </aside>
  );
}
