/**
 * /admin/health — founder 自检看板 (W5D2-D)。
 *
 * 4 块:
 *   1. 服务器(CPU / Memory / Disk progress + uptime)
 *   2. 过去 5 分钟事件(by_type 柱状)
 *   3. 上游成功率(analysis / rewrite,< 90% 标红)
 *   4. 最近 10 条 failure(时间 / event_name / failure_code / user_id)
 *
 * Auto-refresh 30s。loading / error / empty 状态都覆盖。配色沿用 AdminEvents
 * 的 paper + clay 语言,无新设计 token。
 *
 * 这页只在内测,founder 自己看,不加 invite gate 之外的鉴权(已经在
 * invite gate 之后)。
 */

import { useEffect, useState } from "react";
import { PageShell } from "../components/PageShell";
import {
  fetchHealthSummary,
  type HealthSummary,
  type HealthRecentFailure,
} from "../lib/healthApi";

const AUTO_REFRESH_MS = 30_000;
const SUCCESS_RATE_THRESHOLD = 0.9;

function formatTs(ts: string): string {
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts;
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return ts;
  }
}

function formatUptime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const parts: string[] = [];
  if (d > 0) parts.push(`${d}天`);
  if (h > 0) parts.push(`${h}小时`);
  parts.push(`${m}分钟`);
  return parts.join(" ");
}

function pct(num: number, denom: number): number {
  if (denom <= 0) return 0;
  return Math.min(100, Math.max(0, (num / denom) * 100));
}

function asFailureCode(payload: Record<string, unknown>): string {
  const code = payload?.failure_code;
  if (typeof code === "string") return code;
  return "—";
}

function asUserId(payload: Record<string, unknown>): string {
  const u = payload?.user_id;
  if (typeof u === "string") return u;
  return "—";
}

interface ProgressBarProps {
  label: string;
  current: string;
  ratio: number;
  warn?: boolean;
}

function ProgressBar({ label, current, ratio, warn }: ProgressBarProps) {
  const widthPct = Math.min(100, Math.max(0, ratio));
  const barColor = warn
    ? "bg-rose-500 dark:bg-rose-400"
    : "bg-[#7c2d12] dark:bg-[#ea580c]";
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-xs uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">
          {label}
        </span>
        <span className="text-sm tabular-nums text-stone-700 dark:text-stone-300">
          {current}
        </span>
      </div>
      <div className="h-2 rounded-full bg-stone-100 dark:bg-stone-800 overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all duration-500`}
          style={{ width: `${widthPct}%` }}
          role="progressbar"
          aria-valuenow={Math.round(widthPct)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label}
        />
      </div>
    </div>
  );
}

function ServerCard({ server }: { server: HealthSummary["server"] }) {
  const cpuWarn = server.cpu_percent >= 80;
  const memRatio = pct(server.mem_used_mb, server.mem_total_mb);
  const memWarn = memRatio >= 85;
  const diskRatio = pct(server.disk_used_gb, server.disk_total_gb);
  const diskWarn = diskRatio >= 85;
  return (
    <section
      data-testid="health-server"
      className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft"
    >
      <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 mb-4">
        服务器
      </h2>
      <div className="space-y-4">
        <ProgressBar
          label="CPU"
          current={`${server.cpu_percent.toFixed(1)}%`}
          ratio={server.cpu_percent}
          warn={cpuWarn}
        />
        <ProgressBar
          label="内存"
          current={`${server.mem_used_mb.toFixed(0)} / ${server.mem_total_mb.toFixed(0)} MB`}
          ratio={memRatio}
          warn={memWarn}
        />
        <ProgressBar
          label="磁盘"
          current={`${server.disk_used_gb.toFixed(1)} / ${server.disk_total_gb.toFixed(1)} GB`}
          ratio={diskRatio}
          warn={diskWarn}
        />
        <div className="flex items-baseline justify-between pt-1 border-t border-stone-100 dark:border-stone-800">
          <span className="text-xs uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">
            运行时长
          </span>
          <span className="text-sm tabular-nums text-stone-700 dark:text-stone-300">
            {formatUptime(server.uptime_seconds)}
          </span>
        </div>
      </div>
    </section>
  );
}

function EventsCard({ events }: { events: HealthSummary["events_5min"] }) {
  const entries = Object.entries(events.by_type).sort((a, b) => b[1] - a[1]);
  const max = entries.reduce((m, [, n]) => Math.max(m, n), 0);
  return (
    <section
      data-testid="health-events"
      className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft"
    >
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50">
          过去 5 分钟
        </h2>
        <span className="text-sm tabular-nums text-stone-500 dark:text-stone-400">
          总计 {events.total}
        </span>
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">无事件</p>
      ) : (
        <ul className="space-y-2">
          {entries.map(([name, count]) => {
            const widthPct = max > 0 ? (count / max) * 100 : 0;
            return (
              <li key={name} className="flex items-center gap-3">
                <span className="w-44 shrink-0 font-mono text-xs text-stone-700 dark:text-stone-300 truncate">
                  {name}
                </span>
                <div className="flex-1 h-2 rounded-full bg-stone-100 dark:bg-stone-800 overflow-hidden">
                  <div
                    className="h-full bg-[#7c2d12] dark:bg-[#ea580c]"
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-sm tabular-nums text-stone-700 dark:text-stone-300">
                  {count}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function UpstreamCard({
  rates,
}: {
  rates: HealthSummary["upstream_success_rate"];
}) {
  const entries = Object.entries(rates);
  return (
    <section
      data-testid="health-upstream"
      className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft"
    >
      <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 mb-4">
        上游成功率
      </h2>
      {entries.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">暂无样本</p>
      ) : (
        <ul className="space-y-3">
          {entries.map(([name, rate]) => {
            const bad = rate < SUCCESS_RATE_THRESHOLD;
            const display = `${(rate * 100).toFixed(1)}%`;
            return (
              <li key={name} className="flex items-baseline justify-between">
                <span className="font-mono text-xs text-stone-700 dark:text-stone-300">
                  {name}
                </span>
                <span
                  className={`text-sm tabular-nums font-medium ${
                    bad
                      ? "text-rose-600 dark:text-rose-400"
                      : "text-stone-700 dark:text-stone-300"
                  }`}
                  data-warn={bad ? "1" : "0"}
                >
                  {display}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function FailuresCard({ failures }: { failures: HealthRecentFailure[] }) {
  return (
    <section
      data-testid="health-failures"
      className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft md:col-span-2"
    >
      <h2 className="font-serif-cn text-lg text-stone-900 dark:text-stone-50 mb-4">
        最近 failure
      </h2>
      {failures.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">无最近 failure。</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400">
              <tr>
                <th className="px-3 py-2 font-medium">时间</th>
                <th className="px-3 py-2 font-medium">事件</th>
                <th className="px-3 py-2 font-medium">failure_code</th>
                <th className="px-3 py-2 font-medium">user_id</th>
              </tr>
            </thead>
            <tbody>
              {failures.slice(0, 10).map((f) => (
                <tr
                  key={f.id}
                  className="border-t border-stone-100 dark:border-stone-800"
                  data-testid="health-failure-row"
                >
                  <td className="px-3 py-2 text-stone-500 dark:text-stone-400 tabular-nums">
                    {formatTs(f.ts)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-stone-800 dark:text-stone-200">
                    {f.event_name}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-rose-600 dark:text-rose-400">
                    {asFailureCode(f.payload)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-stone-700 dark:text-stone-300">
                    {asUserId(f.payload)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function AdminHealth() {
  const [data, setData] = useState<HealthSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const summary = await fetchHealthSummary();
      if (cancelled) return;
      if (summary === null) {
        setError(true);
      } else {
        setError(false);
        setData(summary);
      }
      setIsLoading(false);
    }

    void load();
    const id = setInterval(() => void load(), AUTO_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <PageShell>
      <main className="px-6 pt-16 pb-20">
        <div className="max-w-6xl mx-auto space-y-6">
          <p
            className="anim-fade-up text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400"
            style={{ animationDelay: "0ms" }}
          >
            Admin · Health
          </p>
          <header
            className="anim-fade-up flex items-baseline justify-between"
            style={{ animationDelay: "120ms" }}
          >
            <div>
              <h1 className="font-serif-cn text-3xl md:text-4xl text-stone-900 dark:text-stone-50">
                运行健康
              </h1>
              <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">
                每 {AUTO_REFRESH_MS / 1000}s 自动刷新
              </p>
            </div>
          </header>

          {isLoading && data === null && (
            <div
              data-testid="health-loading"
              className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-10 text-center text-sm text-stone-500 dark:text-stone-400"
            >
              加载中…
            </div>
          )}

          {error && data === null && (
            <div
              data-testid="health-error"
              className="rounded-2xl border border-rose-300/70 bg-rose-50/95 dark:bg-rose-950/90 dark:border-rose-900/60 p-6 text-sm text-rose-700 dark:text-rose-300"
            >
              拉取健康数据失败 — 检查 backend `/api/health/summary` 是否正常。
            </div>
          )}

          {data && (
            <div
              className="anim-fade-up grid grid-cols-1 md:grid-cols-2 gap-4"
              style={{ animationDelay: "240ms" }}
            >
              <ServerCard server={data.server} />
              <EventsCard events={data.events_5min} />
              <UpstreamCard rates={data.upstream_success_rate} />
              <FailuresCard failures={data.recent_failures} />
            </div>
          )}
        </div>
      </main>
    </PageShell>
  );
}
