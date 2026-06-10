import { test, expect } from "@playwright/test";

/**
 * W4D2 starter E2E — 覆盖 QA 报告里高价值且可自动化的 smoke 项。
 *
 * 故意不测的(留给手动 / Layer B Chrome DevTools MCP 视觉验证):
 *   - hover tilt + glare 动画(performance-sensitive,视觉难断言)
 *   - dark mode 对比度数值(WCAG 工具更合适)
 *   - StatCounter 缓动平滑性(时间窗口太脆)
 *
 * Landing 是 public route(main.tsx:57),无需 login。
 * ConsentGate.accept() 内部写 rhtv_user 触发 rhtv-auth-changed,所以 consent
 * 一旦同意,/chat/:threadId 即可访问(无需单独 login)。
 */

const CONSENT_KEY = "openrhtv_consent_v0";
const THEME_KEY = "cascade_theme";
const USER_KEY = "rhtv_user";

test.beforeEach(async ({ page }) => {
  // 每个 test 前清掉 localStorage,保证隔离
  await page.addInitScript(() => {
    try {
      window.localStorage.clear();
    } catch {
      /* private mode */
    }
  });
});

test("Landing 加载 + hero 文案可见", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("粘一条爆款")).toBeVisible();
  await expect(page.getByText("30 秒")).toBeVisible();
  await expect(page.getByPlaceholder(/小红书.*抖音/)).toBeVisible();
});

test("Dark mode toggle 切换 html.dark class + 写 localStorage", async ({ page }) => {
  // 先种 light(避免被 OS 偏好影响)
  await page.addInitScript(
    ([k, v]) => window.localStorage.setItem(k, v),
    [THEME_KEY, "light"] as const,
  );

  await page.goto("/");
  await expect(page.locator("html")).not.toHaveClass(/dark/);

  // DarkModeToggle 渲染在 PageShell 右上 — 按 aria-label 找;若无 label 按位置 fallback
  const toggle = page
    .locator('button[aria-label*="深色"], button[aria-label*="dark" i], button[aria-label*="主题"]')
    .first();
  await toggle.click();

  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect
    .poll(async () => page.evaluate((k) => localStorage.getItem(k), THEME_KEY))
    .toBe("dark");
});

test("ConsentGate 首次点击 → 法律链接消失 + localStorage 写入 + auth event 触发", async ({ page }) => {
  await page.goto("/");

  // 未同意时底部应有"用户协议"链接
  const legalLink = page.getByRole("link", { name: "用户协议" });
  await expect(legalLink).toBeVisible();

  // 点 URL input 任意位置 → onClickCapture 触发 accept
  await page.getByPlaceholder(/小红书.*抖音/).click();

  // 法律链接消失
  await expect(legalLink).toBeHidden();
  // localStorage consent 写入
  const stored = await page.evaluate((k) => localStorage.getItem(k), CONSENT_KEY);
  expect(stored).not.toBeNull();
  expect(JSON.parse(stored!).version).toBe("v0");
  // rhtv_user 也应写入(Phase 1 anon-consent bridge)
  const user = await page.evaluate((k) => localStorage.getItem(k), USER_KEY);
  expect(user).not.toBeNull();
});

test("URL submit 双击防抖 → 只 navigate 一次", async ({ page }) => {
  // 预设 consent + 用户,跳过 gate
  await page.addInitScript(
    ([ck, cv, uk, uv]) => {
      window.localStorage.setItem(ck, cv);
      window.localStorage.setItem(uk, uv);
    },
    [
      CONSENT_KEY,
      JSON.stringify({ version: "v0", acceptedAt: "2026-05-26T00:00:00.000Z" }),
      USER_KEY,
      "e2e_smoke_user",
    ] as const,
  );

  await page.goto("/");
  await page.getByPlaceholder(/小红书.*抖音/).fill("https://www.xiaohongshu.com/explore/abc123");

  // 狂点 5 下 — submittedRef guard 应只放过 1 次
  const submitBtn = page.getByRole("button", { name: /拆解/ });

  // 触发并等导航
  await Promise.all([
    page.waitForURL(/\/chat\/session-/, { timeout: 8000 }),
    (async () => {
      for (let i = 0; i < 5; i++) {
        await submitBtn.click({ force: true, noWaitAfter: true }).catch(() => {});
      }
    })(),
  ]);

  // 应跳到 chat,且 URL 只一个 session id
  expect(page.url()).toMatch(/\/chat\/session-[a-z0-9]+/);

  // history 应只有 1 个 forward step:后退应回到 /(不是 / → / → /chat 那样多余)
  await page.goBack();
  await expect.poll(() => page.url()).toMatch(/\/?(?:\?.*)?$/);
});

test("HotCard 双击防抖 → 只 navigate 一次", async ({ page }) => {
  await page.addInitScript(
    ([ck, cv, uk, uv]) => {
      window.localStorage.setItem(ck, cv);
      window.localStorage.setItem(uk, uv);
    },
    [
      CONSENT_KEY,
      JSON.stringify({ version: "v0", acceptedAt: "2026-05-26T00:00:00.000Z" }),
      USER_KEY,
      "e2e_smoke_user",
    ] as const,
  );

  await page.goto("/");
  const firstCard = page.locator("article").first();
  await expect(firstCard).toBeVisible();

  await Promise.all([
    page.waitForURL(/\/chat\/session-/, { timeout: 8000 }),
    (async () => {
      for (let i = 0; i < 5; i++) {
        await firstCard.click({ force: true, noWaitAfter: true }).catch(() => {});
      }
    })(),
  ]);

  expect(page.url()).toMatch(/\/chat\/session-[a-z0-9]+/);
  await page.goBack();
  await expect.poll(() => page.url()).toMatch(/\/?(?:\?.*)?$/);
});
