import { useState } from "react";
import type { Warning_ } from "../../types/cascade";
import { RECOVERY_HINTS } from "../../lib/recoveryHints";

export function WarningChips({ warnings }: { warnings: Warning_[] }) {
  const [expanded, setExpanded] = useState(false);
  const visibleWarnings = warnings.filter((warning) => warning.severity !== "info");
  if (visibleWarnings.length === 0) return null;
  const shown = expanded ? visibleWarnings : visibleWarnings.slice(0, 2);
  const hidden = visibleWarnings.length - shown.length;

  return (
    <div className="flex flex-wrap gap-2">
      {shown.map((warning, index) => (
        <WarningChip key={`${warning.code}-${index}`} warning={warning} />
      ))}
      {hidden > 0 && (
        <button
          type="button"
          className="inline-flex items-center px-2 py-1 rounded-full bg-stone-100 text-stone-700 text-xs"
          onClick={() => setExpanded(true)}
        >
          +{hidden} more
        </button>
      )}
    </div>
  );
}

export function WarningChip({ warning }: { warning: Warning_ }) {
  if (warning.severity === "info") return null;
  const hint = RECOVERY_HINTS[warning.code];
  if (!hint) return null;
  const tone = warning.severity === "error" ? "bg-red-50 text-red-800" : "bg-amber-50 text-amber-800";
  return <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full ${tone} text-xs`}>{hint}</span>;
}
