import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RewriteShotCard } from "../RewriteShotCard";
import { COPY } from "../../../lib/cardCopy";
import type { RewriteShot } from "../../../lib/cascadeMapper";

const shot: RewriteShot = { shot_index: 2, dialogue: "在家两块钱烤一炉", visual: "中景,酥皮特写" };

describe("RewriteShotCard · 生成草稿图 leg", () => {
  it("无 onGenerateFirstFrame 时不渲染草稿图区(向后兼容)", () => {
    render(<RewriteShotCard shot={shot} />);
    expect(screen.queryByTestId("rewrite-shot-card-2-generate")).toBeNull();
    // 文案仍在
    expect(screen.getByText(shot.dialogue)).toBeInTheDocument();
  });

  it("IDLE:有回调且无图 → 显示「生成草稿图」按钮,点击触发回调", async () => {
    const user = userEvent.setup();
    const onGen = vi.fn();
    render(<RewriteShotCard shot={shot} onGenerateFirstFrame={onGen} />);
    const btn = screen.getByTestId("rewrite-shot-card-2-generate");
    expect(btn).toHaveTextContent(COPY.shot_draft_generate);
    await user.click(btn);
    expect(onGen).toHaveBeenCalledWith(2); // 传 shot_index
  });

  it("PENDING:点击后显示生成中(按钮消失)", async () => {
    const user = userEvent.setup();
    render(<RewriteShotCard shot={shot} onGenerateFirstFrame={vi.fn()} />);
    await user.click(screen.getByTestId("rewrite-shot-card-2-generate"));
    expect(screen.getByText(COPY.shot_draft_generating)).toBeInTheDocument();
    expect(screen.queryByTestId("rewrite-shot-card-2-generate")).toBeNull();
  });

  it("DONE:firstFrameUrl 存在 → 渲染图,不显示按钮/转圈", () => {
    const { container } = render(
      <RewriteShotCard
        shot={{ ...shot, firstFrameUrl: "https://cdn.test/draft.png" }}
        onGenerateFirstFrame={vi.fn()}
      />
    );
    // alt="" 是装饰性图(视觉内容已在下方文字描述),不进 a11y tree → 直接查 DOM。
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img).toHaveAttribute("src", "https://cdn.test/draft.png");
    expect(screen.queryByTestId("rewrite-shot-card-2-generate")).toBeNull();
    expect(screen.queryByText(COPY.shot_draft_generating)).toBeNull();
  });

  it("FAILED:firstFrameError 存在 → 即时显示后端友好提示 + 重试(不等超时)", async () => {
    const user = userEvent.setup();
    const onGen = vi.fn();
    const msg = "草稿图功能还没开通(管理员需配置生图密钥),其他都能正常用";
    render(
      <RewriteShotCard
        shot={{ ...shot, firstFrameError: msg }}
        onGenerateFirstFrame={onGen}
      />
    );
    // 友好提示直接展示,不显示「生成草稿图」首发按钮
    expect(screen.getByText(msg)).toBeInTheDocument();
    expect(screen.queryByTestId("rewrite-shot-card-2-generate")).toBeNull();
    // 点重试 → 重新触发生成
    await user.click(screen.getByTestId("rewrite-shot-card-2-retry"));
    expect(onGen).toHaveBeenCalledWith(2);
  });
});

describe("RewriteShotCard · 图生视频 leg", () => {
  const withImage: RewriteShot = { ...shot, firstFrameUrl: "https://cdn.test/draft.png" };

  it("有草稿图 + onGenerateShotVideo → 出「生成视频」按钮,点击触发", async () => {
    const user = userEvent.setup();
    const onVid = vi.fn();
    render(
      <RewriteShotCard shot={withImage} onGenerateFirstFrame={vi.fn()} onGenerateShotVideo={onVid} />
    );
    const btn = screen.getByTestId("rewrite-shot-card-2-video-generate");
    expect(btn).toHaveTextContent(COPY.shot_video_generate);
    await user.click(btn);
    expect(onVid).toHaveBeenCalledWith(2);
  });

  it("无草稿图时不出「生成视频」(image-grounded,需先有图)", () => {
    render(<RewriteShotCard shot={shot} onGenerateFirstFrame={vi.fn()} onGenerateShotVideo={vi.fn()} />);
    expect(screen.queryByTestId("rewrite-shot-card-2-video-generate")).toBeNull();
  });

  it("videoUrl 存在 → 渲染 <video>(poster=草稿图),不再出生成视频按钮", () => {
    render(
      <RewriteShotCard
        shot={{ ...withImage, videoUrl: "https://cdn.test/shot.mp4" }}
        onGenerateFirstFrame={vi.fn()}
        onGenerateShotVideo={vi.fn()}
      />
    );
    const video = screen.getByTestId("rewrite-shot-card-2-video");
    expect(video).toHaveAttribute("src", "https://cdn.test/shot.mp4");
    expect(video).toHaveAttribute("poster", "https://cdn.test/draft.png");
    expect(screen.queryByTestId("rewrite-shot-card-2-video-generate")).toBeNull();
  });

  it("videoError 存在 → 即时显示提示 + 视频重试", () => {
    render(
      <RewriteShotCard
        shot={{ ...withImage, videoError: "这条视频没生成成功,点重试试试" }}
        onGenerateFirstFrame={vi.fn()}
        onGenerateShotVideo={vi.fn()}
      />
    );
    expect(screen.getByText("这条视频没生成成功,点重试试试")).toBeInTheDocument();
    expect(screen.getByTestId("rewrite-shot-card-2-video-retry")).toBeInTheDocument();
  });
});
