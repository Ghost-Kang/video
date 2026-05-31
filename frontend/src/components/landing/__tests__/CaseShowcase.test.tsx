import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CaseShowcase } from "../CaseShowcase";
import { SAMPLE_CASES } from "../../../lib/sampleCases";

const sample = SAMPLE_CASES[0];

describe("CaseShowcase", () => {
  it("renders the case + its first shot slide + one dot per slide", () => {
    render(<CaseShowcase sample={sample} onPick={() => {}} />);
    expect(screen.getByTestId("case-showcase")).toBeInTheDocument();
    expect(screen.getByText(new RegExp(sample.category))).toBeInTheDocument();
    expect(screen.getByText(sample.slides![0].theme)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /第 \d+ 幕/ }).length).toBe(
      sample.slides!.length,
    );
  });

  it("jumps to a slide on dot click, and opens the case on body click", () => {
    const onPick = vi.fn();
    render(<CaseShowcase sample={sample} onPick={onPick} />);
    // dot 3 → shows slide 3's theme
    fireEvent.click(screen.getByRole("button", { name: "第 3 幕" }));
    expect(screen.getByText(sample.slides![2].theme)).toBeInTheDocument();
    expect(onPick).not.toHaveBeenCalled(); // dot click doesn't open

    fireEvent.click(screen.getByTestId("case-showcase"));
    expect(onPick).toHaveBeenCalledWith(sample);
  });
});
