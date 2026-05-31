import { COPY } from "../../lib/cardCopy";
import { SAMPLE_CASES } from "../../lib/sampleCases";

interface Props {
  onPick: (url: string) => void;
  disabled?: boolean;
  variant?: "block" | "inline";
}

// 「试一条」chip —— 用真实已拆案例(不再按 宝妈/育儿/家庭厨房 等垂类)。多案例→多 chip,
// 可扩展;案例来自 SAMPLE_CASES 配置。
export function SampleUrlChips({ onPick, disabled = false, variant = "block" }: Props) {
  const cases = SAMPLE_CASES;
  if (cases.length === 0) return null;

  return (
    <div className={variant === "block" ? "space-y-2" : ""}>
      {variant === "block" && (
        <p className="text-xs text-stone-500 dark:text-stone-400">{COPY.sample_url_label}</p>
      )}
      <div className="flex flex-wrap gap-2">
        {cases.map((c) => {
          const label = `${COPY.sample_try_prefix} ${c.category}`;
          return (
            <button
              key={c.id}
              type="button"
              disabled={disabled}
              onClick={() => !disabled && onPick(c.source_url)}
              aria-label={label}
              title={c.source_url}
              className={
                "inline-flex items-center gap-1.5 rounded-full border border-stone-300 dark:border-stone-700 bg-white/70 dark:bg-stone-900/70 px-3 py-1.5 text-[12px] text-stone-700 dark:text-stone-300 font-inherit transition-all duration-200 " +
                (disabled
                  ? "opacity-40 cursor-not-allowed"
                  : "hover:border-[#7c2d12]/60 dark:hover:border-[#ea580c]/60 hover:text-[#7c2d12] dark:hover:text-[#ea580c]")
              }
            >
              {c.emoji && <span aria-hidden>{c.emoji}</span>}
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
