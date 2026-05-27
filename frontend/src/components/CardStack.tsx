import { ScriptCard } from "./cards/ScriptCard";
import { ShotCard } from "./cards/ShotCard";
import { RewriteShotCard } from "./cards/RewriteShotCard";
import { PublishPackCard } from "./cards/PublishPackCard";
import { AudioCard } from "./cards/AudioCard";
import { ProductionCard } from "./cards/ProductionCard";
import { TranscriptCard } from "./cards/TranscriptCard";
import { useCanvasStore } from "../store/canvasStore";
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

export function CardStack({ onGenerateFirstFrame, onTriggerRewrite }: CardStackProps = {}) {
  const analysis = useCanvasStore((s) => s.analysis);
  const script = useCanvasStore((s) => s.script);
  const shots = useCanvasStore((s) => s.shots);
  const rewriteShots = useCanvasStore((s) => s.rewriteShots);
  const setScript = useCanvasStore((s) => s.setScript);
  const failure = useCanvasStore((s) => s.failure);

  // W4D5: empty-state condition is just `!analysis`. The store now ships
  // `null` until a real analysis arrives via WS, so this is the single
  // source of truth — no more messages-length fallback.
  if (!analysis) {
    return (
      <main className="flex-1 overflow-y-auto bg-transparent p-6">
        <div className="mx-auto max-w-[760px] pt-6 pb-12">
          <OnboardingSteps currentStep={1} />
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto bg-transparent p-4 md:p-6">
      <div className="mx-auto flex max-w-[920px] gap-4">
        <div className="w-full max-w-[640px] space-y-4">
          {failure ? (
            <FailureBanner failure={failure} />
          ) : (
            <>
              <ConfidenceBanner confidence={analysis.confidence} />

              <ScriptCard
                analysis={analysis}
                script={script}
                onScriptChange={setScript}
                // 改写 CTA 只在还没改写过(rewriteShots 空)时显示。已经有
                // rewrite 产物了就别再勾引用户重复触发。想换 niche 直接 chat
                // 跟 Director 说就行。
                onTriggerRewrite={rewriteShots.length === 0 ? onTriggerRewrite : undefined}
              />

              {analysis.viral_analysis.audio && (
                <AudioCard audio={analysis.viral_analysis.audio} />
              )}
              {analysis.viral_analysis.production && (
                <ProductionCard production={analysis.viral_analysis.production} />
              )}
              <TranscriptCard transcript={analysis.full_transcript ?? ""} />

              {shots.length > 0 && (
                <>
                  <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 px-1 pt-2">
                    {COPY.source_shots_header}
                  </h2>

                  {shots.map((scene) => (
                    <ShotCard
                      key={scene.scene_index}
                      scene={scene}
                      onGenerateFirstFrame={onGenerateFirstFrame}
                    />
                  ))}
                </>
              )}

              {rewriteShots.length > 0 && (
                <>
                  <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 px-1 pt-2">
                    {COPY.rewrite_shots_header}
                  </h2>

                  {rewriteShots.map((shot) => (
                    <RewriteShotCard key={shot.shot_index} shot={shot} />
                  ))}
                </>
              )}

              {script && <PublishPackCard script={script} analysis={analysis} />}
            </>
          )}
        </div>
        <AnchorSidebar />
      </div>
    </main>
  );
}
