import { useState } from "react";
import { LOW_CONFIDENCE_THRESHOLD } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";

export function ConfidenceBanner({ confidence }: { confidence: number }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed || confidence >= LOW_CONFIDENCE_THRESHOLD) return null;
  return (
    <div className="flex items-center justify-between bg-amber-50 dark:bg-amber-950/30 border-l-4 border-amber-400 dark:border-amber-500 px-4 py-2 text-sm text-amber-900 dark:text-amber-200">
      <span>{COPY.low_confidence_banner}</span>
      <button type="button" className="text-amber-700 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-200" onClick={() => setDismissed(true)} aria-label="关闭">
        ×
      </button>
    </div>
  );
}
