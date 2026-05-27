import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TranscriptCard } from "../TranscriptCard";
import { COPY } from "../../../lib/cardCopy";

const LONG_TRANSCRIPT =
  "你家宝宝是不是也这样，怎么喂都不吃？\n试试换成苹果，颜色更亮宝宝更感兴趣\n蒸 8 分钟，又软又香\n看，张嘴了！这一勺下去妈妈眼泪都要出来了\n我哭了。你家宝宝几个月开始抢勺子的？评论区告诉我。";

describe("TranscriptCard", () => {
  it("renders nothing when transcript is empty", () => {
    const { container } = render(<TranscriptCard transcript="" />);
    expect(container.firstChild).toBeNull();
  });

  it("shows truncated preview by default with expand button", () => {
    render(<TranscriptCard transcript={LONG_TRANSCRIPT} />);
    expect(screen.getByText(COPY.transcript_header)).toBeInTheDocument();
    expect(screen.getByTestId("transcript-toggle-btn")).toHaveTextContent(
      COPY.transcript_expand
    );
    expect(screen.getByTestId("transcript-copy-btn")).toBeInTheDocument();
    // Preview shows truncated prefix; not the full body
    expect(screen.queryByText(LONG_TRANSCRIPT)).not.toBeInTheDocument();
  });

  it("expands to show full transcript when toggle clicked", () => {
    const { container } = render(<TranscriptCard transcript={LONG_TRANSCRIPT} />);
    fireEvent.click(screen.getByTestId("transcript-toggle-btn"));
    expect(screen.getByTestId("transcript-toggle-btn")).toHaveTextContent(
      COPY.transcript_collapse
    );
    // Full transcript inside <pre> — getByText normalizes whitespace, so check
    // raw textContent of the <pre> directly.
    const pre = container.querySelector("pre");
    expect(pre).not.toBeNull();
    expect(pre!.textContent).toBe(LONG_TRANSCRIPT);
  });
});
