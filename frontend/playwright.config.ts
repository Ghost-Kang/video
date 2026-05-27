import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config — Vite dev server on 5173 + backend on 8766(可选).
 *
 * 跑法:
 *   npm run test:e2e              # 跑全套(自动起 vite dev)
 *   npm run test:e2e:ui           # 交互 UI 调试
 *   npm run test:e2e -- --headed  # 看着浏览器跑
 *
 * 注:Vite dev server 启动较慢首次,timeout 调高;backend 需要手动起
 *     (cd backend && uv run python -m agent.server)。
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // localStorage / theme 全局状态会互相干扰,先串行
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
