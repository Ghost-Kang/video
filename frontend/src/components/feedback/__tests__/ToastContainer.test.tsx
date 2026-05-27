/**
 * Unit tests for <ToastContainer/> — W4D5-T2 action 按钮。
 *
 * 覆盖:action 按钮渲染、点击触发 onClick + 自动 dismiss、closeOnClick=false 保留 toast。
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
