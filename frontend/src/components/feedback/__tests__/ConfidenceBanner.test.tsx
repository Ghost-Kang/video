import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConfidenceBanner } from "../ConfidenceBanner";

describe("ConfidenceBanner", () => {
  it("shows when confidence is low", () => {
    render(<ConfidenceBanner confidence={0.3} />);
    expect(screen.getByText(/把握一般/)).toBeInTheDocument();
  });

  it("hides when confidence is high", () => {
    const { container } = render(<ConfidenceBanner confidence={0.8} />);
    expect(container.textContent).toBe("");
  });
});
