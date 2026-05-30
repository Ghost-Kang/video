import { ViralAnalysisCard } from "./cards/ViralAnalysisCard";
import { SceneAnalysisCard } from "./cards/SceneAnalysisCard";
import { useCanvasStore } from "../store/canvasStore";
import { useWSStore } from "../store/wsStore";
import { COPY } from "../lib/cardCopy";
import { ConfidenceBanner } from "./feedback/ConfidenceBanner";
import { FailureBanner } from "./feedback/FailureBanner";
import { OnboardingSteps } from "./onboarding/OnboardingSteps";
import type { NicheId } from "../store/nicheStore";

interface CardStackProps {
  onGenerateFirstFrame?: (sceneIndex: number) => void;
  onTriggerRewrite?: (niche: NicheId) => void;
}

// 2026-05-30 toprador 对齐重设计:分析输出 = 爆点分析(总结+主题+维度网格) +
// 视频分析(逐幕网格)。维度齐全但结构清晰、好理解(founder 实测 toprador 样例为准)。
// 改写「你的版本」本轮暂挂 —— 不渲染 CTA/改写脚本/发布包(代码保留,见 wsStore +
// rewrite_service,随时可重接)。源逐镜/音频/成本旧抽屉也撤掉(逐幕已含这些维度)。
export function CardStack(_props: CardStackProps = {}) {
  const analysis = useCanvasStore((s) => s.analysis);
  const failure = useCanvasStore((s) => s.failure);
  const loading = useWSStore((s) => s.loading);

  if (!analysis) {
    return (
      <main className="flex-1 overflow-y-auto bg-transparent p-6">
        <div className="mx-auto max-w-[640px] pt-6 pb-12">
          <OnboardingSteps currentStep={loading ? 2 : 1} />
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

  const scenes = [...analysis.scenes].sort((a, b) => a.scene_index - b.scene_index);

  return (
    <main className="flex-1 overflow-y-auto bg-transparent p-4 md:p-6">
      <div className="mx-auto w-full max-w-[680px] space-y-4">
        <ConfidenceBanner confidence={analysis.confidence} />

        {/* 爆点分析:总结 + 主题 + 创作者向维度网格 */}
        <ViralAnalysisCard analysis={analysis} />

        {/* 视频分析:逐幕拆解网格 */}
        <section className="space-y-3">
          <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 px-1 pt-2">
            {COPY.video_analysis_header}
          </h2>
          {scenes.map((scene) => (
            <SceneAnalysisCard key={scene.scene_index} scene={scene} />
          ))}
        </section>
      </div>
    </main>
  );
}
