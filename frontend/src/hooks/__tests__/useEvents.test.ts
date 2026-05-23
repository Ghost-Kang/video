import { renderHook, waitFor, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEvents } from "../useEvents";
import type { EventRow, EventsPage } from "../../lib/eventsApi";

const listEventsMock = vi.fn<(args?: unknown) => Promise<EventsPage>>();

vi.mock("../../lib/eventsApi", () => ({
  listEvents: (args: unknown) => listEventsMock(args),
}));

function row(overrides: Partial<EventRow> = {}): EventRow {
  return {
    id: 1,
    ts: "2026-05-22T10:00:00Z",
    event_name: "run_started",
    user_id: "u_alpha",
    run_id: "r1",
    payload: {},
    ...overrides,
  };
}

describe("useEvents", () => {
  beforeEach(() => {
    listEventsMock.mockReset();
    listEventsMock.mockResolvedValue({ events: [], has_more: false, next_offset: null });
  });
  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("loads initial page on mount", async () => {
    listEventsMock.mockResolvedValueOnce({
      events: [row({ id: 2, event_name: "consent_accepted" })],
      has_more: false,
      next_offset: null,
    });
    const { result } = renderHook(() => useEvents());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.events).toHaveLength(1);
    expect(result.current.events[0].event_name).toBe("consent_accepted");
    expect(listEventsMock).toHaveBeenCalled();
  });

  it("re-fetches when type filter changes", async () => {
    const { rerender } = renderHook(({ type }: { type?: string }) => useEvents({ type }), {
      initialProps: {},
    });
    await waitFor(() => expect(listEventsMock).toHaveBeenCalledTimes(1));
    rerender({ type: "run_started" });
    await waitFor(() => expect(listEventsMock).toHaveBeenCalledTimes(2));
    const lastCallArg = listEventsMock.mock.calls[1][0] as { type?: string };
    expect(lastCallArg.type).toBe("run_started");
  });

  it("auto-refreshes on interval and refresh() manually reloads", async () => {
    vi.useFakeTimers();
    listEventsMock.mockResolvedValue({ events: [], has_more: false, next_offset: null });
    const { result } = renderHook(() => useEvents({ autoRefreshMs: 1000 }));
    await vi.waitFor(() => expect(listEventsMock).toHaveBeenCalledTimes(1));
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    await vi.waitFor(() => expect(listEventsMock).toHaveBeenCalledTimes(2));
    await act(async () => {
      await result.current.refresh();
    });
    expect(listEventsMock).toHaveBeenCalledTimes(3);
  });
});
