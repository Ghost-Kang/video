import { useEffect, useRef, useState } from "react";
import { ArrowRight, Play } from "lucide-react";
import type { SampleCase } from "../../lib/sampleCases";
import { COPY } from "../../lib/cardCopy";

interface Props {
  sample: SampleCase;
  onPick: (c: SampleCase) => void;
}

const ADVANCE_MS = 3800;

// 一个真实案例 → 逐幕视频轮播。活的展示「能拆出什么」:逐幕 clip 自动轮播(静音循环),
// 底部叠当前幕的主题/情绪/一句话;点开进真实完整分析。可扩展(slides 来自配置)。
export function CaseShowcase({ sample, onPick }: Props) {
  const slides = sample.slides ?? [];
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);

  const reduce =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 自动轮播(reduced-motion / hover 暂停)。
  const timer = useRef<number | null>(null);
  useEffect(() => {
    if (reduce || paused || slides.length <= 1) return;
    timer.current = window.setTimeout(
      () => setActive((i) => (i + 1) % slides.length),
      ADVANCE_MS,
    );
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    };
  }, [active, paused, reduce, slides.length]);

  if (slides.length === 0) return null;
  const cur = slides[active];

  return (
    <div
      className="mx-auto max-w-[300px] cursor-pointer"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onClick={() => onPick(sample)}
      data-testid="case-showcase"
    >
      <div className="hover-glow overflow-hidden rounded-2xl border border-stone-200/60 bg-white/70 backdrop-blur-sm dark:border-stone-800/60 dark:bg-stone-900/55">
        {/* 头:品类 + 真实拆解 */}
        <div className={`flex items-center justify-between px-4 py-2.5 ${sample.gradient ?? ""}`}>
          <span className="font-serif-cn text-[15px] text-stone-900/90">
            {sample.emoji ? `${sample.emoji} ` : ""}
            {sample.category}
          </span>
          <span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-medium tracking-wide text-[#7c2d12] backdrop-blur-sm">
            {COPY.sample_case_tag}
          </span>
        </div>

        {/* 视频帧(竖屏) + 底部叠当前幕 */}
        <div className="relative aspect-[3/4] w-full overflow-hidden bg-stone-950">
          {reduce ? (
            <img src={cur.poster} alt="" className="h-full w-full object-cover" />
          ) : (
            <video
              key={active}
              src={cur.clip}
              poster={cur.poster}
              muted
              loop
              autoPlay
              playsInline
              preload="none"
              className="h-full w-full object-cover"
            />
          )}

          {/* 底部信息叠层 */}
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/30 to-transparent px-3.5 pb-3 pt-8 text-white">
            <div className="mb-0.5 flex items-center gap-2">
              <span className="num-tech text-[11px] text-white/70">
                {active + 1} / {slides.length}
              </span>
              <span className="font-serif-cn text-[14px]">{cur.theme}</span>
              {cur.emotion && (
                <span className="ml-auto rounded-full bg-white/15 px-1.5 py-0.5 text-[10px] text-white/90 backdrop-blur-sm">
                  {cur.emotion}
                </span>
              )}
            </div>
            <p className="text-[12px] leading-[1.5] text-white/85">{cur.note}</p>
          </div>

          {/* 进度点 */}
          <div className="absolute inset-x-0 top-2.5 flex justify-center gap-1">
            {slides.map((_, i) => (
              <button
                key={i}
                type="button"
                aria-label={`第 ${i + 1} 幕`}
                onClick={(e) => {
                  e.stopPropagation();
                  setActive(i);
                }}
                className={`h-1 rounded-full transition-all ${
                  i === active ? "w-5 bg-white" : "w-1.5 bg-white/45 hover:bg-white/70"
                }`}
              />
            ))}
          </div>
        </div>

        {/* 钩子洞察 + CTA */}
        <div className="px-4 py-3">
          <div className="mb-1 text-[11px] font-semibold text-[#7c2d12] dark:text-[#ea580c]">
            🪝 {COPY.sample_case_hook}
          </div>
          <p className="mb-2.5 text-[12.5px] leading-[1.6] text-stone-700 dark:text-stone-300">
            {sample.hook}
          </p>
          <div className="flex items-center gap-1 text-[12px] font-medium text-[#7c2d12] dark:text-[#ea580c]">
            <Play className="h-3 w-3 fill-current" />
            {COPY.sample_case_cta}
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </div>
  );
}
