import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnchorBarChart } from "../AnchorBarChart";
import type { Anchor } from "../../../lib/anchorApi";

function anchor(overrides: Partial<Anchor> = {}): Anchor {
  return {
    id: "anc_" + Math.random().toString(36).slice(2, 10),
    kind: "character",
    label: "test",
    image_url: "",
    reuse_count: 0,
    created_at: "2026-05-19T00:00:00Z",
    ...overrides,
  };
}

describe("AnchorBarChart", () => {
  it("renders an empty state when no anchors", () => {
    render(<AnchorBarChart anchors={[]} />);
    expect(screen.getByText(/还没有素材可以统计/)).toBeInTheDocument();
  });

  it("renders bars sorted by reuse_count DESC", () => {
    const anchors = [
      anchor({ label: "low", reuse_count: 1 }),
      anchor({ label: "high", reuse_count: 9 }),
      anchor({ label: "mid", reuse_count: 5 }),
    ];
    render(<AnchorBarChart anchors={anchors} />);
    const labels = screen.getAllByText(/^(low|high|mid)$/).map((n) => n.textContent);
    expect(labels).toEqual(["high", "mid", "low"]);
  });

  it("truncates to maxItems", () => {
    const anchors = Array.from({ length: 10 }, (_, i) =>
      anchor({ label: `a${i}`, reuse_count: i }),
    );
    render(<AnchorBarChart anchors={anchors} maxItems={3} />);
    expect(screen.getAllByText(/已用/)).toHaveLength(3);
  });

  it("uses fallback icon when image_url is empty", () => {
    const anchors = [anchor({ image_url: "" })];
    render(<AnchorBarChart anchors={anchors} />);
    // Fallback ImageIcon is svg; ensure no <img> is rendered
    expect(document.querySelector("img")).toBeNull();
  });

  it("renders an <img> when image_url is set", () => {
    const anchors = [anchor({ image_url: "https://cdn.example.com/img.png" })];
    render(<AnchorBarChart anchors={anchors} />);
    const img = document.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.getAttribute("src")).toBe("https://cdn.example.com/img.png");
  });
});
