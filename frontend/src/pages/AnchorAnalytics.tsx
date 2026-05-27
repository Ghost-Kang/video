import { useMemo, useState } from "react";
import { useAnchorAnalytics } from "../hooks/useAnchorAnalytics";
import { StatCard } from "../components/analytics/StatCard";
import { AnchorBarChart } from "../components/analytics/AnchorBarChart";
import { PageShell } from "../components/PageShell";

type KindFilter = "all" | "character" | "scene";

const PILL_BASE = "rounded-full px-3 py-1 text-xs transition-colors";
const PILL_ACTIVE = "bg-[#7c2d12] dark:bg-[#ea580c] text-white";
const PILL_INACTIVE = "bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 hover:bg-stone-200 dark:hover:bg-stone-700";

function formatRatio(ratio: number): string {
  if (!Number.isFinite(ratio)) return "∞";
  if (ratio === 0) return "0";
  return ratio.toFixed(2);
}

function formatAvg(avg: number): string {
  if (!Number.isFinite(avg) || Number.isNaN(avg)) return "0.0";
  return avg.toFixed(1);
}

export function AnchorAnalytics() {
  const analytics = useAnchorAnalytics();
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");

  const filteredAnchors = useMemo(() => {
    if (kindFilter === "all") return analytics.anchors;
    return analytics.anchors.filter((a) => a.kind === kindFilter);
  }, [analytics.anchors, kindFilter]);

  const distributionBins = useMemo(() => {
    const entries = Object.entries(analytics.distribution).map(([k, v]) => ({
      reuse: Number(k),
      count: v,
    }));
    entries.sort((a, b) => a.reuse - b.reuse);
    const maxCount = entries.reduce((acc, e) => Math.max(acc, e.count), 0);
    return entries.map((e) => ({ ...e, ratio: maxCount > 0 ? e.count / maxCount : 0 }));
  }, [analytics.distribution]);

  if (analytics.isLoading && analytics.anchors.length === 0) {
    return (
      <PageShell>
        <main className="px-6 pt-16 pb-20">
          <div className="max-w-4xl mx-auto text-stone-500 dark:text-stone-400 text-sm">加载中…</div>
        </main>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <main className="px-6 pt-16 pb-20">
        <div className="max-w-4xl mx-auto space-y-8">
          <p className="anim-fade-up text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400" style={{ animationDelay: "0ms" }}>
            Analytics · 复用看板
          </p>
          <header className="anim-fade-up flex items-baseline justify-between" style={{ animationDelay: "120ms" }}>
            <div>
              <h1 className="font-serif-cn text-3xl md:text-4xl text-stone-900 dark:text-stone-50">你的素材复用看板</h1>
              <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">
                这一页看的是 H8 — 用过的角色和场景被你在新一条里「又拖一次」的频次
              </p>
            </div>
            <button
              type="button"
              onClick={() => void analytics.refresh()}
              className="text-xs text-stone-500 dark:text-stone-400 hover:text-[#7c2d12] dark:hover:text-[#ea580c] underline underline-offset-4 transition-colors"
            >
              刷新
            </button>
          </header>

        {analytics.totalAnchors === 0 ? (
          <section className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-10 shadow-soft text-center">
            <p className="text-stone-700 dark:text-stone-200">还没有素材,先在画布里创建一些试试。</p>
            <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">
              当你在 ShotCard 上配置角色或场景图后,它们会自动出现在「你之前用过的」侧栏,反复拖入新的 run 累计复用次数。
            </p>
          </section>
        ) : (
          <>
            <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="素材总数" value={analytics.totalAnchors} hint="角色 + 场景" />
              <StatCard label="累计复用" value={analytics.totalReuses} hint="所有 anchor reuse_count 之和" />
              <StatCard label="平均每条复用" value={formatAvg(analytics.avgReuseCount)} hint="reuse_count 平均值" />
              <StatCard
                label="单条最高复用"
                value={analytics.maxReuseCount}
                hint={analytics.maxReuseCount > 0 ? "已经在重复用了" : "还没产生复用"}
              />
            </section>

            <section className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-medium text-stone-900 dark:text-stone-50">复用次数 Top 5</h2>
                <div className="flex gap-2" role="radiogroup" aria-label="kind filter">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={kindFilter === "all"}
                    className={`${PILL_BASE} ${kindFilter === "all" ? PILL_ACTIVE : PILL_INACTIVE}`}
                    onClick={() => setKindFilter("all")}
                  >
                    全部
                  </button>
                  <button
                    type="button"
                    role="radio"
                    aria-checked={kindFilter === "character"}
                    className={`${PILL_BASE} ${kindFilter === "character" ? PILL_ACTIVE : PILL_INACTIVE}`}
                    onClick={() => setKindFilter("character")}
                  >
                    角色
                  </button>
                  <button
                    type="button"
                    role="radio"
                    aria-checked={kindFilter === "scene"}
                    className={`${PILL_BASE} ${kindFilter === "scene" ? PILL_ACTIVE : PILL_INACTIVE}`}
                    onClick={() => setKindFilter("scene")}
                  >
                    场景
                  </button>
                </div>
              </div>
              <AnchorBarChart anchors={filteredAnchors} />
            </section>

            <section className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft">
              <h2 className="text-base font-medium text-stone-900 dark:text-stone-50 mb-4">复用分布直方图</h2>
              <div className="flex items-end gap-2 h-32" aria-label="reuse distribution histogram">
                {distributionBins.map((bin) => (
                  <div key={bin.reuse} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full bg-[#7c2d12] dark:bg-[#ea580c] rounded-t"
                      style={{ height: `${Math.max(4, bin.ratio * 100)}%` }}
                      title={`复用 ${bin.reuse} 次的 anchor:${bin.count} 个`}
                      role="presentation"
                    />
                    <div className="text-xs text-stone-500 dark:text-stone-400 tabular-nums">{bin.count}</div>
                    <div className="text-[10px] text-stone-400 dark:text-stone-600 tabular-nums">×{bin.reuse}</div>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">
                横轴 = 该 anchor 被复用了几次,纵轴 = 有多少个 anchor 落在这一档
              </p>
            </section>

            <section className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft">
                <h3 className="text-sm uppercase tracking-wider text-stone-500 dark:text-stone-400">角色</h3>
                <div className="mt-2 text-2xl font-medium tabular-nums text-stone-900 dark:text-stone-50">
                  {analytics.byKind.character.total}{" "}
                  <span className="text-base text-stone-500 dark:text-stone-400">个 · 共复用 {analytics.byKind.character.totalReuses} 次</span>
                </div>
              </div>
              <div className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft">
                <h3 className="text-sm uppercase tracking-wider text-stone-500 dark:text-stone-400">场景</h3>
                <div className="mt-2 text-2xl font-medium tabular-nums text-stone-900 dark:text-stone-50">
                  {analytics.byKind.scene.total}{" "}
                  <span className="text-base text-stone-500 dark:text-stone-400">个 · 共复用 {analytics.byKind.scene.totalReuses} 次</span>
                </div>
              </div>
            </section>

            <footer className="text-xs text-stone-400 dark:text-stone-600 pt-4 leading-relaxed">
              角色/场景比例 {formatRatio(analytics.ratioCharacterToScene)} · 最早一个素材已经 {analytics.oldestAnchorDays} 天
            </footer>
          </>
        )}
        </div>
      </main>
    </PageShell>
  );
}
