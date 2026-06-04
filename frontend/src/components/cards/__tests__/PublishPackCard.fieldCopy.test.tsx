import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PublishPackCard } from "../PublishPackCard";
import { useCanvasStore } from "../../../store/canvasStore";
import { MOCK_BAOMAM_ANALYSIS } from "../../../fixtures/baomamFushi001";

const writeText = vi.fn(() => Promise.resolve());

beforeEach(() => {
  useCanvasStore.getState().clear();
  Object.assign(navigator, { clipboard: { writeText } });
  writeText.mockClear();
});

describe("PublishPackCard — 分字段复制 (P2 step5)", () => {
  it("渲染 复制标题/复制话题/复制脚本 + 整段复制 四个按钮", () => {
    useCanvasStore.setState({
      rewriteShots: [{ shot_index: 1, dialogue: "三分钟搞定减脂早餐", visual: "x" }],
    });
    render(<PublishPackCard script={"### 改写脚本\n1. 三分钟搞定减脂早餐"} analysis={MOCK_BAOMAM_ANALYSIS} />);
    for (const id of ["copy-title", "copy-tags", "copy-script", "copy-all"]) {
      expect(screen.getByTestId(id)).toBeInTheDocument();
    }
  });

  it("复制脚本 写入脚本正文;复制话题 写入 #标签", async () => {
    useCanvasStore.setState({
      rewriteShots: [{ shot_index: 1, dialogue: "三分钟搞定减脂早餐", visual: "x" }],
    });
    render(<PublishPackCard script={"### 改写脚本\n1. 三分钟搞定减脂早餐"} analysis={MOCK_BAOMAM_ANALYSIS} />);

    fireEvent.click(screen.getByTestId("copy-script"));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
    expect(writeText.mock.calls.some((c) => String(c[0]).includes("三分钟搞定减脂早餐"))).toBe(true);

    writeText.mockClear();
    fireEvent.click(screen.getByTestId("copy-tags"));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
    expect(writeText.mock.calls.some((c) => String(c[0]).includes("#"))).toBe(true);
  });
});
