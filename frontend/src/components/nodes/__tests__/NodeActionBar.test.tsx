import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NodeActionBar } from "../NodeActionBar";
import { NodeActionsContext } from "../../../lib/nodeActionsContext";
import type { NodeActions } from "../../../hooks/useNodeActions";
import type { CanvasNode } from "../../../types";

// NodeToolbar 依赖 ReactFlow store(portal + 节点上下文),单元测试里直接透传 children,
// 隔离我们真正要验证的「重生 vs 生成」路由逻辑。
vi.mock("@xyflow/react", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  NodeToolbar: ({ children, isVisible }: any) => (isVisible ? children : null),
  Position: { Top: "top", Left: "left", Right: "right", Bottom: "bottom" },
}));

function makeNode(over: Partial<CanvasNode> = {}): CanvasNode {
  return {
    id: "n1",
    type: "image",
    title: "镜头 1",
    description: "a cat",
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

function makeActions(over: Partial<NodeActions> = {}): NodeActions {
  return {
    handleReview: vi.fn(),
    handleExecuteNode: vi.fn(),
    handleUpdateNodeStatus: vi.fn(),
    handleRegenerateNode: vi.fn(),
    handleListNodeVersions: vi.fn(),
    handleRestoreNodeVersion: vi.fn(),
    handleOptimizePrompt: vi.fn(),
    handleCreateEdge: vi.fn(),
    handleDeleteEdge: vi.fn(),
    handleReorderEdge: vi.fn(),
    ...over,
  };
}

function renderBar(node: CanvasNode, actions: NodeActions) {
  return render(
    <NodeActionsContext.Provider value={actions}>
      <NodeActionBar node={node} selected />
    </NodeActionsContext.Provider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("NodeActionBar — regenerate vs generate routing", () => {
  it("a media node with a finished asset shows ↻ 重生 and routes to regenerate_node (NOT execute_node)", () => {
    const actions = makeActions();
    renderBar(makeNode({ asset_status: "done" }), actions);
    fireEvent.click(screen.getByText("↻ 重生"));
    expect(actions.handleRegenerateNode).toHaveBeenCalledWith("n1");
    expect(actions.handleExecuteNode).not.toHaveBeenCalled();
  });

  it("a stale (needs_regen) node routes to regenerate even when the asset is not 'done'", () => {
    const actions = makeActions();
    // 上游被重生 → 此节点产物过时;asset 可能停在 failed/timeout 但仍有旧 result。
    renderBar(
      makeNode({ asset_status: "failed", needs_regen: true, result: { url: "http://x/old.png" } }),
      actions,
    );
    fireEvent.click(screen.getByText("↻ 重生"));
    expect(actions.handleRegenerateNode).toHaveBeenCalledWith("n1");
    expect(actions.handleExecuteNode).not.toHaveBeenCalled();
  });

  it("a stale node that NEVER produced a result (first-gen failed, then marked stale) routes to execute, not regenerate — no null snapshot", () => {
    const actions = makeActions();
    // 后端 _mark_descendants_stale 的 has_asset 把 asset=failed 也算「有产物」,会给从未成功
    // 的节点标 needs_regen。这种没有旧 result 的节点应走 execute 重试,不该重生(否则快照一条
    // result=null 的垃圾版本)。
    renderBar(
      makeNode({ asset_status: "failed", needs_regen: true, result: null, generation_status: "failed" }),
      actions,
    );
    fireEvent.click(screen.getByText("⚡ 生成"));
    expect(actions.handleExecuteNode).toHaveBeenCalledWith("n1", "image", "a cat");
    expect(actions.handleRegenerateNode).not.toHaveBeenCalled();
  });

  it("a first-time (no asset) media node shows ⚡ 生成 and routes to execute_node (NOT regenerate)", () => {
    const actions = makeActions();
    renderBar(
      makeNode({ asset_status: "idle", result: null, generation_status: "idle" }),
      actions,
    );
    fireEvent.click(screen.getByText("⚡ 生成"));
    expect(actions.handleExecuteNode).toHaveBeenCalledWith("n1", "image", "a cat");
    expect(actions.handleRegenerateNode).not.toHaveBeenCalled();
  });

  it("a first-time composite node shows 🎬 合成 and routes to execute_node", () => {
    const actions = makeActions();
    renderBar(
      makeNode({ type: "composite", asset_status: "idle", result: null, generation_status: "idle" }),
      actions,
    );
    fireEvent.click(screen.getByText("🎬 合成"));
    expect(actions.handleExecuteNode).toHaveBeenCalledWith("n1", "composite", "a cat");
    expect(actions.handleRegenerateNode).not.toHaveBeenCalled();
  });

  it("hides the generate/regenerate button while the asset is generating", () => {
    const actions = makeActions();
    renderBar(makeNode({ asset_status: "generating" }), actions);
    expect(screen.queryByText("↻ 重生")).toBeNull();
    expect(screen.queryByText("⚡ 生成")).toBeNull();
  });

  it("does not offer regenerate on a reviewing (unconfirmed) node — only the confirm button", () => {
    const actions = makeActions();
    renderBar(makeNode({ node_status: "reviewing", asset_status: "done" }), actions);
    expect(screen.getByText("✓ 确认")).toBeInTheDocument();
    expect(screen.queryByText("↻ 重生")).toBeNull();
  });
});
