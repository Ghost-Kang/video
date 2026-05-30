/**
 * W5D3 layout reform — ChatPanel renders as a bottom-docked strip
 * (full-width, max-h-[50vh]) instead of the old 360px right rail.
 * Long URLs in user bubbles get break-all so they don't overflow.
 */

import { describe, it, expect, vi, beforeAll } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ChatPanel } from "../ChatPanel";

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const baseProps = {
  streaming: "",
  thinking: [],
  onSend: () => {},
  onToggleCollapse: () => {},
};

describe("ChatPanel dock layout (W5D3)", () => {
  it("renders a full-width dock container with bottom-dock geometry, not a 360px right rail", () => {
    render(
      <ChatPanel
        {...baseProps}
        messages={[]}
        loading={false}
        analysis={null}
        script=""
        failure={null}
      />
    );
    const dock = screen.getByTestId("dock-chat");
    expect(dock).toBeInTheDocument();
    // Class signal: full-width + top border + max-h cap, not w-[360px] + border-l.
    expect(dock.className).toContain("w-full");
    expect(dock.className).toContain("border-t");
    expect(dock.className).toContain("max-h-[50vh]");
    expect(dock.className).not.toContain("w-[360px]");
    // state attribute lets layout-sizing CSS rules key off state if needed.
    expect(dock).toHaveAttribute("data-state", "idle");
  });

  it("keeps history out of the dock until the overlay is toggled open", () => {
    const longDouyinUrl =
      "https://www.douyin.com/video/7350123456789012345?modal_id=7350123456789012345&from_user=foo&share_token=barbazquux";
    render(
      <ChatPanel
        {...baseProps}
        messages={[{ role: "user", content: longDouyinUrl }]}
        loading={true}
        analysis={null}
        script=""
        failure={null}
      />
    );
    expect(screen.queryByTestId("messages-overlay")).not.toBeInTheDocument();
    expect(screen.queryByText(longDouyinUrl)).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("history-toggle"));

    expect(screen.getByTestId("messages-overlay")).toBeInTheDocument();
    const bubble = screen.getByTestId("chat-user-bubble");
    expect(bubble).not.toHaveTextContent(longDouyinUrl);
    expect(bubble.className).toContain("overflow-hidden");
  });

  it("Escape collapses the dock when focus is not in a text field", () => {
    const onToggleCollapse = vi.fn();
    render(
      <ChatPanel
        {...baseProps}
        onToggleCollapse={onToggleCollapse}
        messages={[]}
        loading={false}
        analysis={null}
        script=""
        failure={null}
      />
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onToggleCollapse).toHaveBeenCalledOnce();
  });

  it("failed sample retry clears failure UI and sends a sample URL", () => {
    const onSend = vi.fn();
    render(
      <ChatPanel
        {...baseProps}
        onSend={onSend}
        messages={[{ role: "agent", content: "failed" }]}
        loading={false}
        analysis={null}
        script=""
        failure={{
          code: "S7_UPSTREAM_TIMEOUT",
          hint: "拆解超时了",
          actions: ["PICK_FROM_FEATURED"],
          request_id: "req_test",
        }}
      />
    );

    fireEvent.click(screen.getByLabelText("试一条 宝妈辅食 爆款"));
    // 时长验证过的 in-range 样本(62.6s),见 SampleUrlChips。
    expect(onSend).toHaveBeenCalledWith("https://www.douyin.com/video/7616954826602428411");
  });
});
