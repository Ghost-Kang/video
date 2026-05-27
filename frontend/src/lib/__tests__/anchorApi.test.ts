import { describe, expect, it, vi } from "vitest";
import { createAnchor, listAnchors, reuseAnchor } from "../anchorApi";

describe("anchorApi", () => {
  it("lists with kind query", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("[]", { status: 200 }));
    await listAnchors("character");
    expect(fetchSpy).toHaveBeenCalledWith("/api/anchors?kind=character");
    fetchSpy.mockRestore();
  });

  it("accepts wrapped anchor list responses", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ anchors: [{ id: "anc_1", kind: "character", label: "妈妈", image_url: "", reuse_count: 0, created_at: "2026-05-20T00:00:00Z" }] }), {
        status: 200,
      }),
    );
    await expect(listAnchors("character")).resolves.toEqual([
      { id: "anc_1", kind: "character", label: "妈妈", image_url: "", reuse_count: 0, created_at: "2026-05-20T00:00:00Z" },
    ]);
    fetchSpy.mockRestore();
  });

  it("creates and reuses with expected urls", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200 }));
    await createAnchor({ kind: "scene", label: "厨房", image_url: "" });
    await reuseAnchor("anc_1", { user_id: "u", reused_in_run_id: "r", reused_in_shot_index: 1 });
    expect(fetchSpy).toHaveBeenCalledWith("/api/anchors", expect.objectContaining({ method: "POST" }));
    expect(fetchSpy).toHaveBeenCalledWith("/api/anchors/anc_1/reuse", expect.objectContaining({ method: "POST" }));
    fetchSpy.mockRestore();
  });
});
