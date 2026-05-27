import { test, expect } from "@playwright/test";

/**
 * W4D2 续集 smoke — 覆盖 chat route gate、legal、anchor analytics、redirect、theme 跨页持久化。
 *
 * 故意不测的(留给 Layer B / 手动):
 *   - chat 内消息发送的完整 round-trip(依赖 backend WS @ 8765,放到 integration)
 *   - markdown 渲染细节
 *   - 直方图视觉对齐
 *
 * mock 策略:/api/anchors 用 page.route 兜底返回小数据集,避免依赖后端。
 *           WS 连不上没关系 — useWebSocket 后台重连不阻塞 UI 渲染,smoke 在 1-2s 内完成。
 */

const CONSENT_KEY = "openrhtv_consent_v0";
const THEME_KEY = "cascade_theme";
const USER_KEY = "rhtv_user";
const CONSENT_VAL = JSON.stringify({ version: "v0", acceptedAt: "2026-05-26T00:00:00.000Z" });
const TEST_USER = "e2e_smoke_user";

test.beforeEach(async ({ page }) => {
  // 只在每个 test 第一次 nav 时清 localStorage —— 否则跨页测试里第二次 goto 也会清掉
  // toggle 之前刚写入的状态。sessionStorage 在同一 page 内跨 nav 保留,适合做 once-flag。
  await page.addInitScript(() => {
    try {
      if (!sessionStorage.getItem("__e2e_storage_cleared")) {
        window.localStorage.clear();
        sessionStorage.setItem("__e2e_storage_cleared", "1");
      }
    } catch {
      /* private mode */
    }
  });
});

async function seedAuth(page: import("@playwright/test").Page) {
  await page.addInitScript(
    ([ck, cv, uk, uv]) => {
      window.localStorage.setItem(ck, cv);
      window.localStorage.setItem(uk, uv);
    },
    [CONSENT_KEY, CONSENT_VAL, USER_KEY, TEST_USER] as const,
  );
}

test("Legal user-agreement 页加载 + 标题 + 返回首页链接", async ({ page }) => {
  await page.goto("/legal/user-agreement");

  await expect(page.getByRole("heading", { level: 1, name: "用户协议" })).toBeVisible();
  await expect(page.getByText("Terms · v0")).toBeVisible();

  const backLink = page.getByRole("link", { name: /回到首页/ });
  await expect(backLink).toBeVisible();
  await expect(backLink).toHaveAttribute("href", "/");

  // markdown 正文需要 fetch /legal/user_agreement_v0.md(Vite dev 会从 public 服)
  await expect(page.getByText(/OpenRHTV 用户协议/)).toBeVisible({ timeout: 5_000 });
});

test("Legal privacy 页加载 + 正文渲染", async ({ page }) => {
  await page.goto("/legal/privacy");

  await expect(page.getByRole("heading", { level: 1, name: "隐私政策", exact: true })).toBeVisible();
  await expect(page.getByText("Privacy · v0")).toBeVisible();
  await expect(page.getByText(/OpenRHTV 隐私政策/)).toBeVisible({ timeout: 5_000 });
});

test("未知路由 → fallback navigate 到 /", async ({ page }) => {
  await page.goto("/some-page-that-does-not-exist");
  // catch-all <Navigate to="/" replace />
  await expect.poll(() => new URL(page.url()).pathname).toBe("/");
  await expect(page.getByText("粘一条爆款")).toBeVisible();
});

test("/chat/:threadId 未登录 → /login", async ({ page }) => {
  // 不种 rhtv_user,直接进 /chat/foo
  await page.goto("/chat/session-abc");
  await expect.poll(() => new URL(page.url()).pathname).toBe("/login");
  await expect(page.getByPlaceholder("输入工号")).toBeVisible();
});

test("/chat/:threadId 已登录 → ChatPanel 骨架渲染", async ({ page }) => {
  await seedAuth(page);
  // useAnchorAnalytics 走 /api/anchors,backend 没起会 hang — 给个 404 兜底
  await page.route("**/api/anchors**", (route) => route.fulfill({ status: 200, body: "[]" }));
  // WS 连不上没关系,UI 仍渲染

  await page.goto("/chat/session-smoke-1");

  // ChatPanel 标题 "问导演"
  await expect(page.getByText("问导演")).toBeVisible({ timeout: 8_000 });
  // 三个 quick action 按钮 + 发送按钮 + 输入框 placeholder
  await expect(page.getByRole("button", { name: "继续下一步" })).toBeVisible();
  await expect(page.getByRole("button", { name: "开头再抓" })).toBeVisible();
  await expect(page.getByRole("button", { name: "更口语" })).toBeVisible();
  await expect(page.getByPlaceholder("想改哪里,直接说")).toBeVisible();
  await expect(page.getByRole("button", { name: "发送", exact: true })).toBeVisible();
});

test("AnchorAnalytics 用 mock 数据渲染看板", async ({ page }) => {
  const mock = (kind: "character" | "scene") => [
    {
      id: `${kind}-1`,
      kind,
      label: kind === "character" ? "小明" : "客厅",
      reuse_count: kind === "character" ? 4 : 2,
      created_at: "2026-05-20T00:00:00.000Z",
    },
    {
      id: `${kind}-2`,
      kind,
      label: kind === "character" ? "小红" : "厨房",
      reuse_count: 1,
      created_at: "2026-05-22T00:00:00.000Z",
    },
  ];

  await page.route("**/api/anchors**", (route) => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get("kind") as "character" | "scene" | null;
    const body = kind ? mock(kind) : [];
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await page.goto("/analytics/anchors");

  await expect(page.getByRole("heading", { level: 1, name: "你的素材复用看板" })).toBeVisible();
  // mock 出来的角色 label
  await expect(page.getByText("小明")).toBeVisible({ timeout: 5_000 });
  await expect(page.getByRole("heading", { name: "复用次数 Top 5" })).toBeVisible();
});

test("Dark mode 跨页持久化 (/ → /legal/privacy)", async ({ page }) => {
  // 首跑只在 storage 还空时写 light(避免每次 nav 都覆盖 toggle 写入的 dark)
  await page.addInitScript(
    ([k, v]) => {
      if (window.localStorage.getItem(k) === null) {
        window.localStorage.setItem(k, v);
      }
    },
    [THEME_KEY, "light"] as const,
  );
  await page.goto("/");

  const toggle = page
    .locator('button[aria-label*="深色"], button[aria-label*="dark" i], button[aria-label*="主题"]')
    .first();
  await toggle.click();
  await expect(page.locator("html")).toHaveClass(/dark/);

  // 导航到 legal 页 — html.dark class + localStorage 应保留
  await page.goto("/legal/privacy");
  await expect(page.locator("html")).toHaveClass(/dark/);
  const stored = await page.evaluate((k) => localStorage.getItem(k), THEME_KEY);
  expect(stored).toBe("dark");
});
