import { ImageIcon } from "lucide-react";
import type { Anchor } from "../../lib/anchorApi";

export function AnchorCard({ anchor, onPick }: { anchor: Anchor; onPick?: (anchor: Anchor) => void }) {
  return (
    <button
      type="button"
      draggable
      onDragStart={(event) => event.dataTransfer.setData("application/json", JSON.stringify(anchor))}
      onClick={() => onPick?.(anchor)}
      className="w-full text-left rounded-xl border border-stone-200 bg-white p-2 hover:bg-stone-50 cursor-grab"
    >
      <div className="aspect-square rounded-lg bg-stone-100 flex items-center justify-center overflow-hidden">
        {anchor.image_url ? <img src={anchor.image_url} alt="" className="h-full w-full object-cover" /> : <ImageIcon className="h-6 w-6 text-stone-300" />}
      </div>
      <div className="mt-2 text-sm text-stone-700 truncate">{anchor.label}</div>
    </button>
  );
}
