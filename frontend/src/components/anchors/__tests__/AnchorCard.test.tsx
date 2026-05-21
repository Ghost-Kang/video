import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnchorCard } from "../AnchorCard";
import type { Anchor } from "../../../lib/anchorApi";

function makeAnchor(overrides: Partial<Anchor> = {}): Anchor {
  return {
    id: "anc_test",
    kind: "character",
    label: "测试角色",
    image_url: "",
    reuse_count: 0,
    created_at: "2026-05-21T00:00:00Z",
    ...overrides,
  };
}

describe("AnchorCard", () => {
  it("hides the reuse pill when reuse_count is 0", () => {
    render(<AnchorCard anchor={makeAnchor({ reuse_count: 0 })} />);
    expect(screen.queryByText(/已用/)).not.toBeInTheDocument();
  });

  it("renders the pill with 已用 1 when reuse_count is 1", () => {
    render(<AnchorCard anchor={makeAnchor({ reuse_count: 1 })} />);
    expect(screen.getByText("已用 1")).toBeInTheDocument();
  });

  it("renders the pill with the actual count for higher values", () => {
    render(<AnchorCard anchor={makeAnchor({ reuse_count: 99 })} />);
    expect(screen.getByText("已用 99")).toBeInTheDocument();
  });

  it("exposes the count via aria-label for accessibility", () => {
    render(<AnchorCard anchor={makeAnchor({ reuse_count: 7 })} />);
    expect(screen.getByLabelText("已用 7 次")).toBeInTheDocument();
  });
});
