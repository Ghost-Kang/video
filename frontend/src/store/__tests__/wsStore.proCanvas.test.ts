import { describe, it, expect, beforeEach } from "vitest";
import { useWSStore } from "../wsStore";
import type { WSEvent } from "../../types/ws";

/** session_state.pro_canvas_enabled 灰度下发 → wsStore.proCanvasEnabled(同 rewrite_enabled 先例)。 */
function ss(extra: object): WSEvent {
  return { type: "session_state", thread_id: "t1", messages: [], canvas: null, run_status: "idle", ...extra } as WSEvent;
}

beforeEach(() => {
  useWSStore.setState({ currentThreadId: "t1", proCanvasEnabled: undefined });
});

describe("session_state → proCanvasEnabled", () => {
  it("captures true", () => {
    useWSStore.getState().dispatch(ss({ pro_canvas_enabled: true }), "u1");
    expect(useWSStore.getState().proCanvasEnabled).toBe(true);
  });

  it("captures false (kill-switch off)", () => {
    useWSStore.setState({ proCanvasEnabled: true });
    useWSStore.getState().dispatch(ss({ pro_canvas_enabled: false }), "u1");
    expect(useWSStore.getState().proCanvasEnabled).toBe(false);
  });

  it("stays undefined when an old backend omits the field", () => {
    useWSStore.getState().dispatch(ss({}), "u1");
    expect(useWSStore.getState().proCanvasEnabled).toBeUndefined();
  });
});
