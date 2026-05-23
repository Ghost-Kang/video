import { useCallback, useEffect, useMemo, useState } from "react";
import { listEvents, type EventRow } from "../lib/eventsApi";

export interface CostKpis {
  today: number;
  week: number;
  allTime: number;
  callsToday: number;
  callsWeek: number;
  callsAllTime: number;
}

export interface UserCostRow {
  user_id: string;
  total_cny: number;
  calls: number;
  today_cny: number;
  is_runaway_red: boolean;
  is_runaway_amber: boolean;
}

export interface KindBreakdownRow {
  call_kind: string;
  total_cny: number;
  calls: number;
  share: number;
}

export interface DailyTrendPoint {
  date: string;
  cny: number;
}

export interface CostAggregate {
  kpis: CostKpis;
  by_user: UserCostRow[];
  by_kind: KindBreakdownRow[];
  trend: DailyTrendPoint[];
}

export interface UseGenerationCostOptions {
  trendDays?: number;
  runawayAmberCny?: number;
  runawayRedCny?: number;
  fetchLimit?: number;
  autoRefreshMs?: number;
  now?: () => Date;
}

export interface UseGenerationCostResult extends CostAggregate {
  isLoading: boolean;
  refresh: () => Promise<void>;
}

const DEFAULT_TREND_DAYS = 14;
const DEFAULT_FETCH_LIMIT = 1000;
const DEFAULT_AMBER = 5;
const DEFAULT_RED = 10;

export function aggregateCostEvents(
  events: EventRow[],
  options: { trendDays?: number; runawayAmberCny?: number; runawayRedCny?: number; now?: () => Date } = {},
): CostAggregate {
  const trendDays = options.trendDays ?? DEFAULT_TREND_DAYS;
  const amber = options.runawayAmberCny ?? DEFAULT_AMBER;
  const red = options.runawayRedCny ?? DEFAULT_RED;
  const now = options.now ? options.now() : new Date();

  const todayKey = isoDay(now);
  const weekCutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const trendCutoff = new Date(now.getTime() - trendDays * 24 * 60 * 60 * 1000);

  const userTotals = new Map<string, { total_fen: number; calls: number; today_fen: number }>();
  const kindTotals = new Map<string, { total_fen: number; calls: number }>();
  const dailyTotals = new Map<string, number>();

  let kpiToday = 0;
  let kpiWeek = 0;
  let kpiAll = 0;
  let callsToday = 0;
  let callsWeek = 0;
  let callsAll = 0;

  for (const ev of events) {
    if (ev.event_name !== "generation_cost") continue;
    const cost_fen = asNonNegativeInt(ev.payload["cost_fen"]);
    const call_kind = String(ev.payload["call_kind"] ?? "unknown");
    const ts = new Date(ev.ts);
    if (Number.isNaN(ts.getTime())) continue;

    kpiAll += cost_fen;
    callsAll += 1;
    if (ts >= weekCutoff) {
      kpiWeek += cost_fen;
      callsWeek += 1;
    }
    const dayKey = isoDay(ts);
    if (dayKey === todayKey) {
      kpiToday += cost_fen;
      callsToday += 1;
    }

    const u = userTotals.get(ev.user_id) ?? { total_fen: 0, calls: 0, today_fen: 0 };
    u.total_fen += cost_fen;
    u.calls += 1;
    if (dayKey === todayKey) u.today_fen += cost_fen;
    userTotals.set(ev.user_id, u);

    const k = kindTotals.get(call_kind) ?? { total_fen: 0, calls: 0 };
    k.total_fen += cost_fen;
    k.calls += 1;
    kindTotals.set(call_kind, k);

    if (ts >= trendCutoff) {
      dailyTotals.set(dayKey, (dailyTotals.get(dayKey) ?? 0) + cost_fen);
    }
  }

  const by_user: UserCostRow[] = Array.from(userTotals.entries())
    .map(([user_id, v]) => {
      const today_cny = v.today_fen / 100;
      return {
        user_id,
        total_cny: v.total_fen / 100,
        calls: v.calls,
        today_cny,
        is_runaway_red: today_cny > red,
        is_runaway_amber: today_cny > amber && today_cny <= red,
      };
    })
    .sort((a, b) => b.total_cny - a.total_cny);

  const kindAllFen = Array.from(kindTotals.values()).reduce((s, v) => s + v.total_fen, 0);
  const by_kind: KindBreakdownRow[] = Array.from(kindTotals.entries())
    .map(([call_kind, v]) => ({
      call_kind,
      total_cny: v.total_fen / 100,
      calls: v.calls,
      share: kindAllFen > 0 ? v.total_fen / kindAllFen : 0,
    }))
    .sort((a, b) => b.total_cny - a.total_cny);

  const trend: DailyTrendPoint[] = [];
  for (let i = trendDays - 1; i >= 0; i -= 1) {
    const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
    const key = isoDay(d);
    trend.push({ date: key, cny: (dailyTotals.get(key) ?? 0) / 100 });
  }

  return {
    kpis: {
      today: kpiToday / 100,
      week: kpiWeek / 100,
      allTime: kpiAll / 100,
      callsToday,
      callsWeek,
      callsAllTime: callsAll,
    },
    by_user,
    by_kind,
    trend,
  };
}

function isoDay(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function asNonNegativeInt(v: unknown): number {
  if (typeof v === "number" && Number.isFinite(v) && v >= 0) return Math.floor(v);
  if (typeof v === "string") {
    const n = Number(v);
    if (Number.isFinite(n) && n >= 0) return Math.floor(n);
  }
  return 0;
}

export function useGenerationCost(options: UseGenerationCostOptions = {}): UseGenerationCostResult {
  const fetchLimit = options.fetchLimit ?? DEFAULT_FETCH_LIMIT;
  const trendDays = options.trendDays ?? DEFAULT_TREND_DAYS;
  const autoRefreshMs = options.autoRefreshMs;

  const [events, setEvents] = useState<EventRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    const page = await listEvents({ type: "generation_cost", limit: fetchLimit });
    setEvents(page.events);
    setIsLoading(false);
  }, [fetchLimit]);

  useEffect(() => {
    queueMicrotask(() => void refresh());
  }, [refresh]);

  useEffect(() => {
    if (!autoRefreshMs || autoRefreshMs <= 0) return;
    const id = setInterval(() => {
      void refresh();
    }, autoRefreshMs);
    return () => clearInterval(id);
  }, [autoRefreshMs, refresh]);

  const aggregate = useMemo(
    () =>
      aggregateCostEvents(events, {
        trendDays,
        runawayAmberCny: options.runawayAmberCny,
        runawayRedCny: options.runawayRedCny,
        now: options.now,
      }),
    [events, trendDays, options.runawayAmberCny, options.runawayRedCny, options.now],
  );

  return { ...aggregate, isLoading, refresh };
}
