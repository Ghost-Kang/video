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
  filtersRef.current = filters;

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
