import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ConsentGate } from "../components/landing/ConsentGate";
import { SampleCaseCarousel } from "../components/landing/SampleCaseCarousel";
import { UrlFallback } from "../components/landing/UrlFallback";
import { CreatorTicker } from "../components/landing/CreatorTicker";
import { StatCounter } from "../components/landing/StatCounter";
import { PageShell } from "../components/PageShell";
import { HighlightPhrase } from "../components/landing/HighlightPhrase";
import { useParallax } from "../hooks/useParallax";
import { useLiveStats } from "../hooks/useLiveStats";
import { COPY } from "../lib/cardCopy";
import type { SampleCase } from "../lib/sampleCases";

function sessionId() {
  return `session-${Date.now().toString(36)}`;
}

export function Landing() {
  const navigate = useNavigate();
  const [exiting, setExiting] = useState(false);
  const stats = useLiveStats();

  // 触发页面退出动画后再 navigate(280ms 让 anim-page-out 跑完)
  const fadeNavigate = useCallback(
    (path: string) => {
      setExiting(true);
      setTimeout(() => navigate(path), 280);
    },
    [navigate],
  );

  // 样例卡 = 一条真实已拆解的视频。点开走真链接管线(命中缓存秒出完整分析)。
  const pickCase = (c: SampleCase) => {
    fadeNavigate(`/chat/${sessionId()}?source_url=${encodeURIComponent(c.source_url)}`);
  };
  const submitUrl = (url: string) => {
    fadeNavigate(`/chat/${sessionId()}?source_url=${encodeURIComponent(url)}`);
  };

  // hero 视差
  const heroRef = useParallax<HTMLHeadingElement>(6);
  const subtitleRef = useParallax<HTMLParagraphElement>(3);

  return (
    <PageShell>
      <div className={`relative z-10 flex-1 ${exiting ? "anim-page-out" : ""}`}>
        <div className="mx-auto max-w-2xl px-6 pt-20 pb-24 md:pt-32 md:pb-32 text-center">
          <p
            className="anim-fade-up mb-10 text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400"
            style={{ animationDelay: "0ms" }}
          >
            <span className="inline-flex items-center gap-2">
              <span className="relative inline-flex h-1.5 w-1.5">
                <span className="absolute inset-0 rounded-full bg-emerald-500 anim-pulse-ring" />
                <span className="relative h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              Cascade · 内测中
            </span>
          </p>

          <h1
            ref={heroRef}
            className="font-serif-cn text-5xl md:text-6xl text-stone-900 dark:text-stone-50 leading-[1.35] mb-8 py-2"
          >
            <span
              className="anim-fade-up inline-block"
              style={{ animationDelay: "120ms" }}
            >
              粘一条爆款,
            </span>
            <br />
            <span
              className="anim-fade-up inline-block"
              style={{ animationDelay: "260ms" }}
            >
              <span className="text-shimmer-clay italic inline-block px-1.5">30 秒</span>
              <span>拆给你看</span>
            </span>
          </h1>

          <p
            ref={subtitleRef}
            className="anim-fade-up text-lg md:text-xl text-stone-700 dark:text-stone-200 leading-relaxed mb-10 max-w-xl mx-auto font-medium"
            style={{ animationDelay: "400ms" }}
          >
            看懂它{" "}
            <HighlightPhrase delay={950}>凭什么火</HighlightPhrase>
            ——钩子、节奏、情绪、人群,{" "}
            <HighlightPhrase delay={1180}>逐帧讲给你听</HighlightPhrase>
            。
          </p>

          {/* live stat — 真实数据 from /api/events */}
          <div
            className="anim-fade-up mb-12 flex items-center justify-center gap-8 opacity-0"
            style={{ animationDelay: "500ms", opacity: stats.loaded ? undefined : 0 }}
          >
            {stats.loaded && (
              <>
                <StatCounter target={stats.runs} label="次拆解记录" delayMs={0} />
                <span className="text-stone-300 dark:text-stone-700">·</span>
                <StatCounter target={stats.creators} label="位内测创作者" delayMs={200} />
              </>
            )}
          </div>

          <ConsentGate>
            <div
              className="anim-fade-up mx-auto max-w-xl"
              style={{ animationDelay: "600ms" }}
            >
              <UrlFallback onSubmit={submitUrl} />
            </div>

            <div className="mt-20">
              <p
                className="anim-fade-up mb-8 text-[13px] text-stone-500 dark:text-stone-400"
                style={{ animationDelay: "780ms" }}
              >
                {COPY.sample_cases_header} 👇
              </p>
              <div className="anim-fade-up" style={{ animationDelay: "900ms" }}>
                <SampleCaseCarousel onPick={pickCase} />
              </div>
            </div>
          </ConsentGate>
        </div>
      </div>

      <div className={`relative z-10 ${exiting ? "anim-page-out" : ""}`}>
        <CreatorTicker />
      </div>
    </PageShell>
  );
}
