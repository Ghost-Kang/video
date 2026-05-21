import type { Anchor, AnchorKind } from "../../lib/anchorApi";
import { COPY } from "../../lib/cardCopy";
import { useAnchors } from "../../hooks/useAnchors";
import { AnchorCard } from "./AnchorCard";

export function AnchorPickerModal({
  kind,
  onClose,
  onPick,
}: {
  kind: AnchorKind;
  onClose: () => void;
  onPick: (anchor: Anchor) => void;
}) {
  const { anchors } = useAnchors(kind);
  return (
    <div className="fixed inset-0 z-40 bg-black/20 flex items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-stone-900">{COPY.anchor_picker_title}</h2>
          <button type="button" onClick={onClose} className="text-stone-500">x</button>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {anchors.map((anchor) => (
            <AnchorCard key={anchor.id} anchor={anchor} onPick={onPick} />
          ))}
        </div>
      </div>
    </div>
  );
}
