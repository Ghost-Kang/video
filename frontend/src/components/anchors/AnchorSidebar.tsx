import { useState } from "react";
import { COPY } from "../../lib/cardCopy";
import { useAnchors } from "../../hooks/useAnchors";
import { AnchorCard } from "./AnchorCard";

export function AnchorSidebar() {
  const [open, setOpen] = useState(true);
  const characters = useAnchors("character");
  const scenes = useAnchors("scene");

  if (!open) {
    return (
      <button type="button" className="hidden md:block h-10 rounded-xl border border-stone-200 bg-white px-3 text-sm" onClick={() => setOpen(true)}>
        {COPY.anchor_picker_title}
      </button>
    );
  }

  return (
    <aside className="hidden md:block w-[240px] shrink-0 rounded-2xl bg-white shadow-sm border border-stone-200 p-4 h-fit">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-stone-900">{COPY.anchor_picker_title}</h2>
        <button type="button" className="text-stone-400 hover:text-stone-700" onClick={() => setOpen(false)} aria-label="收起">
          x
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
