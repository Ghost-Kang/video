import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Sidebar } from "../Sidebar";
import type { SessionMeta } from "../../lib/sessionTitle";

const noop = () => {};
const analyzed: Record<string, SessionMeta> = {
  t1: { title: "童年怀旧动画", ts: Date.now(), platform: "douyin" },
};

describe("Sidebar", () => {
  it("shows the auto-derived title + 平台·时间 for analyzed sessions", () => {
    render(
      <Sidebar
        sessions={["t1"]}
        current="t1"
        names={{}}
        meta={analyzed}
        onSwitch={noop}
        onRename={noop}
        onDelete={noop}
      />,
    );
    expect(screen.getByText("童年怀旧动画")).toBeInTheDocument();
    expect(screen.getByText(/抖音/)).toBeInTheDocument();
  });

  it("shows 新会话 · 待拆解 for un-analyzed sessions (no more wall of 新会话)", () => {
    render(
      <Sidebar
        sessions={["t1"]}
        current="t1"
        names={{}}
        meta={{}}
        onSwitch={noop}
        onRename={noop}
        onDelete={noop}
      />,
    );
    expect(screen.getByText("新会话")).toBeInTheDocument();
    expect(screen.getByText("待拆解")).toBeInTheDocument();
  });

  it("a user rename overrides the auto title", () => {
    render(
      <Sidebar
        sessions={["t1"]}
        current="t1"
        names={{ t1: "我命名的" }}
        meta={analyzed}
        onSwitch={noop}
        onRename={noop}
        onDelete={noop}
      />,
    );
    expect(screen.getByText("我命名的")).toBeInTheDocument();
    expect(screen.queryByText("童年怀旧动画")).toBeNull();
  });

  it("switches session on title click", () => {
    const onSwitch = vi.fn();
    render(
      <Sidebar
        sessions={["t1", "t2"]}
        current="t2"
        names={{}}
        meta={analyzed}
        onSwitch={onSwitch}
        onRename={noop}
        onDelete={noop}
      />,
    );
    fireEvent.click(screen.getByText("童年怀旧动画"));
    expect(onSwitch).toHaveBeenCalledWith("t1");
  });

  it("offers 清理空会话 only when empty sessions exist, and confirms before clearing", () => {
    const onClearEmpty = vi.fn();
    // t1 analyzed (kept), t2 current (kept), t3+t4 empty → clearable = 2
    render(
      <Sidebar
        sessions={["t1", "t2", "t3", "t4"]}
        current="t2"
        names={{}}
        meta={analyzed}
        onSwitch={noop}
        onRename={noop}
        onDelete={noop}
        onClearEmpty={onClearEmpty}
      />,
    );
    fireEvent.click(screen.getByText("清理空会话"));
    // two-tap confirm shows the count and only fires on confirm
    const confirm = screen.getByText("清除 2 条");
    expect(onClearEmpty).not.toHaveBeenCalled();
    fireEvent.click(confirm);
    expect(onClearEmpty).toHaveBeenCalledTimes(1);
  });

  it("hides 清理空会话 when there are no empty sessions", () => {
    render(
      <Sidebar
        sessions={["t1"]}
        current="t1"
        names={{}}
        meta={analyzed}
        onSwitch={noop}
        onRename={noop}
        onDelete={noop}
        onClearEmpty={() => {}}
      />,
    );
    expect(screen.queryByText("清理空会话")).toBeNull();
  });
});
