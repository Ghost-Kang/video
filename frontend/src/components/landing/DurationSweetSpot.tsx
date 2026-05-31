import { Clock } from "lucide-react";
import { COPY } from "../../lib/cardCopy";
import { useInView } from "../../hooks/useInView";

const MIN = 5;
const MAX = 180;
const LO = 15;
const HI = 90;
const pct = (s: number) => ((s - MIN) / (MAX - MIN)) * 100;

// 时长甜蜜点 —— 暖色 mini-meter,取代灰脚注。视觉震撼 + 一直动:
//   甜区渐变持续流动 + 脉冲发光 + 一束暖光流过 + 中心涟漪扩散 + 锚点高亮;
//   「⭐ 拆得最透」用流光渐变文字 + 浮动,文字本身是视觉奇观。
export function DurationSweetSpot() {
  const { ref, inView } = useInView<HTMLDivElement>();
  const marks = [MIN, LO, HI, MAX];
  const bandLeft = pct(LO);
  const bandWidth = pct(HI) - pct(LO);
  const sweetCenter = (pct(LO) + pct(HI)) / 2;

  return (
    <div
      ref={ref}
      className="mt-3 overflow-hidden rounded-xl border border-[#7c2d12]/15 bg-white/60 px-3.5 pb-2.5 pt-2.5 backdrop-blur-sm dark:border-[#ea580c]/20 dark:bg-stone-900/45"
    >
      <div className="mb-1 flex items-center gap-1.5 text-[12px] font-semibold text-stone-700 dark:text-stone-200">
        <Clock className={`h-3.5 w-3.5 text-[#7c2d12] dark:text-[#ea580c] ${inView ? "anim-icon-breathe" : ""}`} />
        {COPY.duration_chip_title}
      </div>

      {/* 浮动「⭐ 拆得最透」—— 流光渐变文字 */}
      <div className="relative h-5">
        <span
          className={`absolute whitespace-nowrap text-[12px] font-bold ${inView ? "anim-bob" : "-translate-x-1/2"}`}
          style={{ left: `${sweetCenter}%` }}
        >
          <span className="text-shimmer-clay">⭐ {COPY.duration_chip_best}</span>
        </span>
      </div>

      {/* 刻度条 */}
      <div className="relative h-2.5 rounded-full bg-stone-200/90 dark:bg-stone-700/60">
        {/* 甜区:渐变流动 + 脉冲发光 */}
        <div
          className={`absolute inset-y-0 overflow-hidden rounded-full bg-gradient-to-r from-amber-300 via-[#ea580c] to-amber-300 ${
            inView ? "anim-sweet-band" : ""
          }`}
          style={{ left: `${bandLeft}%`, width: `${bandWidth}%` }}
        >
          {/* 持续流过的一束暖光 */}
          {inView && (
            <span className="anim-meter-flow absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/85 to-transparent" />
          )}
        </div>

        {/* 甜区中心:涟漪扩散 + 实心锚点 */}
        {inView && (
          <span
            className="anim-sweet-ripple absolute top-1/2 h-3 w-3 rounded-full bg-[#ea580c]/50"
            style={{ left: `${sweetCenter}%` }}
            aria-hidden
          />
        )}
        <span
          className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-[0_0_8px_2px_rgba(234,88,12,0.7)] ring-2 ring-[#ea580c]"
          style={{ left: `${sweetCenter}%` }}
          aria-hidden
        />
      </div>

      {/* 刻度标 */}
      <div className="relative mt-2 h-3.5">
        {marks.map((s) => (
          <span
            key={s}
            className={`num-tech absolute top-0 text-[10px] ${
              s === LO || s === HI
                ? "font-bold text-[#7c2d12] dark:text-[#ea580c]"
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
      </div>

      <p className="mt-2 text-[11px] leading-[1.5] text-stone-500 dark:text-stone-400">
        {COPY.duration_chip_sub}
      </p>
    </div>
  );
}
