import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalysisStatStrip } from "../AnalysisStatStrip";
import { MOCK_BAOMAM_ANALYSIS } from "../../../fixtures/baomamFushi001";
import { COPY } from "../../../lib/cardCopy";

describe("AnalysisStatStrip", () => {
  it("renders 镜头/时长/把握 stats with units", () => {
    render(<AnalysisStatStrip analysis={MOCK_BAOMAM_ANALYSIS} />);
    expect(screen.getByTestId("analysis-stat-strip")).toBeInTheDocument();
    expect(screen.getByText(COPY.stat_scenes)).toBeInTheDocument();
    expect(screen.getByText(COPY.stat_duration)).toBeInTheDocument();
    expect(screen.getByText(COPY.stat_confidence)).toBeInTheDocument();
    expect(screen.getByText("%")).toBeInTheDocument();
    expect(screen.getByText(COPY.stat_duration_unit)).toBeInTheDocument();
  });

  it("count-up shows the final scene count instantly without IntersectionObserver (test env)", () => {
    render(<AnalysisStatStrip analysis={MOCK_BAOMAM_ANALYSIS} />);
    expect(
      screen.getByText(String(MOCK_BAOMAM_ANALYSIS.scenes.length)),
    ).toBeInTheDocument();
  });
});
