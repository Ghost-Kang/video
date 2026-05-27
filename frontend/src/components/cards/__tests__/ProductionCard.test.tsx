import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProductionCard } from "../ProductionCard";
import { COPY, FORBIDDEN_TERMS } from "../../../lib/cardCopy";
import type { ProductionDim } from "../../../types/cascade";

const SOLO: ProductionDim = {
  cost_tier: "solo_phone",
  estimated_hours: 2.5,
  replaceable_anchors: ["原片厨房 → 你的厨房", "原片宝宝餐椅 → 你家同款"],
};

const TEAM_NO_ANCHORS: ProductionDim = {
  cost_tier: "small_team",
  estimated_hours: 8,
  replaceable_anchors: [],
};

describe("ProductionCard", () => {
  it("renders cost tier chip + hours + replaceable anchors", () => {
    render(<ProductionCard production={SOLO} />);

    expect(screen.getByText(COPY.production_header)).toBeInTheDocument();
    expect(screen.getByText(COPY.production_cost_solo)).toBeInTheDocument();
    expect(screen.getByText(`2.5${COPY.production_hours_suffix}`)).toBeInTheDocument();
    expect(screen.getByText(COPY.production_replaceable_header)).toBeInTheDocument();
    expect(screen.getByText(SOLO.replaceable_anchors[0])).toBeInTheDocument();
  });

  it("hides replaceable section when anchors empty + shows team label", () => {
    render(<ProductionCard production={TEAM_NO_ANCHORS} />);
    expect(screen.getByText(COPY.production_cost_team)).toBeInTheDocument();
    expect(screen.queryByText(COPY.production_replaceable_header)).not.toBeInTheDocument();
  });

  it("never displays forbidden schema terms", () => {
    const { container } = render(<ProductionCard production={SOLO} />);
    const text = container.textContent || "";
    for (const term of FORBIDDEN_TERMS) {
      expect(text).not.toContain(term);
    }
  });
});
