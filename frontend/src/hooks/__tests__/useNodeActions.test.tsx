import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useNodeActions } from "../useNodeActions";

describe("useNodeActions — regenerate", () => {
  it("handleRegenerateNode sends a regenerate_node command for the thread/node", () => {
    const send = vi.fn();
    const { result } = renderHook(() => useNodeActions("t1", send, vi.fn()));
    result.current.handleRegenerateNode("n9");
    expect(send).toHaveBeenCalledWith({
      type: "regenerate_node",
      thread_id: "t1",
      node_id: "n9",
    });
  });

  it("handleExecuteNode still sends execute_node (the first-time generation path is unchanged)", () => {
    const send = vi.fn();
    const { result } = renderHook(() => useNodeActions("t1", send, vi.fn()));
    result.current.handleExecuteNode("n1", "image", "a cat");
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "execute_node", thread_id: "t1", node_id: "n1", node_type: "image" }),
    );
  });

  it("handleListNodeVersions sends a list_node_versions command (2b)", () => {
    const send = vi.fn();
    const { result } = renderHook(() => useNodeActions("t1", send, vi.fn()));
    result.current.handleListNodeVersions("n5");
    expect(send).toHaveBeenCalledWith({ type: "list_node_versions", thread_id: "t1", node_id: "n5" });
  });

  it("handleRegenerateScriptNode sends a regenerate_script_node command with feedback (2d)", () => {
    const send = vi.fn();
    const { result } = renderHook(() => useNodeActions("t1", send, vi.fn()));
    result.current.handleRegenerateScriptNode("s1", "更钩子");
    expect(send).toHaveBeenCalledWith({ type: "regenerate_script_node", thread_id: "t1", node_id: "s1", feedback: "更钩子" });
  });

  it("handleCancelGeneration sends a cancel_generation command (P2 ③)", () => {
    const send = vi.fn();
    const { result } = renderHook(() => useNodeActions("t1", send, vi.fn()));
    result.current.handleCancelGeneration("v3");
    expect(send).toHaveBeenCalledWith({ type: "cancel_generation", thread_id: "t1", node_id: "v3" });
  });

  it("handleRestoreNodeVersion sends a restore_node_version command (2c)", () => {
    const send = vi.fn();
    const { result } = renderHook(() => useNodeActions("t1", send, vi.fn()));
    result.current.handleRestoreNodeVersion("n5", 2);
    expect(send).toHaveBeenCalledWith({ type: "restore_node_version", thread_id: "t1", node_id: "n5", version_seq: 2 });
  });
});
