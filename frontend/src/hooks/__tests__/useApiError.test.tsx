import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useApiError } from "../useApiError";
import { useCanvasStore } from "../../store/canvasStore";

describe("useApiError", () => {
  it("sets parsed failure payload on 4xx", async () => {
    const failure = { code: "S1_NO_SOURCE_URL", hint: "hint", actions: ["REPORT"], request_id: "req_1" };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(failure), { status: 422, headers: { "Content-Type": "application/json" } })
    );
    const { result } = renderHook(() => useApiError());
    await expect(result.current.wrappedFetch("/x")).rejects.toMatchObject(failure);
    expect(useCanvasStore.getState().failure?.request_id).toBe("req_1");
    vi.restoreAllMocks();
  });

  it("falls back for non-json errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("nope", { status: 500 }));
    const { result } = renderHook(() => useApiError());
    await expect(result.current.wrappedFetch("/x")).rejects.toMatchObject({ code: "S5_INVALID_PAYLOAD" });
    vi.restoreAllMocks();
  });
});
