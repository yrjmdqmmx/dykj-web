const { test, expect } = require("@playwright/test");
const { scrollScrollyTo, waitForScrolly } = require("./helpers");

test.describe("cinematic homepage", () => {
  test("stays readable without horizontal overflow at 1920 desktop", async ({ browser }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit 1920 desktop context");
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();

    await page.goto("http://127.0.0.1:4173/index.html");
    const state = await waitForScrolly(page);
    const layout = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      copyLeft: Math.round(document.querySelector(".company-copy").getBoundingClientRect().left),
      copyWidth: Math.round(document.querySelector(".company-copy").getBoundingClientRect().width)
    }));

    expect(state.variant).toBe("desktop");
    expect(layout.innerWidth).toBe(1920);
    expect(layout.scrollWidth).toBeLessThanOrEqual(1920);
    expect(layout.copyLeft).toBeLessThanOrEqual(Math.round(1920 * 0.25));
    expect(layout.copyWidth).toBeLessThanOrEqual(Math.round(1920 * 0.35));
    await expect(page.locator(".company-canvas")).toBeVisible();
    await context.close();
  });

  test("loads only the sequence matching the 1440 or 390 viewport", async ({ page }, testInfo) => {
    const frameRequests = [];
    page.on("request", (request) => {
      if (/\/assets\/scrolly\/v2\/(desktop|mobile)\/frame-/.test(request.url())) {
        frameRequests.push(request.url());
      }
    });

    await page.goto("/index.html");
    const state = await waitForScrolly(page);
    const mobile = testInfo.project.name === "mobile-chromium";
    const expectedVariant = mobile ? "mobile" : "desktop";
    const expectedViewport = mobile ? { width: 390, height: 844 } : { width: 1440, height: 900 };

    expect(page.viewportSize()).toEqual(expectedViewport);
    expect(state.variant).toBe(expectedVariant);
    expect(state.cacheLimit).toBe(mobile ? 9 : 16);
    expect(state.cacheKeys.length).toBeLessThanOrEqual(mobile ? 9 : 16);
    expect(frameRequests.length).toBeGreaterThan(0);
    expect(frameRequests.every((url) => url.includes(`/${expectedVariant}/`))).toBe(true);
    await expect(page.locator(".company-canvas")).toBeVisible();
  });

  test("maps 0 20 40 60 and 80 percent to the five acts", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one desktop run covers the progress contract");
    await page.goto("/index.html");
    await waitForScrolly(page);

    const checkpoints = [0, 0.2, 0.4, 0.6, 0.8];
    for (let index = 0; index < checkpoints.length; index += 1) {
      await scrollScrollyTo(page, checkpoints[index]);
      await expect(page.locator(`.company-act[data-act='${index + 1}']`)).toHaveClass(/is-current/);
      await expect(page.locator(`.company-progress [data-progress-act='${index + 1}']`)).toHaveClass(/is-active/);
    }
  });

  test("switches from desktop to mobile sequence without exceeding the mobile cache", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "starts from the desktop project only");
    const requested = [];
    page.on("request", (request) => {
      if (/\/assets\/scrolly\/v2\/(desktop|mobile)\/frame-/.test(request.url())) requested.push(request.url());
    });

    await page.goto("/index.html");
    await waitForScrolly(page);
    const resizeMarker = requested.length;
    await page.setViewportSize({ width: 390, height: 844 });
    await expect.poll(() => page.evaluate(() => window.__COMPANY_SCROLLY__?.variant)).toBe("mobile");
    await expect.poll(() => page.evaluate(() => window.__COMPANY_SCROLLY__?.enhanced)).toBe(true);

    const state = await page.evaluate(() => window.__COMPANY_SCROLLY__);
    expect(state.cacheLimit).toBe(9);
    expect(state.cacheKeys.length).toBeLessThanOrEqual(9);
    expect(requested.slice(resizeMarker).some((url) => url.includes("/mobile/"))).toBe(true);
  });
});
