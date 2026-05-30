import { COPY } from "../../lib/cardCopy";
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

// 首屏「试一条」样本必须落在分析时长闸门内(5s–180s,后端 analysis_service
// _enforce_duration_guard)。2026-05-30 founder 实测发现旧的三条样本全部 >180s
// (baomam 203.9s / yuer 255.2s / kitchen 393.7s)—— 新用户点任意一条都吃
// 「视频太长」错误,首屏直接劝退(缺陷 C)。下面三条均经 prod resolver 实测时长,
// 优选 15-90s 甜区。换样本前务必重测时长(抖音视频会被删/替换)。
const SAMPLES: Sample[] = [
  // 62.6s · 「添加辅食 #宝宝辅食 #厨房小白 #只有宝妈才懂吧」自嘲钩子
  { niche: "baomam_fushi", url: "https://www.douyin.com/video/7616954826602428411", emoji: "🍼", hintKey: "sample_url_hint_baomam" },
  // 58.6s · 家庭厨房调味场景
  { niche: "jiating_chufang", url: "https://www.douyin.com/video/7296430710208941322", emoji: "🍳", hintKey: "sample_url_hint_kitchen" },
  // 126s · 「当妈以后才发现,最累的不是熬夜,是没人懂」情绪共鸣
  { niche: "yuer_richang", url: "https://www.douyin.com/video/7610100974662207717", emoji: "👶", hintKey: "sample_url_hint_yuer" },
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
