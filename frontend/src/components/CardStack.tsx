import { ScriptCard } from "./cards/ScriptCard";
import { ShotCard } from "./cards/ShotCard";
import { RewriteShotCard } from "./cards/RewriteShotCard";
import { PublishPackCard } from "./cards/PublishPackCard";
import { AudioCard } from "./cards/AudioCard";
import { ProductionCard } from "./cards/ProductionCard";
import { TranscriptCard } from "./cards/TranscriptCard";
import { useCanvasStore } from "../store/canvasStore";
import { useWSStore } from "../store/wsStore";
import { COPY } from "../lib/cardCopy";
import { ConfidenceBanner } from "./feedback/ConfidenceBanner";
import { FailureBanner } from "./feedback/FailureBanner";
import { AnchorSidebar } from "./anchors/AnchorSidebar";
import { OnboardingSteps } from "./onboarding/OnboardingSteps";
import type { NicheId } from "../store/nicheStore";

interface CardStackProps {
  onGenerateFirstFrame?: (sceneIndex: number) => void;
  onTriggerRewrite?: (niche: NicheId) => void;
}

// W4 redesign (2026-05-29, founder feedback「复杂乱 / UX 不友好」):
// 从「一屏 20+ 块分析师 dump」改成「三幕一屉」——
//   幕1+2  为什么火 + 你的版本   (ScriptCard:抓/留/带+套路 + 改写脚本/CTA)
//   幕2续  改写后的镜头          (rewriteShots,价值主角,保持显眼)
//   幕3    拿去发                (PublishPackCard)
//   抽屉   想还原拍摄细节?        (源逐镜/台词/音频/成本/锚点,默认折叠)
// 单列手机优先;源镜头/音频/成本不再常驻主流,降为「想照着拍才打开」的参考。
export function CardStack({ onGenerateFirstFrame, onTriggerRewrite }: CardStackProps = {}) {
  const analysis = useCanvasStore((s) => s.analysis);
  const script = useCanvasStore((s) => s.script);
  const shots = useCanvasStore((s) => s.shots);
  const rewriteShots = useCanvasStore((s) => s.rewriteShots);
  const setScript = useCanvasStore((s) => s.setScript);
  const failure = useCanvasStore((s) => s.failure);
  const loading = useWSStore((s) => s.loading);

  if (!analysis) {
    return (
      <main className="flex-1 overflow-y-auto bg-transparent p-6">
        <div className="mx-auto max-w-[640px] pt-6 pb-12">
          <OnboardingSteps currentStep={1} />
        </div>
      </main>
    );
  }

  if (failure) {
    return (
      <main className="flex-1 overflow-y-auto bg-transparent p-4 md:p-6">
        <div className="mx-auto w-full max-w-[640px]">
          <FailureBanner failure={failure} />
        </div>
      </main>
    );
  }

  const hasRewrite = rewriteShots.length > 0;
  // 改写在途:分析已回、还没改写结果、但有运行中的 run(自动改写 effect 已发,或
  // 用户刚点了方向)。此窗口别显示「选方向」CTA(防双发),也别显示空的幕2/3
  // (script 此时为空,见 canvasStore 缺陷 ① 修复),而是给一句「正在帮你改…」。
  const rewritePending = !hasRewrite && loading;

  return (
    <main className="flex-1 overflow-y-auto bg-transparent p-4 md:p-6">
      <div className="mx-auto w-full max-w-[640px] space-y-4">
        <ConfidenceBanner confidence={analysis.confidence} />

        {/* 幕1+2:为什么火(抓/留/带+套路)+ 你的版本(脚本 / 选方向 CTA) */}
        <ScriptCard
          analysis={analysis}
          script={script}
          onScriptChange={setScript}
          // CTA 只在「还没改写、且没有改写在途」时显示;改写出来后或正在改时都别再
          // 勾引重复触发,换方向直接 chat。
          onTriggerRewrite={hasRewrite || rewritePending ? undefined : onTriggerRewrite}
        />

        {/* 改写在途:一句轻提示占住幕2的位置,等 rewrite_returned 替换成真脚本 */}
        {rewritePending && (
          <div
            className="rounded-2xl border border-stone-200 dark:border-stone-700 bg-white/50 dark:bg-stone-900/40 px-4 py-5 text-center text-[15px] text-stone-600 dark:text-stone-300"
            role="status"
            aria-live="polite"
          >
            <span className="inline-flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-[#7c2d12] dark:bg-[#ea580c] animate-pulse" aria-hidden />
              {COPY.your_version_waiting}
            </span>
          </div>
        )}

        {/* 幕2续:改写后的镜头 — 价值主角,留在主流显眼处 */}
        {hasRewrite && (
          <section className="space-y-3">
            <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 px-1 pt-2">
              {COPY.your_version_header}
            </h2>
            {rewriteShots.map((shot) => (
              <RewriteShotCard key={shot.shot_index} shot={shot} />
            ))}
          </section>
        )}

        {/* 幕3:拿去发 */}
        {script && <PublishPackCard script={script} analysis={analysis} />}

        {/* 抽屉:想还原拍摄细节?(源逐镜 / 台词 / 音频 / 成本 / 锚点,默认折叠) */}
        <details className="group rounded-2xl border border-stone-200 dark:border-stone-700 bg-white/50 dark:bg-stone-900/40 overflow-hidden">
          <summary className="cursor-pointer select-none list-none px-4 py-3.5 flex items-center justify-between gap-3 hover:bg-stone-50 dark:hover:bg-stone-800/40 transition-colors">
            <span>
              <span className="font-serif-cn text-[15px] text-stone-900 dark:text-stone-100">
                {COPY.detail_drawer_label}
              </span>
              <span className="block text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                {COPY.detail_drawer_hint}
              </span>
            </span>
            <svg
              className="shrink-0 text-stone-400 transition-transform duration-200 group-open:rotate-180"
              width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5"
              aria-hidden="true"
            >
              <path d="M4 7l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </summary>

          <div className="px-3 pb-4 pt-1 space-y-4 border-t border-stone-100 dark:border-stone-800">
            {analysis.viral_analysis.audio && (
              <AudioCard audio={analysis.viral_analysis.audio} />
            )}
            {analysis.viral_analysis.production && (
              <ProductionCard production={analysis.viral_analysis.production} />
            )}
            <TranscriptCard transcript={analysis.full_transcript ?? ""} />

            {shots.length > 0 && (
              <>
                <h3 className="font-serif-cn text-base text-stone-900 dark:text-stone-50 px-1 pt-1">
                  {COPY.source_shots_header}
                </h3>
                {shots.map((scene) => (
                  <ShotCard
                    key={scene.scene_index}
                    scene={scene}
                    onGenerateFirstFrame={onGenerateFirstFrame}
                  />
                ))}
              </>
            )}

            <AnchorSidebar />
          </div>
        </details>
      </div>
    </main>
  );
}
