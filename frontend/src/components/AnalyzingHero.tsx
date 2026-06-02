import { useEffect, useRef, useState } from "react";
import type { SampleCase } from "../lib/sampleCases";
import { COPY } from "../lib/cardCopy";
import { AnalysisProgress } from "./chat/AnalysisProgress";

const SCAN_ADVANCE_MS = 3200;

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

interface Props {
  /** 从 CaseShowcase 透传的「用户刚点的那条」素材;粘陌生链接时为空 → 通用骨架。 */
  caseData?: SampleCase | null;
  thinking: string[];
}

/**
 * 分析中主画面沉浸态 —— 取代旧的静态「①粘链接 ②看拆解」说明卡。
 *
 * 把「用户刚点的那条」连续地带进等待:
 *  - 有案例素材:封面逐幕轮播 + 扫描线 + 逐幕进度点 + 已拆出的钩子(让等待变预热阅读)
 *  - 无案例素材(粘陌生链接):退化为通用暖色扫描骨架
 *
 * 两种情况都内嵌 <AnalysisProgress> —— 它是分析中**唯一**的进度实例
 * (含阶段 + 百分比 + 95% 逃生),底部 dock 已降级为轻提示,避免 ticker/pin-escape
 * 副作用重复。reduced-motion 下停止自动轮播/扫描线/脉冲,只保留静态封面 + 文本 + 进度。
 */
export function AnalyzingHero({ caseData, thinking }: Props) {
  const slides = caseData?.slides ?? [];
  const reduced = prefersReducedMotion();
  const [active, setActive] = useState(0);

  // 逐幕扫描:沿 slides 自动推进 active(reduced / 单幕 不推进)。
  const timer = useRef<number | null>(null);
  useEffect(() => {
    if (reduced || slides.length <= 1) return;
    timer.current = window.setTimeout(
      () => setActive((i) => (i + 1) % slides.length),
      SCAN_ADVANCE_MS,
    );
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    };
  }, [active, reduced, slides.length]);

  const hasSlides = slides.length > 0;
  const cur = hasSlides ? slides[Math.min(active, slides.length - 1)] : null;

  return (
    <main
      className="relative flex-1 overflow-y-auto bg-transparent p-4 md:p-6"
      data-testid="analyzing-hero"
    >
      {/* 暖色科技背景层:细网格 + 顶部柔光 */}
      <div
        className="pointer-events-none absolute inset-0 tech-grid opacity-[0.5] dark:opacity-[0.6]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-64 opacity-70 dark:opacity-60"
        aria-hidden
        style={{
          background:
            "radial-gradient(60% 100% at 50% 0%, rgba(234,88,12,0.10), transparent 70%)",
        }}
      />

      <div className="relative mx-auto w-full max-w-[520px] space-y-4 pt-2 pb-12">
        {/* 标题 + 「逐幕扫描中」状态点 */}
        <header className="text-center anim-fade-up">
          <div className="mb-2 inline-flex items-center gap-2 text-[12px] text-[#7c2d12] dark:text-[#ea580c]">
            <span className="relative inline-flex h-1.5 w-1.5">
              <span className="absolute inset-0 rounded-full bg-[#ea580c] anim-pulse-ring" />
              <span className="relative h-1.5 w-1.5 rounded-full bg-[#ea580c]" />
            </span>
            {COPY.analyzing_hero_scanning}
          </div>
          <h1
            className="font-serif-cn text-xl md:text-2xl text-stone-900 dark:text-stone-50 tracking-[-0.02em]"
            data-testid="analyzing-hero-title"
          >
            {caseData ? COPY.analyzing_hero_title_case : COPY.analyzing_hero_title_generic}
          </h1>
          <p className="mt-2 text-[13px] leading-[1.7] text-stone-500 dark:text-stone-400">
            {COPY.analyzing_hero_subtitle}
          </p>
        </header>

        {/* 有案例素材 → 逐幕封面轮播 + 扫描线 + 进度点 + 当前幕叠层 */}
        {cur && (
          <div
            className="relative mx-auto max-w-[260px] overflow-hidden rounded-2xl border border-[#7c2d12]/30 dark:border-[#ea580c]/40 glow-warm"
            data-testid="analyzing-hero-cover"
          >
            <div className="relative aspect-[3/4] w-full overflow-hidden bg-stone-950">
              {reduced ? (
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
              {/* 扫描线(reduced 下被 index.css 媒体查询静音) */}
              <span
                className="tech-topline pointer-events-none absolute inset-x-0 top-0 h-[3px]"
                aria-hidden
              />
              {/* 逐幕进度点:已扫亮 / 当前 / 未到 */}
              <div className="absolute inset-x-0 top-2.5 flex justify-center gap-1">
                {slides.map((_, i) => (
                  <span
                    key={i}
                    className={`h-1 rounded-full transition-all ${
                      i === active
                        ? "w-5 bg-white"
                        : i < active
                          ? "w-1.5 bg-white/70"
                          : "w-1.5 bg-white/35"
                    }`}
                    aria-hidden
                  />
                ))}
              </div>
              {/* 当前幕叠层 */}
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/30 to-transparent px-3.5 pb-3 pt-8 text-white">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="num-tech text-[11px] text-white/70">
                    {COPY.analyzing_hero_scene_prefix}
                    {active + 1}
                    {COPY.analyzing_hero_scene_suffix} · {active + 1}/{slides.length}
                  </span>
                  {cur.emotion && (
                    <span className="ml-auto rounded-full bg-white/15 px-1.5 py-0.5 text-[10px] text-white/90 backdrop-blur-sm">
                      {cur.emotion}
                    </span>
                  )}
                </div>
                <p className="font-serif-cn text-[14px]">{cur.theme}</p>
                <p className="mt-0.5 text-[12px] leading-[1.5] text-white/85">{cur.note}</p>
              </div>
            </div>
          </div>
        )}

        {/* 无案例素材 → 通用暖色扫描骨架 */}
        {!cur && (
          <div
            className="mx-auto max-w-[360px] rounded-2xl glass glow-warm p-5 text-center"
            data-testid="analyzing-hero-generic"
          >
            <div className="mb-3 flex justify-center gap-1.5" aria-hidden>
              {[0, 1, 2, 3, 4].map((i) => (
                <span
                  key={i}
                  className={`h-8 w-2 rounded-full bg-[#7c2d12]/20 dark:bg-[#ea580c]/25 ${
                    reduced ? "" : "animate-pulse"
                  }`}
                  style={{ animationDelay: `${i * 140}ms` }}
                />
              ))}
            </div>
            <p className="text-[13px] leading-[1.7] text-stone-500 dark:text-stone-400">
              {COPY.analyzing_hero_generic_note}
            </p>
          </div>
        )}

        {/* 进度真理之源:阶段 + 百分比 + 95% 逃生(分析中唯一实例) */}
        <AnalysisProgress thinking={thinking} />

        {/* 已拆出的钩子:有案例时投喂,把等待变成预热阅读 */}
        {caseData?.hook && (
          <div
            className="rounded-2xl border border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-stone-900/70 p-4 shadow-soft anim-fade-up"
            data-testid="analyzing-hero-hook"
          >
            <div className="mb-1.5 text-[11px] font-semibold text-[#7c2d12] dark:text-[#ea580c]">
              🪝 {COPY.analyzing_hero_hook_label}
            </div>
            <p className="text-[13px] leading-[1.7] text-stone-700 dark:text-stone-300">
              {caseData.hook}
            </p>
            {caseData.emotion && (
              <p className="mt-2 text-[11px] text-stone-400 dark:text-stone-500">
                {caseData.emotion}
              </p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
