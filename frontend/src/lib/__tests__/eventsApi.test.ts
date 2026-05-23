import { describe, expect, it, vi } from "vitest";
import { listEvents } from "../eventsApi";

describe("listEvents", () => {
  it("composes query string from filters", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ events: [], has_more: false, next_offset: null }), { status: 200 })
    );
    await listEvents({ limit: 50, type: "run_started", user_id: "u_alpha" });
    const calledWith = fetchSpy.mock.calls[0][0] as string;
    expect(calledWith.startsWith("/api/events?")).toBe(true);
    expect(calledWith).toContain("limit=50");
    expect(calledWith).toContain("type=run_started");
    expect(calledWith).toContain("user_id=u_alpha");
    fetchSpy.mockRestore();
  });

  it("returns empty page when backend responds with 500", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("oops", { status: 500 }));
    const page = await listEvents();
    expect(page.events).toEqual([]);
    expect(page.has_more).toBe(false);
    expect(page.next_offset).toBeNull();
    fetchSpy.mockRestore();
  });

  it("parses normal response into typed page", async () => {
    const payload = {
      events: [
        {
          id: 1,
          ts: "2026-05-22T10:00:00Z",
          event_name: "consent_accepted",
          user_id: "u_alpha",
          run_id: null,
          payload: { version: "v0" },
        },
      ],
      has_more: true,
      next_offset: 200,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 })
    );
    const page = await listEvents();
    expect(page.events).toHaveLength(1);
    expect(page.events[0].event_name).toBe("consent_accepted");
    expect(page.has_more).toBe(true);
    expect(page.next_offset).toBe(200);
    fetchSpy.mockRestore();
  });
});
