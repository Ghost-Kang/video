/**
 * W5D3 — agent_response 启发式触发 setFailure(client-synth)。
 *
 * 场景:后端 HardFailure 落到 agent_response (而不是结构化 failure)。
 * 前端检测 content 命中"请求超时/系统暂时繁忙",且此前 loading=true,
 * 就把它合成一个 FailurePayload,推 canvasStore.setFailure,顺手清 loading。
 * 这样 ChatPanel 立刻切到 failed 状态,不会和 95% 进度条共存。
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useCanvasStore } from "../canvasStore";
import { useWSStore, synthesizeFailureFromContent } from "../wsStore";

describe("wsStore agent_response → synthetic failure heuristic", () => {
  beforeEach(() => {
    useCanvasStore.getState().clear();
    useWSStore.setState({
      currentThreadId: "t1",
      loading: true,
      thinking: ["在拆解视频…"],
    });
  });

  afterEach(() => {
    useCanvasStore.getState().clear();
    useWSStore.setState({ loading: false, thinking: [] });
  });

  it("timeout content while loading → synthesizes S7_UPSTREAM_TIMEOUT + clears loading", () => {
    useWSStore.getState().dispatch(
      {
        type: "agent_response",
        thread_id: "t1",
        content: "请求超时,请检查后端是否正常运行",
      },
      "user_test",
    );
    // flush queueMicrotask
    return Promise.resolve().then(() => {
      const failure = useCanvasStore.getState().failure;
      expect(failure).not.toBeNull();
      expect(failure?.code).toBe("S7_UPSTREAM_TIMEOUT");
      // W5D3 — client-synthesized failures now carry empty request_id
      // (the "(client-synth)" sentinel was leaking into the diagnostic chip UI).
      expect(failure?.request_id).toBe("");
      expect(failure?.actions).toContain("RETRY_SAME_URL_AFTER_60S");
      expect(failure?.actions).toContain("PICK_FROM_FEATURED");
      expect(useWSStore.getState().loading).toBe(false);
      // 关键:不该把错误内容当成普通 agent 消息塞到聊天历史
      const msgs = useCanvasStore.getState().messages;
      expect(msgs.find((m) => m.content.includes("请求超时"))).toBeUndefined();
    });
  });

  it("'系统暂时繁忙' content → S8_UPSTREAM_REFUSED branch", () => {
    useWSStore.getState().dispatch(
      {
        type: "agent_response",
        thread_id: "t1",
        content: "系统暂时繁忙,稍后再来",
      },
      "user_test",
    );
    return Promise.resolve().then(() => {
      const failure = useCanvasStore.getState().failure;
      expect(failure?.code).toBe("S8_UPSTREAM_REFUSED");
    });
  });

  it("normal agent reply while NOT loading → no synthetic failure (refine answers safe)", () => {
    useWSStore.setState({ loading: false });
    useWSStore.getState().dispatch(
      {
        type: "agent_response",
        thread_id: "t1",
        // 包含"超时"但不是错误(比如分析里讨论 viral 超时机制) — 守卫:loading=false 不触发
        content: "这条视频的开头讲了请求超时的故事",
      },
      "user_test",
    );
    return Promise.resolve().then(() => {
      expect(useCanvasStore.getState().failure).toBeNull();
    });
  });

  it("synthesizeFailureFromContent is a pure helper exported for App-level timeout reuse", () => {
    const f = synthesizeFailureFromContent("请求超时,请检查后端");
    expect(f.code).toBe("S7_UPSTREAM_TIMEOUT");
    expect(f.actions.length).toBeGreaterThan(0);
    expect(f.hint).toBeTruthy();
  });
});
