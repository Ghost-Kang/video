// 前端链接预判 —— 在「拆解」前认一认用户粘的是什么,给即时反馈/引导。
// 后端能解析:抖音完整视频 URL(www.douyin.com/video/<id> / iesdouyin/share/video)
// + v.douyin.com 短链(已支持跟随 302)+ 整段分享文案(里面含上述任一)。
// 其它平台 / 没认出 → 拦截 + 引导,不要把垃圾甩给后端。

const DOUYIN_FULL = /(?:www\.douyin\.com\/video\/|iesdouyin\.com\/share\/video\/)\d+/i;
const DOUYIN_SHORT = /v\.douyin\.com\/[A-Za-z0-9_-]+/i;

const OTHER_PLATFORMS: { re: RegExp; name: string }[] = [
  { re: /xiaohongshu\.com|xhslink\.com/i, name: "小红书" },
  { re: /kuaishou\.com|kwai|chenzhongtech/i, name: "快手" },
  { re: /bilibili\.com|b23\.tv/i, name: "B 站" },
  { re: /youtube\.com|youtu\.be/i, name: "YouTube" },
  { re: /v\.qq\.com|weibo\.com|weishi/i, name: "其它平台" },
];

export type LinkCheck =
  | { ok: true; kind: "full" | "short" }
  | { ok: false; reason: "platform"; platform: string }
  | { ok: false; reason: "empty" }
  | { ok: false; reason: "unknown" };

export function checkLink(raw: string): LinkCheck {
  const t = (raw ?? "").trim();
  if (!t) return { ok: false, reason: "empty" };
  if (DOUYIN_FULL.test(t)) return { ok: true, kind: "full" };
  if (DOUYIN_SHORT.test(t)) return { ok: true, kind: "short" };
  for (const p of OTHER_PLATFORMS) {
    if (p.re.test(t)) return { ok: false, reason: "platform", platform: p.name };
  }
  return { ok: false, reason: "unknown" };
}
