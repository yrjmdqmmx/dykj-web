const { test, expect } = require("@playwright/test");
const { collectBrowserErrors } = require("./helpers");

test.describe("static homepage", () => {
  test("desktop and mobile render five readable acts without dynamic assets or overflow", async ({ page }) => {
    const dynamicRequests = [];
    const browserErrors = collectBrowserErrors(page);
    page.on("request", (request) => {
      if (request.url().includes("/assets/scrolly/v2/")) dynamicRequests.push(request.url());
    });

    await page.goto("/index.html");
    const acts = page.locator(".company-act[data-act]");
    await expect(acts).toHaveCount(5);
    for (let index = 0; index < 5; index += 1) {
      await expect(acts.nth(index)).toBeVisible();
    }
    await expect(acts.nth(0)).toContainText("真空领域");
    await expect(acts.nth(4)).toContainText("可靠交付");
    await expect(page.locator("#companyScrolly .company-stage")).toHaveCount(0);
    await expect(page.locator("#companyScrolly picture")).toHaveCount(0);
    await expect(page.locator("#companyScrolly canvas")).toHaveCount(0);

    const layout = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      runtime: window.__COMPANY_SCROLLY__
    }));
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth);
    expect(layout.runtime).toBeUndefined();
    expect(dynamicRequests).toEqual([]);
    expect(browserErrors).toEqual([]);
  });
});
