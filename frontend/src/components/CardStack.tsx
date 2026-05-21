import { ScriptCard } from "./cards/ScriptCard";
import { ShotCard } from "./cards/ShotCard";
import { PublishPackCard } from "./cards/PublishPackCard";
import { useCanvasStore } from "../store/canvasStore";
import { COPY } from "../lib/cardCopy";
import { ConfidenceBanner } from "./feedback/ConfidenceBanner";
import { FailureBanner } from "./feedback/FailureBanner";
import { AnchorSidebar } from "./anchors/AnchorSidebar";

export function CardStack() {
  const analysis = useCanvasStore((s) => s.analysis);
  const script = useCanvasStore((s) => s.script);
  const shots = useCanvasStore((s) => s.shots);
  const setScript = useCanvasStore((s) => s.setScript);
  const failure = useCanvasStore((s) => s.failure);

  if (!analysis) {
    return (
      <main className="flex-1 overflow-y-auto bg-stone-50 p-6">
        <div className="mx-auto max-w-[640px]">
          <p className="text-base text-stone-600 text-center py-16">
            {COPY.empty_state}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto bg-stone-50 p-4 md:p-6">
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
              />

              <h2 className="text-lg font-medium text-stone-900 px-1 pt-2">
                {COPY.shots_header}
              </h2>

              {shots.map((scene) => (
                <ShotCard key={scene.scene_index} scene={scene} />
              ))}

              <PublishPackCard script={script} analysis={analysis} />
            </>
          )}
        </div>
        <AnchorSidebar />
      </div>
    </main>
  );
}
