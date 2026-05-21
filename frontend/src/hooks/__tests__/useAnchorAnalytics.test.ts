import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAnchorAnalytics } from "../useAnchorAnalytics";
import type { Anchor } from "../../lib/anchorApi";

let mockAnchors: Anchor[] = [];

vi.mock("../../lib/anchorApi", () => ({
  listAnchors: vi.fn(async (kind?: "character" | "scene") => {
    if (!kind) return mockAnchors;
    return mockAnchors.filter((a) => a.kind === kind);
  }),
}));

function anchor(overrides: Partial<Anchor> = {}): Anchor {
  return {
    id: "anc_" + Math.random().toString(36).slice(2, 10),
    kind: "character",
    label: "test",
    image_url: "",
    reuse_count: 0,
    created_at: "2026-05-19T00:00:00Z",
    ...overrides,
  };
}

describe("useAnchorAnalytics", () => {
  beforeEach(() => {
    mockAnchors = [];
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("reports zero stats on empty response", async () => {
    const { result } = renderHook(() => useAnchorAnalytics());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.totalAnchors).toBe(0);
    expect(result.current.totalReuses).toBe(0);
    expect(result.current.topByReuse).toEqual([]);
  });

  it("aggregates totals from a mixed list", async () => {
    mockAnchors = [
      anchor({ kind: "character", reuse_count: 5 }),
      anchor({ kind: "character", reuse_count: 2 }),
      anchor({ kind: "scene", reuse_count: 0 }),
    ];
    const { result } = renderHook(() => useAnchorAnalytics());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.totalAnchors).toBe(3);
    expect(result.current.totalReuses).toBe(7);
    expect(result.current.avgReuseCount).toBeCloseTo(7 / 3, 2);
    expect(result.current.maxReuseCount).toBe(5);
  });

  it("builds a distribution histogram", async () => {
    mockAnchors = [
      anchor({ reuse_count: 0 }),
      anchor({ reuse_count: 0 }),
      anchor({ reuse_count: 1 }),
      anchor({ reuse_count: 1 }),
      anchor({ reuse_count: 3 }),
      anchor({ reuse_count: 5 }),
    ];
    const { result } = renderHook(() => useAnchorAnalytics());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.distribution[0]).toBe(2);
    expect(result.current.distribution[1]).toBe(2);
    expect(result.current.distribution[3]).toBe(1);
    expect(result.current.distribution[5]).toBe(1);
  });

  it("splits aggregates by kind", async () => {
    mockAnchors = [
      anchor({ kind: "character", reuse_count: 3 }),
      anchor({ kind: "character", reuse_count: 1 }),
      anchor({ kind: "scene", reuse_count: 2 }),
    ];
    const { result } = renderHook(() => useAnchorAnalytics());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.byKind.character.total).toBe(2);
    expect(result.current.byKind.character.totalReuses).toBe(4);
    expect(result.current.byKind.scene.total).toBe(1);
    expect(result.current.byKind.scene.totalReuses).toBe(2);
  });

  it("returns Infinity ratio when no scenes exist", async () => {
    mockAnchors = [anchor({ kind: "character" })];
    const { result } = renderHook(() => useAnchorAnalytics());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.ratioCharacterToScene).toBe(Infinity);
  });

  it("returns zero ratio when no characters exist", async () => {
    mockAnchors = [anchor({ kind: "scene" })];
    const { result } = renderHook(() => useAnchorAnalytics());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.ratioCharacterToScene).toBe(0);
  });
});
