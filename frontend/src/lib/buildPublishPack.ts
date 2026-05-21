import type { CascadeAnalysisContract } from "../types/cascade";

const NICHE_TAGS: Record<string, string[]> = {
  baomam_fushi: ["#辅食", "#辅食教程", "#宝妈日常", "#育儿干货"],
  yuer_richang: ["#育儿日常", "#宝妈", "#新手妈妈", "#带娃日常"],
  jiating_chufang: ["#家庭厨房", "#简单晚餐", "#美食教程", "#在家做饭"],
};

export function buildPublishPack(
  script: string,
  analysis: CascadeAnalysisContract,
  shotImages: string[] = []
): string {
  const titles = getPublishTitles(analysis);
  const tags = getPublishTags(analysis);
  const imageLines = shotImages.map((url, index) => `镜头 ${index + 1}: ${url}`);
  const lines = [
    "【标题候选】",
    titles.map((title, index) => `${index + 1}. ${title}`).join("\n"),
    "",
    "【标签】",
    tags.join(" "),
    "",
    "【完整脚本】",
    script.trim(),
    "",
    "【镜头图】",
    imageLines.length ? imageLines.join("\n") : "镜头 1: 待补充",
    "",
    "—— 用 Cascade 做的 · cascade.app",
  ];
  return lines.join("\n").trim();
}

export function getPublishTitles(analysis?: CascadeAnalysisContract): string[] {
  const hook = analysis?.viral_analysis.hook.replace(/[，。,.].*$/, "") || "宝宝拒食三次后，第一口终于吃下了";
  const climax = analysis?.viral_analysis.climax.replace(/[，。,.].*$/, "") || "这一勺下去我哭了";
  const audience = analysis?.viral_analysis.target_audience.split(/[，,、 ]/)[0] || "新手妈妈";
  return [hook, climax, `${audience}也能直接照着拍`].slice(0, 3);
}

export function getPublishTags(analysis?: CascadeAnalysisContract, niche = "baomam_fushi"): string[] {
  const base = NICHE_TAGS[niche] ?? NICHE_TAGS.baomam_fushi;
  const audience = (analysis?.viral_analysis.target_audience ?? "")
    .split(/[，,、\s]+/)
    .filter((part) => part.length >= 2)
    .slice(0, 3)
    .map((part) => `#${part.replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, "")}`)
    .filter((tag) => tag.length > 1);
  return Array.from(new Set([...base, ...audience])).slice(0, 8);
}
