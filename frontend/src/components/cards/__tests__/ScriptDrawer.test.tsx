import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScriptDrawer } from "../ScriptDrawer";
import { MOCK_BAOMAM_ANALYSIS } from "../../../fixtures/baomamFushi001";
import { COPY, FORBIDDEN_TERMS } from "../../../lib/cardCopy";

describe("ScriptDrawer", () => {
  it("shows both tabs and defaults to the shot-script tab", () => {
    render(<ScriptDrawer analysis={MOCK_BAOMAM_ANALYSIS} onClose={() => {}} />);
    expect(screen.getByRole("tab", { name: COPY.script_tab_shots })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: COPY.script_tab_transcript })).toBeInTheDocument();
  });

  it("switches to the transcript tab on click", () => {
    render(<ScriptDrawer analysis={MOCK_BAOMAM_ANALYSIS} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: COPY.script_tab_transcript }));
    expect(screen.getByRole("tab", { name: COPY.script_tab_transcript })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("Escape closes the drawer", () => {
    const onClose = vi.fn();
    render(<ScriptDrawer analysis={MOCK_BAOMAM_ANALYSIS} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("never displays forbidden schema terms", () => {
    const { container } = render(
      <ScriptDrawer analysis={MOCK_BAOMAM_ANALYSIS} onClose={() => {}} />,
    );
    const text = container.textContent || "";
    for (const term of FORBIDDEN_TERMS) {
      expect(text).not.toContain(term);
    }
  });
});
