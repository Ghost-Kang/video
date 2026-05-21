import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WarningChip } from "../WarningChip";

describe("WarningChip", () => {
  it("filters info severity", () => {
    const { container } = render(<WarningChip warning={{ code: "W1_AUTO_ID", field: "", message: "", severity: "info" }} />);
    expect(container.textContent).toBe("");
  });

  it("renders warn severity", () => {
    render(<WarningChip warning={{ code: "W2_FALLBACK_USED", field: "", message: "", severity: "warn" }} />);
    expect(screen.getByText(/通用判断/)).toBeInTheDocument();
  });

  it("renders error severity with red style", () => {
    const { container } = render(<WarningChip warning={{ code: "W2_FALLBACK_USED", field: "", message: "", severity: "error" }} />);
    expect(container.innerHTML).toContain("bg-red-50");
  });
});
