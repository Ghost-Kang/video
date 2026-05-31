// 逐字稿清洗:剥掉平台水印 / 引流尾巴(抖音号、抖音搜索、来抖音发现更多、@账号、
// 长按识别…),只留原片真实台词/旁白。脚本原稿要的是内容,不是水印。
const WATERMARK_PATTERNS: RegExp[] = [
  /^抖音号[:：]/,
  /^快手号[:：]/,
  /^视频号[:：]/,
  /^抖音搜索/,
  /^快手搜索/,
  /来抖音.*发现更多/,
  /来快手.*发现更多/,
  /^@[^\s]+$/,
  /^长按.*识别/,
  /^点击.*关注/,
  /^关注.*不迷路/,
];

export function cleanTranscript(raw: string | null | undefined): string {
  return (raw ?? "")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !WATERMARK_PATTERNS.some((re) => re.test(l)))
    .join("\n");
}

export function transcriptLines(raw: string | null | undefined): string[] {
  const cleaned = cleanTranscript(raw);
  return cleaned ? cleaned.split("\n") : [];
}
