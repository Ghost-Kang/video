import { Clock } from "lucide-react";
import { COPY } from "../../lib/cardCopy";
import { useInView } from "../../hooks/useInView";

const MIN = 5;
const MAX = 180;
const LO = 15;
const HI = 90;
const pct = (s: number) => ((s - MIN) / (MAX - MIN)) * 100;

// 时长甜蜜点 —— 暖色 mini-meter,取代没人看的灰脚注。一眼可见 + 活感:
//   进入视口时甜区从左「长出来」+ 一次发光脉冲;之后一束暖光持续流过甜区,⭐ 轻浮动。
export function DurationSweetSpot() {
  const { ref, inView } = useInView<HTMLDivElement>();
  const marks = [MIN, LO, HI, MAX];
  const bandLeft = pct(LO);
  const bandWidthPct = pct(HI) - pct(LO);

  return (
    <div
      ref={ref}
      className="mt-3 rounded-xl border border-stone-200/60 bg-white/55 px-3.5 py-2.5 backdrop-blur-sm dark:border-stone-700/50 dark:bg-stone-900/40"
    >
      <div className="mb-2 flex items-center gap-1.5 text-[12px] font-medium text-stone-700 dark:text-stone-200">
        <Clock className="h-3.5 w-3.5 text-[#7c2d12] dark:text-[#ea580c]" />
        {COPY.duration_chip_title}
      </div>

      {/* 刻度条:甜区高亮 + 流光 */}
      <div className="relative h-1.5 rounded-full bg-stone-200/80 dark:bg-stone-700/60">
        <div
          className={`absolute inset-y-0 origin-left overflow-hidden rounded-full bg-gradient-to-r from-amber-400 to-[#ea580c] ${
            inView ? "anim-draw-line anim-glow-pulse" : "scale-x-0"
          }`}
          style={{ left: `${bandLeft}%`, width: `${bandWidthPct}%` }}
        >
          {/* 持续流过的一束暖光 */}
          {inView && (
            <span className="anim-meter-flow absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/70 to-transparent dark:via-white/40" />
          )}
        </div>
      </div>

      {/* 刻度标 */}
      <div className="relative mt-1.5 h-3.5">
        {marks.map((s) => (
          <span
            key={s}
            className={`num-tech absolute top-0 text-[10px] ${
              s === LO || s === HI
                ? "font-medium text-[#7c2d12] dark:text-[#ea580c]"
                : "text-stone-400 dark:text-stone-500"
            }`}
            style={{
              left: `${pct(s)}%`,
              transform: s === MIN ? "translateX(0)" : s === MAX ? "translateX(-100%)" : "translateX(-50%)",
            }}
          >
            {s}s
          </span>
        ))}
        {/* 甜区标记 ⭐ 浮动 */}
        <span
          className={`absolute top-0 text-[10px] font-medium text-[#7c2d12] dark:text-[#ea580c] ${
            inView ? "anim-bob" : "-translate-x-1/2"
          }`}
          style={{ left: `${(pct(LO) + pct(HI)) / 2}%` }}
        >
          ⭐ {COPY.duration_chip_best}
        </span>
      </div>

      <p className="mt-2.5 text-[11px] leading-[1.5] text-stone-500 dark:text-stone-400">
        {COPY.duration_chip_sub}
      </p>
    </div>
  );
}
