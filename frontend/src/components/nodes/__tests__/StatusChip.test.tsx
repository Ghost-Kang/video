import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusChip } from "../StatusChip";
import type { CanvasNode } from "../../../types";

function makeNode(over: Partial<CanvasNode> = {}): CanvasNode {
  return {
    id: "n1",
    type: "image",
    title: "镜头 1",
    description: "",
    status: "pending",
    node_status: "reviewing",
    asset_status: "idle",
    result: null,
    needs_regen: false,
    subtype: null,
    shot_no: null,
    image_gen_provider: null,
    feedback: null,
    generation_status: "idle",
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

describe("StatusChip (单一状态芯片)", () => {
  it("needs_regen 最高优先 → 待重生告警", () => {
    render(<StatusChip node={makeNode({ needs_regen: true, asset_status: "done", node_status: "confirmed" })} />);
    expect(screen.getByTestId("status-chip")).toHaveTextContent("待重生");
    expect(screen.getByTestId("status-chip")).toHaveAttribute("data-state", "needs-regen");
  });

  it("生成中 → 呼吸态(composite 显示合成中)", () => {
    render(<StatusChip node={makeNode({ asset_status: "generating" })} />);
    expect(screen.getByTestId("status-chip")).toHaveTextContent("生成中");
    render(<StatusChip node={makeNode({ type: "composite", asset_status: "generating" })} />);
    expect(screen.getAllByTestId("status-chip").some((e) => e.textContent?.includes("合成中"))).toBe(true);
  });

  it("失败/超时 → 重试文案", () => {
    render(<StatusChip node={makeNode({ asset_status: "failed" })} />);
    expect(screen.getByTestId("status-chip")).toHaveTextContent("失败重试");
  });

  it("已生成 + 已确认 → ✓ 已确认", () => {
    render(<StatusChip node={makeNode({ asset_status: "done", node_status: "confirmed" })} />);
    expect(screen.getByTestId("status-chip")).toHaveTextContent("已确认");
  });

  it("已生成 + 待审 → 已生成", () => {
    render(<StatusChip node={makeNode({ asset_status: "done", node_status: "reviewing" })} />);
    expect(screen.getByTestId("status-chip")).toHaveTextContent("已生成");
  });

  it("无成品 + 待审(默认 script) → 待确认", () => {
    render(<StatusChip node={makeNode({ type: "script", asset_status: "idle", node_status: "reviewing" })} />);
    expect(screen.getByTestId("status-chip")).toHaveTextContent("待确认");
  });
});
