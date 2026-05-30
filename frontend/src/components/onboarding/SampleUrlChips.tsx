import { COPY } from "../../lib/cardCopy";
import { SAMPLE_URL_BY_NICHE } from "../../lib/sampleUrls";
import { useNicheStore, type NicheId } from "../../store/nicheStore";

interface Props {
  onPick: (url: string, niche: NicheId) => void;
  disabled?: boolean;
  variant?: "block" | "inline";
}

interface Sample {
  niche: NicheId;
  url: string;
  emoji: string;
  hintKey: "sample_url_hint_baomam" | "sample_url_hint_yuer" | "sample_url_hint_kitchen";
}

// URL 是时长验证过的(见 sampleUrls.ts,与落地页 HotCard 共用同一份),首屏点样本
// 必须能过分析时长闸门 —— 旧的三条曾全部 >180s,点任意一条即报「视频太长」(缺陷 C)。
const SAMPLES: Sample[] = [
  { niche: "baomam_fushi", url: SAMPLE_URL_BY_NICHE.baomam_fushi, emoji: "🍼", hintKey: "sample_url_hint_baomam" },
  { niche: "jiating_chufang", url: SAMPLE_URL_BY_NICHE.jiating_chufang, emoji: "🍳", hintKey: "sample_url_hint_kitchen" },
  { niche: "yuer_richang", url: SAMPLE_URL_BY_NICHE.yuer_richang, emoji: "👶", hintKey: "sample_url_hint_yuer" },
];

export function SampleUrlChips({ onPick, disabled = false, variant = "block" }: Props) {
  const setNiche = useNicheStore((s) => s.setNiche);

  const handleClick = (s: Sample) => {
    if (disabled) return;
    setNiche(s.niche);
    onPick(s.url, s.niche);
  };

  return (
    <div className={variant === "block" ? "space-y-2" : ""}>
      {variant === "block" && (
        <p className="text-xs text-stone-500 dark:text-stone-400">
          {COPY.sample_url_label}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {SAMPLES.map((s) => (
          <button
            key={s.niche}
            type="button"
            disabled={disabled}
            onClick={() => handleClick(s)}
            aria-label={COPY[s.hintKey]}
            title={s.url}
            className={
              "inline-flex items-center gap-1.5 rounded-full border border-stone-300 dark:border-stone-700 bg-white/70 dark:bg-stone-900/70 px-3 py-1.5 text-[12px] text-stone-700 dark:text-stone-300 font-inherit transition-all duration-200 " +
              (disabled
                ? "opacity-40 cursor-not-allowed"
                : "hover:border-[#7c2d12]/60 dark:hover:border-[#ea580c]/60 hover:text-[#7c2d12] dark:hover:text-[#ea580c]")
            }
          >
            <span aria-hidden>{s.emoji}</span>
            <span>{COPY[s.hintKey]}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
