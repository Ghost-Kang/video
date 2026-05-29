import { apiFetch } from "./apiClient";

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
