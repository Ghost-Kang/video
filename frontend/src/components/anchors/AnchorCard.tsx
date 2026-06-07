import { ImageIcon } from "lucide-react";
import type { Anchor } from "../../lib/anchorApi";

export function AnchorCard({ anchor, onPick }: { anchor: Anchor; onPick?: (anchor: Anchor) => void }) {
  const showPill = anchor.reuse_count > 0;
  return (
    <button
      type="button"
      draggable
      onDragStart={(event) => event.dataTransfer.setData("application/json", JSON.stringify(anchor))}
      onClick={() => onPick?.(anchor)}
      className="w-full text-left rounded-xl border border-stone-200 bg-white p-2 hover:bg-stone-50 cursor-grab dark:border-stone-700 dark:bg-stone-800 dark:hover:bg-stone-700"
    >
      <div className="relative aspect-square rounded-lg bg-stone-100 flex items-center justify-center overflow-hidden dark:bg-stone-700">
        {anchor.image_url ? <img src={anchor.image_url} alt="" className="h-full w-full object-cover" /> : <ImageIcon className="h-6 w-6 text-stone-300 dark:text-stone-500" />}
        {showPill && (
          <span
            className="absolute top-1 right-1 rounded-full bg-stone-900/80 px-1.5 py-0.5 text-[10px] font-medium text-white"
            title={`已用 ${anchor.reuse_count} 次`}
            aria-label={`已用 ${anchor.reuse_count} 次`}
          >
            已用 {anchor.reuse_count}
          </span>
        )}
      </div>
      <div className="mt-2 text-sm text-stone-700 truncate dark:text-stone-200">{anchor.label}</div>
    </button>
  );
}
