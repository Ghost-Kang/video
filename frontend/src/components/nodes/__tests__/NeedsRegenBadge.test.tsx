import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeedsRegenBadge } from "../NeedsRegenBadge";
import type { CanvasNode } from "../../../types";

function makeNode(over: Partial<CanvasNode> = {}): CanvasNode {
  return {
    id: "n1",
    type: "image",
    title: "镜头 1",
    description: "",
    status: "pending",
    node_status: "confirmed",
    asset_status: "done",
    result: { url: "http://x/a.png" },
    needs_regen: false,
    subtype: null,
    shot_no: null,
    image_gen_provider: null,
    feedback: null,
    generation_status: "done",
    generation_task_id: null,
    generation_error: null,
    generation_attempt_count: 0,
    generation_lease_until: null,
    generation_next_retry_at: null,
    user_id: "u",
    thread_id: "t",
    x: 0,
    y: 0,
    ...over,
  };
}

describe("NeedsRegenBadge", () => {
  it("renders the stale badge when needs_regen is true", () => {
    render(<NeedsRegenBadge node={makeNode({ needs_regen: true })} />);
    expect(screen.getByTestId("needs-regen-badge")).toHaveTextContent("需重生");
  });

  it("renders nothing when needs_regen is false", () => {
    const { container } = render(<NeedsRegenBadge node={makeNode({ needs_regen: false })} />);
    expect(container.firstChild).toBeNull();
  });
});
