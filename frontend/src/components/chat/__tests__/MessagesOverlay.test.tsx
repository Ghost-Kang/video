import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeAll } from "vitest";
import { MessagesOverlay, UserUrlBubble } from "../MessagesOverlay";
import { truncateUrlMiddle } from "../../../lib/urlDisplay";

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe("MessagesOverlay", () => {
  it("renders messages in a scrollable overlay above the dock", () => {
    render(
      <MessagesOverlay
        messages={[
          { role: "user", content: "https://www.douyin.com/video/1234567890123456789?share_token=abcdefghijklmnopqrstuvwxyz" },
          { role: "agent", content: "**好了**" },
        ]}
        streaming=""
        onClose={() => {}}
      />,
    );

    const overlay = screen.getByTestId("messages-overlay");
    expect(overlay).toBeInTheDocument();
    expect(overlay.className).toContain("bottom-[168px]");
    expect(screen.getByText("好了")).toBeInTheDocument();
    expect(screen.getByTestId("user-url-bubble")).toBeInTheDocument();
  });

  it("closes on backdrop click and Escape", () => {
    const onClose = vi.fn();
    render(<MessagesOverlay messages={[]} streaming="" onClose={onClose} />);

    fireEvent.mouseDown(screen.getByTestId("messages-overlay"));
    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(2);
  });
});

describe("UserUrlBubble", () => {
  it("does not truncate short URLs", () => {
    const url = "https://douyin.com/video/123";
    render(<UserUrlBubble url={url} />);
    expect(screen.getByTestId("user-url-bubble")).toHaveTextContent(url);
  });

  it("middle-ellipsizes long URLs and toggles full text on click", () => {
    const url =
      "https://www.douyin.com/video/7350123456789012345?modal_id=7350123456789012345&share_token=barbazquux";
    render(<UserUrlBubble url={url} />);

    const button = screen.getByTestId("user-url-bubble");
    expect(button).toHaveTextContent(truncateUrlMiddle(url));
    expect(button).not.toHaveTextContent(url);

    fireEvent.click(button);
    expect(button).toHaveTextContent(url);
  });
});
