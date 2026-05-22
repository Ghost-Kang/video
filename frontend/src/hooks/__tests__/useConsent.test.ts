import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CONSENT_STORAGE_KEY, CONSENT_VERSION, useConsent } from "../useConsent";

describe("useConsent", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status: 200 }))
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns accepted=false when localStorage is empty", () => {
    const { result } = renderHook(() => useConsent());
    expect(result.current.accepted).toBe(false);
    expect(result.current.acceptedAt).toBeNull();
  });

  it("returns accepted=true after accept() and persists to localStorage + POSTs event", async () => {
    const { result } = renderHook(() => useConsent());
    expect(result.current.accepted).toBe(false);

    await act(async () => {
      await result.current.accept();
    });

    await waitFor(() => expect(result.current.accepted).toBe(true));
    expect(result.current.acceptedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);

    const stored = window.localStorage.getItem(CONSENT_STORAGE_KEY);
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored as string);
    expect(parsed.version).toBe(CONSENT_VERSION);
    expect(typeof parsed.acceptedAt).toBe("string");

    expect(fetch).toHaveBeenCalledTimes(1);
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/events");
    const body = JSON.parse(call[1].body);
    expect(body.event_name).toBe("consent_accepted");
    expect(body.payload.version).toBe(CONSENT_VERSION);
    expect(body.payload.documents).toEqual([
      "user_agreement_v0",
      "privacy_v0",
    ]);
  });

  it("reads existing consent from localStorage on initial mount", () => {
    window.localStorage.setItem(
      CONSENT_STORAGE_KEY,
      JSON.stringify({ version: "v0", acceptedAt: "2026-05-22T10:00:00.000Z" })
    );
    const { result } = renderHook(() => useConsent());
    expect(result.current.accepted).toBe(true);
    expect(result.current.acceptedAt).toBe("2026-05-22T10:00:00.000Z");
  });

  it("ignores stored consent with a mismatched version", () => {
    window.localStorage.setItem(
      CONSENT_STORAGE_KEY,
      JSON.stringify({ version: "v1", acceptedAt: "2026-05-22T10:00:00.000Z" })
    );
    const { result } = renderHook(() => useConsent());
    expect(result.current.accepted).toBe(false);
  });
});
