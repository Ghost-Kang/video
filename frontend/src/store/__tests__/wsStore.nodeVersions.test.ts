/**
 * time-travel 回溯(P2 slice-2b)— node_versions_returned 事件落到 canvasStore.nodeVersions,
 * 供 NodeVersionHistory 渲染历史 + 对比。
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useCanvasStore } from "../canvasStore";
import { useWSStore } from "../wsStore";
import type { NodeVersion } from "../../types/ws";

const VERSIONS: NodeVersion[] = [
  { version_seq: 1, description: "镜头1", result: { url: "v1.png" }, asset_status: "done", reason: "regenerate", created_at: "2026-06-03T14:05:00Z" },
  { version_seq: 2, description: "镜头1", result: { url: "v2.png" }, asset_status: "done", reason: "regenerate", created_at: "2026-06-03T14:20:00Z" },
];

describe("wsStore node_versions_returned (2b)", () => {
  beforeEach(() => {
    useCanvasStore.getState().clear();
    // dispatch() buffers frames whose thread_id != currentThreadId — match it so the frame is processed.
    useWSStore.setState({ currentThreadId: "t1" });
  });
  afterEach(() => useCanvasStore.getState().clear());

  it("caches versions under the node_id", () => {
    useWSStore.getState().dispatch(
      { type: "node_versions_returned", thread_id: "t1", node_id: "n1", versions: VERSIONS },
      "user_test",
    );
    return Promise.resolve().then(() => {
      expect(useCanvasStore.getState().nodeVersions["n1"]).toHaveLength(2);
      expect(useCanvasStore.getState().nodeVersions["n1"][1].result).toEqual({ url: "v2.png" });
    });
  });

  it("clear() wipes the version cache (session switch)", () => {
    useCanvasStore.getState().setNodeVersions("n1", VERSIONS);
    expect(useCanvasStore.getState().nodeVersions["n1"]).toHaveLength(2);
    useCanvasStore.getState().clear();
    expect(useCanvasStore.getState().nodeVersions).toEqual({});
  });
});
