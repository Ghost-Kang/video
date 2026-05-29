/**
 * useWebSocket — terminal auth-close handling (W5D4 regression).
 *
 * Root cause of the 2-day "拆解 95% + 网络已恢复 狂闪" bug: a user whose stored
 * invite_code was wrong (observed: "ee") got WS-closed by the backend with code
 * 4003 right after auth. The old onclose ignored the code and ALWAYS reconnected
 * → connect→4003→reconnect death loop. No user_message ever reached the backend,
 * so the dock spun a fake 95% forever and the reconnect toast flashed each cycle.
 *
 * These tests pin: on 4001/4003 we (a) do NOT reconnect, (b) clear the bad
 * invite code, (c) fire `rhtv-invite-rejected`; on a normal close we DO reconnect.
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWebSocket } from "../useWebSocket";

// Minimal fake WebSocket: records instances, lets the test drive lifecycle.
class FakeWS {
  static instances: FakeWS[] = [];
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;
  readyState = FakeWS.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: ((e: { code: number; reason: string }) => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  closedWith: number | null = null;
  constructor(public url: string) {
    FakeWS.instances.push(this);
  }
  send(d: string) {
    this.sent.push(d);
  }
  close(code?: number) {
    this.closedWith = code ?? 1000;
    this.readyState = FakeWS.CLOSED;
  }
  // test helpers
  fireClose(code: number, reason = "") {
    this.readyState = FakeWS.CLOSED;
    this.onclose?.({ code, reason });
  }
}

describe("useWebSocket auth-fatal close handling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("openrhtv_invite_code", "ee"); // the bad code
    FakeWS.instances = [];
    vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("does NOT reconnect on 4003 (invalid invite) and clears the bad code", () => {
    const onMessage = vi.fn();
    const rejected = vi.fn();
    window.addEventListener("rhtv-invite-rejected", rejected);

    const { result } = renderHook(() => useWebSocket("u1", onMessage));
    act(() => result.current.connect());

    expect(FakeWS.instances).toHaveLength(1);
    act(() => FakeWS.instances[0].fireClose(4003, "invite code required"));

    // No reconnect scheduled: advancing time creates no new socket.
    act(() => vi.advanceTimersByTime(60_000));
    expect(FakeWS.instances).toHaveLength(1);

    // Bad code cleared + rejection event fired + flag set for the gate.
    expect(localStorage.getItem("openrhtv_invite_code")).toBeNull();
    expect(rejected).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem("openrhtv_invite_rejected")).toBe("1");

    window.removeEventListener("rhtv-invite-rejected", rejected);
  });

  it("does NOT reconnect on 4001 (unauth)", () => {
    const { result } = renderHook(() => useWebSocket("u1", vi.fn()));
    act(() => result.current.connect());
    act(() => FakeWS.instances[0].fireClose(4001, "未认证"));
    act(() => vi.advanceTimersByTime(60_000));
    expect(FakeWS.instances).toHaveLength(1); // no new socket
  });

  it("DOES reconnect on a normal close (1006) — transient network drop", () => {
    const { result } = renderHook(() => useWebSocket("u1", vi.fn()));
    act(() => result.current.connect());
    act(() => FakeWS.instances[0].fireClose(1006, "abnormal"));

    // First backoff is RECONNECT_BASE_MS (1000ms) → a new socket appears.
    act(() => vi.advanceTimersByTime(1100));
    expect(FakeWS.instances.length).toBeGreaterThanOrEqual(2);
    // invite code preserved on a non-auth close.
    expect(localStorage.getItem("openrhtv_invite_code")).toBe("ee");
  });
});
