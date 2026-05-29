/**
 * W5D3 — 95% pin escape:进度卡 95% 卡 > 90 秒 → 弹软警告 + 两个按钮。
 * 点「换一条」合成 failure → ChatPanel 会切到 failed。
 * 点「继续等」沉默 60 秒。
 */

import { describe, it, expect, vi, beforeAll, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AnalysisProgress } from "../chat/AnalysisProgress";
import { useCanvasStore } from "../../store/canvasStore";

beforeAll(() => {
  // matchMedia stub for prefersReducedMotion — default to NOT reduced.
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

describe("AnalysisProgress 95% pin escape (W5D3)", () => {
  beforeEach(() => {
    useCanvasStore.getState().clear();
  });

  afterEach(() => {
    useCanvasStore.getState().clear();
  });

  it("does NOT render pin-escape warning when fresh (just started)", () => {
    render(<AnalysisProgress thinking={[]} startedAtMs={Date.now()} />);
    expect(screen.queryByTestId("pin-escape")).not.toBeInTheDocument();
  });

  it("renders pin-escape warning when elapsed > 90s AND progress is pinned at 95%", () => {
    // 100s ago → percent caps at 95, elapsed >= threshold.
    // Need elapsed ≥ 120s so the % asymptote caps at 95 (80 + (60/60)*15).
    // 200s is safely past both the 90s threshold AND the 120s saturation point.
    const startedAtMs = Date.now() - 200_000;
    render(<AnalysisProgress thinking={[]} startedAtMs={startedAtMs} />);
    const escape = screen.getByTestId("pin-escape");
    expect(escape).toBeInTheDocument();
    expect(escape).toHaveTextContent("比预期慢");
    expect(screen.getByTestId("pin-escape-switch")).toBeInTheDocument();
    expect(screen.getByTestId("pin-escape-wait")).toBeInTheDocument();
  });

  it("clicking 换一条 synthesizes a failure on canvasStore (ChatPanel will flip to failed)", () => {
    // Need elapsed ≥ 120s so the % asymptote caps at 95 (80 + (60/60)*15).
    // 200s is safely past both the 90s threshold AND the 120s saturation point.
    const startedAtMs = Date.now() - 200_000;
    render(<AnalysisProgress thinking={[]} startedAtMs={startedAtMs} />);
    fireEvent.click(screen.getByTestId("pin-escape-switch"));
    const failure = useCanvasStore.getState().failure;
    expect(failure).not.toBeNull();
    expect(failure?.code).toBe("S7_UPSTREAM_TIMEOUT");
    // W5D3 P2 — client-synth failures carry CLIENT_SYNTH_REQUEST_ID sentinel
    expect(failure?.request_id).toBe("__client_synth__");
  });

  it("clicking 继续等 hides the warning (snoozed)", () => {
    // Need elapsed ≥ 120s so the % asymptote caps at 95 (80 + (60/60)*15).
    // 200s is safely past both the 90s threshold AND the 120s saturation point.
    const startedAtMs = Date.now() - 200_000;
    render(<AnalysisProgress thinking={[]} startedAtMs={startedAtMs} />);
    expect(screen.getByTestId("pin-escape")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("pin-escape-wait"));
    expect(screen.queryByTestId("pin-escape")).not.toBeInTheDocument();
    // failure was NOT set
    expect(useCanvasStore.getState().failure).toBeNull();
  });
});
