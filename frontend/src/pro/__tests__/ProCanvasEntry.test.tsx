import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProCanvasEntry } from "../ProCanvasEntry";
import { useWSStore } from "../../store/wsStore";

beforeEach(() => useWSStore.setState({ proCanvasEnabled: undefined, currentThreadId: "t1" }));

describe("ProCanvasEntry gating", () => {
  it("hidden when flag undefined (old backend / not loaded)", () => {
    render(<ProCanvasEntry />);
    expect(screen.queryByTestId("pro-canvas-entry")).toBeNull();
  });

  it("hidden when flag explicitly off", () => {
    useWSStore.setState({ proCanvasEnabled: false });
    render(<ProCanvasEntry />);
    expect(screen.queryByTestId("pro-canvas-entry")).toBeNull();
  });

  it("hidden without an active threadId", () => {
    useWSStore.setState({ proCanvasEnabled: true, currentThreadId: "" });
    render(<ProCanvasEntry />);
    expect(screen.queryByTestId("pro-canvas-entry")).toBeNull();
  });

  it("shows toolbar entry linking to /pro/:threadId when enabled", () => {
    useWSStore.setState({ proCanvasEnabled: true, currentThreadId: "t1" });
    render(<ProCanvasEntry />);
    const a = screen.getByTestId("pro-canvas-entry") as HTMLAnchorElement;
    expect(a.getAttribute("href")).toBe("/pro/t1");
  });

  it("card variant links with ?seed=analysis:<id>", () => {
    useWSStore.setState({ proCanvasEnabled: true, currentThreadId: "t1" });
    render(<ProCanvasEntry variant="card" analysisId="ana_x" />);
    const a = screen.getByTestId("pro-canvas-expand") as HTMLAnchorElement;
    expect(a.textContent).toContain("展开为计算图");
    expect(a.getAttribute("href")).toBe("/pro/t1?seed=analysis:ana_x");
  });
});
