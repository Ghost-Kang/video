// ============================================================================
// 落地页「看看能拆出什么」样例案例 —— 可扩展配置
// ----------------------------------------------------------------------------
// 这里的每一条都是一个【真实已拆解】的视频:source_url 必须是已经分析过、命中
// 缓存能秒出完整拆解的抖音链接。卡面展示我们「拆出的洞察」(钩子/情绪),点开直接
// 进入这条的真实完整分析。
//
// 👉 后续新增真实案例:在 SAMPLE_CASES 数组里**追加一条**即可(无需改组件)。
//    字段说明见 SampleCase。建议品类多样化(美食/剧情/知识/宠物/穿搭…),别只放一类。
// ============================================================================

export interface SampleCase {
  id: string;
  /** 真实已拆解的抖音链接(命中缓存秒出)。必填。 */
  source_url: string;
  /** 品类/题材标签,如「童年怀旧」「美食」「剧情」。 */
  category: string;
  /** 一个点缀 emoji(可选,纯装饰)。 */
  emoji?: string;
  /** 拆出的洞察 · 钩子(卡面主展示,秀交付物质量)。 */
  hook: string;
  /** 拆出的洞察 · 情绪触发(可选)。 */
  emotion?: string;
  /** 卡面暖色渐变(可选,默认用暖橙渐变)。Tailwind 任意值类名。 */
  gradient?: string;
}

export const SAMPLE_CASES: SampleCase[] = [
  {
    id: "tongnian-huaijiu",
    source_url: "https://www.douyin.com/video/7643989458156861038",
    category: "童年怀旧",
    emoji: "🌿",
    hook: "开场直接放出三个孩童满脸西瓜汁啃瓜的治愈画面,配标题《那条河,装满了夏天》,瞬间抓住怀旧受众。",
    emotion: "治愈感 · 怀旧共鸣 · 温暖感",
    gradient: "bg-[radial-gradient(120%_120%_at_30%_20%,#fff7ec_0%,#fbe0b0_45%,#e8a766_100%)]",
  },
  // ⬇️ 新案例往这里加(复制上面一条,换 source_url / category / hook / emotion)
];

const DEFAULT_GRADIENT =
  "bg-[radial-gradient(120%_120%_at_30%_20%,#fff7ec_0%,#fbe0b0_45%,#e8a766_100%)]";

export function caseGradient(c: SampleCase): string {
  return c.gradient || DEFAULT_GRADIENT;
}
