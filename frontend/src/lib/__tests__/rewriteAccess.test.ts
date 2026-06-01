import { afterEach, describe, expect, it, vi } from "vitest";
import { resolveRewriteEnabled } from "../rewriteAccess";

describe("resolveRewriteEnabled", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("默认关闭:无 cohort flag、无 env → false(灰度未开,行为同硬常量)", () => {
    expect(resolveRewriteEnabled()).toBe(false);
  });

  it("VITE_REWRITE_ENABLED='true' → 开启", () => {
    vi.stubEnv("VITE_REWRITE_ENABLED", "true");
    expect(resolveRewriteEnabled()).toBe(true);
  });

  it("VITE_REWRITE_ENABLED 非 'true' 字面量一律视为关闭", () => {
    for (const v of ["false", "1", "0", "TRUE", "yes", ""]) {
      vi.stubEnv("VITE_REWRITE_ENABLED", v);
      expect(resolveRewriteEnabled()).toBe(false);
    }
  });

  it("后端 cohort flag=true 覆盖 env=false(per-cohort 优先)", () => {
    vi.stubEnv("VITE_REWRITE_ENABLED", "false");
    expect(resolveRewriteEnabled(true)).toBe(true);
  });

  it("后端 cohort flag=false 覆盖 env=true(显式关闭优先,不下探)", () => {
    vi.stubEnv("VITE_REWRITE_ENABLED", "true");
    expect(resolveRewriteEnabled(false)).toBe(false);
  });

  it("cohort flag=undefined 时下探到 env(后端未下发的当前状态)", () => {
    vi.stubEnv("VITE_REWRITE_ENABLED", "true");
    expect(resolveRewriteEnabled(undefined)).toBe(true);
  });
});
