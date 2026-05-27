import { COPY } from "../../lib/cardCopy";
import { NICHE_LABELS, type NicheId } from "../../store/nicheStore";

interface Props {
  onPick: (niche: NicheId) => void;
}

const EMOJI_BY_NICHE: Record<NicheId, string> = {
  baomam_fushi: "🍼",
  yuer_richang: "👶",
  jiating_chufang: "🍳",
};

/**
 * Surfaces after analysis lands but before a rewrite has been requested.
 * Replaces the "改完的版本" section when `script` is empty.
 *
 * Picking a chip calls `onPick(niche)` — App.tsx wires that to
 * `useNicheStore.setNiche(niche) + sendChatMessage("[selected_niche: ...] 改成这个方向")`,
 * which Director picks up in §0.6 and runs `cascade_rewrite`.
 */
export function NicheCTA({ onPick }: Props) {
  const niches: NicheId[] = ["baomam_fushi", "yuer_richang", "jiating_chufang"];

  return (
    <section
      className="mt-8 rounded-2xl border border-[#7c2d12]/20 dark:border-[#ea580c]/30 bg-[#fef7f0]/40 dark:bg-stone-800/40 p-5"
      data-testid="niche-cta"
      aria-label="改写方向选择"
    >
      <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 mb-2 tracking-[-0.01em]">
        {COPY.rewrite_cta_header}
      </h2>
      <p className="text-sm text-stone-600 dark:text-stone-400 mb-4">
        {COPY.rewrite_cta_hint}
      </p>
      <div className="flex flex-wrap gap-2">
        {niches.map((id) => {
          const meta = NICHE_LABELS[id];
          const label = COPY[meta.key];
          return (
            <button
              key={id}
              type="button"
              onClick={() => onPick(id)}
              className="inline-flex items-center gap-2 rounded-full border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 px-4 py-2 text-sm font-medium text-stone-800 dark:text-stone-100 hover:border-[#7c2d12]/50 dark:hover:border-[#ea580c]/60 hover:bg-[#fef7f0] dark:hover:bg-stone-800 transition-colors"
            >
              <span aria-hidden>{EMOJI_BY_NICHE[id]}</span>
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
