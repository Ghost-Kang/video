/**
 * wsStore P0-C — per-thread frame buffering instead of silent drop.
 *
 * The thread guard used to `return` (drop) any frame whose thread_id != the
 * current thread. A mid-run redirect/session-switch therefore discarded the
 * running thread's analysis_progress/analysis_returned → blank/卡死. Now such
 * frames are buffered per thread and replayed when the user switches to it.
 */

import { beforeEach, describe, expect, it } from "vitest";
import { useWSStore } from "../wsStore";
import { useCanvasStore } from "../canvasStore";
import { useSessionStore } from "../sessionStore";

describe("wsStore P0-C per-thread buffering", () => {
  beforeEach(() => {
    localStorage.clear();
    useSessionStore.getState().reset();
    useSessionStore.getState().setUserId("u1");
    useWSStore.setState({ currentThreadId: "tA", pendingByThread: {} });
    useCanvasStore.getState().clear?.();
  });

  it("buffers a frame for a non-current thread instead of dropping it", () => {
    // Current thread is tA; a frame for tB arrives.
    useWSStore.getState().dispatch(
      { type: "analysis_progress", thread_id: "tB", stage: "ark_overlay", percent: 50, eta_seconds: 10, detail: "" } as never,
      "u1",
    );
    const pending = useWSStore.getState().pendingByThread;
    expect(pending.tB).toHaveLength(1);
    // current thread state untouched
    expect(useWSStore.getState().progressPercent).toBeNull();
  });

  it("drains buffered frames in order when switching to that thread", () => {
    // Buffer two progress frames for tB while on tA.
    useWSStore.getState().dispatch(
      { type: "analysis_progress", thread_id: "tB", stage: "resolve_url", percent: 10, eta_seconds: 50, detail: "" } as never,
      "u1",
    );
    useWSStore.getState().dispatch(
      { type: "analysis_progress", thread_id: "tB", stage: "ark_overlay", percent: 80, eta_seconds: 5, detail: "" } as never,
      "u1",
    );
    expect(useWSStore.getState().pendingByThread.tB).toHaveLength(2);

    // Switch to tB → drain. Last drained progress wins.
    useWSStore.getState().setCurrentThreadId("tB");
    expect(useWSStore.getState().pendingByThread.tB).toBeUndefined();
    expect(useWSStore.getState().progressPercent).toBe(80);
  });

  it("caps a bucket at 200 (drop-oldest)", () => {
    for (let i = 0; i < 250; i++) {
      useWSStore.getState().dispatch(
        { type: "analysis_progress", thread_id: "tB", stage: "ark_overlay", percent: i % 100, eta_seconds: 1, detail: String(i) } as never,
        "u1",
      );
    }
    expect(useWSStore.getState().pendingByThread.tB).toHaveLength(200);
    // oldest dropped: the first buffered detail "0" is gone, "249" retained
    const details = useWSStore.getState().pendingByThread.tB.map((e: any) => e.detail);
    expect(details).not.toContain("0");
    expect(details[details.length - 1]).toBe("249");
  });

  it("current-thread frames still dispatch normally (not buffered)", () => {
    useWSStore.getState().dispatch(
      { type: "analysis_progress", thread_id: "tA", stage: "ark_overlay", percent: 42, eta_seconds: 8, detail: "" } as never,
      "u1",
    );
    expect(useWSStore.getState().progressPercent).toBe(42);
    expect(useWSStore.getState().pendingByThread.tA).toBeUndefined();
  });
});
