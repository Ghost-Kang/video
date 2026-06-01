import type { CascadeAnalysisContract } from "../types/cascade";
import type { RewriteShot } from "./cascadeMapper";
import { stripHookCode, scrubUiForbidden } from "./cardCopy";

// 发布包标题/标签描述的是「创作者改完的版本」,不是源片。
//
// 旧实现按 3 个写死 niche(辅食/育儿/厨房)给标签,且未选方向时硬回退辅食。
// 929cb21 砍掉 niche 后运行时 niche 恒 null → 任何视频的发布包都套辅食标签(P2 缺陷)。
// 现改成:有 niche 表命中就用(向后兼容旧 3 赛道),否则从「分析的 theme + 改写台词」
// 派生标签,通用空态兜底 —— 绝不再默认辅食,也绝不掺源片受众(缺陷 E)。
const NICHE_TAGS: Record<string, string[]> = {
  baomam_fushi: ["#辅食", "#辅食教程", "#宝宝辅食", "#宝妈日常", "#育儿干货", "#辅食记录"],
  yuer_richang: ["#育儿日常", "#宝妈", "#新手妈妈", "#带娃日常", "#育儿干货", "#当妈以后"],
  jiating_chufang: ["#家庭厨房", "#简单晚餐", "#美食教程", "#在家做饭", "#家常菜", "#今天吃什么"],
};

const NICHE_TAGLINE: Record<string, string> = {
  baomam_fushi: "新手妈妈也能照着做",
  yuer_richang: "当妈以后才懂的日常",
  jiating_chufang: "厨房新手也能直接上手",
};

// 通用兜底标签(去 niche 后,无主题信息时的安全空态 —— 不暴露任何赛道假设)。
const GENERIC_TAGS = ["#拆解爆款", "#内容创作", "#短视频", "#爆款拆解", "#创作灵感"];
const GENERIC_TAGLINE = "照着这条思路拍你自己的";

function isKnownNiche(niche?: string | null): niche is keyof typeof NICHE_TAGS {
  return !!niche && niche in NICHE_TAGS;
}

/** 从分析的 theme(去 niche 后的标签主源)抽 1-2 个短词做 hashtag,scrub 禁词。 */
function tagsFromAnalysis(analysis?: CascadeAnalysisContract): string[] {
  const theme = scrubUiForbidden(stripHookCode(analysis?.viral_analysis?.theme ?? "")).trim();
  // theme 形如「趣味动物观察」「童年怀旧」—— 拆成 1 个主标签 + 通用补充,不掺受众。
  const themeTag = theme ? `#${theme.replace(/[\s#，,。·]+/g, "").slice(0, 10)}` : "";
  return Array.from(new Set([themeTag, ...GENERIC_TAGS].filter((t) => t && t !== "#"))).slice(0, 6);
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
  // titles/tags 已在各自函数里 scrub;script 是改写稿,也可能含禁词 → 复制前最后一道
  // scrub(P2:之前只 stripHookCode 不 scrub,禁词可漏到剪贴板)。
  const titles = getPublishTitles(analysis, rewriteShots, niche).map(scrubUiForbidden);
  const tags = getPublishTags(niche, analysis);
  const cleanScript = scrubUiForbidden(script.trim());
  // 镜头图缺失:优雅降级到一句提示,不塞坏链(best-effort,clip 范式)。
  const imageLines = shotImages.filter(Boolean).map((url, index) => `镜头 ${index + 1}: ${url}`);
  const lines = [
    "【标题候选】",
    titles.map((title, index) => `${index + 1}. ${title}`).join("\n"),
    "",
    "【标签】",
    tags.join(" "),
    "",
    "【完整脚本】",
    cleanScript,
    "",
    "【镜头图】",
    imageLines.length ? imageLines.join("\n") : "(草稿图生成后自动填入)",
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
  // tagline:已知 niche 用其专属句,否则通用句(不再默认辅食)。
  const tagline = isKnownNiche(niche) ? NICHE_TAGLINE[niche] : GENERIC_TAGLINE;
  const fromRewrite = rewriteShots
    .map((s) => titleClause(s.dialogue))
    .filter((t) => t.length >= 4);
  if (fromRewrite.length > 0) {
    const primary = fromRewrite[0];
    const secondary = fromRewrite.slice(1).find((t) => t !== primary) ?? "";
    return [primary, secondary, tagline].filter(Boolean).slice(0, 3);
  }
  // 无改写稿:回退源片 hook/climax(剥 Hxx 码)。去 niche 后不再硬编辅食兜底句 ——
  // 用分析 theme 兜底,真没有就只给 tagline。
  const hook = titleClause(analysis?.viral_analysis.hook ?? "");
  const climax = titleClause(analysis?.viral_analysis.climax ?? "");
  const themeFallback = titleClause(analysis?.viral_analysis.theme ?? "");
  return [hook, climax, themeFallback, tagline].filter(Boolean).slice(0, 3);
}

/** 标签:已知 niche 用其标签表(向后兼容旧 3 赛道);否则从分析 theme 派生 +
 *  通用兜底。绝不掺源片受众(缺陷 E),绝不默认辅食。全部已 scrub。 */
export function getPublishTags(niche?: string | null, analysis?: CascadeAnalysisContract): string[] {
  const raw = isKnownNiche(niche) ? NICHE_TAGS[niche] : tagsFromAnalysis(analysis);
  return Array.from(new Set(raw.map(scrubUiForbidden).filter(Boolean))).slice(0, 8);
}
