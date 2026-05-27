/**
 * wsStore "error" frame → toast wiring.
 *
 * Backend (Claude-B Pydantic dispatch) emits:
 *   { type: "error", code: "invalid_command", message, bad_type }
 *
 * 我们这里直接喂 dispatch(),不起真实 WS,验证 toast 落地。
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useToastStore } from "../toastStore";
import { useWSStore } from "../wsStore";

describe("wsStore error frame → toast", () => {
  beforeEach(() => {
    useToastStore.getState().clear();
  });

  afterEach(() => {
    useToastStore.getState().clear();
  });

  it("invalid_command error pushes a toast with friendly title + bad_type body", () => {
    useWSStore.getState().dispatch(
      {
        type: "error",
        code: "invalid_command",
        message: "1 validation error for ExecuteNodeMsg ...",
        bad_type: "execute_node",
      },
      "user_test",
    );

    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0].kind).toBe("error");
    expect(toasts[0].title).toBe("请求格式不对"); // mapped from invalid_command
    expect(toasts[0].body).toBe("操作:execute_node");
  });

  it("malformed_json error uses its own friendly title", () => {
    useWSStore.getState().dispatch(
      {
        type: "error",
        code: "malformed_json",
        message: "Expecting value: line 1 column 1",
      },
      "user_test",
    );

    const toast = useToastStore.getState().toasts[0];
    expect(toast.title).toBe("数据格式不对");
    expect(toast.body).toBeUndefined(); // no bad_type → no body
  });

  it("unknown error code falls back to generic title", () => {
    useWSStore.getState().dispatch(
      {
        type: "error",
        code: "some_new_code",
        message: "anything",
      },
      "user_test",
    );

    expect(useToastStore.getState().toasts[0].title).toBe("请求出错");
  });
});
