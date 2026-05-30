import { describe, expect, it } from "vitest";
import { MOCK_BAOMAM_ANALYSIS, buildDefaultScript } from "../../fixtures/baomamFushi001";
import { buildPublishPack, getPublishTags, getPublishTitles } from "../buildPublishPack";
import type { RewriteShot } from "../cascadeMapper";
import { FORBIDDEN_TERMS } from "../cardCopy";

describe("buildPublishPack", () => {
  it("returns three titles and five to eight tags", () => {
    expect(getPublishTitles(MOCK_BAOMAM_ANALYSIS)).toHaveLength(3);
    const tags = getPublishTags("baomam_fushi");
    expect(tags.length).toBeGreaterThanOrEqual(5);
    expect(tags.length).toBeLessThanOrEqual(8);
  });

  it("includes image urls in order and stays small", () => {
    const payload = buildPublishPack(buildDefaultScript(MOCK_BAOMAM_ANALYSIS), MOCK_BAOMAM_ANALYSIS, ["https://a", "https://b"]);
    expect(payload.indexOf("镜头 1: https://a")).toBeLessThan(payload.indexOf("镜头 2: https://b"));
    expect(payload.length).toBeLessThan(4096);
  });

  it("does not include forbidden terms before trailer", () => {
    const payload = buildPublishPack(buildDefaultScript(MOCK_BAOMAM_ANALYSIS), MOCK_BAOMAM_ANALYSIS);
    const [body] = payload.split("—— 用 Cascade 做的");
    for (const term of FORBIDDEN_TERMS) {
      expect(body).not.toMatch(new RegExp(term, "i"));
    }
  });

  // ── 缺陷 E 回归(2026-05-30 founder 实测):发布包别泄漏源片标签/受众 ───────

  it("tags follow the selected niche, not the source", () => {
    expect(getPublishTags("jiating_chufang")).toContain("#家庭厨房");
    expect(getPublishTags("yuer_richang")).toContain("#育儿日常");
    // 未选方向时给安全默认(辅食),不报错。
    expect(getPublishTags(null).length).toBeGreaterThanOrEqual(5);
  });

  it("never leaks source target_audience into tags", () => {
    // MOCK 源片受众含「普通家庭厨房环境」之类;改写成育儿后,标签里不该出现源片受众词。
    const tags = getPublishTags("yuer_richang");
    expect(tags.join(" ")).not.toMatch(/厨房环境|普通家庭/);
  });

  it("strips internal hook taxonomy codes (Hxx) from titles", () => {
    const leaky = {
      ...MOCK_BAOMAM_ANALYSIS,
      viral_analysis: {
        ...MOCK_BAOMAM_ANALYSIS.viral_analysis,
        hook: "H4 发现孩子落水的危机场景",
        climax: "H6 夏天+童年欢笑",
      },
    };
    const titles = getPublishTitles(leaky);
    for (const t of titles) {
      expect(t).not.toMatch(/^H\d/);
    }
  });

  it("prefers the rewritten script's voice over the source hook", () => {
    const shots: RewriteShot[] = [
      { shot_index: 1, dialogue: "哎呀今天小安又闹脾气了，蒸的胡萝卜泥碰都不碰", visual: "" },
      { shot_index: 2, dialogue: "换个颜色试试，南瓜泥总该吃了吧", visual: "" },
    ];
    const titles = getPublishTitles(MOCK_BAOMAM_ANALYSIS, shots, "baomam_fushi");
    expect(titles[0]).toBe("哎呀今天小安又闹脾气了");
    // 第二条来自另一镜,不是源片 hook。
    expect(titles[1]).toBe("换个颜色试试");
  });
});
