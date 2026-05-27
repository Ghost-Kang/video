import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConsentGate } from "../ConsentGate";
import { CONSENT_STORAGE_KEY } from "../../../hooks/useConsent";

/**
 * v8 (2026-05-26): ConsentGate 改为非阻塞 —
 *  - children 始终可交互(不再 pointer-events-none / opacity-50)
 *  - 不再渲染 testid="consent-block" / "consent-checkbox" / "consent-gated"
 *  - 未同意时仅在底部渲染极小法律链接(包含"用户协议" + "隐私政策"文字)
 *  - 首次点击 children 内部任何元素 → onClickCapture 自动触发 accept()
 */
describe("ConsentGate (v8 non-blocking)", () => {
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

  it("renders children at full opacity + shows non-blocking legal footer before consent", () => {
    render(
      <ConsentGate>
        <button>start</button>
      </ConsentGate>
    );

    // children 永远可见可交互
    expect(screen.getByText("start")).toBeInTheDocument();
    // 未同意时,底部小字法律链接出现
    expect(screen.getByRole("link", { name: "用户协议" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "隐私政策" })).toBeInTheDocument();
    // 旧的阻塞 UI 已撤
    expect(screen.queryByTestId("consent-block")).not.toBeInTheDocument();
    expect(screen.queryByTestId("consent-checkbox")).not.toBeInTheDocument();
    expect(screen.queryByTestId("consent-gated")).not.toBeInTheDocument();
  });

  it("auto-accepts on first interaction click + removes footer + writes localStorage", async () => {
    const user = userEvent.setup();
    render(
      <ConsentGate>
        <button>start</button>
      </ConsentGate>
    );

    // 首次点 children 内任意元素 → 自动同意
    await user.click(screen.getByText("start"));

    // 法律链接消失
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "用户协议" })).not.toBeInTheDocument()
    );
    expect(screen.queryByRole("link", { name: "隐私政策" })).not.toBeInTheDocument();
    // children 仍在
    expect(screen.getByText("start")).toBeInTheDocument();

    // localStorage 写入 v0 同意记录
    const stored = window.localStorage.getItem(CONSENT_STORAGE_KEY);
    expect(stored).not.toBeNull();
    expect(JSON.parse(stored as string).version).toBe("v0");
  });

  it("auto-passes silently when a valid consent record already exists", () => {
    window.localStorage.setItem(
      CONSENT_STORAGE_KEY,
      JSON.stringify({ version: "v0", acceptedAt: "2026-05-22T10:00:00.000Z" })
    );

    render(
      <ConsentGate>
        <button>start</button>
      </ConsentGate>
    );

    // 已同意 → children 直接渲染,无任何法律 UI
    expect(screen.getByText("start")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "用户协议" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "隐私政策" })).not.toBeInTheDocument();
  });
});
