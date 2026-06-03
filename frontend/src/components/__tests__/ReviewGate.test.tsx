import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { ReviewGate } from "../ReviewGate";
import { useReviewStore, type PendingReview } from "../../store/reviewStore";

const review: PendingReview = {
  threadId: "t1",
  summary: "待你确认：生成镜头 2 的草稿图（约 ¥1.5）",
  interruptId: "int_1",
  reviews: [
    {
      tool: "cascade_generate_first_frame",
      label: "生成镜头 2 的草稿图（约 ¥1.5）",
      args: { rewrite_id: "rw_1", shot_index: 2 },
      allowed_decisions: ["approve", "edit", "reject"],
    },
  ],
};

beforeEach(() => useReviewStore.setState({ pending: null }));

describe("ReviewGate", () => {
  it("renders nothing when there is no pending review", () => {
    const { container } = render(<ReviewGate threadId="t1" sendCommand={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when the pending review belongs to a different thread", () => {
    useReviewStore.setState({ pending: review });
    const { container } = render(<ReviewGate threadId="other" sendCommand={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows summary + review labels for the current thread", () => {
    useReviewStore.setState({ pending: review });
    render(<ReviewGate threadId="t1" sendCommand={vi.fn()} />);
    expect(screen.getByTestId("review-gate")).toBeInTheDocument();
    // label appears in both summary + list; scope to the list to assert uniquely.
    const list = screen.getByTestId("review-gate-list");
    expect(within(list).getByText(/镜头 2 的草稿图/)).toBeInTheDocument();
  });

  it("approve sends one approve decision per review and clears the gate", () => {
    useReviewStore.setState({ pending: review });
    const send = vi.fn();
    render(<ReviewGate threadId="t1" sendCommand={send} />);
    fireEvent.click(screen.getByTestId("review-gate-approve"));
    expect(send).toHaveBeenCalledWith({
      type: "review_decision",
      thread_id: "t1",
      decisions: [{ type: "approve" }],
      interrupt_id: "int_1",
    });
    expect(useReviewStore.getState().pending).toBeNull();
  });

  it("reject sends reject decisions and clears the gate", () => {
    useReviewStore.setState({ pending: review });
    const send = vi.fn();
    render(<ReviewGate threadId="t1" sendCommand={send} />);
    fireEvent.click(screen.getByTestId("review-gate-reject"));
    expect(send).toHaveBeenCalledWith({
      type: "review_decision",
      thread_id: "t1",
      decisions: [{ type: "reject" }],
      interrupt_id: "int_1",
    });
    expect(useReviewStore.getState().pending).toBeNull();
  });

  it("emits exactly N decisions for N gated calls (order/count must match backend)", () => {
    useReviewStore.setState({
      pending: {
        threadId: "t1",
        summary: "导演想执行 2 步生成",
        interruptId: "int_2",
        reviews: [
          { tool: "cascade_generate_first_frame", label: "镜头 1 草稿图", args: {}, allowed_decisions: ["approve", "reject"] },
          { tool: "cascade_generate_shot_video", label: "镜头 1 视频", args: {}, allowed_decisions: ["approve", "reject"] },
        ],
      },
    });
    const send = vi.fn();
    render(<ReviewGate threadId="t1" sendCommand={send} />);
    fireEvent.click(screen.getByTestId("review-gate-approve"));
    expect(send).toHaveBeenCalledWith({
      type: "review_decision",
      thread_id: "t1",
      decisions: [{ type: "approve" }, { type: "approve" }],
      interrupt_id: "int_2",
    });
  });
});
