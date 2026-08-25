const { test, expect } = require("@playwright/test");
const { collectBrowserErrors } = require("./helpers");

async function expectReadableStaticHome(page) {
  const acts = page.locator(".company-act[data-act]");
  await expect(acts).toHaveCount(5);
  for (let index = 0; index < 5; index += 1) {
    await expect(acts.nth(index)).toBeVisible();
  }
  await expect(acts.nth(0)).toContainText("真空领域");
  await expect(acts.nth(4)).toContainText("可靠交付");
  await expect(page.locator("#companyScrolly .company-stage, #companyScrolly picture, #companyScrolly canvas")).toHaveCount(0);
  const layout = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth);
}

test.describe("static homepage fallbacks", () => {

  test("reduced motion avoids the manifest and presents a readable static flow", async ({ browser }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit reduced-motion context");
    const context = await browser.newContext({
      reducedMotion: "reduce",
      viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();
    const dynamicRequests = [];
    const browserErrors = collectBrowserErrors(page);
    page.on("request", (request) => {
      if (request.url().includes("/assets/scrolly/v2/")) dynamicRequests.push(request.url());
    });

    await page.goto("http://127.0.0.1:4173/index.html");
    await expectReadableStaticHome(page);
    expect(dynamicRequests).toEqual([]);
    expect(browserErrors).toEqual([]);
    await context.close();
  });

  test("Save-Data avoids all sequence requests", async ({ page }, testInfo) => {
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
      if (request.url().includes("/assets/scrolly/v2/")) dynamicRequests.push(request.url());
    });

    await page.goto("/index.html");
    await expectReadableStaticHome(page);
    expect(dynamicRequests).toEqual([]);
    expect(browserErrors).toEqual([]);
  });

  test("the no-JavaScript homepage retains the key visual text and navigation", async ({ browser }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one explicit no-JavaScript context");
    const context = await browser.newContext({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 }
    });
    const page = await context.newPage();
    const dynamicRequests = [];
    page.on("request", (request) => {
      if (request.url().includes("/assets/scrolly/v2/")) dynamicRequests.push(request.url());
    });

    await page.goto("http://127.0.0.1:4173/index.html");
    await expectReadableStaticHome(page);
    await expect(page.locator(".company-actions a[href='business.html']")).toHaveAttribute("href", "business.html");
    expect(dynamicRequests).toEqual([]);
    await context.close();
  });
});
