import { useCallback, useEffect, useRef, useState } from "react";
import { listEvents, type EventRow, type ListEventsParams } from "../lib/eventsApi";

export interface UseEventsOptions extends ListEventsParams {
  autoRefreshMs?: number;
}

export interface UseEventsResult {
  events: EventRow[];
  isLoading: boolean;
  hasMore: boolean;
  nextOffset: number | null;
  refresh: () => Promise<void>;
}

export function useEvents(options: UseEventsOptions = {}): UseEventsResult {
  const { autoRefreshMs, ...filters } = options;
  const [events, setEvents] = useState<EventRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState<number | null>(null);

  const filtersRef = useRef(filters);
  // latest-value ref:render 期写 ref 违反 react-hooks/refs(并发渲染下可能写入
  // 被丢弃渲染的值)。挪进 effect — 下面的首刷 effect 排在其后,顺序保证可见。
  useEffect(() => {
    filtersRef.current = filters;
  });

  const refresh = useCallback(async () => {
    setIsLoading(true);
    const page = await listEvents(filtersRef.current);
    setEvents(page.events);
    setHasMore(page.has_more);
    setNextOffset(page.next_offset);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    queueMicrotask(() => void refresh());
  }, [refresh, filters.type, filters.user_id, filters.limit, filters.offset, filters.since_ts]);

  useEffect(() => {
    if (!autoRefreshMs || autoRefreshMs <= 0) return;
    const id = setInterval(() => {
      void refresh();
    }, autoRefreshMs);
    return () => clearInterval(id);
  }, [autoRefreshMs, refresh]);

  return { events, isLoading, hasMore, nextOffset, refresh };
}
