import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NicheCTA } from "../NicheCTA";
import { COPY, FORBIDDEN_TERMS } from "../../../lib/cardCopy";

describe("NicheCTA", () => {
  it("renders header, hint, and three niche chips", () => {
    render(<NicheCTA onPick={() => {}} />);
    expect(screen.getByText(COPY.rewrite_cta_header)).toBeInTheDocument();
    expect(screen.getByText(COPY.rewrite_cta_hint)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /宝妈辅食/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /育儿日常/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /家庭厨房/ })).toBeInTheDocument();
  });

  it("invokes onPick with the niche id when a chip is clicked", () => {
    const onPick = vi.fn();
    render(<NicheCTA onPick={onPick} />);
    fireEvent.click(screen.getByRole("button", { name: /宝妈辅食/ }));
    expect(onPick).toHaveBeenCalledWith("baomam_fushi");

    fireEvent.click(screen.getByRole("button", { name: /家庭厨房/ }));
    expect(onPick).toHaveBeenCalledWith("jiating_chufang");
  });

  it("contains no forbidden terms", () => {
    const { container } = render(<NicheCTA onPick={() => {}} />);
    const text = container.textContent ?? "";
    for (const term of FORBIDDEN_TERMS) {
      expect(text).not.toMatch(new RegExp(term, "i"));
    }
  });
});
