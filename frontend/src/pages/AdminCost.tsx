import { useGenerationCost, type DailyTrendPoint } from "../hooks/useGenerationCost";
import { PageShell } from "../components/PageShell";

const AUTO_REFRESH_MS = 30_000;

function fmtCny(n: number): string {
  return `¥${n.toFixed(2)}`;
}

function fmtShare(s: number): string {
  return `${(s * 100).toFixed(1)}%`;
}

export function AdminCost() {
  const { kpis, by_user, by_kind, trend, isLoading, refresh } = useGenerationCost({
    autoRefreshMs: AUTO_REFRESH_MS,
  });

  return (
    <PageShell>
      <main className="px-6 pt-16 pb-20">
        <div className="max-w-6xl mx-auto space-y-6">
          <p className="anim-fade-up text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400" style={{ animationDelay: "0ms" }}>
            Admin · Cost
          </p>
          <header className="anim-fade-up flex items-baseline justify-between" style={{ animationDelay: "120ms" }}>
            <div>
              <h1 className="font-serif-cn text-3xl md:text-4xl text-stone-900 dark:text-stone-50">成本看板</h1>
              <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">
                generation_cost 聚合 · 每 {AUTO_REFRESH_MS / 1000}s 自动刷新
              </p>
            </div>
            <button
              type="button"
              onClick={() => void refresh()}
              className="text-xs text-stone-500 dark:text-stone-400 hover:text-[#7c2d12] dark:hover:text-[#ea580c] underline underline-offset-4 transition-colors"
            >
              手动刷新
            </button>
          </header>

        <section className="grid grid-cols-1 sm:grid-cols-3 gap-4" aria-label="KPI">
          <KpiTile label="今日" value={fmtCny(kpis.today)} hint={`${kpis.callsToday} 次调用`} />
          <KpiTile label="本周(7 天)" value={fmtCny(kpis.week)} hint={`${kpis.callsWeek} 次调用`} />
          <KpiTile label="累计" value={fmtCny(kpis.allTime)} hint={`${kpis.callsAllTime} 次调用`} />
        </section>

        <section className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft">
          <h2 className="text-sm uppercase tracking-wider text-stone-500 mb-3">14 日 trend</h2>
          {trend.length === 0 ? (
            <EmptyHint />
          ) : (
            <TrendChart points={trend} />
          )}
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <section className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft">
            <h2 className="text-sm uppercase tracking-wider text-stone-500 mb-3">按 creator</h2>
            {by_user.length === 0 ? (
              isLoading ? <p className="text-sm text-stone-500">加载中…</p> : <EmptyHint />
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wider text-stone-500">
                  <tr>
                    <th className="px-2 py-2 font-medium">user_id</th>
                    <th className="px-2 py-2 font-medium text-right">今日</th>
                    <th className="px-2 py-2 font-medium text-right">累计</th>
                    <th className="px-2 py-2 font-medium text-right">次数</th>
                  </tr>
                </thead>
                <tbody>
                  {by_user.slice(0, 10).map((row) => {
                    const tone =
                      row.is_runaway_red
                        ? "bg-rose-50 text-rose-700"
                        : row.is_runaway_amber
                        ? "bg-amber-50 text-amber-700"
                        : "";
                    return (
                      <tr key={row.user_id} className={`border-t border-stone-100 ${tone}`}>
                        <td className="px-2 py-2 font-mono text-xs">{row.user_id}</td>
                        <td className="px-2 py-2 text-right tabular-nums">{fmtCny(row.today_cny)}</td>
                        <td className="px-2 py-2 text-right tabular-nums">{fmtCny(row.total_cny)}</td>
                        <td className="px-2 py-2 text-right tabular-nums text-stone-500">{row.calls}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
            <p className="mt-3 text-xs text-stone-500">
              runaway 阈值:今日 &gt; ¥5 amber · &gt; ¥10 red
            </p>
          </section>

          <section className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft">
            <h2 className="text-sm uppercase tracking-wider text-stone-500 mb-3">按 call_kind</h2>
            {by_kind.length === 0 ? (
              isLoading ? <p className="text-sm text-stone-500">加载中…</p> : <EmptyHint />
            ) : (
              <ul className="space-y-2">
                {by_kind.map((row) => (
                  <li key={row.call_kind}>
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="font-mono text-xs">{row.call_kind}</span>
                      <span className="text-stone-500 tabular-nums">
                        {fmtCny(row.total_cny)} · {fmtShare(row.share)} · {row.calls} 次
                      </span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-stone-100 overflow-hidden">
                      <div
                        className="h-full bg-stone-700"
                        style={{ width: `${Math.max(4, row.share * 100)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
          </div>
        </div>
      </main>
    </PageShell>
  );
}

interface KpiTileProps {
  label: string;
  value: string;
  hint: string;
}

function KpiTile({ label, value, hint }: KpiTileProps) {
  return (
    <div className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft hover:shadow-soft-lg hover:-translate-y-0.5 transition-all duration-300">
      <div className="text-[11px] uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">{label}</div>
      <div className="mt-2 font-serif-cn text-3xl text-stone-900 dark:text-stone-50 tabular">{value}</div>
      <div className="mt-1 text-xs text-stone-500 dark:text-stone-400">{hint}</div>
    </div>
  );
}

function EmptyHint() {
  return (
    <p className="text-sm text-stone-500">
      尚无成本数据 — 等 concierge creator 触发首次 generation_cost event。
    </p>
  );
}

interface TrendChartProps {
  points: DailyTrendPoint[];
}

function TrendChart({ points }: TrendChartProps) {
  const max = points.reduce((m, p) => Math.max(m, p.cny), 0);
  const W = 600;
  const H = 120;
  const padX = 28;
  const padY = 8;
  const innerW = W - padX * 2;
  const innerH = H - padY * 2;
  const stepX = points.length > 1 ? innerW / (points.length - 1) : 0;

  const pathD = points
    .map((p, i) => {
      const x = padX + i * stepX;
      const y = padY + innerH - (max > 0 ? (p.cny / max) * innerH : 0);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div className="overflow-x-auto" role="img" aria-label="14 日成本 trend">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-32" preserveAspectRatio="none">
        <path d={pathD} fill="none" stroke="#1c1917" strokeWidth={1.5} strokeLinejoin="round" />
        {points.map((p, i) => {
          const x = padX + i * stepX;
          const y = padY + innerH - (max > 0 ? (p.cny / max) * innerH : 0);
          return <circle key={p.date} cx={x} cy={y} r={2} fill="#1c1917" />;
        })}
        <text x={padX} y={H - 1} fontSize="8" fill="#78716c">
          {points[0]?.date}
        </text>
        <text x={W - padX} y={H - 1} fontSize="8" fill="#78716c" textAnchor="end">
          {points[points.length - 1]?.date}
        </text>
        <text x={padX} y={padY + 6} fontSize="8" fill="#78716c">
          max ¥{max.toFixed(2)}
        </text>
      </svg>
    </div>
  );
}
