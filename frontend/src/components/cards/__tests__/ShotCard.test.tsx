import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ShotCard } from "../ShotCard";
import { MOCK_BAOMAM_ANALYSIS } from "../../../fixtures/baomamFushi001";
import { COPY, FORBIDDEN_TERMS } from "../../../lib/cardCopy";
import type { Scene } from "../../../types/cascade";

describe("ShotCard", () => {
  const scene = MOCK_BAOMAM_ANALYSIS.scenes[0];

  it("shows placeholder when dialogue is empty", () => {
    const emptyDialogue: Scene = {
      ...scene,
      dialogue_and_narration: "   ",
    };
    render(<ShotCard scene={emptyDialogue} />);
    expect(screen.getByText(COPY.shot_dialogue_placeholder)).toBeInTheDocument();
  });

  it("renders anchor action buttons", () => {
    render(<ShotCard scene={scene} />);
    expect(screen.getByRole("button", { name: COPY.change_character })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: COPY.reuse_scene })).toBeInTheDocument();
  });

  it("anchor buttons open picker", async () => {
    const user = userEvent.setup();
    render(<ShotCard scene={scene} />);
    await user.click(screen.getByRole("button", { name: COPY.change_character }));
    expect(await screen.findByText(COPY.anchor_picker_title)).toBeInTheDocument();
  });

  it("contains no forbidden terms in rendered output", () => {
    const { container } = render(<ShotCard scene={scene} />);
    const text = container.textContent ?? "";
    for (const term of FORBIDDEN_TERMS) {
      expect(text).not.toMatch(new RegExp(term, "i"));
    }
  });
});
