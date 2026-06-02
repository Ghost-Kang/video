import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatPanel } from "../ChatPanel";
import { COPY } from "../../lib/cardCopy";
import type { FailurePayload } from "../../types/cascade";

beforeAll(() => {
  // jsdom 不实现 scrollIntoView,ChatPanel 在 useEffect 里调用会爆。
  Element.prototype.scrollIntoView = vi.fn();
});

const baseProps = {
  streaming: "",
  thinking: [],
  onSend: () => {},
  onToggleCollapse: () => {},
};

describe("ChatPanel 5-state machine (W5D3)", () => {
  it("state=idle: empty store + no messages → shows idle hint + sample chips, no input", () => {
    render(
      <ChatPanel
        {...baseProps}
        messages={[]}
        loading={false}
        analysis={null}
        script=""
        failure={null}
      />
    );

    expect(screen.getByTestId("side-title")).toHaveAttribute("data-state", "idle");
    expect(screen.getByTestId("side-title")).toHaveTextContent(COPY.side_title_idle);
    expect(screen.getByTestId("side-idle")).toBeInTheDocument();
    // 无输入框 — refine textarea + 发送按钮都不应渲染
    expect(screen.queryByTestId("refine-textarea")).not.toBeInTheDocument();
    expect(screen.queryByText("发送")).not.toBeInTheDocument();
  });

  it("state=running: loading=true + no analysis → dock 轻提示(进度真理之源在主画面) + no input", () => {
    render(
      <ChatPanel
        {...baseProps}
        messages={[{ role: "user", content: "https://www.douyin.com/video/123" }]}
        loading={true}
        analysis={null}
        script=""
        failure={null}
      />
    );

    expect(screen.getByTestId("side-title")).toHaveAttribute("data-state", "running");
    expect(screen.getByTestId("side-title")).toHaveTextContent(COPY.side_title_running);
    // 进度条/阶段/95%逃生已上移到主画面 AnalyzingHero;dock 只留一句轻提示,不再重复。
    expect(screen.getByTestId("side-running")).toHaveTextContent(COPY.side_running_dock_hint);
    expect(screen.queryByTestId("analysis-progress")).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(screen.queryByTestId("refine-textarea")).not.toBeInTheDocument();
  });

  it("state=failed: failure payload → red banner + retry samples, no quick chips", () => {
    const failure: FailurePayload = {
      code: "S4_SCENES_LEN_OUT_OF_RANGE",
      hint: "这条视频镜头太少",
      actions: ["RETRY_WITH_NEW_URL", "PICK_FROM_FEATURED"],
      request_id: "req_abc123",
    };
    render(
      <ChatPanel
        {...baseProps}
        messages={[{ role: "user", content: "https://www.douyin.com/video/x" }]}
        loading={false}
        analysis={null}
        script=""
        failure={failure}
      />
    );

    expect(screen.getByTestId("side-title")).toHaveAttribute("data-state", "failed");
    expect(screen.getByTestId("side-title")).toHaveTextContent(COPY.side_title_failed);

    const banner = screen.getByTestId("side-failed");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("这条视频镜头太少");
    expect(banner).toHaveTextContent("S4_SCENES_LEN_OUT_OF_RANGE");
    expect(banner).toHaveTextContent("req_abc123");

    // 报告按钮存在
    expect(screen.getByTestId("side-failed-report")).toBeInTheDocument();

    // 无 quick reply chips、无 refine 输入框
    expect(screen.queryByTestId("ask-chip")).not.toBeInTheDocument();
    expect(screen.queryByTestId("refine-textarea")).not.toBeInTheDocument();

    // 报警 role
    expect(banner).toHaveAttribute("role", "alert");
  });

  it("state=ready: analysis present + script empty → headline + hint, no chips/input", () => {
    const fakeAnalysis = {
      schema_version: "1.0",
      analysis_id: "a1",
      source_url: "https://www.douyin.com/video/1",
      platform: "douyin",
      created_at: "2026-05-27T00:00:00Z",
      model: "doubao",
      cost_cny: 0.1,
      duration_s: 30,
      // viral_analysis / scenes minimal — ChatPanel ignores fields, only checks truthy
      viral_analysis: {},
      scenes: [],
      warnings: [],
      confidence: 0.7,
      full_transcript: "",
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;

    render(
      <ChatPanel
        {...baseProps}
        messages={[{ role: "user", content: "first" }]}
        loading={false}
        analysis={fakeAnalysis}
        script=""
        failure={null}
      />
    );

    expect(screen.getByTestId("side-title")).toHaveAttribute("data-state", "ready");
    expect(screen.getByTestId("side-title")).toHaveTextContent(COPY.side_title_ready);
    expect(screen.getByTestId("side-ready")).toBeInTheDocument();
    expect(screen.getByTestId("side-ready")).toHaveTextContent(COPY.side_ready_headline);

    expect(screen.queryByTestId("ask-chip")).not.toBeInTheDocument();
    expect(screen.queryByTestId("refine-textarea")).not.toBeInTheDocument();
  });

  it("state=refine: script non-empty → quick chips + refine textarea + 发送 button", () => {
    render(
      <ChatPanel
        {...baseProps}
        messages={[{ role: "user", content: "first" }]}
        loading={false}
        analysis={null}
        script="改完的版本 Markdown 内容"
        failure={null}
      />
    );

    expect(screen.getByTestId("side-title")).toHaveAttribute("data-state", "refine");
    expect(screen.getByTestId("side-title")).toHaveTextContent(COPY.side_title_refine);

    expect(screen.getByTestId("ask-chip")).toBeInTheDocument();
    expect(screen.getByTestId("refine-textarea")).toBeInTheDocument();
    expect(screen.getByText("发送")).toBeInTheDocument();
    // refine placeholder 替换原「想改哪里,直接说」
    expect(screen.getByTestId("refine-textarea")).toHaveAttribute(
      "placeholder",
      COPY.side_refine_placeholder
    );
  });

  it("failed beats running: failure + loading=true → still shows failed UI", () => {
    // 边缘条件 — 失败先到、loading 还没被翻 false 的瞬间。该走 failed 路径。
    const failure: FailurePayload = {
      code: "S7_UPSTREAM_TIMEOUT",
      hint: "分析超时了",
      actions: ["RETRY_SAME_URL_AFTER_30S"],
      request_id: "req_x",
    };
    render(
      <ChatPanel
        {...baseProps}
        messages={[]}
        loading={true}
        analysis={null}
        script=""
        failure={failure}
      />
    );
    expect(screen.getByTestId("side-title")).toHaveAttribute("data-state", "failed");
    expect(screen.queryByTestId("analysis-progress")).not.toBeInTheDocument();
    expect(screen.queryByTestId("side-running")).not.toBeInTheDocument();
  });
});
