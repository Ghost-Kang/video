import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { TodoProgress } from "../TodoProgress";
import { useCanvasStore } from "../../store/canvasStore";

beforeEach(() => useCanvasStore.setState({ todos: [], nodes: [] }));

describe("TodoProgress (P2 六步向导 StageRail)", () => {
  it("无 todos 时常驻显示六步路线图(让用户先看懂流程)", () => {
    render(<TodoProgress />);
    expect(screen.getByTestId("todo-progress")).toHaveTextContent("创作流程 · 0/6");
    for (const s of ["策划书", "角色", "场景", "分镜", "视频", "合成"]) {
      expect(screen.getByText(s)).toBeInTheDocument();
    }
  });

  it("renders the plan steps + completed count", () => {
    useCanvasStore.setState({
      todos: [
        { content: "策划书", status: "completed" },
        { content: "角色三视图", status: "in_progress" },
        { content: "场景图", status: "pending" },
      ],
    });
    render(<TodoProgress />);
    expect(screen.getByTestId("todo-progress")).toHaveTextContent("导演计划 · 1/3");
    expect(screen.getByText("角色三视图")).toBeInTheDocument();
    expect(screen.getByTestId("todo-in_progress")).toBeInTheDocument();
    expect(screen.getByTestId("todo-completed")).toBeInTheDocument();
  });
});
