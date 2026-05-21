import { LayoutGrid, GitBranch } from "lucide-react";
import { COPY } from "../lib/cardCopy";

interface Props {
  isProView: boolean;
  onToggle: () => void;
  hidden?: boolean;
}

export function ProViewToggle({ isProView, onToggle, hidden }: Props) {
  if (hidden) return null;

  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-50 transition-colors"
      title={isProView ? COPY.card_view_label : COPY.pro_view_label}
    >
      {isProView ? (
        <>
          <LayoutGrid className="h-3.5 w-3.5" aria-hidden />
          {COPY.card_view_label}
        </>
      ) : (
        <>
          <GitBranch className="h-3.5 w-3.5" aria-hidden />
          {COPY.pro_view_label}
        </>
      )}
    </button>
  );
}
