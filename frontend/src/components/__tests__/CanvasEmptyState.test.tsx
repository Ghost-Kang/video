import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CanvasEmptyState } from "../CanvasEmptyState";

afterEach(() => vi.restoreAllMocks());

describe("CanvasEmptyState (画布空态引导)", () => {
  it("渲染六步流程 + 告诉导演 CTA", () => {
    render(<CanvasEmptyState />);
    expect(screen.getByTestId("canvas-empty-state")).toBeInTheDocument();
    for (const s of ["策划书", "角色", "场景", "分镜", "视频", "合成"]) {
      expect(screen.getByText(s)).toBeInTheDocument();
    }
    expect(screen.getByTestId("empty-ask-director")).toHaveTextContent("告诉导演");
  });

  it("点 CTA dispatch open_canvas_chat 事件", () => {
    const spy = vi.fn();
    window.addEventListener("open_canvas_chat", spy);
    render(<CanvasEmptyState />);
    fireEvent.click(screen.getByTestId("empty-ask-director"));
    expect(spy).toHaveBeenCalledTimes(1);
    window.removeEventListener("open_canvas_chat", spy);
  });
});
