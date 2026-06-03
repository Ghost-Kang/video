import { describe, it, expect, beforeEach } from "vitest";
import { useWSStore } from "../wsStore";
import { useReviewStore } from "../reviewStore";
import type { WSEvent } from "../../types/ws";

beforeEach(() => {
  useReviewStore.setState({ pending: null });
  useWSStore.setState({ currentThreadId: "t1", loading: true, thinking: ["在生成…"] });
});

describe("wsStore review_required dispatch", () => {
  it("stores the pending review and clears the spinner", () => {
    const ev: WSEvent = {
      type: "review_required",
      thread_id: "t1",
      reviews: [
        {
          tool: "cascade_generate_shot_video",
          label: "把镜头 3 生成视频（约 ¥1.5）",
          args: { rewrite_id: "rw_1", shot_index: 3 },
          allowed_decisions: ["approve", "reject"],
        },
      ],
      summary: "待你确认：把镜头 3 生成视频（约 ¥1.5）",
      interrupt_id: "int_abc",
    };
    useWSStore.getState().dispatch(ev, "u1");

    const pending = useReviewStore.getState().pending;
    expect(pending?.threadId).toBe("t1");
    expect(pending?.reviews[0].tool).toBe("cascade_generate_shot_video");
    expect(pending?.summary).toContain("镜头 3");
    expect(pending?.interruptId).toBe("int_abc");
    // paused turn must drop the spinner (it's waiting on the user, not the model)
    expect(useWSStore.getState().loading).toBe(false);
    expect(useWSStore.getState().thinking).toEqual([]);
  });

  it("buffers a review_required for a non-current thread (not applied until switch)", () => {
    useWSStore.setState({ currentThreadId: "current" });
    const ev: WSEvent = {
      type: "review_required",
      thread_id: "other",
      reviews: [],
      summary: "",
      interrupt_id: "int_other",
    };
    useWSStore.getState().dispatch(ev, "u1");
    // P0-C buffering: held, not applied to reviewStore until the user switches.
    expect(useReviewStore.getState().pending).toBeNull();

    // switching to "other" drains the buffer → the review is applied.
    useWSStore.getState().setCurrentThreadId("other");
    expect(useReviewStore.getState().pending?.threadId).toBe("other");
  });

  it("session_state clears a stale review when the thread is no longer awaiting review", () => {
    useReviewStore.setState({
      pending: { threadId: "t1", summary: "x", reviews: [] },
    });
    const ev: WSEvent = {
      type: "session_state",
      thread_id: "t1",
      messages: [],
      canvas: null,
      run_status: "done",
    };
    useWSStore.getState().dispatch(ev, "u1");
    expect(useReviewStore.getState().pending).toBeNull();
  });
});
