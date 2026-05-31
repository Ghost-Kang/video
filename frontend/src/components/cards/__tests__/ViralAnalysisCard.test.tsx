import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ViralAnalysisCard } from "../ViralAnalysisCard";
import { MOCK_BAOMAM_ANALYSIS } from "../../../fixtures/baomamFushi001";
import { COPY, FORBIDDEN_TERMS } from "../../../lib/cardCopy";

describe("ViralAnalysisCard", () => {
  it("renders the 原视频脚本 entry and the card header", () => {
    render(<ViralAnalysisCard analysis={MOCK_BAOMAM_ANALYSIS} />);
    expect(screen.getByText(COPY.viral_header)).toBeInTheDocument();
    expect(screen.getByTestId("script-entry")).toHaveTextContent(COPY.script_entry);
  });

  it("opens the script drawer on entry click", () => {
    render(<ViralAnalysisCard analysis={MOCK_BAOMAM_ANALYSIS} />);
    expect(screen.queryByTestId("script-drawer")).toBeNull();
    fireEvent.click(screen.getByTestId("script-entry"));
    expect(screen.getByTestId("script-drawer")).toBeInTheDocument();
  });

  it("never displays forbidden schema terms", () => {
    const { container } = render(<ViralAnalysisCard analysis={MOCK_BAOMAM_ANALYSIS} />);
    const text = container.textContent || "";
    for (const term of FORBIDDEN_TERMS) {
      expect(text).not.toContain(term);
    }
  });
});
