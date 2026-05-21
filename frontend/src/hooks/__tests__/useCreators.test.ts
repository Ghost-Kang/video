import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { deriveStatus, useCreators } from "../useCreators";
import type { Creator } from "../../lib/creatorsApi";

let mockCreators: Creator[] = [];

vi.mock("../../lib/creatorsApi", () => ({
  listCreators: vi.fn(async () => mockCreators),
}));

function creator(overrides: Partial<Creator> = {}): Creator {
  return {
    user_id: "u_" + Math.random().toString(36).slice(2, 10),
    first_seen: "2026-05-20T08:00:00Z",
    last_seen: "2026-05-21T08:00:00Z",
    runs_started: 0,
    rewrites_completed: 0,
    publish_packs_copied: 0,
    anchors_count: 0,
    anchors_total_reuse_count: 0,
    interview_logged: false,
    ...overrides,
  };
}

describe("deriveStatus", () => {
  it("invited when no activity", () => {
    expect(deriveStatus(creator())).toBe("invited");
  });
  it("registered after first run", () => {
    expect(deriveStatus(creator({ runs_started: 1 }))).toBe("registered");
  });
  it("rewritten after a rewrite", () => {
    expect(deriveStatus(creator({ runs_started: 1, rewrites_completed: 1 }))).toBe("rewritten");
  });
  it("published after publish pack copied", () => {
    expect(
      deriveStatus(
        creator({ runs_started: 1, rewrites_completed: 1, publish_packs_copied: 1 }),
      ),
    ).toBe("published");
  });
  it("looping once any anchor reuse fires", () => {
    expect(
      deriveStatus(
        creator({
          runs_started: 1,
          rewrites_completed: 1,
          publish_packs_copied: 1,
          anchors_total_reuse_count: 1,
        }),
      ),
    ).toBe("looping");
  });
});

describe("useCreators", () => {
  beforeEach(() => {
    mockCreators = [];
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("exposes empty state cleanly", async () => {
    const { result } = renderHook(() => useCreators());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.creators).toEqual([]);
    expect(result.current.total).toBe(0);
  });

  it("returns the backend's order (already sorted by last_seen DESC)", async () => {
    mockCreators = [
      creator({ user_id: "u_recent", last_seen: "2026-05-21T12:00:00Z" }),
      creator({ user_id: "u_older", last_seen: "2026-05-20T12:00:00Z" }),
    ];
    const { result } = renderHook(() => useCreators());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.creators[0].user_id).toBe("u_recent");
    expect(result.current.creators[1].user_id).toBe("u_older");
  });

  it("filters by user_id substring", async () => {
    mockCreators = [
      creator({ user_id: "u_alpha" }),
      creator({ user_id: "u_beta" }),
      creator({ user_id: "u_alphax" }),
    ];
    const { result } = renderHook(() => useCreators({ search: "alpha" }));
    await waitFor(() => expect(result.current.creators.length).toBe(2));
  });

  it("filters by status pill", async () => {
    mockCreators = [
      creator({ user_id: "u_inv" }),
      creator({ user_id: "u_run", runs_started: 1 }),
      creator({ user_id: "u_loop", runs_started: 3, anchors_total_reuse_count: 2 }),
    ];
    const { result } = renderHook(() => useCreators({ statusFilter: "looping" }));
    await waitFor(() => expect(result.current.creators.length).toBe(1));
    expect(result.current.creators[0].user_id).toBe("u_loop");
  });

  it("counts per status across all creators (not filtered)", async () => {
    mockCreators = [
      creator(),
      creator({ runs_started: 1 }),
      creator({ runs_started: 1, rewrites_completed: 1 }),
      creator({ runs_started: 1, rewrites_completed: 1, publish_packs_copied: 1 }),
      creator({ anchors_total_reuse_count: 4 }),
    ];
    const { result } = renderHook(() => useCreators({ statusFilter: "invited" }));
    await waitFor(() => expect(result.current.total).toBe(5));
    expect(result.current.counts.invited).toBe(1);
    expect(result.current.counts.registered).toBe(1);
    expect(result.current.counts.rewritten).toBe(1);
    expect(result.current.counts.published).toBe(1);
    expect(result.current.counts.looping).toBe(1);
  });
});
