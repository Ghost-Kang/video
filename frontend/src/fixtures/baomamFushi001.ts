import type { CascadeAnalysisContract } from "../types/cascade";

/** synthetic_v1/baomam_fushi/001 — dev default for card stack */
export const MOCK_BAOMAM_ANALYSIS: CascadeAnalysisContract = {
  schema_version: "1.0",
  analysis_id: "ana_syn_baomam_001",
  source_url: "https://www.douyin.com/video/synthetic_baomam_001",
  platform: "douyin",
  created_at: "2026-05-19T08:00:00+00:00",
  model: "doubao-seed-2-0-pro",
  cost_cny: 0.42,
  duration_s: 38,
  confidence: 0.88,
  viral_analysis: {
    hook: "开场 1.2 秒抛出「宝宝拒食三次后第一口吃下」的悬念画面",
    pacing: "节奏 4-3-2 秒压缩，越接近结尾镜头越短",
    climax: "倒数第二镜：宝宝抢勺子的笑声 + 妈妈惊喜表情",
    visual_style: "暖色厨房，木质砧板，自然光，俯拍为主",
    emotional_arc: "焦虑（喂不下）→ 尝试（换花样）→ 惊喜（吃下）→ 成就感",
    target_audience: "0-3 岁宝宝妈妈，普通家庭厨房环境",
    engagement_levers: "评论区抛「你家宝宝几个月开始吃辅食」诱导互动",
    replicable_formula:
      "悬念开场（拒食痛点） + 3 步解决方案（换花样/换温度/换工具） + 反差结尾（小孩抢勺子）",
  },
  scenes: [
    {
      scene_index: 1,
      timestamp_start: 0,
      timestamp_end: 4.5,
      scene: "宝宝坐在餐椅上撇头拒食，桌上一碗胡萝卜泥",
      dialogue_and_narration: "你家宝宝是不是也这样，怎么喂都不吃？",
      visual_content:
        "暖色调俯拍，宝宝餐椅特写，背景虚化的厨房，碗里橙色胡萝卜泥",
      subject: "宝宝",
      shot_type: "close_up",
      camera_movement: "static",
      first_frame_url: null,
      warnings: [],
    },
    {
      scene_index: 2,
      timestamp_start: 4.5,
      timestamp_end: 11,
      scene: "妈妈在木质砧板上切苹果块，准备替换胡萝卜泥",
      dialogue_and_narration: "试试换成苹果，颜色更亮宝宝更感兴趣",
      visual_content: "暖色俯拍砧板，红苹果块，妈妈手部动作清晰可见",
      subject: "妈妈",
      shot_type: "medium",
      camera_movement: "static",
      first_frame_url: null,
      warnings: [],
    },
    {
      scene_index: 3,
      timestamp_start: 11,
      timestamp_end: 18,
      scene: "锅中蒸苹果块，水蒸气升腾",
      dialogue_and_narration: "蒸 8 分钟，又软又香",
      visual_content: "侧拍蒸锅，蒸汽中显出红色苹果块，暖光",
      subject: null,
      shot_type: "medium",
      camera_movement: "static",
      first_frame_url: null,
      warnings: [],
    },
    {
      scene_index: 4,
      timestamp_start: 18,
      timestamp_end: 28,
      scene: "妈妈用勺子舀苹果泥喂宝宝，宝宝主动张嘴",
      dialogue_and_narration: "看，张嘴了！这一勺下去妈妈眼泪都要出来了",
      visual_content: "中景斜俯拍，妈妈手持勺子，宝宝张嘴接住，背景餐椅与厨房",
      subject: "妈妈",
      shot_type: "medium",
      camera_movement: "static",
      first_frame_url: null,
      warnings: [],
    },
    {
      scene_index: 5,
      timestamp_start: 28,
      timestamp_end: 38,
      scene: "宝宝抢过勺子自己吃，妈妈在镜头外大笑",
      dialogue_and_narration:
        "我哭了。你家宝宝几个月开始抢勺子的？评论区告诉我。",
      visual_content: "宝宝面部特写，手抓勺子，勺上残留苹果泥，光线明亮",
      subject: "宝宝",
      shot_type: "close_up",
      camera_movement: "handheld",
      first_frame_url: null,
      warnings: [],
    },
  ],
  warnings: [],
};

export function buildDefaultScript(analysis: CascadeAnalysisContract): string {
  return analysis.scenes
    .map((s) => s.dialogue_and_narration.trim())
    .filter(Boolean)
    .join("\n\n");
}
