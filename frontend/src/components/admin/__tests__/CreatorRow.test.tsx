import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CreatorRow } from "../CreatorRow";
import type { Creator } from "../../../lib/creatorsApi";

function row(c: Creator) {
  return (
    <table>
      <tbody>
        <CreatorRow creator={c} />
      </tbody>
    </table>
  );
}

function creator(overrides: Partial<Creator> = {}): Creator {
  return {
    user_id: "u_test_alpha",
    first_seen: "2026-05-20T08:00:00Z",
    last_seen: "2026-05-21T08:00:00Z",
    runs_started: 0,
    rewrites_completed: 0,
    publish_packs_copied: 0,
    anchors_count: 0,
    anchors_total_reuse_count: 0,
    interview_logged: false,
    ...overrides,
  };
}

describe("CreatorRow", () => {
  it("renders all aggregate columns", () => {
    render(
      row(
        creator({
          runs_started: 4,
          rewrites_completed: 3,
          publish_packs_copied: 1,
          anchors_count: 2,
          anchors_total_reuse_count: 5,
        }),
      ),
    );
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText(/2 个 · 复用 5/)).toBeInTheDocument();
  });

  it("shows the invited badge when zero activity", () => {
    render(row(creator()));
    expect(screen.getByText("已邀请")).toBeInTheDocument();
  });

  it("shows the looping badge when reuse_count is non-zero", () => {
    render(row(creator({ runs_started: 1, anchors_total_reuse_count: 3 })));
    expect(screen.getByText("循环复用")).toBeInTheDocument();
  });

  it("shows the interview chip when interview_logged is true", () => {
    render(row(creator({ runs_started: 1, interview_logged: true })));
    expect(screen.getByText("已访谈")).toBeInTheDocument();
  });

  it("truncates very long user_ids", () => {
    const long = "u_" + "x".repeat(40);
    render(row(creator({ user_id: long })));
    const cell = screen.getByTitle(long);
    expect(cell.textContent?.length).toBeLessThan(long.length);
    expect(cell.textContent?.endsWith("…")).toBe(true);
  });
});
