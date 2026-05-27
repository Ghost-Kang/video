import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "../sessionStore";

describe("sessionStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useSessionStore.getState().reset();
    useSessionStore.getState().setUserId("u1");
  });

  it("adds sessions newest first and persists", () => {
    const store = useSessionStore.getState();
    store.addSession("t1");
    store.addSession("t2");
    store.addSession("t1");

    expect(useSessionStore.getState().sessions).toEqual(["t2", "t1"]);
    expect(JSON.parse(localStorage.getItem("openrhtv_u1_sessions") || "[]")).toEqual(["t2", "t1"]);
  });

  it("renames and deletes sessions", () => {
    const store = useSessionStore.getState();
    store.addSession("t1");
    store.rename("t1", "第一条");
    store.deleteSession("t1");

    expect(useSessionStore.getState().sessions).toEqual([]);
    expect(useSessionStore.getState().names).toEqual({});
  });

  it("reset clears in-memory state", () => {
    const store = useSessionStore.getState();
    store.addSession("t1");
    store.rename("t1", "第一条");
    store.reset();

    expect(useSessionStore.getState().sessions).toEqual([]);
    expect(useSessionStore.getState().names).toEqual({});
  });
});
