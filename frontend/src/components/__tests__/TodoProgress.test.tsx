import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { TodoProgress } from "../TodoProgress";
import { useCanvasStore } from "../../store/canvasStore";

beforeEach(() => useCanvasStore.setState({ todos: [] }));

describe("TodoProgress (P2 ③ write_todos→画布进度)", () => {
  it("renders nothing when there are no todos", () => {
    const { container } = render(<TodoProgress />);
    expect(container.firstChild).toBeNull();
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
