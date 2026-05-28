import { describe, it, expect } from "vitest";
import {
  deriveChatPanelState,
  type ChatPanelInputs,
} from "../chatPanelState";
import type { FailurePayload } from "../../types/cascade";

function inputs(over: Partial<ChatPanelInputs> = {}): ChatPanelInputs {
  return {
    analysis: null,
    script: "",
    loading: false,
    failure: null,
    messagesLength: 0,
    ...over,
  };
}

const FAILURE: FailurePayload = {
  code: "S4_SCENES_LEN_OUT_OF_RANGE",
  hint: "h",
  actions: ["RETRY_WITH_NEW_URL"],
  request_id: "req_1",
};

describe("deriveChatPanelState", () => {
  it("idle when nothing happening", () => {
    expect(deriveChatPanelState(inputs())).toBe("idle");
  });

  it("running when loading flag is set", () => {
    expect(deriveChatPanelState(inputs({ loading: true }))).toBe("running");
  });

  it("failed when failure payload present (even if loading)", () => {
    expect(
      deriveChatPanelState(inputs({ loading: true, failure: FAILURE }))
    ).toBe("failed");
  });

  it("ready when analysis present but no script", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const analysis = { analysis_id: "x" } as any;
    expect(deriveChatPanelState(inputs({ analysis }))).toBe("ready");
  });

  it("refine when script is non-empty (rewrite has landed)", () => {
    expect(deriveChatPanelState(inputs({ script: "hello" }))).toBe("refine");
  });

  it("refine beats ready when both analysis + script present", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const analysis = { analysis_id: "x" } as any;
    expect(
      deriveChatPanelState(inputs({ analysis, script: "改完的" }))
    ).toBe("refine");
  });

  it("running when messagesLength>0 but no analysis/script/failure yet (post-send pre-ack)", () => {
    expect(deriveChatPanelState(inputs({ messagesLength: 1 }))).toBe("running");
  });
});
