import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { NodeVersionHistory } from "../NodeVersionHistory";
import { useCanvasStore } from "../../store/canvasStore";
import type { NodeActions } from "../../hooks/useNodeActions";
import type { CanvasNode } from "../../types";
import type { NodeVersion } from "../../types/ws";

function makeNode(over: Partial<CanvasNode> = {}): CanvasNode {
  return {
    id: "n1", type: "image", title: "镜头1", description: "",
    status: "done", node_status: "confirmed", asset_status: "done",
    result: { url: "current.png" }, needs_regen: false,
    subtype: null, shot_no: null, image_gen_provider: null, feedback: null,
    generation_status: "done", generation_task_id: null, generation_error: null,
    generation_attempt_count: 0, generation_lease_until: null, generation_next_retry_at: null,
    user_id: "u", thread_id: "t", x: 0, y: 0, ...over,
  };
}

function makeActions(over: Partial<NodeActions> = {}): NodeActions {
  return {
    handleReview: vi.fn(), handleExecuteNode: vi.fn(), handleUpdateNodeStatus: vi.fn(),
    handleRegenerateNode: vi.fn(), handleListNodeVersions: vi.fn(), handleRestoreNodeVersion: vi.fn(),
    handleRegenerateScriptNode: vi.fn(), handleOptimizePrompt: vi.fn(),
    handleCreateEdge: vi.fn(), handleDeleteEdge: vi.fn(), handleReorderEdge: vi.fn(), ...over,
  };
}

const VERSIONS: NodeVersion[] = [
  { version_seq: 1, description: "镜头1", result: { url: "v1.png" }, asset_status: "done", reason: "regenerate", created_at: "2026-06-03T14:05:00Z" },
  { version_seq: 2, description: "镜头1", result: { url: "v2.png" }, asset_status: "done", reason: "regenerate", created_at: "2026-06-03T14:20:00Z" },
];

beforeEach(() => useCanvasStore.setState({ nodeVersions: {} }));

describe("NodeVersionHistory (2b)", () => {
  it("requests the node's versions on mount", () => {
    const actions = makeActions();
    render(<NodeVersionHistory node={makeNode()} actions={actions} />);
    expect(actions.handleListNodeVersions).toHaveBeenCalledWith("n1");
  });

  it("refetches when asset_status changes (in-place regenerate keeps the panel open) so the new version isn't missed", () => {
    const actions = makeActions();
    const { rerender } = render(<NodeVersionHistory node={makeNode({ asset_status: "done" })} actions={actions} />);
    expect(actions.handleListNodeVersions).toHaveBeenCalledTimes(1);
    // regenerate flips done → generating on the SAME node (node.id unchanged) → must refetch.
    rerender(<NodeVersionHistory node={makeNode({ asset_status: "generating", result: null })} actions={actions} />);
    expect(actions.handleListNodeVersions).toHaveBeenCalledTimes(2);
  });

  it("shows 生成中… in the current column during the post-regenerate window (result null + generating)", () => {
    useCanvasStore.setState({ nodeVersions: { n1: VERSIONS } });
    render(<NodeVersionHistory node={makeNode({ asset_status: "generating", result: null })} actions={makeActions()} />);
    const compare = screen.getByTestId("version-compare");
    expect(within(compare).getByText("生成中…")).toBeInTheDocument();
  });

  it("shows a loading state until versions arrive", () => {
    render(<NodeVersionHistory node={makeNode()} actions={makeActions()} />);
    expect(screen.getByText("加载中…")).toBeInTheDocument();
  });

  it("shows an empty hint when the node has no history", () => {
    useCanvasStore.setState({ nodeVersions: { n1: [] } });
    render(<NodeVersionHistory node={makeNode()} actions={makeActions()} />);
    expect(screen.getByText(/暂无历史版本/)).toBeInTheDocument();
    expect(screen.queryByTestId("version-compare")).toBeNull();
  });

  it("lists versions and auto-compares current vs the latest old version", () => {
    useCanvasStore.setState({ nodeVersions: { n1: VERSIONS } });
    render(<NodeVersionHistory node={makeNode({ result: { url: "current.png" } })} actions={makeActions()} />);
    expect(screen.getByTestId("version-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("version-row-2")).toBeInTheDocument();
    const compare = screen.getByTestId("version-compare");
    const imgs = within(compare).getAllByRole("img").map((i) => i.getAttribute("src"));
    // current (new) on the left, latest old version (v2) on the right
    expect(imgs).toEqual(["current.png", "v2.png"]);
  });

  it("switches the compared version when a different row is clicked", () => {
    useCanvasStore.setState({ nodeVersions: { n1: VERSIONS } });
    render(<NodeVersionHistory node={makeNode({ result: { url: "current.png" } })} actions={makeActions()} />);
    fireEvent.click(screen.getByTestId("version-row-1"));
    const imgs = within(screen.getByTestId("version-compare")).getAllByRole("img").map((i) => i.getAttribute("src"));
    expect(imgs).toEqual(["current.png", "v1.png"]);
  });

  it("restores the auto-selected (latest) version when the restore button is clicked (2c)", () => {
    useCanvasStore.setState({ nodeVersions: { n1: VERSIONS } });
    const actions = makeActions();
    render(<NodeVersionHistory node={makeNode({ result: { url: "current.png" } })} actions={actions} />);
    fireEvent.click(screen.getByTestId("restore-button"));
    expect(actions.handleRestoreNodeVersion).toHaveBeenCalledWith("n1", 2); // latest old version
  });

  it("restores the version the user switched to (2c)", () => {
    useCanvasStore.setState({ nodeVersions: { n1: VERSIONS } });
    const actions = makeActions();
    render(<NodeVersionHistory node={makeNode({ result: { url: "current.png" } })} actions={actions} />);
    fireEvent.click(screen.getByTestId("version-row-1"));
    fireEvent.click(screen.getByTestId("restore-button"));
    expect(actions.handleRestoreNodeVersion).toHaveBeenCalledWith("n1", 1);
  });

  it("disables the restore button while the node is generating — race guard (2c)", () => {
    useCanvasStore.setState({ nodeVersions: { n1: VERSIONS } });
    const actions = makeActions();
    render(<NodeVersionHistory node={makeNode({ asset_status: "generating", result: null })} actions={actions} />);
    const btn = screen.getByTestId("restore-button") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    fireEvent.click(btn);
    expect(actions.handleRestoreNodeVersion).not.toHaveBeenCalled();
  });

  it("resets the compare selection after restore so it auto-advances to the freshly-archived version (2c)", () => {
    useCanvasStore.setState({ nodeVersions: { n1: VERSIONS } });
    render(<NodeVersionHistory node={makeNode({ result: { url: "current.png" } })} actions={makeActions()} />);
    fireEvent.click(screen.getByTestId("version-row-1")); // pin v1 → old col = v1.png
    expect(
      within(screen.getByTestId("version-compare")).getAllByRole("img").map((i) => i.getAttribute("src")),
    ).toEqual(["current.png", "v1.png"]);
    fireEvent.click(screen.getByTestId("restore-button")); // restore resets selection → back to latest
    expect(
      within(screen.getByTestId("version-compare")).getAllByRole("img").map((i) => i.getAttribute("src")),
    ).toEqual(["current.png", "v2.png"]);
  });
});
