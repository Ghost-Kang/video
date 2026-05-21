import { useState } from "react";
import { LOW_CONFIDENCE_THRESHOLD } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";

export function ConfidenceBanner({ confidence }: { confidence: number }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed || confidence >= LOW_CONFIDENCE_THRESHOLD) return null;
  return (
    <div className="flex items-center justify-between bg-stone-100 border-l-4 border-stone-400 px-4 py-2 text-sm text-stone-700">
      <span>{COPY.low_confidence_banner}</span>
      <button type="button" className="text-stone-500 hover:text-stone-900" onClick={() => setDismissed(true)} aria-label="关闭">
        x
      </button>
    </div>
  );
}
