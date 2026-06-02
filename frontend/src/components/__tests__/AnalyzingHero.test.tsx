import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalyzingHero } from "../AnalyzingHero";
import { COPY } from "../../lib/cardCopy";
import type { SampleCase } from "../../lib/sampleCases";

const caseData: SampleCase = {
  id: "t",
  source_url: "https://www.douyin.com/video/1",
  category: "童年怀旧",
  emoji: "🌿",
  hook: "开场三个孩童啃西瓜,瞬间抓住怀旧受众。",
  emotion: "治愈感 · 怀旧共鸣",
  slides: [
    { clip: "/m/1.mp4", poster: "/m/1.jpg", theme: "开场吃西瓜", note: "啃西瓜", emotion: "欢快" },
    { clip: "/m/2.mp4", poster: "/m/2.jpg", theme: "乡村全景", note: "全景", emotion: "舒缓" },
  ],
};

describe("AnalyzingHero", () => {
  it("有案例素材:显示「你刚点的这条」标题 + 封面 + 已拆出的钩子 + 内嵌进度真理之源", () => {
    render(<AnalyzingHero caseData={caseData} thinking={[]} />);
    expect(screen.getByTestId("analyzing-hero-title")).toHaveTextContent(
      COPY.analyzing_hero_title_case,
    );
    expect(screen.getByTestId("analyzing-hero-cover")).toBeInTheDocument();
    expect(screen.getByTestId("analyzing-hero-hook")).toHaveTextContent(caseData.hook);
    // 关键:进度条/阶段/95%逃生在主画面(不再埋底部 dock)。
    expect(screen.getByTestId("analysis-progress")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("无案例素材(粘陌生链接):退化为通用扫描骨架 + 通用标题,但仍含进度", () => {
    render(<AnalyzingHero caseData={null} thinking={[]} />);
    expect(screen.getByTestId("analyzing-hero-title")).toHaveTextContent(
      COPY.analyzing_hero_title_generic,
    );
    expect(screen.getByTestId("analyzing-hero-generic")).toBeInTheDocument();
    expect(screen.queryByTestId("analyzing-hero-cover")).not.toBeInTheDocument();
    expect(screen.queryByTestId("analyzing-hero-hook")).not.toBeInTheDocument();
    expect(screen.getByTestId("analysis-progress")).toBeInTheDocument();
  });
});
