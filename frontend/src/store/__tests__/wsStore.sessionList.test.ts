/**
 * wsStore `session_list` frame → sessionStore UNION (W5D4 regression).
 *
 * Root cause of the "拆解中界面完全空白" bug: the backend session_list only
 * contains sessions that already have persisted messages. A session the user
 * JUST created (landing → 拆解) has no messages yet, so it's absent. The old
 * handler OVERWROTE the local session list with the backend list, dropping the
 * just-created session; App's redirect effect then navigated away mid-run,
 * changing currentThreadId so the running session's WS frames were discarded.
 *
 * These tests pin the union behavior: a locally-known session survives a
 * backend session_list that doesn't mention it.
 */

import { beforeEach, describe, expect, it } from "vitest";
import { useWSStore } from "../wsStore";
import { useSessionStore } from "../sessionStore";

describe("wsStore session_list → union with local sessions", () => {
  beforeEach(() => {
    localStorage.clear();
    useSessionStore.getState().reset();
    useSessionStore.getState().setUserId("u1");
  });

  it("keeps a just-created local session absent from the backend list", () => {
    // User created session-new (landing → 拆解) — added locally, no messages yet.
    useSessionStore.getState().addSession("session-new");

    // Backend session_list arrives with only the older, persisted sessions.
    useWSStore.getState().dispatch(
      {
        type: "session_list",
        sessions: [{ thread_id: "session-old1" }, { thread_id: "session-old2" }],
      },
      "u1",
    );

    const ids = useSessionStore.getState().sessions;
    // Backend ids lead (recent-active first), the local-only new one survives.
    expect(ids).toContain("session-new");
    expect(ids).toContain("session-old1");
    expect(ids).toContain("session-old2");
    // Backend order preserved up front; local-only appended.
    expect(ids.slice(0, 2)).toEqual(["session-old1", "session-old2"]);
  });

  it("does not duplicate a session present in both backend and local", () => {
    useSessionStore.getState().addSession("session-shared");

    useWSStore.getState().dispatch(
      {
        type: "session_list",
        sessions: [{ thread_id: "session-shared" }, { thread_id: "session-old" }],
      },
      "u1",
    );

    const ids = useSessionStore.getState().sessions;
    expect(ids.filter((id) => id === "session-shared")).toHaveLength(1);
    expect(ids).toEqual(["session-shared", "session-old"]);
  });

  it("an empty backend list still preserves local sessions", () => {
    useSessionStore.getState().addSession("session-new");

    useWSStore.getState().dispatch({ type: "session_list", sessions: [] }, "u1");

    expect(useSessionStore.getState().sessions).toEqual(["session-new"]);
  });
});
