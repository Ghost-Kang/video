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
});
