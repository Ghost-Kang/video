/**
 * Unit tests for errorReporter — W5D2-E。覆盖:
 * - POST 命中 `/api/client_error` + 关键字段
 * - dedup: 同 (kind+msg.slice(0,80)) 1 分钟内只投一次
 * - 不同 kind / 不同 msg 不被去重
 * - reporter 内部失败静默(不 throw 出去)
 * - extractThreadId 边界
 */

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import {
  _resetReporterStateForTests,
  extractThreadId,
  reportClientError,
} from "../errorReporter";

describe("errorReporter — POST shape", () => {
  beforeEach(() => {
    _resetReporterStateForTests();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("POSTs to /api/client_error with payload + content-type json", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    reportClientError({
      kind: "window_error",
      message: "ReferenceError: x is not defined",
      stack: "stack-here",
      filename: "main.js",
      lineno: 42,
      colno: 7,
      url: "https://cascade.herwin.top/chat/s-1",
      user_id: "u_alpha",
      thread_id: "s-1",
      ua: "Mozilla/5.0 (test)",
    });

    // flush the setTimeout(..., 0)
    await vi.advanceTimersByTimeAsync(1);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/client_error");
    expect(init?.method).toBe("POST");
    const headers = init?.headers as Record<string, string>;
    expect(headers["content-type"]).toBe("application/json");

    const body = JSON.parse(init?.body as string);
    expect(body.kind).toBe("window_error");
    expect(body.message).toContain("ReferenceError");
    expect(body.user_id).toBe("u_alpha");
    expect(body.thread_id).toBe("s-1");
    expect(body.filename).toBe("main.js");
    expect(body.lineno).toBe(42);
  });

  it("truncates stack to <= 4000 and ua to <= 200", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    const longStack = "x".repeat(10_000);
    const longUa = "U".repeat(500);

    reportClientError({
      kind: "window_error",
      message: "boom",
      stack: longStack,
      url: "https://example.com",
      user_id: null,
      ua: longUa,
    });

    await vi.advanceTimersByTimeAsync(1);

    const body = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
    expect(body.stack.length).toBe(4000);
    expect(body.ua.length).toBe(200);
  });
});

describe("errorReporter — dedup window", () => {
  beforeEach(() => {
    _resetReporterStateForTests();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("dedups same (kind+msg) within 1 minute (only first POST goes through)", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    for (let i = 0; i < 5; i++) {
      reportClientError({
        kind: "window_error",
        message: "Cannot read properties of undefined",
        url: "https://example.com",
        user_id: null,
        ua: "ua",
      });
    }
    await vi.advanceTimersByTimeAsync(1);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("allows re-POST after 60s window elapses", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    reportClientError({
      kind: "window_error",
      message: "boom",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    await vi.advanceTimersByTimeAsync(1);

    // advance > 60s — Date.now mocked along with timers
    await vi.advanceTimersByTimeAsync(60_001);

    reportClientError({
      kind: "window_error",
      message: "boom",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    await vi.advanceTimersByTimeAsync(1);

    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("different kinds are not deduped against each other", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    reportClientError({
      kind: "window_error",
      message: "boom",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    reportClientError({
      kind: "unhandled_rejection",
      message: "boom",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    await vi.advanceTimersByTimeAsync(1);

    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("different messages are not deduped", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    reportClientError({
      kind: "window_error",
      message: "first-error-distinct-message",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    reportClientError({
      kind: "window_error",
      message: "second-error-distinct-message",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    await vi.advanceTimersByTimeAsync(1);

    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("dedup keys by first 80 chars of message — long tails do not bypass", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    const prefix = "A".repeat(80);
    reportClientError({
      kind: "window_error",
      message: prefix + "-tail-1",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    reportClientError({
      kind: "window_error",
      message: prefix + "-tail-2-different-tail",
      url: "https://example.com",
      user_id: null,
      ua: "ua",
    });
    await vi.advanceTimersByTimeAsync(1);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});

describe("errorReporter — failure isolation", () => {
  beforeEach(() => {
    _resetReporterStateForTests();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("does not throw when fetch rejects (silent failure, console.warn ok)", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network down"));
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    expect(() =>
      reportClientError({
        kind: "window_error",
        message: "boom",
        url: "https://example.com",
        user_id: null,
        ua: "ua",
      })
    ).not.toThrow();

    await vi.advanceTimersByTimeAsync(1);
    // Microtask for .catch() handler resolution
    await Promise.resolve();
    await Promise.resolve();

    expect(warnSpy).toHaveBeenCalled();
  });

  it("does not throw when fetch is synchronously broken", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      throw new Error("fetch is busted");
    });
    vi.spyOn(console, "warn").mockImplementation(() => {});

    expect(() =>
      reportClientError({
        kind: "window_error",
        message: "boom",
        url: "https://example.com",
        user_id: null,
        ua: "ua",
      })
    ).not.toThrow();
  });
});

describe("extractThreadId", () => {
  it("pulls threadId out of /chat/:threadId", () => {
    expect(extractThreadId("/chat/session-abc123")).toBe("session-abc123");
    expect(extractThreadId("/chat/s-1?view=pro")).toBe("s-1");
    expect(extractThreadId("/chat/s-1/extra")).toBe("s-1");
  });

  it("returns null for non-chat routes", () => {
    expect(extractThreadId("/admin/events")).toBeNull();
    expect(extractThreadId("/")).toBeNull();
    expect(extractThreadId("/login")).toBeNull();
  });
});
