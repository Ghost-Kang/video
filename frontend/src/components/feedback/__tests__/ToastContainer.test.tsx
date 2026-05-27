/**
 * Unit tests for <ToastContainer/> — W4D5-T2 action 按钮 + W4D5-T3 a11y polish。
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastContainer } from "../ToastContainer";
import { useToastStore } from "../../../store/toastStore";

describe("ToastContainer — T2 action button", () => {
  beforeEach(() => {
    useToastStore.getState().clear();
  });

  afterEach(() => {
    useToastStore.getState().clear();
  });

  it("renders an action button when toast.action is set", () => {
    useToastStore.getState().push({
      title: "broke",
      action: { label: "再试一次", onClick: () => {} },
    });
    render(<ToastContainer />);
    expect(screen.getByRole("button", { name: "再试一次" })).toBeInTheDocument();
  });

  it("clicking action invokes onClick AND auto-dismisses by default", () => {
    const onClick = vi.fn();
    useToastStore.getState().push({
      title: "broke",
      action: { label: "刷新", onClick },
    });
    render(<ToastContainer />);
    fireEvent.click(screen.getByRole("button", { name: "刷新" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("closeOnClick=false keeps the toast after action click", () => {
    const onClick = vi.fn();
    useToastStore.getState().push({
      title: "sticky",
      action: { label: "x", onClick, closeOnClick: false },
    });
    render(<ToastContainer />);
    fireEvent.click(screen.getByRole("button", { name: "x" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(useToastStore.getState().toasts).toHaveLength(1);
  });

  it("renders no action button when toast.action is absent", () => {
    useToastStore.getState().push({ title: "plain" });
    render(<ToastContainer />);
    // 只有 close 按钮(aria-label=关闭通知),没有 action
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(1);
    expect(buttons[0].getAttribute("aria-label")).toBe("关闭通知");
  });
});

describe("ToastContainer — T3 a11y polish", () => {
  beforeEach(() => {
    useToastStore.getState().clear();
  });

  afterEach(() => {
    useToastStore.getState().clear();
  });

  it("toast card carries data-toast-id for selector lookup", () => {
    const id = useToastStore.getState().push({ title: "x" });
    render(<ToastContainer />);
    const card = document.querySelector(`[data-toast-id="${id}"]`);
    expect(card).not.toBeNull();
  });

  it("close button has 32x32 hitbox + focus-visible:ring", () => {
    useToastStore.getState().push({ title: "x" });
    render(<ToastContainer />);
    const closeBtn = screen.getByRole("button", { name: "关闭通知" });
    // h-8 + w-8 = 32x32 (Tailwind 8 = 2rem)
    expect(closeBtn.className).toMatch(/\bh-8\b/);
    expect(closeBtn.className).toMatch(/\bw-8\b/);
    expect(closeBtn.className).toMatch(/focus-visible:ring/);
  });

  it("ESC dismisses the toast whose close button is focused", () => {
    const id1 = useToastStore.getState().push({ title: "first" });
    const id2 = useToastStore.getState().push({ title: "second" });
    render(<ToastContainer />);

    const cards = document.querySelectorAll<HTMLElement>("[data-toast-id]");
    expect(cards).toHaveLength(2);
    const secondCloseBtn = cards[1].querySelector<HTMLButtonElement>('button[aria-label="关闭通知"]');
    expect(secondCloseBtn).not.toBeNull();
    secondCloseBtn!.focus();
    expect(document.activeElement).toBe(secondCloseBtn);

    fireEvent.keyDown(window, { key: "Escape" });

    const remaining = useToastStore.getState().toasts.map((t) => t.id);
    expect(remaining).toEqual([id1]);
    expect(remaining).not.toContain(id2);
  });

  it("ESC dismisses the toast whose action button is focused", () => {
    const id = useToastStore.getState().push({
      title: "with action",
      action: { label: "再试", onClick: () => {} },
    });
    render(<ToastContainer />);

    const actionBtn = screen.getByRole("button", { name: "再试" });
    actionBtn.focus();
    expect(document.activeElement).toBe(actionBtn);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(useToastStore.getState().toasts.map((t) => t.id)).not.toContain(id);
  });

  it("ESC outside the container is a no-op (does not dismiss)", () => {
    useToastStore.getState().push({ title: "x" });
    render(<ToastContainer />);
    // body has focus, not within the toast container
    if (document.body.tabIndex < 0) document.body.tabIndex = -1;
    document.body.focus();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(useToastStore.getState().toasts).toHaveLength(1);
  });

  it("non-Escape keys are ignored", () => {
    useToastStore.getState().push({ title: "x" });
    render(<ToastContainer />);
    const closeBtn = screen.getByRole("button", { name: "关闭通知" });
    closeBtn.focus();
    fireEvent.keyDown(window, { key: "Enter" });
    fireEvent.keyDown(window, { key: " " });
    expect(useToastStore.getState().toasts).toHaveLength(1);
  });

  it("error toast uses aria-live=assertive, others polite", () => {
    useToastStore.getState().push({ kind: "error", title: "bad" });
    useToastStore.getState().push({ kind: "info", title: "ok" });
    render(<ToastContainer />);
    const cards = document.querySelectorAll<HTMLElement>("[data-toast-id]");
    expect(cards[0].getAttribute("aria-live")).toBe("assertive");
    expect(cards[1].getAttribute("aria-live")).toBe("polite");
  });
});
