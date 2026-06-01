import { describe, it, expect, vi, beforeAll, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { CaseShowcaseRow } from "../CaseShowcaseRow";
import { SAMPLE_CASES } from "../../../lib/sampleCases";
import type { SampleCase } from "../../../lib/sampleCases";

// matchMedia stub — default NOT reduced, NOT mobile (so desktop perPage applies).
beforeAll(() => {
  if (!window.matchMedia) {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    });
  }
});

afterEach(() => vi.useRealTimers());

function fakeCase(id: string): SampleCase {
  return {
    id,
    source_url: `https://www.douyin.com/video/${id}`,
    category: `品类-${id}`,
    hook: `钩子-${id}`,
    slides: [
      { clip: `/m/${id}/1.mp4`, poster: `/m/${id}/1.jpg`, theme: `幕1-${id}`, note: "n" },
    ],
  };
}

describe("CaseShowcaseRow", () => {
  it("renders EVERY case as a video CaseShowcase card (fix: 萌宠 also shows video)", () => {
    // both real cases (tongnian + menchong) have slides → both must render as video cards
    render(<CaseShowcaseRow cases={SAMPLE_CASES} onPick={() => {}} />);
    const cards = screen.getAllByTestId("case-showcase");
    // perPage desktop = 2, and there are exactly 2 real cases → both visible on page 1
    expect(cards.length).toBe(Math.min(2, SAMPLE_CASES.length));
    // each visible card actually has a <video> (the bug was menchong rendered a
    // static card with no video). jsdom: not reduced-motion → <video> path.
    for (const card of cards) {
      expect(card.querySelector("video")).not.toBeNull();
    }
  });

  it("no pagination dots when all cases fit one page (≤2 desktop)", () => {
    render(<CaseShowcaseRow cases={[fakeCase("a"), fakeCase("b")]} onPick={() => {}} />);
    expect(screen.queryByRole("tablist", { name: "案例分页" })).not.toBeInTheDocument();
  });

  it("paginates when cases exceed one page, and dot click switches page", () => {
    const cases = [fakeCase("a"), fakeCase("b"), fakeCase("c"), fakeCase("d"), fakeCase("e")];
    render(<CaseShowcaseRow cases={cases} onPick={() => {}} perPageDesktop={2} />);
    // 5 cases / 2 per page = 3 pages → 3 dots
    const tabs = screen.getAllByRole("tab");
    expect(tabs.length).toBe(3);
    // page 1 shows a, b
    expect(screen.getByText("品类-a")).toBeInTheDocument();
    expect(screen.getByText("品类-b")).toBeInTheDocument();
    expect(screen.queryByText("品类-c")).not.toBeInTheDocument();
    // click page 2 → shows c, d
    fireEvent.click(screen.getByRole("tab", { name: "第 2 页案例" }));
    expect(screen.getByText("品类-c")).toBeInTheDocument();
    expect(screen.getByText("品类-d")).toBeInTheDocument();
    expect(screen.queryByText("品类-a")).not.toBeInTheDocument();
    // click page 3 → shows the lone e
    fireEvent.click(screen.getByRole("tab", { name: "第 3 页案例" }));
    expect(screen.getByText("品类-e")).toBeInTheDocument();
  });

  it("auto-rotates pages on a timer", () => {
    vi.useFakeTimers();
    const cases = [fakeCase("a"), fakeCase("b"), fakeCase("c"), fakeCase("d")];
    render(<CaseShowcaseRow cases={cases} onPick={() => {}} perPageDesktop={2} />);
    expect(screen.getByText("品类-a")).toBeInTheDocument();
    // advance past PAGE_ADVANCE_MS → page 2 (c, d)
    act(() => {
      vi.advanceTimersByTime(9100);
    });
    expect(screen.getByText("品类-c")).toBeInTheDocument();
  });

  it("renders nothing for empty cases", () => {
    const { container } = render(<CaseShowcaseRow cases={[]} onPick={() => {}} />);
    expect(container.firstChild).toBeNull();
  });
});
