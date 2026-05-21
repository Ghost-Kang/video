import { describe, expect, it } from "vitest";
import { MOCK_BAOMAM_ANALYSIS, buildDefaultScript } from "../../fixtures/baomamFushi001";
import { buildPublishPack, getPublishTags, getPublishTitles } from "../buildPublishPack";
import { FORBIDDEN_TERMS } from "../cardCopy";

describe("buildPublishPack", () => {
  it("returns three titles and five to eight tags", () => {
    expect(getPublishTitles(MOCK_BAOMAM_ANALYSIS)).toHaveLength(3);
    const tags = getPublishTags(MOCK_BAOMAM_ANALYSIS);
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
});
