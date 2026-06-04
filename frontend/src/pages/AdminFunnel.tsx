import { useEffect, useState } from "react";
import { PageShell } from "../components/PageShell";
import { fetchFunnel, type FunnelStage } from "../lib/funnelApi";

export function AdminFunnel() {
  const [stages, setStages] = useState<FunnelStage[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    void fetchFunnel().then((s) => {
      setStages(s);
      setLoading(false);
    });
  };
  useEffect(() => {
    // 初始拉取:setState 放异步 .then 回调里(非 effect 体内同步),避开 set-state-in-effect。
    // loading 初值已是 true,无需在 effect 里同步置真。
    let active = true;
    void fetchFunnel().then((s) => {
      if (!active) return;
      setStages(s);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const top = stages[0]?.users ?? 0;
  const hasData = stages.length > 0 && top > 0;

  return (
    <PageShell>
      <main className="px-6 pt-16 pb-20">
        <div className="max-w-3xl mx-auto space-y-6">
          <p className="anim-fade-up text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400" style={{ animationDelay: "0ms" }}>
            Admin · Funnel
          </p>
          <header className="anim-fade-up flex items-baseline justify-between" style={{ animationDelay: "120ms" }}>
            <div>
              <h1 className="font-serif-cn text-3xl md:text-4xl text-stone-900 dark:text-stone-50">Beta 转化漏斗</h1>
              <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">
                分析 → 改写 → 草稿图 → 发布 → 付费意向 · 各阶段去重用户
              </p>
            </div>
            <button
              type="button"
              onClick={load}
              className="text-xs text-stone-500 dark:text-stone-400 hover:text-[#7c2d12] dark:hover:text-[#ea580c] underline underline-offset-4 transition-colors"
            >
              手动刷新
            </button>
          </header>

          <section className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft space-y-3" aria-label="转化漏斗">
            {loading && stages.length === 0 ? (
              <p className="text-sm text-stone-500 dark:text-stone-400">加载中…</p>
            ) : !hasData ? (
              <p className="text-sm text-stone-500 dark:text-stone-400">
                还没有漏斗数据 — 等用户开始粘链接分析(analysis_wait_started)。
              </p>
            ) : (
              stages.map((s, i) => (
                <div key={s.label}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-stone-800 dark:text-stone-200">
                      {i + 1}. {s.label}
                    </span>
                    <span className="tabular-nums text-stone-500 dark:text-stone-400">
                      {s.users} 人
                      {s.step_conv != null && <> · 转化 {(s.step_conv * 100).toFixed(0)}%</>}
                    </span>
                  </div>
                  <div className="h-6 rounded-lg bg-stone-100 dark:bg-stone-800 overflow-hidden">
                    <div
                      className="h-full bg-[#7c2d12] dark:bg-[#ea580c] flex items-center px-2 text-[11px] text-white tabular-nums transition-all duration-500"
                      style={{ width: `${Math.max(3, top ? (s.users / top) * 100 : 0)}%` }}
                    >
                      {s.pct_of_top != null ? `${(s.pct_of_top * 100).toFixed(0)}%` : ""}
                    </div>
                  </div>
                </div>
              ))
            )}
          </section>

          <p className="text-xs text-stone-500 dark:text-stone-400">
            口径:每阶段「至少触发过一次该事件的去重 user_id」(近似漏斗,Beta 量足够)。起点用「分析完成」
            (analysis_returned,长期可靠);「发起/放弃」靠 analysis_wait_started 单独看(2026-06-04 才补进
            allowlist,随 Beta 累积)。付费意向 = interview_logged 且 would_pay_39。
          </p>
        </div>
      </main>
    </PageShell>
  );
}
