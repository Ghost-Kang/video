/**
 * Bugfix regression (萌宠 case) — inter-stage progress creep.
 *
 * The backend emits at stage boundaries (5% resolve_url → 15% ark_overlay → …).
 * Between boundaries there can be a long silence (a v.douyin.com short-link
 * resolve does a 302-follow + SSR scrape, ~10-20s at 5%). Previously percent was
 * pinned to the last real value, so the bar FROZE between stages = "进入拆解后
 * 没显示进度". Fix: creep from the last real percent toward the next boundary as
 * time passes, so the bar always inches forward.
 */

import { describe, it, expect, vi, beforeAll, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { AnalysisProgress } from "../chat/AnalysisProgress";
import { useWSStore } from "../../store/wsStore";
import { useCanvasStore } from "../../store/canvasStore";

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

afterEach(() => {
  vi.useRealTimers();
  useCanvasStore.getState().clear();
  // reset progress so other tests aren't polluted
  useWSStore.setState({
    progressStage: null,
    progressPercent: null,
    progressEta: null,
    progressDetail: "",
  });
});

function pctFromBar(): number {
  const bar = screen.getByRole("progressbar");
  return Number(bar.getAttribute("aria-valuenow"));
}

describe("AnalysisProgress inter-stage creep (萌宠 bugfix)", () => {
  it("creeps forward while stuck at the 5% resolve stage, never reaching 15%", () => {
    vi.useFakeTimers();
    // Backend pushed only the first frame: 5% resolve_url, then silence.
    useWSStore.setState({
      progressStage: "resolve_url",
      progressPercent: 5,
      progressEta: 55,
      progressDetail: "拉抖音 CDN 直链",
    });

    render(<AnalysisProgress thinking={[]} startedAtMs={Date.now()} />);
    const initial = pctFromBar();
    expect(initial).toBe(5); // starts at the real value

    // Advance 20s of silence (the slow short-link resolve window).
    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    const crept = pctFromBar();
    expect(crept).toBeGreaterThan(5); // bar moved — NOT frozen (the bug)
    expect(crept).toBeLessThan(15); // but never overshoots the next real stage
  });

  it("a new real frame (15%) advances past the creep ceiling", () => {
    vi.useFakeTimers();
    useWSStore.setState({ progressStage: "resolve_url", progressPercent: 5, progressEta: 55, progressDetail: "" });
    render(<AnalysisProgress thinking={[]} startedAtMs={Date.now()} />);

    act(() => {
      vi.advanceTimersByTime(20_000);
    });
    // backend's next stage lands
    act(() => {
      useWSStore.setState({ progressStage: "ark_overlay", progressPercent: 15, progressEta: 50, progressDetail: "" });
      vi.advanceTimersByTime(600);
    });
    expect(pctFromBar()).toBeGreaterThanOrEqual(15);
  });
});
