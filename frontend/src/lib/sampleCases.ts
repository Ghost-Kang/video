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

/** 一个案例里的逐幕视频(轮播的一帧)。clip/poster 是 /media/showcase/<case>/… 的
 *  稳定路径(由 backend 预生成、永不清理)。 */
export interface ShowcaseSlide {
  clip: string;
  poster: string;
  theme: string;
  note: string;
  emotion?: string;
}

export interface SampleCase {
  id: string;
  /** 真实已拆解的抖音链接(命中缓存秒出)。必填。 */
  source_url: string;
  /** 品类/题材标签,如「童年怀旧」「美食」「剧情」。 */
  category: string;
  /** 一个点缀 emoji(可选,纯装饰)。 */
  emoji?: string;
  /** 拆出的洞察 · 钩子(秀交付物质量)。 */
  hook: string;
  /** 拆出的洞察 · 情绪触发(可选)。 */
  emotion?: string;
  /** 卡面暖色渐变(可选)。 */
  gradient?: string;
  /** 该案例的逐幕视频片段 —— 一个案例就能轮播。空则退化为静态卡。 */
  slides?: ShowcaseSlide[];
}

const TONGNIAN = "/media/showcase/tongnian";

export const SAMPLE_CASES: SampleCase[] = [
  {
    id: "tongnian-huaijiu",
    source_url: "https://www.douyin.com/video/7643989458156861038",
    category: "童年怀旧",
    emoji: "🌿",
    hook: "开场直接放出三个孩童满脸西瓜汁啃瓜的治愈画面,配标题《那条河,装满了夏天》,瞬间抓住怀旧受众。",
    emotion: "治愈感 · 怀旧共鸣 · 温暖感",
    gradient: "bg-[radial-gradient(120%_120%_at_30%_20%,#fff7ec_0%,#fbe0b0_45%,#e8a766_100%)]",
    slides: [
      { clip: `${TONGNIAN}/scene_1.mp4`, poster: `${TONGNIAN}/scene_1.jpg`, theme: "开场吃西瓜", note: "三个孩童举着西瓜开心啃食", emotion: "欢快" },
      { clip: `${TONGNIAN}/scene_2.mp4`, poster: `${TONGNIAN}/scene_2.jpg`, theme: "夏日乡村全景", note: "从蓝天白云向下移镜展现乡村全景", emotion: "舒缓" },
      { clip: `${TONGNIAN}/scene_3.mp4`, poster: `${TONGNIAN}/scene_3.jpg`, theme: "河边摸鱼前奏", note: "孩子弯腰看水面,男孩做噤声手势", emotion: "趣味" },
      { clip: `${TONGNIAN}/scene_4.mp4`, poster: `${TONGNIAN}/scene_4.jpg`, theme: "嬉水打闹", note: "多镜头切换展现孩童嬉水", emotion: "欢快热闹" },
      { clip: `${TONGNIAN}/scene_5.mp4`, poster: `${TONGNIAN}/scene_5.jpg`, theme: "切冰镇西瓜", note: "男孩切冰在河里的西瓜,特写切面", emotion: "愉悦" },
      { clip: `${TONGNIAN}/scene_6.mp4`, poster: `${TONGNIAN}/scene_6.jpg`, theme: "吃西瓜玩闹", note: "取笑沾了西瓜籽的男孩", emotion: "治愈" },
      { clip: `${TONGNIAN}/scene_7.mp4`, poster: `${TONGNIAN}/scene_7.jpg`, theme: "黄昏回家", note: "手牵手的背影朝夕阳走在田埂上", emotion: "温情怀旧" },
    ],
  },
  {
    // 趣味萌宠 —— 「派大星跳钢管舞」(海星缠水草的猎奇治愈向)。真实分析数据:
    // 本地真 doubao 跑通(theme/hook/emotion/9 幕均为模型实际输出);resolver 实测
    // 可解析(duration 49.6s,desc「如何让派大星跳钢管舞」by 神奇小查)。
    // slides 暂缺:逐幕 clip 媒体需在 prod 容器跑 gen_showcase_case.py 生成到
    //   /media/showcase/menchong/(见文件头注释)。无 slides → 在 SampleCaseCarousel
    //   里以静态洞察卡呈现(hook+情绪),点开走真链接进完整分析。prod 生成后把打印的
    //   slides 数组粘到下方 `slides:` 即可升级成逐幕视频轮播(亦可提到数组首位做 hero)。
    id: "menchong-paidaxing",
    source_url: "https://www.douyin.com/video/7645650053617609381",
    category: "趣味萌宠",
    emoji: "🐾",
    hook: "开场特写粉色海星缠绕水草,字幕「世界上最喜欢跳钢管舞的动物」,用新奇比喻一秒抓住好奇心。",
    emotion: "趣味性 · 治愈感 · 好奇心",
    gradient: "bg-[radial-gradient(120%_120%_at_30%_20%,#fdf2f8_0%,#fbcfe8_45%,#f0a4c8_100%)]",
  },
  // ⬇️ 新案例往这里加(给我 source_url + 品类 + 钩子/情绪,我把它的逐幕 clip 预生成到
  //    /media/showcase/<id>/ 后填进 slides 即可)。
];

const DEFAULT_GRADIENT =
  "bg-[radial-gradient(120%_120%_at_30%_20%,#fff7ec_0%,#fbe0b0_45%,#e8a766_100%)]";

export function caseGradient(c: SampleCase): string {
  return c.gradient || DEFAULT_GRADIENT;
}
