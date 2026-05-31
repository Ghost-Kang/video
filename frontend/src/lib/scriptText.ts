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

export type TranscriptKind = "title" | "reaction" | "line";
export interface TranscriptItem {
  text: string;
  kind: TranscriptKind;
}

// 片头标题卡:《…》/「…」/【…】整行包裹(屏幕标题,非口播)
const TITLE_RE = /^[《「【(].+[》」】)]$/;
// 纯笑声 / 语气词(哈哈哈、嗯啊、哦…)—— 逐字稿里真实存在但非「重点内容」,弱化
const REACTION_RE = /^[哈呵嘿嘻啊嗯哦噢哎唉呀哇咦\s]+[！!。.,，、…~～\s]*$/;

// 分类逐字稿每句,供 UI 凸显重点(片头标题/有意义台词)、弱化语气词。
export function transcriptItems(raw: string | null | undefined): TranscriptItem[] {
  return transcriptLines(raw).map((text, i) => {
    if (i === 0 && TITLE_RE.test(text)) return { text, kind: "title" as const };
    if (REACTION_RE.test(text)) return { text, kind: "reaction" as const };
    return { text, kind: "line" as const };
  });
}
