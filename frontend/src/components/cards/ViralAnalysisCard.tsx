import { useState } from "react";
import { ScrollText } from "lucide-react";
import type { CascadeAnalysisContract } from "../../types/cascade";
import { COPY, scrubUiForbidden, stripHookCode } from "../../lib/cardCopy";
import { CARD_GLASS } from "../../lib/cardStyles";
import { useInView } from "../../hooks/useInView";
import { ScriptDrawer } from "./ScriptDrawer";
import { ProCanvasEntry } from "../../pro/ProCanvasEntry";

interface Props {
  analysis: CascadeAnalysisContract;
}

// 爆点分析 — 暖色科技重设计:玻璃拟态卡 + 顶部流光描边 + 入场光扫;三级层级,
// 英雄四维(钩子/痛点/情绪/人群)入场发光脉冲吸睛 + 悬浮暖光;主题用流光渐变。
export function ViralAnalysisCard({ analysis }: Props) {
  const va = analysis.viral_analysis;
  const [scriptOpen, setScriptOpen] = useState(false);
  const { ref, inView } = useInView<HTMLElement>();
  const clean = (s: string | undefined) => scrubUiForbidden(stripHookCode(s ?? "")).trim();

  const heroDims = [
    { emoji: "🪝", label: COPY.va_hook, text: clean(va.hook) },
    { emoji: "💢", label: COPY.va_pain_points, text: clean(va.pain_points) },
    { emoji: "❤️", label: COPY.va_emotion_trigger, text: clean(va.emotion_trigger) },
    { emoji: "🎯", label: COPY.va_target_audience, text: clean(va.target_audience) },
  ].filter((d) => d.text);

  const restDims = [
    { label: COPY.va_material_benefit, text: clean(va.material_benefit) },
    { label: COPY.va_main_elements, text: clean(va.main_elements) },
    { label: COPY.va_micro_innovation, text: clean(va.micro_innovation) },
  ].filter((d) => d.text);

  const bgm = clean(va.bgm_style);
  const summary = clean(va.summary) || scrubUiForbidden(analysis.video_summary);

  return (
    <section
      ref={ref}
      className={`${CARD_GLASS} ${inView ? "anim-tech-in anim-sheen" : "opacity-0"}`}
      data-testid="viral-analysis-card"
    >
      {/* 顶部流光描边 */}
      <span className="tech-topline pointer-events-none absolute inset-x-0 top-0 h-[3px]" aria-hidden />

      {/* 标题行 + 原视频脚本入口 */}
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-serif-cn text-lg font-medium tracking-[-0.01em] text-stone-900 dark:text-stone-50">
          {COPY.viral_header}
        </h2>
        <div className="flex shrink-0 items-center gap-2">
          {/* Pro 画布入口(灰度自门控):把这条分析「展开为计算图」种子图。 */}
          <ProCanvasEntry variant="card" analysisId={analysis.analysis_id} />
          <button
            type="button"
            onClick={() => setScriptOpen(true)}
            aria-haspopup="dialog"
            aria-expanded={scriptOpen}
            data-testid="script-entry"
            className="group inline-flex shrink-0 items-center gap-1.5 rounded-full border border-stone-200/80 bg-white/50 px-3 py-1.5 text-[12px] font-medium text-stone-600 backdrop-blur transition-all hover:border-[#7c2d12]/40 hover:text-[#7c2d12] hover:shadow-[0_0_14px_-2px_rgba(234,88,12,0.4)] dark:border-stone-700 dark:bg-stone-900/40 dark:text-stone-300 dark:hover:text-[#ea580c]"
          >
            <ScrollText className="h-3.5 w-3.5 group-hover:anim-icon-breathe" />
            {COPY.script_entry}
          </button>
        </div>
      </div>

      {clean(va.theme) && (
        <p className="mb-2 text-[15px] text-stone-800 dark:text-stone-200">
          <span className="font-medium text-[#7c2d12] dark:text-[#ea580c]">{COPY.va_theme}：</span>
          <span className="font-serif-cn text-[17px] text-shimmer-clay">{clean(va.theme)}</span>
        </p>
      )}
      {summary && (
        <p className="mb-5 text-[15px] leading-[1.7] text-stone-800 dark:text-stone-200">
          <span className="font-medium text-[#7c2d12] dark:text-[#ea580c]">{COPY.va_summary}：</span>
          {summary}
        </p>
      )}

      {/* 英雄四维 */}
      {heroDims.length > 0 && (
        <div className="grid grid-cols-1 gap-3 border-t border-stone-200/60 pt-4 dark:border-stone-700/50 sm:grid-cols-2">
          {heroDims.map((d, i) => (
            <div
              key={d.label}
              className="va-hero anim-fade-up glow-warm hover-glow relative rounded-xl bg-[#fef7f0]/70 py-3 pl-4 pr-3 dark:bg-stone-800/40"
              style={{ animationDelay: `${120 + i * 80}ms` }}
            >
              {/* 入场一次性发光脉冲 — 吸睛 */}
              <span
                className="anim-glow-pulse pointer-events-none absolute inset-0 rounded-xl"
                style={{ animationDelay: `${360 + i * 110}ms` }}
                aria-hidden
              />
              {/* accent 左条绘入 */}
              <span
                className="anim-draw-line-y absolute inset-y-2 left-0 w-[3px] rounded bg-[#7c2d12] dark:bg-[#ea580c]"
                style={{ animationDelay: `${260 + i * 80}ms` }}
                aria-hidden
              />
              <div className="mb-1 text-[12px] font-semibold text-[#7c2d12] dark:text-[#ea580c]">
                <span aria-hidden className="mr-1">
                  {d.emoji}
                </span>
                {d.label}
              </div>
              <p className="text-[15px] leading-[1.6] text-stone-800 dark:text-stone-200">{d.text}</p>
            </div>
          ))}
        </div>
      )}

      {/* 次级维度 + BGM 辅助 */}
      {(restDims.length > 0 || bgm) && (
        <div className="anim-fade-in mt-4 grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2" style={{ animationDelay: "460ms" }}>
          {restDims.map((d) => (
            <div key={d.label} className="border-l-2 border-stone-200 pl-3 dark:border-stone-700">
              <div className="mb-0.5 text-[12px] font-medium text-stone-500 dark:text-stone-400">{d.label}</div>
              <p className="text-[14px] leading-[1.6] text-stone-700 dark:text-stone-300">{d.text}</p>
            </div>
          ))}
          {bgm && (
            <div className="border-l-2 border-stone-100 pl-3 dark:border-stone-800">
              <div className="mb-0.5 text-[11px] text-stone-400 dark:text-stone-500">{COPY.va_bgm_style}</div>
              <p className="text-[13px] leading-[1.5] text-stone-500 dark:text-stone-400">{bgm}</p>
            </div>
          )}
        </div>
      )}

      {scriptOpen && <ScriptDrawer analysis={analysis} onClose={() => setScriptOpen(false)} />}
    </section>
  );
}
