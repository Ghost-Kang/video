import { describe, it, expect } from "vitest";
import { checkLink } from "../linkValidator";

describe("checkLink", () => {
  it("accepts full douyin video URLs, including inside share text", () => {
    expect(checkLink("https://www.douyin.com/video/7643989458156861038")).toMatchObject({
      ok: true,
      kind: "full",
    });
    expect(checkLink("https://www.iesdouyin.com/share/video/123/")).toMatchObject({ ok: true });
    expect(
      checkLink("7.65 复制打开抖音，看看【…】 https://www.douyin.com/video/123 啊"),
    ).toMatchObject({ ok: true, kind: "full" });
  });

  it("accepts v.douyin.com short links and the App share text around them", () => {
    expect(checkLink("https://v.douyin.com/iRabc123/")).toMatchObject({ ok: true, kind: "short" });
    expect(checkLink("复制打开抖音 https://v.douyin.com/iRabc/ 看看")).toMatchObject({
      ok: true,
      kind: "short",
    });
  });

  it("rejects other platforms and names them", () => {
    expect(checkLink("https://www.xiaohongshu.com/discovery/item/x")).toMatchObject({
      ok: false,
      reason: "platform",
      platform: "小红书",
    });
    expect(checkLink("https://b23.tv/xyz")).toMatchObject({ ok: false, platform: "B 站" });
  });

  it("flags empty + unknown", () => {
    expect(checkLink("")).toMatchObject({ ok: false, reason: "empty" });
    expect(checkLink("随便一段不是链接的文字")).toMatchObject({ ok: false, reason: "unknown" });
  });
});
