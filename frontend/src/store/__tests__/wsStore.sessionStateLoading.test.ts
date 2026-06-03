import { describe, it, expect, beforeEach } from "vitest";
import { useWSStore } from "../wsStore";
import { useCanvasStore } from "../canvasStore";
import type { WSEvent } from "../../types/ws";

/**
 * Regression — landing「点案例」后分析中 AnalyzingHero 被收掉、卡静态 idle 屏。
 *
 * 根因:/chat/<新会话> mount 同时 (a) 发 get_session_state (b) auto-send 分析
 * setLoading(true)。后端对**新会话**答 get_session_state = run_status "idle"
 * (还没 run 行),旧逻辑 `rs !== "running"` 把刚点亮的 loading 清掉 → AnalyzingHero
 * 塌回静态屏,直到 S7 超时。"idle" 不能区分「从没跑」和「客户端刚发起、服务端还没记」,
 * 所以 session_state "idle" **不该**清 loading —— 由真正的终态帧接管。
 */
function ss(run_status: string, failure?: object): WSEvent {
  return {
    type: "session_state",
    thread_id: "t1",
    messages: [],
    canvas: null,
    run_status,
    ...(failure ? { failure } : {}),
  } as WSEvent;
}

beforeEach(() => {
  useWSStore.setState({ currentThreadId: "t1", loading: true, thinking: ["分析中…"] });
  useCanvasStore.setState({ failure: null });
});

describe("session_state run_status → loading", () => {
  it("does NOT clear loading on 'idle' (the case-click race fix)", () => {
    useWSStore.getState().dispatch(ss("idle"), "u1");
    expect(useWSStore.getState().loading).toBe(true); // AnalyzingHero stays up
  });

  it("leaves loading untouched on 'running'", () => {
    useWSStore.getState().dispatch(ss("running"), "u1");
    expect(useWSStore.getState().loading).toBe(true);
  });

  it("clears loading on terminal 'done'", () => {
    useWSStore.getState().dispatch(ss("done"), "u1");
    expect(useWSStore.getState().loading).toBe(false);
  });

  it("clears loading on 'failed' (with payload)", () => {
    useWSStore.getState().dispatch(
      ss("failed", { code: "S7_UPSTREAM_TIMEOUT", hint: "超时", actions: ["RETRY_SAME_URL"], request_id: "" }),
      "u1",
    );
    expect(useWSStore.getState().loading).toBe(false);
  });

  it("clears loading on 'awaiting_review' (review card replaces the spinner)", () => {
    useWSStore.getState().dispatch(ss("awaiting_review"), "u1");
    expect(useWSStore.getState().loading).toBe(false);
  });
});
