import { apiFetch } from "./apiClient";

/**
 * Fire-and-forget 埋点。失败(网络/鉴权)绝不影响用户体验 —— 静默吞掉。
 * 用 localStorage 里的 rhtv_user 作 user_id(与 buildDiagnostic 一致),取不到退 "default"。
 * 观测用,不在关键路径上。
 */
export function trackEvent(
  event_name: string,
  payload: Record<string, unknown> = {},
  runId?: string | null,
): void {
  let user_id = "default";
  try {
    user_id = localStorage.getItem("rhtv_user") || "default";
  } catch {
    /* private mode — fall back to default */
  }
  try {
    apiFetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_name, user_id, run_id: runId ?? null, payload }),
    }).catch(() => {
      /* 异步失败(网络/鉴权)静默吞 */
    });
  } catch {
    /* 同步异常(如测试环境无 fetch)也吞掉 —— 埋点绝不影响调用方控制流 */
  }
}

export interface EventRow {
  id: number;
  ts: string;
  event_name: string;
  user_id: string;
  run_id: string | null;
  payload: Record<string, unknown>;
}

export interface EventsPage {
  events: EventRow[];
  has_more: boolean;
  next_offset: number | null;
}

export interface ListEventsParams {
  limit?: number;
  offset?: number;
  type?: string;
  user_id?: string;
  since_ts?: string;
}

export async function listEvents(params: ListEventsParams = {}): Promise<EventsPage> {
  const qs = new URLSearchParams();
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  if (params.type) qs.set("type", params.type);
  if (params.user_id) qs.set("user_id", params.user_id);
  if (params.since_ts) qs.set("since_ts", params.since_ts);
  const url = qs.toString() ? `/api/events?${qs}` : "/api/events";
  const res = await apiFetch(url);
  if (!res.ok) {
    return { events: [], has_more: false, next_offset: null };
  }
  const body = (await res.json()) as Partial<EventsPage>;
  return {
    events: Array.isArray(body.events) ? body.events : [],
    has_more: Boolean(body.has_more),
    next_offset: body.next_offset ?? null,
  };
}
