import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatPanel } from "../ChatPanel";
import { COPY } from "../../lib/cardCopy";

beforeAll(() => {
  // jsdom 不实现 scrollIntoView,ChatPanel 在 useEffect 里调用会爆。
  Element.prototype.scrollIntoView = vi.fn();
});

describe("ChatPanel ask chip", () => {
  const baseProps = {
    streaming: "",
    thinking: [],
    loading: false,
    onToggleCollapse: () => {},
  };

  it("does not show ask chip when message list empty (still onboarding)", () => {
    render(<ChatPanel {...baseProps} messages={[]} onSend={() => {}} />);
    // Empty state shows sample URL chips, not ask chip — ask chip is for
    // post-analysis follow-up only.
    expect(screen.queryByTestId("ask-chip")).not.toBeInTheDocument();
  });

  it("shows ask chip after user has sent a message + opens textarea on click", () => {
    render(
      <ChatPanel
        {...baseProps}
        messages={[{ role: "user", content: "https://www.douyin.com/video/123" }]}
        onSend={() => {}}
      />
    );

    const chip = screen.getByTestId("ask-chip");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveTextContent(COPY.ask_chip_label);

    fireEvent.click(chip);
    expect(screen.getByTestId("ask-textarea")).toBeInTheDocument();
    expect(screen.getByTestId("ask-submit")).toBeInTheDocument();
  });

  it("sends [ask: <question>] prefixed message on submit", () => {
    const onSend = vi.fn();
    render(
      <ChatPanel
        {...baseProps}
        messages={[{ role: "user", content: "first" }]}
        onSend={onSend}
      />
    );

    fireEvent.click(screen.getByTestId("ask-chip"));
    fireEvent.change(screen.getByTestId("ask-textarea"), {
      target: { value: "这条 BGM 给人什么感觉?" },
    });
    fireEvent.click(screen.getByTestId("ask-submit"));

    expect(onSend).toHaveBeenCalledWith("[ask: 这条 BGM 给人什么感觉?]");
    // Textarea + submit hidden after send (panel collapses)
    expect(screen.queryByTestId("ask-textarea")).not.toBeInTheDocument();
  });
});
