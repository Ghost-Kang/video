import { describe, expect, it } from "vitest";
import { aggregateCostEvents } from "../useGenerationCost";
import type { EventRow } from "../../lib/eventsApi";

function ev(
  overrides: Partial<EventRow> & { cost_fen?: number; call_kind?: string; ts?: string; user_id?: string },
): EventRow {
  const { cost_fen, call_kind, ts, user_id, ...rest } = overrides;
  return {
    id: rest.id ?? Math.floor(Math.random() * 1e6),
    ts: ts ?? "2026-05-22T10:00:00Z",
    event_name: "generation_cost",
    user_id: user_id ?? "u_alpha",
    run_id: rest.run_id ?? "r1",
    payload: {
      run_id: rest.run_id ?? "r1",
      call_kind: call_kind ?? "analysis",
      provider: "fixture",
      model: "stub",
      cost_fen: cost_fen ?? 50,
      latency_ms: 0,
      tokens_in: null,
      tokens_out: null,
      outcome: "done",
    },
    ...rest,
  };
}

const NOW = () => new Date("2026-05-22T12:00:00Z");

describe("aggregateCostEvents", () => {
  it("sums KPIs across today / week / all_time and counts calls", () => {
    const events: EventRow[] = [
      ev({ ts: "2026-05-22T08:00:00Z", cost_fen: 100 }), // today
      ev({ ts: "2026-05-22T11:30:00Z", cost_fen: 250 }), // today
      ev({ ts: "2026-05-18T10:00:00Z", cost_fen: 200 }), // within week
      ev({ ts: "2026-05-05T10:00:00Z", cost_fen: 500 }), // outside week, in all_time
    ];
    const agg = aggregateCostEvents(events, { now: NOW });
    expect(agg.kpis.today).toBeCloseTo(3.5, 2);
    expect(agg.kpis.callsToday).toBe(2);
    expect(agg.kpis.week).toBeCloseTo(5.5, 2);
    expect(agg.kpis.callsWeek).toBe(3);
    expect(agg.kpis.allTime).toBeCloseTo(10.5, 2);
    expect(agg.kpis.callsAllTime).toBe(4);
  });

  it("groups by user with runaway thresholds applied to today's spend", () => {
    const events: EventRow[] = [
      ev({ user_id: "u_quiet", cost_fen: 100, ts: "2026-05-22T01:00:00Z" }),
      ev({ user_id: "u_amber", cost_fen: 600, ts: "2026-05-22T03:00:00Z" }),
      ev({ user_id: "u_red", cost_fen: 1200, ts: "2026-05-22T03:00:00Z" }),
      ev({ user_id: "u_red", cost_fen: 50, ts: "2026-05-21T10:00:00Z" }),
    ];
    const agg = aggregateCostEvents(events, { now: NOW });
    const byId = Object.fromEntries(agg.by_user.map((u) => [u.user_id, u]));
    expect(byId["u_quiet"].is_runaway_amber).toBe(false);
    expect(byId["u_quiet"].is_runaway_red).toBe(false);
    expect(byId["u_amber"].is_runaway_amber).toBe(true);
    expect(byId["u_amber"].is_runaway_red).toBe(false);
    expect(byId["u_red"].is_runaway_red).toBe(true);
    expect(byId["u_red"].today_cny).toBeCloseTo(12, 2);
    expect(byId["u_red"].total_cny).toBeCloseTo(12.5, 2);
    // Top-of-list is highest total
    expect(agg.by_user[0].user_id).toBe("u_red");
  });

  it("builds by_kind shares and a contiguous trend window padded with zeros", () => {
    const events: EventRow[] = [
      ev({ call_kind: "analysis", cost_fen: 300, ts: "2026-05-22T01:00:00Z" }),
      ev({ call_kind: "rewrite", cost_fen: 100, ts: "2026-05-22T01:00:00Z" }),
      ev({ call_kind: "rewrite", cost_fen: 100, ts: "2026-05-15T01:00:00Z" }),
      ev({ call_kind: "shot", cost_fen: 0, ts: "2026-05-22T01:00:00Z" }), // edge: zero-cost call still counts
    ];
    const agg = aggregateCostEvents(events, { now: NOW, trendDays: 5 });
    const kindMap = Object.fromEntries(agg.by_kind.map((k) => [k.call_kind, k]));
    expect(kindMap["analysis"].total_cny).toBeCloseTo(3, 2);
    expect(kindMap["rewrite"].total_cny).toBeCloseTo(2, 2);
    expect(kindMap["shot"].calls).toBe(1);
    // Shares sum to ~1
    const shareSum = agg.by_kind.reduce((s, k) => s + k.share, 0);
    expect(shareSum).toBeCloseTo(1, 5);
    // 5-day window: 2026-05-18 .. 2026-05-22 chronological
    expect(agg.trend).toHaveLength(5);
    expect(agg.trend[0].date).toBe("2026-05-18");
    expect(agg.trend[4].date).toBe("2026-05-22");
    // 2026-05-15 datapoint is outside the trend window, so its rewrite ¥1 doesn't show
    expect(agg.trend[4].cny).toBeCloseTo(4, 2); // 3 + 1 + 0 today
    expect(agg.trend[0].cny).toBe(0);
  });
});
