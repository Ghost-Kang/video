import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useShowcaseCases } from "../useShowcaseCases";
import { SAMPLE_CASES } from "../../lib/sampleCases";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useShowcaseCases", () => {
  it("starts with seed cases immediately (first paint, no wait)", () => {
    vi.spyOn(global, "fetch").mockImplementation(() => new Promise(() => {})); // never resolves
    const { result } = renderHook(() => useShowcaseCases());
    expect(result.current).toEqual(SAMPLE_CASES);
  });

  it("merges fetched DB cases with seeds, deduped by source_url (DB first)", async () => {
    const dbCase = {
      id: "auto-x",
      source_url: "https://www.douyin.com/video/AUTO",
      category: "自动案例",
      hook: "h",
      slides: [{ clip: "/m/a/1.mp4", poster: "", theme: "t", note: "n" }],
    };
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ cases: [dbCase] }),
    } as Response);

    const { result } = renderHook(() => useShowcaseCases());
    await waitFor(() => expect(result.current[0].id).toBe("auto-x"));
    // DB case first, then all seeds (none share the AUTO url)
    expect(result.current.length).toBe(1 + SAMPLE_CASES.length);
    expect(result.current[0].source_url).toBe("https://www.douyin.com/video/AUTO");
  });

  it("DB case with same source_url as a seed overrides the seed (no dup)", async () => {
    const seedUrl = SAMPLE_CASES[0].source_url;
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ cases: [{ id: "auto-dup", source_url: seedUrl, category: "X", hook: "h", slides: [] }] }),
    } as Response);

    const { result } = renderHook(() => useShowcaseCases());
    await waitFor(() => expect(result.current.some((c) => c.id === "auto-dup")).toBe(true));
    // total = seeds count (the dup seed replaced by DB version, others appended)
    expect(result.current.length).toBe(SAMPLE_CASES.length);
    const urls = result.current.map((c) => c.source_url);
    expect(urls.filter((u) => u === seedUrl).length).toBe(1); // no duplicate url
  });

  it("falls back to seeds when fetch fails", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("network"));
    const { result } = renderHook(() => useShowcaseCases());
    // stays seeds (give the rejected promise a tick)
    await new Promise((r) => setTimeout(r, 0));
    expect(result.current).toEqual(SAMPLE_CASES);
  });

  it("falls back to seeds when DB returns empty list", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ cases: [] }),
    } as Response);
    const { result } = renderHook(() => useShowcaseCases());
    await new Promise((r) => setTimeout(r, 0));
    expect(result.current).toEqual(SAMPLE_CASES);
  });
});
