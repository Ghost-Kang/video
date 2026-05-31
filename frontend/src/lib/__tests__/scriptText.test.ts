import { describe, it, expect } from "vitest";
import { cleanTranscript, transcriptLines, transcriptItems } from "../scriptText";

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

describe("transcriptItems", () => {
  it("classifies title / reaction / meaningful lines", () => {
    const items = transcriptItems(
      ["《那条河，装满了夏天》", "那时候夏天，总是很长", "哈哈哈哈", "嗯啊", "呀我的衣服", "真甜！"].join("\n"),
    );
    expect(items[0]).toEqual({ text: "《那条河，装满了夏天》", kind: "title" });
    expect(items[1].kind).toBe("line"); // 旁白
    expect(items[2].kind).toBe("reaction"); // 纯笑声
    expect(items[3].kind).toBe("reaction"); // 语气词
    expect(items[4].kind).toBe("line"); // 呀我的衣服 → 有实义
    expect(items[5].kind).toBe("line"); // 真甜！
  });

  it("only treats a wrapped FIRST line as title", () => {
    const items = transcriptItems("先说一句\n《不是标题》");
    expect(items[0].kind).toBe("line");
    expect(items[1].kind).toBe("line");
  });
});
