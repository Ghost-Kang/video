import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConsentGate } from "../ConsentGate";
import { CONSENT_STORAGE_KEY } from "../../../hooks/useConsent";

describe("ConsentGate", () => {
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

  it("renders checkbox + dims children before consent is accepted", () => {
    render(
      <ConsentGate>
        <button>start</button>
      </ConsentGate>
    );

    expect(screen.getByTestId("consent-block")).toBeInTheDocument();
    expect(screen.getByTestId("consent-checkbox")).not.toBeChecked();

    const gated = screen.getByTestId("consent-gated");
    expect(gated.className).toMatch(/pointer-events-none/);
    expect(gated.className).toMatch(/opacity-50/);
    expect(gated.getAttribute("aria-disabled")).toBe("true");
  });

  it("unlocks children + writes localStorage after the checkbox is ticked", async () => {
    const user = userEvent.setup();
    render(
      <ConsentGate>
        <button>start</button>
      </ConsentGate>
    );

    await user.click(screen.getByTestId("consent-checkbox"));

    await waitFor(() =>
      expect(screen.queryByTestId("consent-block")).not.toBeInTheDocument()
    );
    expect(screen.queryByTestId("consent-gated")).not.toBeInTheDocument();
    expect(screen.getByText("start")).toBeInTheDocument();

    const stored = window.localStorage.getItem(CONSENT_STORAGE_KEY);
    expect(stored).not.toBeNull();
    expect(JSON.parse(stored as string).version).toBe("v0");
  });

  it("auto-passes on mount when a valid consent record already exists", () => {
    window.localStorage.setItem(
      CONSENT_STORAGE_KEY,
      JSON.stringify({ version: "v0", acceptedAt: "2026-05-22T10:00:00.000Z" })
    );

    render(
      <ConsentGate>
        <button>start</button>
      </ConsentGate>
    );

    expect(screen.queryByTestId("consent-block")).not.toBeInTheDocument();
    expect(screen.queryByTestId("consent-gated")).not.toBeInTheDocument();
    expect(screen.getByText("start")).toBeInTheDocument();
  });
});
