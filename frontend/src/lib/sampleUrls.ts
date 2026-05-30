import type { NicheId } from "../store/nicheStore";

// 首屏「挑一条试试」(落地页 HotCard + 聊天内「试一条 X 爆款」chip)共用的样本链接。
// 必须落在 analysis 时长闸门内(5s–180s,后端 _enforce_duration_guard),优选 15-90s 甜区。
// 2026-05-30 经 prod resolver 实测时长(见注释)。换链接前务必重测 —— 抖音视频会被删/替换,
// 旧的三条曾全部 >180s 导致首屏点任意样本即报「视频太长」(缺陷 C)。
export const SAMPLE_URL_BY_NICHE: Record<NicheId, string> = {
  // 62.6s · 「添加辅食 #宝宝辅食 #厨房小白 #只有宝妈才懂吧」自嘲钩子
  baomam_fushi: "https://www.douyin.com/video/7616954826602428411",
  // 126s · 「当妈以后才发现,最累的不是熬夜,是没人懂」情绪共鸣
  yuer_richang: "https://www.douyin.com/video/7610100974662207717",
  // 58.6s · 家庭厨房调味场景
  jiating_chufang: "https://www.douyin.com/video/7296430710208941322",
};
