import { describe, expect, it } from "vitest";
import { MOCK_BAOMAM_ANALYSIS, buildDefaultScript } from "../../fixtures/baomamFushi001";
import { buildCanvasPublishPack, buildPublishPack, getPublishTags, getPublishTitles } from "../buildPublishPack";
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

  it("keeps correct 镜头 numbers when a middle shot has no draft image (no renumber)", () => {
    // 镜头 2 缺草稿图 → 镜头 3 仍标「镜头 3」,不被错位重编成「镜头 2」(发布收尾 P2 修复)。
    const payload = buildPublishPack(buildDefaultScript(MOCK_BAOMAM_ANALYSIS), MOCK_BAOMAM_ANALYSIS, ["https://a", "", "https://c"]);
    expect(payload).toContain("镜头 1: https://a");
    expect(payload).toContain("镜头 3: https://c");
    expect(payload).not.toContain("镜头 2: https://c"); // 不被错位重编号
    expect(payload).not.toContain("镜头 2:"); // 镜头 2 无图 → 整条跳过
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

  it("strips internal hook taxonomy codes (Hxx, incl. +H8) from titles", () => {
    const leaky = {
      ...MOCK_BAOMAM_ANALYSIS,
      viral_analysis: {
        ...MOCK_BAOMAM_ANALYSIS.viral_analysis,
        hook: "+H8 家庭温情+情绪共鸣", // 模型实测带前导「+」的变体
        climax: "H6 夏天+童年欢笑",
      },
    };
    const titles = getPublishTitles(leaky);
    for (const t of titles) {
      expect(t).not.toMatch(/^[+＋]?H\d/);
    }
    // 「+H8 」前缀剥掉,正文保留。
    expect(titles[0]).toMatch(/^家庭温情/);
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

  // ── P2 去 niche 化(2026-06-01):任意视频不再套辅食标签 ──────────────

  it("derives tags from analysis theme when niche is unknown (no baomam default)", () => {
    const petAnalysis = {
      ...MOCK_BAOMAM_ANALYSIS,
      viral_analysis: { ...MOCK_BAOMAM_ANALYSIS.viral_analysis, theme: "趣味动物观察" },
    };
    // niche=null + 有 theme → 标签来自 theme,绝不出现辅食/宝妈
    const tags = getPublishTags(null, petAnalysis);
    expect(tags.length).toBeGreaterThanOrEqual(5);
    expect(tags.join(" ")).toContain("#趣味动物观察");
    expect(tags.join(" ")).not.toMatch(/辅食|宝妈|宝宝/);
  });

  it("generic niche → generic tagline, never the hardcoded niche tagline", () => {
    // 无改写 + 无源 hook/climax → 第 3 条(tagline)应是通用句,不是辅食专属句。
    const blankAnalysis = {
      ...MOCK_BAOMAM_ANALYSIS,
      viral_analysis: { ...MOCK_BAOMAM_ANALYSIS.viral_analysis, hook: "", climax: "", theme: "" },
    };
    const titles = getPublishTitles(blankAnalysis, [], "generic");
    // 旧实现 niche=generic 不在表里 → niceNiche 默认 baomam → 塞「新手妈妈也能照着做」
    expect(titles).not.toContain("新手妈妈也能照着做");
    expect(titles).toContain("照着这条思路拍你自己的"); // 通用 tagline
  });

  it("scrubs forbidden terms from the rewritten script before clipboard (P2 hole)", () => {
    // 改写稿里混进禁词 → 复制前必须被 scrub 掉(之前只 stripHookCode 不 scrub)
    const dirtyScript = "用这个神器三步搞定，营养师都推荐";
    const payload = buildPublishPack(dirtyScript, MOCK_BAOMAM_ANALYSIS);
    const [body] = payload.split("—— 用 Cascade 做的");
    for (const term of FORBIDDEN_TERMS) {
      expect(body).not.toMatch(new RegExp(term, "i"));
    }
  });

  it("degrades gracefully when no shot images (no broken 待补充 link)", () => {
    const payload = buildPublishPack(buildDefaultScript(MOCK_BAOMAM_ANALYSIS), MOCK_BAOMAM_ANALYSIS, []);
    expect(payload).not.toContain("镜头 1: 待补充");
    expect(payload).toContain("草稿图生成后自动填入");
  });
});

// ── H1(审计 2026-06-06):画布原生发布包 —— Pro 画布闭环最后一公里 ──────────────
describe("buildCanvasPublishPack", () => {
  it("assembles titles from the script when no structured analysis is on the canvas", () => {
    const pack = buildCanvasPublishPack({
      scriptText: "今天教你三步搞定免烤提拉米苏\n## 分镜表\n1 | 中景 | 摆盘",
      shotImageUrls: ["https://img/1.png", "https://img/2.png"],
      filmUrl: "https://media/film.mp4",
    });
    expect(pack).toContain("【标题候选】");
    expect(pack).toContain("今天教你三步搞定免烤提拉米苏");
    // 镜头图按序、成片就位
    expect(pack.indexOf("镜头 1: https://img/1.png")).toBeLessThan(pack.indexOf("镜头 2: https://img/2.png"));
    expect(pack).toContain("https://media/film.mp4");
    // 标题不混进分镜表格行(| 开头)
    expect(pack).not.toContain("1. 1 | 中景");
  });

  it("scrubs forbidden terms from the script before clipboard", () => {
    const pack = buildCanvasPublishPack({
      scriptText: "用这个神器三步搞定，营养师都推荐",
      shotImageUrls: [],
      filmUrl: "https://media/film.mp4",
    });
    const [body] = pack.split("—— 用 Cascade 做的");
    for (const term of FORBIDDEN_TERMS) {
      expect(body).not.toMatch(new RegExp(term, "i"));
    }
  });

  it("prefers structured analysis titles/tags when present (analysis→canvas path)", () => {
    const pack = buildCanvasPublishPack({
      scriptText: "占位脚本",
      shotImageUrls: [],
      analysis: MOCK_BAOMAM_ANALYSIS,
      niche: "baomam_fushi",
    });
    expect(pack).toContain("#辅食");
  });

  it("shows placeholders when film/images not ready yet (no broken links)", () => {
    const pack = buildCanvasPublishPack({ scriptText: "脚本", shotImageUrls: [] });
    expect(pack).toContain("草稿图生成后自动填入");
    expect(pack).toContain("合成整片后自动填入");
  });
});
