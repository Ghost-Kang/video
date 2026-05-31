import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SceneClip } from "../SceneClip";
import { COPY } from "../../../lib/cardCopy";

describe("SceneClip", () => {
  it("renders nothing when there is neither clip nor poster", () => {
    const { container } = render(<SceneClip clipUrl={null} poster={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("poster-only (no clip) shows the 仅首帧 badge and no play button", () => {
    render(<SceneClip clipUrl={null} poster="/media/a/scene_1.jpg" />);
    expect(screen.getByText(COPY.clip_poster_only)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: COPY.clip_play_label })).toBeNull();
  });

  it("with a clip shows a play button and no poster-only badge", () => {
    render(<SceneClip clipUrl="/media/a/scene_1.mp4" poster="/media/a/scene_1.jpg" />);
    expect(screen.getByRole("button", { name: COPY.clip_play_label })).toBeInTheDocument();
    expect(screen.queryByText(COPY.clip_poster_only)).toBeNull();
  });

  it("clicking play mounts an inline video", () => {
    render(<SceneClip clipUrl="/media/a/scene_1.mp4" poster={null} />);
    expect(document.querySelector("video")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: COPY.clip_play_label }));
    expect(document.querySelector("video")).not.toBeNull();
  });

  // Regression: every hook must run before the no-media early return, else
  // flipping props between media→no-media changes the hook count and React
  // throws #310 (crashed the whole result page in prod 2026-05-31).
  it("survives re-renders flipping between media and no-media", () => {
    const { rerender, container } = render(<SceneClip clipUrl="/media/a/s.mp4" poster={null} />);
    expect(container.firstChild).not.toBeNull();
    rerender(<SceneClip clipUrl={null} poster={null} />);
    expect(container.firstChild).toBeNull();
    rerender(<SceneClip clipUrl="/media/a/s.mp4" poster={null} />);
    expect(screen.getByRole("button", { name: COPY.clip_play_label })).toBeInTheDocument();
  });
});
