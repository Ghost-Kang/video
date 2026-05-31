import type { CascadeAnalysisContract } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";
import { useInView } from "../../hooks/useInView";
import { useCountUp } from "../../hooks/useCountUp";

interface Props {
  analysis: CascadeAnalysisContract;
}

// 数据条 — 暖色科技:三个关键数字(镜头 / 时长 / 把握)滚动计数入场,玻璃拟态 +
// 等宽数字,给结果页一眼「数据感 / 科技感」。
export function AnalysisStatStrip({ analysis }: Props) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const scenes = useCountUp(analysis.scenes.length, { start: inView, duration: 650 });
  const duration = useCountUp(Math.max(0, Math.round(analysis.duration_s)), {
    start: inView,
    duration: 900,
  });
  const confidence = useCountUp(Math.round((analysis.confidence ?? 0) * 100), {
    start: inView,
    duration: 1000,
  });

  const items = [
    { value: `${scenes}`, label: COPY.stat_scenes },
    { value: `${duration}`, label: COPY.stat_duration, unit: COPY.stat_duration_unit },
    { value: `${confidence}`, label: COPY.stat_confidence, unit: "%" },
  ];

  return (
    <div ref={ref} className="grid grid-cols-3 gap-2.5" data-testid="analysis-stat-strip">
      {items.map((it) => (
        <div
          key={it.label}
          className="glass glow-warm relative flex flex-col items-center overflow-hidden rounded-xl py-3"
        >
          <div className="flex items-baseline gap-0.5">
            <span className="num-tech text-2xl font-semibold leading-none text-[#7c2d12] dark:text-[#ea580c]">
              {it.value}
            </span>
            {it.unit && (
              <span className="num-tech text-[12px] font-medium text-[#7c2d12]/70 dark:text-[#ea580c]/70">
                {it.unit}
              </span>
            )}
          </div>
          <span className="mt-1 text-[11px] tracking-wide text-stone-500 dark:text-stone-400">
            {it.label}
          </span>
        </div>
      ))}
    </div>
  );
}
