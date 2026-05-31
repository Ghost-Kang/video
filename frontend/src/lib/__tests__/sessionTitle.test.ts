import { describe, it, expect } from "vitest";
import {
  deriveSessionTitle,
  deriveSessionMeta,
  relativeTime,
  sessionDisplayName,
  sessionSubtitle,
  type SessionMeta,
} from "../sessionTitle";
import type { CascadeAnalysisContract } from "../../types/cascade";

function mk(partial: Record<string, unknown>): CascadeAnalysisContract {
  return {
    viral_analysis: {},
    video_summary: "",
    platform: "douyin",
    created_at: "",
    ...partial,
  } as unknown as CascadeAnalysisContract;
}

describe("deriveSessionTitle", () => {
  it("prefers the video theme", () => {
    expect(deriveSessionTitle(mk({ viral_analysis: { theme: "童年怀旧动画" } }))).toBe(
      "童年怀旧动画",
    );
  });

  it("falls back to video_summary, then a default", () => {
    expect(deriveSessionTitle(mk({ video_summary: "一条治愈系乡村动画" }))).toBe(
      "一条治愈系乡村动画",
    );
    expect(deriveSessionTitle(mk({}))).toBe("已拆解的视频");
  });

  it("truncates overly long titles", () => {
    const long = "一二三四五六七八九十一二三四五六七八九十廿";
    expect(deriveSessionTitle(mk({ viral_analysis: { theme: long } }))).toHaveLength(19); // 18 + …
    expect(deriveSessionTitle(mk({ viral_analysis: { theme: long } })).endsWith("…")).toBe(true);
  });

  it("scrubs UI-forbidden terms", () => {
    const t = deriveSessionTitle(mk({ viral_analysis: { theme: "智能工具测评" } }));
    expect(t).not.toContain("工具");
    expect(t).not.toContain("智能");
  });
});

describe("deriveSessionMeta", () => {
  it("carries title + platform + parsed timestamp", () => {
    const m = deriveSessionMeta(
      mk({
        viral_analysis: { theme: "家常菜教程" },
        platform: "xiaohongshu",
        created_at: "2026-05-31T00:00:00Z",
      }),
    );
    expect(m.title).toBe("家常菜教程");
    expect(m.platform).toBe("xiaohongshu");
    expect(m.ts).toBe(Date.parse("2026-05-31T00:00:00Z"));
  });
});

describe("relativeTime", () => {
  const now = 1_000_000_000_000;
  it("buckets durations into Chinese labels", () => {
    expect(relativeTime(now, now)).toBe("刚刚");
    expect(relativeTime(now - 5 * 60_000, now)).toBe("5 分钟前");
    expect(relativeTime(now - 3 * 3_600_000, now)).toBe("3 小时前");
    expect(relativeTime(now - 25 * 3_600_000, now)).toBe("昨天");
    expect(relativeTime(now - 3 * 86_400_000, now)).toBe("3 天前");
  });
});

describe("sessionDisplayName / sessionSubtitle", () => {
  const meta: Record<string, SessionMeta> = {
    t1: { title: "童年怀旧动画", ts: 1000, platform: "douyin" },
  };

  it("prefers a user rename over the auto title, else default", () => {
    expect(sessionDisplayName({ t1: "我的会话" }, meta, "t1")).toBe("我的会话");
    expect(sessionDisplayName({}, meta, "t1")).toBe("童年怀旧动画");
    expect(sessionDisplayName({}, {}, "t2")).toBe("新会话");
  });

  it("subtitle: platform·time when analyzed, 待拆解 for fresh, empty when user-named-unanalyzed", () => {
    expect(sessionSubtitle({}, meta, "t1", 1000)).toContain("抖音");
    expect(sessionSubtitle({}, {}, "t2")).toBe("待拆解");
    expect(sessionSubtitle({ t3: "named" }, {}, "t3")).toBe("");
  });
});
