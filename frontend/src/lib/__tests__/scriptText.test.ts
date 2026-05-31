import { describe, it, expect } from "vitest";
import { cleanTranscript, transcriptLines } from "../scriptText";

describe("cleanTranscript", () => {
  it("strips douyin watermark / promo lines, keeps real content", () => {
    const raw = [
      "《那条河，装满了夏天》",
      "那时候夏天，总是很长",
      "真甜！",
      "抖音号:89876680627",
      "抖音搜索 美好如初",
      "来抖音 发现更多创作者",
      "@美好如初",
      "",
    ].join("\n");
    const out = cleanTranscript(raw);
    expect(out).toContain("《那条河，装满了夏天》");
    expect(out).toContain("那时候夏天，总是很长");
    expect(out).toContain("真甜！");
    expect(out).not.toContain("抖音号");
    expect(out).not.toContain("抖音搜索");
    expect(out).not.toContain("发现更多");
    expect(out).not.toContain("@美好如初");
  });

  it("transcriptLines drops blanks + watermark and splits", () => {
    const lines = transcriptLines("台词一\n\n抖音号:123\n台词二\n");
    expect(lines).toEqual(["台词一", "台词二"]);
  });

  it("handles empty input", () => {
    expect(cleanTranscript("")).toBe("");
    expect(transcriptLines(null)).toEqual([]);
  });
});
