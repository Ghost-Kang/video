import { beforeEach, describe, expect, it } from "vitest";
import { useProCanvasStore } from "../proCanvasStore";

function reset() {
  useProCanvasStore.getState().reset();
}

describe("proCanvasStore edges", () => {
  beforeEach(reset);

  it("adds an edge with a generated id", () => {
    useProCanvasStore.getState().addEdge({ source: "a", sourceHandle: "image", target: "b", targetHandle: "image" });
    const edges = useProCanvasStore.getState().edges;
    expect(edges).toHaveLength(1);
    expect(edges[0].id).toBeTruthy();
    expect(edges[0].source).toBe("a");
  });

  it("single-valued input: new edge into same target+handle replaces the old", () => {
    const s = useProCanvasStore.getState();
    s.addEdge({ source: "a", sourceHandle: "text", target: "g", targetHandle: "positive" });
    s.addEdge({ source: "b", sourceHandle: "text", target: "g", targetHandle: "positive" });
    const edges = useProCanvasStore.getState().edges;
    expect(edges).toHaveLength(1);
    expect(edges[0].source).toBe("b");
  });

  it("different input handles on same target coexist", () => {
    const s = useProCanvasStore.getState();
    s.addEdge({ source: "m", sourceHandle: "model", target: "g", targetHandle: "model" });
    s.addEdge({ source: "p", sourceHandle: "text", target: "g", targetHandle: "positive" });
    expect(useProCanvasStore.getState().edges).toHaveLength(2);
  });

  it("removeEdgesForNodes drops edges touching deleted nodes", () => {
    const s = useProCanvasStore.getState();
    s.addEdge({ source: "a", sourceHandle: "image", target: "b", targetHandle: "image" });
    s.addEdge({ source: "b", sourceHandle: "image", target: "c", targetHandle: "image" });
    s.removeEdgesForNodes(["b"]);
    expect(useProCanvasStore.getState().edges).toHaveLength(0);
  });
});

describe("proCanvasStore connection handshake", () => {
  beforeEach(reset);

  it("startConnection sets pending; cancel clears it", () => {
    const s = useProCanvasStore.getState();
    s.startConnection({ nodeId: "a", handle: "image", portType: "image", end: "source" });
    expect(useProCanvasStore.getState().pending?.nodeId).toBe("a");
    s.cancelConnection();
    expect(useProCanvasStore.getState().pending).toBeNull();
  });
});

describe("proCanvasStore run lifecycle", () => {
  beforeEach(reset);

  it("queued progress mints runId and sets status", () => {
    useProCanvasStore.getState().applyProRunEvent({
      type: "pro_run_progress", thread_id: "t", run_id: "pro_1", status: "queued", pct: 0,
    });
    const run = useProCanvasStore.getState().run;
    expect(run.runId).toBe("pro_1");
    expect(run.status).toBe("queued");
  });

  it("ignores frames from a different run once runId is set", () => {
    const s = useProCanvasStore.getState();
    s.applyProRunEvent({ type: "pro_run_progress", thread_id: "t", run_id: "pro_1", status: "queued", pct: 0 });
    s.applyProRunEvent({ type: "pro_run_failed", thread_id: "t", run_id: "pro_OTHER", error: "x" });
    expect(useProCanvasStore.getState().run.status).toBe("queued"); // unchanged
  });

  it("node_done appends outputs; done finalizes", () => {
    const s = useProCanvasStore.getState();
    s.applyProRunEvent({ type: "pro_run_progress", thread_id: "t", run_id: "pro_1", status: "running", pct: 30 });
    s.applyProRunEvent({ type: "pro_run_node_done", thread_id: "t", run_id: "pro_1", output_url: "u1" });
    s.applyProRunEvent({ type: "pro_run_done", thread_id: "t", run_id: "pro_1", outputs: ["u1", "u2"] });
    const run = useProCanvasStore.getState().run;
    expect(run.status).toBe("done");
    expect(run.pct).toBe(100);
    expect(run.outputs).toEqual(["u1", "u2"]);
  });

  it("failed sets error", () => {
    const s = useProCanvasStore.getState();
    s.applyProRunEvent({ type: "pro_run_progress", thread_id: "t", run_id: "pro_1", status: "queued", pct: 0 });
    s.applyProRunEvent({ type: "pro_run_failed", thread_id: "t", run_id: "pro_1", error: "boom" });
    const run = useProCanvasStore.getState().run;
    expect(run.status).toBe("failed");
    expect(run.error).toBe("boom");
  });

  it("cancelled progress flips status", () => {
    const s = useProCanvasStore.getState();
    s.applyProRunEvent({ type: "pro_run_progress", thread_id: "t", run_id: "pro_1", status: "queued", pct: 0 });
    s.applyProRunEvent({ type: "pro_run_progress", thread_id: "t", run_id: "pro_1", status: "cancelled", pct: 0 });
    expect(useProCanvasStore.getState().run.status).toBe("cancelled");
  });
});

describe("proCanvasStore cost modal", () => {
  beforeEach(reset);
  it("open/close cost modal carries estimate", () => {
    const s = useProCanvasStore.getState();
    s.openCostModal({ billable_node_count: 2, cached_skipped: 1, cost_cny: 3 });
    expect(useProCanvasStore.getState().costModalOpen).toBe(true);
    expect(useProCanvasStore.getState().estimate?.cost_cny).toBe(3);
    s.closeCostModal();
    expect(useProCanvasStore.getState().costModalOpen).toBe(false);
  });
});
