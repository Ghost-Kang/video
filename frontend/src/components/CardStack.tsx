import { useMemo } from "react";
import { ViralAnalysisCard } from "./cards/ViralAnalysisCard";
import { SceneAnalysisCard } from "./cards/SceneAnalysisCard";
import { AnalysisStatStrip } from "./cards/AnalysisStatStrip";
import { RewriteCTA } from "./cards/RewriteCTA";
import { RewriteShotCard } from "./cards/RewriteShotCard";
import { PublishPackCard } from "./cards/PublishPackCard";
import { useCanvasStore } from "../store/canvasStore";
import { useWSStore } from "../store/wsStore";
import { useInView } from "../hooks/useInView";
import { COPY } from "../lib/cardCopy";
import { ConfidenceBanner } from "./feedback/ConfidenceBanner";
import { FailureBanner } from "./feedback/FailureBanner";
import { OnboardingSteps } from "./onboarding/OnboardingSteps";
import { AnalyzingHero } from "./AnalyzingHero";
import { resolveRewriteEnabled } from "../lib/rewriteAccess";
import type { SampleCase } from "../lib/sampleCases";

interface CardStackProps {
  onGenerateFirstFrame?: (sceneIndex: number) => void;
  /** 触发通用改写;topic 为可选的一句话主题(去 niche 后无赛道参数)。 */
  onTriggerRewrite?: (topic?: string) => void;
  /** 图生视频(单镜)。 */
  onGenerateShotVideo?: (shotIndex: number) => void;
  /** 合成整片。 */
  onComposeFilm?: () => void;
  /** 分析中沉浸态:用户刚点的那条案例素材(粘陌生链接时为 null)。 */
  pendingCase?: SampleCase | null;
  /** Director 实时 tool_call label,透传给内嵌进度组件。 */
  thinking?: string[];
}

// 2026-05-30 toprador 对齐重设计:分析输出 = 爆点分析(总结+主题+维度网格) +
// 视频分析(逐幕网格)。维度齐全但结构清晰、好理解(founder 实测 toprador 样例为准)。
// 改写「你的版本」本轮暂挂 —— 不渲染 CTA/改写脚本/发布包(代码保留,见 wsStore +
// rewrite_service,随时可重接)。源逐镜/音频/成本旧抽屉也撤掉(逐幕已含这些维度)。
export function CardStack({ onTriggerRewrite, onGenerateFirstFrame, onGenerateShotVideo, onComposeFilm, pendingCase, thinking }: CardStackProps = {}) {
  const analysis = useCanvasStore((s) => s.analysis);
  const failure = useCanvasStore((s) => s.failure);
  const loading = useWSStore((s) => s.loading);
  const filmUrl = useCanvasStore((s) => s.filmUrl);
  const filmError = useCanvasStore((s) => s.filmError);
  // 改写-发布闭环依赖的状态 + 灰度门。**全部 hook 必须在下面的 early return 之前** —
  // React rules of hooks(把 hook 放在 `!analysis` return 之后,analysis 到达时
  // hook 数变化 → #310 崩溃被错误边界吞成空白页)。
  const script = useCanvasStore((s) => s.script);
  const rewriteShots = useCanvasStore((s) => s.rewriteShots);
  // 改写解封灰度门(VITE_REWRITE_ENABLED / 将来按 cohort)。关时下方改写区完全不渲染,
  // 行为 = 解封前(只展示分析)。
  const REWRITE_ENABLED = useMemo(() => resolveRewriteEnabled(), []);
  const { ref: headerRef, inView: headerInView } = useInView<HTMLHeadingElement>();

  if (!analysis) {
    // 分析中 → 沉浸骨架(把用户刚点的那条带进等待态 + 内嵌进度真理之源)。
    // 取代旧的「静态两步说明卡 step2」—— 那张卡在分析时装死还反向叫用户粘链接。
    if (loading) {
      return <AnalyzingHero caseData={pendingCase ?? null} thinking={thinking ?? []} />;
    }
    // 纯 idle(空会话等粘链接):仍是两步说明卡,但只高亮 step1。
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

  const scenes = [...analysis.scenes].sort((a, b) => a.scene_index - b.scene_index);
  // 改写区状态(纯派生,非 hook —— 放 early return 之后安全)。
  const hasRewrite = rewriteShots.length > 0;
  // 改写在途:解封开、还没改写结果、但有运行中的 run(用户刚点了 CTA)。此窗口
  // 别再显示 CTA(防双发),给一句「正在帮你改…」。
  const rewritePending = REWRITE_ENABLED && !hasRewrite && loading;
  // 视频闭环:有任一镜出了视频 → 可「合成整片」。
  const hasAnyShotVideo = rewriteShots.some((s) => Boolean(s.videoUrl));

  return (
    <main className="relative flex-1 overflow-y-auto bg-transparent p-4 md:p-6">
      {/* 暖色科技背景层:细网格 + 顶部柔光,营造深度与科技感(克制、不抢内容) */}
      <div className="pointer-events-none absolute inset-0 tech-grid opacity-[0.5] dark:opacity-[0.6]" aria-hidden />
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-64 opacity-70 dark:opacity-60"
        aria-hidden
        style={{
          background:
            "radial-gradient(60% 100% at 50% 0%, rgba(234,88,12,0.10), transparent 70%)",
        }}
      />
      <div className="relative mx-auto w-full max-w-[680px] space-y-4">
        <ConfidenceBanner confidence={analysis.confidence} />

        {/* 数据条:镜头 / 时长 / 把握 滚动计数 */}
        <AnalysisStatStrip analysis={analysis} />

        {/* 爆点分析:总结 + 主题 + 创作者向维度网格 */}
        <ViralAnalysisCard analysis={analysis} />

        {/* 视频分析:逐幕拆解网格 */}
        <section className="space-y-3">
          <h2
            ref={headerRef}
            className={`font-serif-cn text-lg text-stone-900 dark:text-stone-50 px-1 pt-2 ${headerInView ? "anim-fade-up" : "opacity-0"}`}
          >
            {COPY.video_analysis_header}
          </h2>
          {scenes.map((scene) => (
            <SceneAnalysisCard key={scene.scene_index} scene={scene} />
          ))}
        </section>

        {/* ── 改写-发布闭环(解封后):分析 → 你的版本 → 拿去发 ──────────────
            门控关时整段不渲染,行为 = 解封前(只展示分析)。去 niche 后 CTA 不再
            让选赛道,而是套用源片骨架 + 可选一句话主题的通用代笔。 */}
        {REWRITE_ENABLED && !hasRewrite && !rewritePending && onTriggerRewrite && (
          <RewriteCTA onPick={onTriggerRewrite} />
        )}

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

        {REWRITE_ENABLED && hasRewrite && (
          <section className="space-y-3">
            <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 px-1 pt-2">
              {COPY.your_version_header}
            </h2>
            {rewriteShots.map((shot) => (
              <RewriteShotCard
                key={shot.shot_index}
                shot={shot}
                onGenerateFirstFrame={onGenerateFirstFrame}
                onGenerateShotVideo={onGenerateShotVideo}
              />
            ))}
          </section>
        )}

        {/* 合成整片:任一镜出了视频后出现「合成整片」;成片用 <video> 播放器展示。 */}
        {REWRITE_ENABLED && hasRewrite && onComposeFilm && (hasAnyShotVideo || filmUrl) && (
          <section className="space-y-3">
            <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 px-1 pt-2">
              {COPY.film_header}
            </h2>
            {filmUrl ? (
              <video
                src={filmUrl}
                controls
                playsInline
                className="w-full rounded-2xl bg-black aspect-video"
                data-testid="film-player"
              />
            ) : filmError ? (
              <div className="rounded-2xl border border-stone-200 dark:border-stone-700 bg-white/50 dark:bg-stone-900/40 px-4 py-5 text-center">
                <p className="mb-2 text-sm text-stone-500 dark:text-stone-400">{filmError}</p>
                <button
                  type="button"
                  onClick={onComposeFilm}
                  className="inline-flex items-center gap-2 rounded-lg bg-white/80 dark:bg-stone-900/60 hover:bg-white dark:hover:bg-stone-900 px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-200 shadow-sm border border-stone-200 dark:border-stone-700 transition-colors"
                  data-testid="film-retry"
                >
                  {COPY.film_retry}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={onComposeFilm}
                className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-[#7c2d12] dark:bg-[#ea580c] text-white px-4 py-3 text-[15px] font-medium hover:opacity-90 transition-opacity"
                data-testid="compose-film"
              >
                {COPY.film_compose}
              </button>
            )}
          </section>
        )}

        {REWRITE_ENABLED && hasRewrite && (
          <PublishPackCard script={script} analysis={analysis} />
        )}
      </div>
    </main>
  );
}
