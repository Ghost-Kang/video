import { ArrowRight } from "lucide-react";
import { SAMPLE_CASES, caseGradient, type SampleCase } from "../../lib/sampleCases";
import { COPY } from "../../lib/cardCopy";

interface Props {
  onPick: (c: SampleCase) => void;
  cases?: SampleCase[];
}

// 「看看能拆出什么」预览轮播 —— 用真实已拆案例,卡面秀「拆出的洞察」(钩子/情绪)
// 而非垂类名。点开进入真实完整分析。可扩展:案例来自 SAMPLE_CASES 配置数组。
export function SampleCaseCarousel({ onPick, cases = SAMPLE_CASES }: Props) {
  if (cases.length === 0) return null;

  // 1 条时居中;多条时横向滑动(swipe)。
  const wrapClass =
    cases.length === 1
      ? "flex justify-center"
      : "flex gap-3.5 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-hidden";

  return (
    <div className={wrapClass}>
      {cases.map((c, i) => (
        <article
          key={c.id}
          onClick={() => onPick(c)}
          className="group w-[300px] max-w-full shrink-0 cursor-pointer snap-start text-left anim-fade-up"
          style={{ animationDelay: `${i * 90}ms` }}
        >
          <div className="hover-glow relative flex h-full flex-col overflow-hidden rounded-2xl border border-stone-200/60 bg-white/70 backdrop-blur-sm transition-transform duration-200 group-hover:-translate-y-0.5 dark:border-stone-800/60 dark:bg-stone-900/55">
            {/* 暖色渐变头:品类 + 真实拆解标 */}
            <div className={`relative flex items-center justify-between px-4 py-3 ${caseGradient(c)}`}>
              <span className="font-serif-cn text-[15px] text-stone-900/90">
                {c.emoji ? `${c.emoji} ` : ""}
                {c.category}
              </span>
              <span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-medium tracking-wide text-[#7c2d12] backdrop-blur-sm">
                {COPY.sample_case_tag}
              </span>
            </div>

            {/* 拆出的洞察 */}
            <div className="flex flex-1 flex-col gap-2.5 px-4 py-3.5">
              <div>
                <div className="mb-1 text-[11px] font-semibold text-[#7c2d12] dark:text-[#ea580c]">
                  🪝 {COPY.sample_case_hook}
                </div>
                <p className="text-[13px] leading-[1.6] text-stone-700 dark:text-stone-300">{c.hook}</p>
              </div>
              {c.emotion && (
                <p className="text-[12px] text-stone-500 dark:text-stone-400">❤️ {c.emotion}</p>
              )}
              <div className="mt-auto flex items-center gap-1 pt-1 text-[12px] font-medium text-[#7c2d12] transition-colors group-hover:text-[#9a3412] dark:text-[#ea580c]">
                {COPY.sample_case_cta}
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
