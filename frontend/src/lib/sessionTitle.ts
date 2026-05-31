import type { CascadeAnalysisContract } from "../types/cascade";
import { scrubUiForbidden, stripHookCode } from "./cardCopy";

// Per-session metadata derived from its analysis, persisted alongside the
// user-rename map. Lets the history sidebar show a meaningful title + context
// (platform · 相对时间) instead of an indistinguishable wall of "新会话".
export interface SessionMeta {
  title: string;
  ts: number; // epoch ms — when analyzed
  platform?: string;
}

const TITLE_MAX = 18;

/** Human-scannable session title from the analysis: prefer the video 主题,
 *  fall back to the 总览/总结. Scrubbed of hook codes + UI-forbidden terms. */
export function deriveSessionTitle(a: CascadeAnalysisContract): string {
  const clean = (s: string | undefined | null) =>
    scrubUiForbidden(stripHookCode(s ?? "")).trim();
  const candidate =
    clean(a.viral_analysis?.theme) ||
    clean(a.video_summary) ||
    clean(a.viral_analysis?.summary) ||
    clean(a.viral_analysis?.hook) ||
    "已拆解的视频";
  return candidate.length > TITLE_MAX ? `${candidate.slice(0, TITLE_MAX)}…` : candidate;
}

export function deriveSessionMeta(a: CascadeAnalysisContract): SessionMeta {
  const parsed = a.created_at ? Date.parse(a.created_at) : NaN;
  return {
    title: deriveSessionTitle(a),
    ts: Number.isNaN(parsed) ? Date.now() : parsed,
    platform: a.platform,
  };
}

export function platformLabel(platform?: string): string {
  if (platform === "douyin") return "抖音";
  if (platform === "xiaohongshu") return "小红书";
  return "视频";
}

export function relativeTime(ts: number, now = Date.now()): string {
  const s = Math.max(0, Math.floor((now - ts) / 1000));
  if (s < 60) return "刚刚";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} 分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} 小时前`;
  const d = Math.floor(h / 24);
  if (d === 1) return "昨天";
  if (d < 7) return `${d} 天前`;
  const date = new Date(ts);
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

/** The title shown for a session. User rename wins; then the auto-derived
 *  title; then the default. */
export function sessionDisplayName(
  names: Record<string, string>,
  meta: Record<string, SessionMeta>,
  id: string,
): string {
  const userName = names[id]?.trim();
  if (userName) return userName;
  return meta[id]?.title || "新会话";
}

/** The muted subtitle: 平台 · 相对时间 for analyzed sessions, a 待拆解 hint for
 *  fresh un-analyzed ones, nothing for user-renamed-but-unanalyzed. */
export function sessionSubtitle(
  names: Record<string, string>,
  meta: Record<string, SessionMeta>,
  id: string,
  now = Date.now(),
): string {
  const m = meta[id];
  if (m) return `${platformLabel(m.platform)} · ${relativeTime(m.ts, now)}`;
  if (!names[id]?.trim()) return "待拆解";
  return "";
}
