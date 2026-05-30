import type { CascadeAnalysisContract } from "../types/cascade";
import type { RewriteShot } from "./cascadeMapper";
import { stripHookCode } from "./cardCopy";

// 发布包标题/标签描述的是「创作者改完的版本」,不是源片。所以标签按创作者
// 选的方向(niche)给,而不是从源片 target_audience 拼 —— 否则把救人视频改成
// 辅食后,标签里会混进「#关注社会新闻的普通大众」这种源片受众(W4 founder 实测缺陷 E)。
const NICHE_TAGS: Record<string, string[]> = {
  baomam_fushi: ["#辅食", "#辅食教程", "#宝宝辅食", "#宝妈日常", "#育儿干货", "#辅食记录"],
  yuer_richang: ["#育儿日常", "#宝妈", "#新手妈妈", "#带娃日常", "#育儿干货", "#当妈以后"],
  jiating_chufang: ["#家庭厨房", "#简单晚餐", "#美食教程", "#在家做饭", "#家常菜", "#今天吃什么"],
};

// 第三条标题用 niche 自己的钩子,而不是源片受众的「X 也能照着拍」。
const NICHE_TAGLINE: Record<string, string> = {
  baomam_fushi: "新手妈妈也能照着做",
  yuer_richang: "当妈以后才懂的日常",
  jiating_chufang: "厨房新手也能直接上手",
};

function niceNiche(niche?: string | null): string {
  return niche && NICHE_TAGS[niche] ? niche : "baomam_fushi";
}

/** 取一句话开头到第一个句读为止,剥掉 Hxx 钩子码,截断成适合做标题的短句。
 *  故意不切裸「.」—— 否则「1.2 秒」「30.5 万赞」这类时间戳/小数会把标题截成「1」。 */
function titleClause(text: string): string {
  return stripHookCode(text)
    .replace(/[，,。!?！？\n].*$/s, "")
    .trim()
    .slice(0, 24);
}

export function buildPublishPack(
  script: string,
  analysis: CascadeAnalysisContract,
  shotImages: string[] = [],
  rewriteShots: RewriteShot[] = [],
  niche?: string | null
): string {
  const titles = getPublishTitles(analysis, rewriteShots, niche);
  const tags = getPublishTags(niche);
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

/**
 * 标题候选优先来自「改写稿」—— 那是创作者目标方向的、她自己口吻的台词,
 * 比源片 hook/climax 贴切得多。没有改写稿时才回退到源片 hook/climax(剥掉 Hxx 码)。
 */
export function getPublishTitles(
  analysis?: CascadeAnalysisContract,
  rewriteShots: RewriteShot[] = [],
  niche?: string | null
): string[] {
  const tagline = NICHE_TAGLINE[niceNiche(niche)];
  const fromRewrite = rewriteShots
    .map((s) => titleClause(s.dialogue))
    .filter((t) => t.length >= 4);
  if (fromRewrite.length > 0) {
    const primary = fromRewrite[0];
    const secondary = fromRewrite.slice(1).find((t) => t !== primary) ?? "";
    return [primary, secondary, tagline].filter(Boolean).slice(0, 3);
  }
  const hook = titleClause(analysis?.viral_analysis.hook ?? "") || "宝宝拒食三次后第一口终于吃下了";
  const climax = titleClause(analysis?.viral_analysis.climax ?? "") || "这一勺下去我哭了";
  return [hook, climax, tagline].slice(0, 3);
}

/** 标签按创作者选的方向给,不掺源片受众。 */
export function getPublishTags(niche?: string | null): string[] {
  return Array.from(new Set(NICHE_TAGS[niceNiche(niche)])).slice(0, 8);
}
