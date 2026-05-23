import { useMemo, useState } from "react";
import { useEvents } from "../hooks/useEvents";
import type { EventRow } from "../lib/eventsApi";

const EVENT_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "全部类型" },
  { value: "run_started", label: "run_started" },
  { value: "analysis_returned", label: "analysis_returned" },
  { value: "script_rewritten", label: "script_rewritten" },
  { value: "shot_generated", label: "shot_generated" },
  { value: "publish_pack_copied", label: "publish_pack_copied" },
  { value: "anchor_created", label: "anchor_created" },
  { value: "anchor_reused", label: "anchor_reused" },
  { value: "failure_emitted", label: "failure_emitted" },
  { value: "failure_recovered", label: "failure_recovered" },
  { value: "generation_cost", label: "generation_cost" },
  { value: "interview_logged", label: "interview_logged" },
  { value: "consent_accepted", label: "consent_accepted" },
];

const AUTO_REFRESH_MS = 30_000;

function formatTs(ts: string): string {
  try {
    const date = new Date(ts);
    if (Number.isNaN(date.getTime())) return ts;
    return date.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return ts;
  }
}

function previewPayload(payload: Record<string, unknown>): string {
  const keys = Object.keys(payload);
  if (keys.length === 0) return "(empty)";
  return keys.slice(0, 3).map((k) => `${k}=${stringifyValue(payload[k])}`).join("  ");
}

function stringifyValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v.length > 32 ? v.slice(0, 32) + "…" : v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v).slice(0, 32);
}

export function AdminEvents() {
  const [eventType, setEventType] = useState("");
  const [userId, setUserId] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { events, isLoading, hasMore, refresh } = useEvents({
    type: eventType || undefined,
    user_id: userId || undefined,
    limit: 200,
    autoRefreshMs: AUTO_REFRESH_MS,
  });

  const summary = useMemo(() => {
    const byType: Record<string, number> = {};
    for (const e of events) {
      byType[e.event_name] = (byType[e.event_name] || 0) + 1;
    }
    return byType;
  }, [events]);

  return (
    <main className="min-h-screen bg-stone-50 py-10 px-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-baseline justify-between">
          <div>
            <h1 className="text-2xl font-medium text-stone-900">事件直播流</h1>
            <p className="mt-1 text-sm text-stone-500">
              最近 {events.length} 条事件 · 每 {AUTO_REFRESH_MS / 1000}s 自动刷新
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            className="text-xs text-stone-500 hover:text-stone-900 underline"
          >
            手动刷新
          </button>
        </header>

        <div className="rounded-2xl bg-white border border-stone-200 p-5 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
            <label className="text-xs text-stone-500 flex items-center gap-2">
              事件类型
              <select
                value={eventType}
                onChange={(e) => setEventType(e.target.value)}
                className="rounded-lg border border-stone-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300"
                aria-label="event type filter"
              >
                {EVENT_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-stone-500 flex items-center gap-2">
              user_id
              <input
                type="search"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="精确匹配"
                className="rounded-lg border border-stone-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300"
                aria-label="user_id filter"
              />
            </label>
            {hasMore && (
              <span className="ml-auto text-xs text-amber-700">
                还有更多事件未加载(已达 200 条上限)
              </span>
            )}
          </div>

          {Object.keys(summary).length > 0 && (
            <div className="flex flex-wrap gap-2 text-xs text-stone-500">
              {Object.entries(summary).map(([t, n]) => (
                <span
                  key={t}
                  className="rounded-full bg-stone-100 px-2 py-0.5"
                  title={`${t}: ${n}`}
                >
                  {t}:{n}
                </span>
              ))}
            </div>
          )}

          {isLoading && events.length === 0 ? (
            <div className="rounded-xl bg-stone-50 p-10 text-center text-sm text-stone-500">
              加载中…
            </div>
          ) : events.length === 0 ? (
            <div className="rounded-xl bg-stone-50 p-10 text-center text-sm text-stone-500">
              没有匹配的事件 — 调整过滤条件或等待新事件触发。
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wider text-stone-500">
                  <tr>
                    <th className="px-3 py-2 font-medium">时间</th>
                    <th className="px-3 py-2 font-medium">事件</th>
                    <th className="px-3 py-2 font-medium">user_id</th>
                    <th className="px-3 py-2 font-medium">run_id</th>
                    <th className="px-3 py-2 font-medium">payload</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <EventTableRow
                      key={e.id}
                      event={e}
                      expanded={expandedId === e.id}
                      onToggle={() =>
                        setExpandedId((prev) => (prev === e.id ? null : e.id))
                      }
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

interface EventTableRowProps {
  event: EventRow;
  expanded: boolean;
  onToggle: () => void;
}

function EventTableRow({ event, expanded, onToggle }: EventTableRowProps) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="border-t border-stone-100 hover:bg-stone-50 cursor-pointer"
        data-testid="event-row"
      >
        <td className="px-3 py-2 text-stone-500 tabular-nums">{formatTs(event.ts)}</td>
        <td className="px-3 py-2 font-mono text-xs">{event.event_name}</td>
        <td className="px-3 py-2 font-mono text-xs text-stone-700">{event.user_id}</td>
        <td className="px-3 py-2 font-mono text-xs text-stone-500">{event.run_id || "—"}</td>
        <td className="px-3 py-2 text-stone-500 text-xs">{previewPayload(event.payload)}</td>
      </tr>
      {expanded && (
        <tr className="border-t border-stone-100 bg-stone-50">
          <td colSpan={5} className="px-3 py-3">
            <pre className="text-xs text-stone-700 whitespace-pre-wrap break-all">
              {JSON.stringify(event.payload, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}
