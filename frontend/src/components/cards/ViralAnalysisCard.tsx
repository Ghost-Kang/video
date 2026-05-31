import { useState } from "react";
import { ScrollText } from "lucide-react";
import type { CascadeAnalysisContract } from "../../types/cascade";
import { COPY, scrubUiForbidden, stripHookCode } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";
import { ScriptDrawer } from "./ScriptDrawer";

interface Props {
  analysis: CascadeAnalysisContract;
}

// 爆点分析 — 三级层级 + 原视频脚本入口。
//   英雄四维(钩子/痛点/情绪/人群):为什么火的命脉,大字 + accent 左条 + 绘入。
//   次级(素材利益点/主要元素/微创新):常规网格。
//   辅助(BGM 风格):弱化,最末。
//   右上角「原视频脚本」pill → 抽屉(分镜脚本 + 逐字稿)。
export function ViralAnalysisCard({ analysis }: Props) {
  const va = analysis.viral_analysis;
  const [scriptOpen, setScriptOpen] = useState(false);
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
    <section className={`${CARD_CLASS} anim-fade-up`} data-testid="viral-analysis-card">
      {/* 标题行 + 原视频脚本入口 */}
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-serif-cn text-lg font-medium tracking-[-0.01em] text-stone-900 dark:text-stone-50">
          {COPY.viral_header}
        </h2>
        <button
          type="button"
          onClick={() => setScriptOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={scriptOpen}
          data-testid="script-entry"
          className="group inline-flex shrink-0 items-center gap-1.5 rounded-full border border-stone-200 px-3 py-1.5 text-[12px] font-medium text-stone-600 transition-colors hover:border-[#7c2d12]/40 hover:text-[#7c2d12] dark:border-stone-700 dark:text-stone-300 dark:hover:text-[#ea580c]"
        >
          <ScrollText className="h-3.5 w-3.5 group-hover:anim-icon-breathe" />
          {COPY.script_entry}
        </button>
      </div>

      {clean(va.theme) && (
        <p className="mb-2 text-[15px] text-stone-800 dark:text-stone-200">
          <span className="font-medium text-[#7c2d12] dark:text-[#ea580c]">{COPY.va_theme}：</span>
          {clean(va.theme)}
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
        <div className="grid grid-cols-1 gap-3 border-t border-stone-100 pt-4 dark:border-stone-800 sm:grid-cols-2">
          {heroDims.map((d, i) => (
            <div
              key={d.label}
              className="va-hero anim-fade-up relative rounded-xl bg-[#fef7f0]/70 py-3 pl-4 pr-3 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-soft-lg dark:bg-stone-800/40"
              style={{ animationDelay: `${120 + i * 80}ms` }}
            >
              <span
                className="anim-draw-line-y absolute inset-y-2 left-0 w-[3px] rounded bg-[#7c2d12] dark:bg-[#ea580c]"
                style={{ animationDelay: `${260 + i * 80}ms` }}
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
