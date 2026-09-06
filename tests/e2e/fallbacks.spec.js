const { test, expect } = require("@playwright/test");
const { collectBrowserErrors } = require("./helpers");

async function expectReadableCorporateHome(page) {
  const hero = page.locator(".corporate-hero");
  await expect(hero).toHaveCount(1);
  await expect(hero).toBeVisible();
  await expect(hero.getByRole("heading", { level: 1 })).toContainText("真空领域全方位整合服务");
  await expect(hero.locator("img[src='assets/img/hero-helium.jpg']")).toBeVisible();
  await expect(page.locator(".company-scrolly, .company-act, picture, canvas")).toHaveCount(0);
  const layout = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth);
}

test.describe("static homepage fallbacks", () => {

  test("reduced motion keeps the corporate hero static and readable", async ({ browser, baseURL }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit reduced-motion context");
    const context = await browser.newContext({
      baseURL,
      reducedMotion: "reduce",
      viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();
    const dynamicRequests = [];
    const browserErrors = collectBrowserErrors(page);
    page.on("request", (request) => {
      if (request.url().includes("/assets/scrolly/") || request.url().includes("company-scrolly")) dynamicRequests.push(request.url());
    });

    await page.goto("/index.html");
    await expectReadableCorporateHome(page);
    expect(dynamicRequests).toEqual([]);
    expect(browserErrors).toEqual([]);
    await context.close();
  });

  test("Save-Data keeps the corporate hero free of sequence requests", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit Save-Data context");
    const dynamicRequests = [];
    const browserErrors = collectBrowserErrors(page);
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "connection", {
        configurable: true,
        value: { saveData: true }
      });
    });
    page.on("request", (request) => {
      if (request.url().includes("/assets/scrolly/") || request.url().includes("company-scrolly")) dynamicRequests.push(request.url());
    });

    await page.goto("/index.html");
    await expectReadableCorporateHome(page);
    expect(dynamicRequests).toEqual([]);
    expect(browserErrors).toEqual([]);
  });

  test("the no-JavaScript homepage retains the key visual text and navigation", async ({ browser, baseURL }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit no-JavaScript context");
    const context = await browser.newContext({
      baseURL,
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 }
    });
    const page = await context.newPage();
    const dynamicRequests = [];
    page.on("request", (request) => {
      if (request.url().includes("/assets/scrolly/") || request.url().includes("company-scrolly")) dynamicRequests.push(request.url());
    });

    await page.goto("/index.html");
    await expectReadableCorporateHome(page);
    await expect(page.locator(".corporate-actions a[href='business.html']")).toHaveAttribute("href", "business.html");
    expect(dynamicRequests).toEqual([]);
    await context.close();
  });
});
