import { render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { AnchorSidebar } from "../AnchorSidebar";

const SORT_KEY = "anchor_sort_preference";

describe("AnchorSidebar", () => {
  beforeEach(() => {
    window.localStorage.removeItem(SORT_KEY);
  });

  it("renders mocked anchors", async () => {
    render(<AnchorSidebar />);
    expect(await screen.findByText("小张妈妈")).toBeInTheDocument();
    expect(await screen.findByText("厨房")).toBeInTheDocument();
  });

  it("defaults to 按使用次数 when no preference is stored", async () => {
    render(<AnchorSidebar />);
    const reusePill = await screen.findByRole("radio", { name: "按使用次数" });
    expect(reusePill).toHaveAttribute("aria-checked", "true");
  });

  it("switches active sort to recency on click and persists to localStorage", async () => {
    const user = userEvent.setup();
    render(<AnchorSidebar />);
    const recencyPill = await screen.findByRole("radio", { name: "按时间" });
    await user.click(recencyPill);
    await waitFor(() => expect(recencyPill).toHaveAttribute("aria-checked", "true"));
    expect(window.localStorage.getItem(SORT_KEY)).toBe("recency");
  });

  it("reads the stored preference on mount", async () => {
    act(() => {
      window.localStorage.setItem(SORT_KEY, "recency");
    });
    render(<AnchorSidebar />);
    const recencyPill = await screen.findByRole("radio", { name: "按时间" });
    expect(recencyPill).toHaveAttribute("aria-checked", "true");
  });

  it("re-orders character anchors when switching to 按时间", async () => {
    // Mock anchors: 小张妈妈 (reuse=4, created 2026-05-19) and 乖宝 (reuse=2, created 2026-05-20).
    // Default sort (reuse): 小张妈妈 first. Recency: 乖宝 first.
    const user = userEvent.setup();
    render(<AnchorSidebar />);
    await screen.findByText("小张妈妈");
    const charsBefore = screen.getAllByText(/小张妈妈|乖宝/).map((n) => n.textContent);
    expect(charsBefore[0]).toBe("小张妈妈");

    const recencyPill = screen.getByRole("radio", { name: "按时间" });
    await user.click(recencyPill);

    await waitFor(() => {
      const charsAfter = screen.getAllByText(/小张妈妈|乖宝/).map((n) => n.textContent);
      expect(charsAfter[0]).toBe("乖宝");
    });
  });
});
