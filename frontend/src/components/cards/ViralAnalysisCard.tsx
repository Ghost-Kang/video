import type { CascadeAnalysisContract } from "../../types/cascade";
import { COPY, scrubUiForbidden, stripHookCode } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";

interface Props {
  analysis: CascadeAnalysisContract;
}

// 爆点分析 — 对齐 toprador:顶部 主题 + 总结(定位锚),下面是创作者向的维度网格。
// 单列手机优先,桌面 2 列。每个维度:小标签 + 一句话,好扫读。
export function ViralAnalysisCard({ analysis }: Props) {
  const va = analysis.viral_analysis;
  const clean = (s: string | undefined) => scrubUiForbidden(stripHookCode(s ?? "")).trim();

  const dims: { label: string; text: string }[] = [
    { label: COPY.va_target_audience, text: clean(va.target_audience) },
    { label: COPY.va_material_benefit, text: clean(va.material_benefit) },
    { label: COPY.va_hook, text: clean(va.hook) },
    { label: COPY.va_main_elements, text: clean(va.main_elements) },
    { label: COPY.va_micro_innovation, text: clean(va.micro_innovation) },
    { label: COPY.va_pain_points, text: clean(va.pain_points) },
    { label: COPY.va_emotion_trigger, text: clean(va.emotion_trigger) },
    { label: COPY.va_bgm_style, text: clean(va.bgm_style) },
  ].filter((d) => d.text);

  return (
    <section className={CARD_CLASS} data-testid="viral-analysis-card">
      <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 mb-4 tracking-[-0.01em]">
        {COPY.viral_header}
      </h2>

      {clean(va.theme) && (
        <p className="mb-2 text-[15px] text-stone-800 dark:text-stone-200">
          <span className="text-[#7c2d12] dark:text-[#ea580c] font-medium">{COPY.va_theme}：</span>
          {clean(va.theme)}
        </p>
      )}
      {(clean(va.summary) || analysis.video_summary) && (
        <p className="mb-5 text-[15px] leading-[1.7] text-stone-800 dark:text-stone-200">
          <span className="text-[#7c2d12] dark:text-[#ea580c] font-medium">{COPY.va_summary}：</span>
          {clean(va.summary) || scrubUiForbidden(analysis.video_summary)}
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 border-t border-stone-100 dark:border-stone-800 pt-4">
        {dims.map((d) => (
          <div key={d.label} className="border-l-2 border-stone-200 dark:border-stone-700 pl-3">
            <div className="text-[12px] font-medium text-[#7c2d12] dark:text-[#ea580c] mb-1">
              {d.label}
            </div>
            <p className="text-[14px] leading-[1.6] text-stone-700 dark:text-stone-300">
              {d.text}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
