const { test, expect } = require("@playwright/test");
const {
  expectStaticScrollyFallback,
  scrollScrollyTo,
  waitForScrolly
} = require("./helpers");

test.describe("cinematic fallbacks", () => {
  test("keeps the poster visible while a slow first frame is still loading", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one deterministic weak-network run");
    await page.route("**/assets/scrolly/v2/desktop/frame-0001.webp", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1_200));
      await route.continue();
    });

    await page.goto("/index.html");
    await expect(page.locator(".company-poster img")).toBeVisible();
    await expect(page.locator(".company-canvas")).toBeHidden();
    await waitForScrolly(page);
    await expect(page.locator(".company-canvas")).toBeVisible();
    await expect(page.locator("#companyScrolly")).toHaveClass(/canvas-ready/);
  });

  test("keeps the poster and HTML when the first frame is 404", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "desktop first-frame contract");
    await page.route("**/assets/scrolly/v2/desktop/frame-0001.webp", (route) => {
      route.fulfill({ status: 404, contentType: "text/plain", body: "missing first frame" });
    });

    await page.goto("/index.html");
    await expect.poll(() => page.evaluate(() => window.__COMPANY_SCROLLY__?.failed || [])).toContain(1);
    await expectStaticScrollyFallback(page);
  });

  test("keeps the nearest rendered frame when a middle frame is 404", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "desktop missing-frame contract");
    await page.route("**/assets/scrolly/v2/desktop/frame-0048.webp", (route) => {
      route.fulfill({ status: 404, contentType: "text/plain", body: "missing middle frame" });
    });

    await page.goto("/index.html");
    await waitForScrolly(page);
    await scrollScrollyTo(page, 47 / 95);
    await expect.poll(() => page.evaluate(() => window.__COMPANY_SCROLLY__?.failed || [])).toContain(48);

    const state = await page.evaluate(() => window.__COMPANY_SCROLLY__);
    expect(state.enhanced).toBe(true);
    expect(state.drawnFrame).not.toBeNull();
    expect(state.drawnFrame).not.toBe(48);
    await expect(page.locator(".company-canvas")).toBeVisible();
    await expect(page.locator(".company-act[data-act='3']")).toHaveClass(/is-current/);
  });

  test("reduced motion avoids the manifest and presents a readable static flow", async ({ browser }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit reduced-motion context");
    const context = await browser.newContext({
      reducedMotion: "reduce",
      viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();
    let manifestRequests = 0;
    page.on("request", (request) => {
      if (request.url().endsWith("/assets/scrolly/v2/manifest.json")) manifestRequests += 1;
    });

    await page.goto("http://127.0.0.1:4173/index.html");
    await expectStaticScrollyFallback(page);
    await expect(page.locator(".company-act[data-act='5']")).toBeVisible();
    expect(manifestRequests).toBe(0);
    await context.close();
  });

  test("Save-Data avoids all sequence requests", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit Save-Data context");
    const sequenceRequests = [];
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "connection", {
        configurable: true,
        value: { saveData: true }
      });
    });
    page.on("request", (request) => {
      if (request.url().includes("/assets/scrolly/v2/")) sequenceRequests.push(request.url());
    });

    await page.goto("/index.html");
    await expectStaticScrollyFallback(page);
    expect(sequenceRequests.filter((url) => /manifest\.json|\/frame-/.test(url))).toEqual([]);
  });

  test("the no-JavaScript homepage retains the key visual text and navigation", async ({ browser }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit no-JavaScript context");
    const context = await browser.newContext({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 }
    });
    const page = await context.newPage();

    await page.goto("http://127.0.0.1:4173/index.html");
    await expectStaticScrollyFallback(page);
    await expect(page.locator(".company-actions a[href='business.html']")).toHaveAttribute("href", "business.html");
    await context.close();
  });
});
