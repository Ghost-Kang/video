import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnchorSidebar } from "../AnchorSidebar";

describe("AnchorSidebar", () => {
  it("renders mocked anchors", async () => {
    render(<AnchorSidebar />);
    expect(await screen.findByText("小张妈妈")).toBeInTheDocument();
    expect(await screen.findByText("厨房")).toBeInTheDocument();
  });
});
