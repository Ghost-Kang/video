import { Clock } from "lucide-react";
import { COPY } from "../../lib/cardCopy";

const MIN = 5;
const MAX = 180;
const LO = 15;
const HI = 90;
const pct = (s: number) => ((s - MIN) / (MAX - MIN)) * 100;

// 时长甜蜜点 —— 把「5s 硬下限 / 15–90s 甜区 / 180s 硬上限」可视化成一个暖色 mini-meter,
// 取代原来没人看的灰色脚注。甜区入场做一次暖色发光脉冲吸睛。
export function DurationSweetSpot() {
  const marks = [MIN, LO, HI, MAX];
  return (
    <div className="mt-3 rounded-xl border border-stone-200/60 bg-white/55 px-3.5 py-2.5 backdrop-blur-sm dark:border-stone-700/50 dark:bg-stone-900/40">
      <div className="mb-2 flex items-center gap-1.5 text-[12px] font-medium text-stone-700 dark:text-stone-200">
        <Clock className="h-3.5 w-3.5 text-[#7c2d12] dark:text-[#ea580c]" />
        {COPY.duration_chip_title}
      </div>

      {/* 刻度条:甜区高亮 */}
      <div className="relative h-1.5 rounded-full bg-stone-200/80 dark:bg-stone-700/60">
        <div
          className="anim-glow-pulse absolute inset-y-0 rounded-full bg-gradient-to-r from-amber-400 to-[#ea580c]"
          style={{ left: `${pct(LO)}%`, right: `${100 - pct(HI)}%` }}
        />
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
        {/* 甜区标记 */}
        <span
          className="absolute top-0 -translate-x-1/2 text-[10px] font-medium text-[#7c2d12]/70 dark:text-[#ea580c]/70"
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
