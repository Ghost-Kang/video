/**
 * W5D4 P1 — the agent_response content-regex failure heuristic was REMOVED.
 *
 * Old behavior (W5D3): if an agent_response arrived while loading and its text
 * matched /请求超时|处理出错|系统暂时繁忙/, the client fabricated a FailurePayload.
 * That false-positived on legitimate answers mentioning those words. With P0-A
 * (structured analysis_failed delivered via live registry) + P0-B (failure
 * persisted in run_lifecycle for replay), the backend always sends a real
 * failure frame, so agent_response is always a success. These tests pin the new
 * behavior: a reply containing "请求超时" no longer flips to failed.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useCanvasStore } from "../canvasStore";
import { useWSStore, synthesizeClientTimeout } from "../wsStore";

describe("wsStore agent_response (post-P1: no content-regex synthesis)", () => {
  beforeEach(() => {
    useCanvasStore.getState().clear();
    useWSStore.setState({
      currentThreadId: "t1",
      loading: true,
      thinking: ["在拆解视频…"],
      pendingByThread: {},
    });
  });

  afterEach(() => {
    useCanvasStore.getState().clear();
    useWSStore.setState({ loading: false, thinking: [] });
  });

  it("agent_response containing '请求超时' while loading does NOT synthesize a failure", () => {
    useWSStore.getState().dispatch(
      { type: "agent_response", thread_id: "t1", content: "请求超时,请检查后端是否正常运行" },
      "user_test",
    );
    return Promise.resolve().then(() => {
      // No fabricated failure — backend would have sent analysis_failed instead.
      expect(useCanvasStore.getState().failure).toBeNull();
      // loading cleared, reply treated as a normal (successful) answer.
      expect(useWSStore.getState().loading).toBe(false);
    });
  });

  it("a normal reply mentioning 处理出错 is NOT misclassified as failed", () => {
    useWSStore.getState().dispatch(
      { type: "agent_response", thread_id: "t1", content: "这条视频开头讲了处理出错的搞笑故事" },
      "user_test",
    );
    return Promise.resolve().then(() => {
      expect(useCanvasStore.getState().failure).toBeNull();
    });
  });

  it("synthesizeClientTimeout is a pure literal helper (no content arg)", () => {
    const f = synthesizeClientTimeout();
    expect(f.code).toBe("S7_UPSTREAM_TIMEOUT");
    expect(f.request_id).toBe("__client_synth__");
    expect(f.actions).toContain("RETRY_SAME_URL_AFTER_60S");
    expect(f.hint).toBeTruthy();
  });

  it("a real analysis_failed frame still drives setFailure", () => {
    useWSStore.getState().dispatch(
      {
        type: "analysis_failed",
        thread_id: "t1",
        code: "S7_UPSTREAM_TIMEOUT",
        hint: "上游超时",
        actions: ["RETRY_SAME_URL_AFTER_60S"],
        request_id: "abc123",
        stage: "analysis",
      } as never,
      "user_test",
    );
    return Promise.resolve().then(() => {
      const f = useCanvasStore.getState().failure;
      expect(f?.code).toBe("S7_UPSTREAM_TIMEOUT");
      expect(f?.request_id).toBe("abc123"); // real backend id, not client-synth
    });
  });
});
