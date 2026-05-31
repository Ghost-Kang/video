import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SampleCaseCarousel } from "../SampleCaseCarousel";
import { SAMPLE_CASES } from "../../../lib/sampleCases";
import { COPY } from "../../../lib/cardCopy";

describe("SampleCaseCarousel", () => {
  it("renders each configured real case with its hook insight", () => {
    render(<SampleCaseCarousel onPick={() => {}} />);
    expect(SAMPLE_CASES.length).toBeGreaterThan(0);
    for (const c of SAMPLE_CASES) {
      expect(screen.getByText(new RegExp(c.category))).toBeInTheDocument();
    }
    // tag + cta present
    expect(screen.getAllByText(COPY.sample_case_tag).length).toBe(SAMPLE_CASES.length);
  });

  it("calls onPick with the case (real source_url) on click", () => {
    const onPick = vi.fn();
    render(<SampleCaseCarousel onPick={onPick} />);
    fireEvent.click(screen.getByText(new RegExp(SAMPLE_CASES[0].category)));
    expect(onPick).toHaveBeenCalledWith(SAMPLE_CASES[0]);
    expect(SAMPLE_CASES[0].source_url).toMatch(/douyin\.com\/video\//);
  });
});
