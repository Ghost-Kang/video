import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CardStack } from "../CardStack";
import { useCanvasStore } from "../../store/canvasStore";
import { useWSStore } from "../../store/wsStore";
import { MOCK_BAOMAM_ANALYSIS } from "../../fixtures/baomamFushi001";

const SHOTS = [
  { shot_index: 1, dialogue: "a", visual: "x" },
  { shot_index: 2, dialogue: "b", visual: "y" },
  { shot_index: 3, dialogue: "c", visual: "z" },
];

beforeEach(() => {
  useCanvasStore.getState().clear();
  // 解封灰度门:后端下发 rewrite_enabled=true(全 beta cohort 开)→ cohortFlag=true。
  useWSStore.setState({ loading: false, rewriteEnabled: true });
});

describe("CardStack — confidence 质量闸 (D6 二轮)", () => {
  it("gated 改写:显示拦截卡 + 不发「你的版本」镜头;点重生触发 onTriggerRewrite", () => {
    useCanvasStore.setState({
      analysis: MOCK_BAOMAM_ANALYSIS,
      rewriteShots: SHOTS,
      rewriteQualityGated: true,
    });
    const onTrigger = vi.fn();
    render(<CardStack onTriggerRewrite={onTrigger} />);
    expect(screen.getByTestId("rewrite-quality-gate")).toBeInTheDocument();
    // 平稿不当「你的版本」直接发 —— 镜头区隐藏。
    expect(screen.queryByText("你的版本")).toBeNull();
    fireEvent.click(screen.getByTestId("rewrite-gate-regen"));
    expect(onTrigger).toHaveBeenCalledTimes(1);
  });

  it("达标改写:正常渲染「你的版本」镜头,无拦截卡", () => {
    useCanvasStore.setState({
      analysis: MOCK_BAOMAM_ANALYSIS,
      rewriteShots: SHOTS,
      rewriteQualityGated: false,
    });
    render(<CardStack onTriggerRewrite={vi.fn()} />);
    expect(screen.queryByTestId("rewrite-quality-gate")).toBeNull();
    expect(screen.getByText("你的版本")).toBeInTheDocument();
  });

  it("解封灰度关时:gated 也不渲染拦截卡(改写区整段隐藏)", () => {
    useWSStore.setState({ rewriteEnabled: false });
    useCanvasStore.setState({
      analysis: MOCK_BAOMAM_ANALYSIS,
      rewriteShots: SHOTS,
      rewriteQualityGated: true,
    });
    render(<CardStack onTriggerRewrite={vi.fn()} />);
    expect(screen.queryByTestId("rewrite-quality-gate")).toBeNull();
  });
});
