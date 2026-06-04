import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CardStack } from "../CardStack";
import { useCanvasStore } from "../../store/canvasStore";
import { useWSStore } from "../../store/wsStore";
import { MOCK_BAOMAM_ANALYSIS } from "../../fixtures/baomamFushi001";

beforeEach(() => {
  useCanvasStore.getState().clear();
  useWSStore.setState({ loading: false });
});

describe("CardStack — seed-canvas CTA (P0 bridge)", () => {
  it("shows the 做我的版本 CTA when analysis is present; clicking fires onSeedCanvas", () => {
    useCanvasStore.setState({ analysis: MOCK_BAOMAM_ANALYSIS });
    const onSeed = vi.fn();
    render(<CardStack onSeedCanvas={onSeed} />);
    const cta = screen.getByTestId("seed-canvas-cta");
    expect(cta).toHaveTextContent("在画布上做我的版本");
    fireEvent.click(cta);
    expect(onSeed).toHaveBeenCalledTimes(1);
  });

  it("does not render the CTA before an analysis exists (analyzing / idle)", () => {
    render(<CardStack onSeedCanvas={vi.fn()} />);
    expect(screen.queryByTestId("seed-canvas-cta")).toBeNull();
  });
});
