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
const MENCHONG = "/media/showcase/menchong";

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
    // 趣味萌宠 —— 「派大星跳钢管舞」(海星缠水草的猎奇治愈向)。
    // slides 由 prod gen_showcase_case.py 生成(7 幕 clip 落 /media/showcase/menchong/,
    // 永不清理),theme/note/emotion 为模型实际输出。
    id: "menchong-paidaxing",
    source_url: "https://www.douyin.com/video/7645650053617609381",
    category: "趣味萌宠",
    emoji: "🐾",
    hook: "开场直接放出粉色海星爬杆的特写画面,配台词「世界上最喜欢跳钢管舞的动物」,用猎奇的表述瞬间抓住观众注意力。",
    emotion: "猎奇感 · 治愈感 · 搞笑趣味感",
    gradient: "bg-[radial-gradient(120%_120%_at_30%_20%,#fdf2f8_0%,#fbcfe8_45%,#f0a4c8_100%)]",
    slides: [
      { clip: `${MENCHONG}/scene_1.mp4`, poster: `${MENCHONG}/scene_1.jpg`, theme: "海星爬杆特写开场", note: "特写粉色海星爬杆的画面", emotion: "猎奇有趣" },
      { clip: `${MENCHONG}/scene_2.mp4`, poster: `${MENCHONG}/scene_2.jpg`, theme: "多海星爬杆展示", note: "中景展示鱼缸内多只海星爬杆", emotion: "轻松有趣" },
      { clip: `${MENCHONG}/scene_3.mp4`, poster: `${MENCHONG}/scene_3.jpg`, theme: "展示准备材料", note: "中景展示手持植物茎秆的画面", emotion: "轻松" },
      { clip: `${MENCHONG}/scene_4.mp4`, poster: `${MENCHONG}/scene_4.jpg`, theme: "展示饲养海星的鱼缸", note: "全景展示鱼缸,手放入海星", emotion: "轻松" },
      { clip: `${MENCHONG}/scene_5.mp4`, poster: `${MENCHONG}/scene_5.jpg`, theme: "实操插杆放海星", note: "近景展示手在缸内插杆放海星的操作", emotion: "轻松" },
      { clip: `${MENCHONG}/scene_6.mp4`, poster: `${MENCHONG}/scene_6.jpg`, theme: "意外状况展示", note: "中景展示被海星拔起的茎秆", emotion: "搞笑" },
      { clip: `${MENCHONG}/scene_7.mp4`, poster: `${MENCHONG}/scene_7.jpg`, theme: "展示成功效果", note: "中景展示多只海星爬杆的效果", emotion: "治愈有趣" },
    ],
  },
  // ⬇️ 新案例往这里加(给我 source_url + 品类 + 钩子/情绪,我把它的逐幕 clip 预生成到
  //    /media/showcase/<id>/ 后填进 slides 即可)。
];

const DEFAULT_GRADIENT =
  "bg-[radial-gradient(120%_120%_at_30%_20%,#fff7ec_0%,#fbe0b0_45%,#e8a766_100%)]";

export function caseGradient(c: SampleCase): string {
  return c.gradient || DEFAULT_GRADIENT;
}
