/**
 * Unit tests for <ConnectionBanner/> — W4D5-T1。
 *
 * 直接 set wsStore 状态,断言 banner DOM 是否出现/消失/文案分支。
 */

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ConnectionBanner } from "../ConnectionBanner";
import { useWSStore } from "../../../store/wsStore";

const initialStatus = {
  connected: false,
  connecting: false,
  reconnectAttempt: 0,
};

function setStatus(status: Partial<typeof initialStatus>) {
  useWSStore.getState().setConnectionStatus(status);
}

describe("ConnectionBanner", () => {
  beforeEach(() => {
    setStatus(initialStatus);
  });

  afterEach(() => {
    setStatus(initialStatus);
  });

  it("hidden by default (connected=false, attempts=0)", () => {
    const { container } = render(<ConnectionBanner />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId("connection-banner")).toBeNull();
  });

  it("hidden when attempts < 3", () => {
    setStatus({ connected: false, reconnectAttempt: 2 });
    const { container } = render(<ConnectionBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("hidden when connected=true even if attempts elevated", () => {
    setStatus({ connected: true, reconnectAttempt: 5 });
    const { container } = render(<ConnectionBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("shows after 3rd reconnect failure (idle wait)", () => {
    setStatus({ connected: false, connecting: false, reconnectAttempt: 3 });
    render(<ConnectionBanner />);
    const banner = screen.getByTestId("connection-banner");
    expect(banner).toBeInTheDocument();
    expect(banner.textContent).toContain("连接断开");
    expect(banner.textContent).toContain("3");
  });

  it("shows reconnecting state when connecting=true with attempts>=3", () => {
    setStatus({ connected: false, connecting: true, reconnectAttempt: 4 });
    render(<ConnectionBanner />);
    const banner = screen.getByTestId("connection-banner");
    expect(banner.textContent).toContain("正在重连");
    expect(banner.textContent).toContain("4");
  });

  it("uses role=status + aria-live=polite for accessibility", () => {
    setStatus({ connected: false, reconnectAttempt: 3 });
    render(<ConnectionBanner />);
    const banner = screen.getByTestId("connection-banner");
    expect(banner.getAttribute("role")).toBe("status");
    expect(banner.getAttribute("aria-live")).toBe("polite");
  });
});
