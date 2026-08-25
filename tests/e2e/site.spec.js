const { test, expect } = require("@playwright/test");
const { collectBrowserErrors } = require("./helpers");

test.describe("static homepage", () => {
  test("desktop and mobile render a readable corporate hero without scrolly assets or overflow", async ({ page }) => {
    const dynamicRequests = [];
    const browserErrors = collectBrowserErrors(page);
    page.on("request", (request) => {
      if (/\/(?:assets\/scrolly|assets\/pump-seq|js\/(?:company|pump)-scrolly)/.test(request.url())) {
        dynamicRequests.push(request.url());
      }
    });

    await page.goto("/index.html");
    const hero = page.locator(".corporate-hero");
    const image = hero.locator("img[src='assets/img/hero-helium.jpg']");
    await expect(hero).toHaveCount(1);
    await expect(hero.getByRole("heading", { level: 1 })).toContainText("真空领域全方位整合服务");
    await expect(hero.locator(".corporate-actions a[href='business.html']")).toBeVisible();
    await expect(hero.locator(".corporate-actions a[href='contact.html']")).toBeVisible();
    await expect(image).toBeVisible();
    await expect(page.locator(".company-scrolly, .company-act, picture, canvas")).toHaveCount(0);

    const layout = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      heroHeight: document.querySelector(".corporate-hero").getBoundingClientRect().height,
      imageWidth: document.querySelector(".corporate-hero img").getBoundingClientRect().width,
      imageHeight: document.querySelector(".corporate-hero img").getBoundingClientRect().height,
      imageNaturalWidth: document.querySelector(".corporate-hero img").naturalWidth,
      runtime: window.__COMPANY_SCROLLY__
    }));
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth);
    expect(layout.heroHeight).toBeGreaterThan(0);
    expect(layout.imageWidth).toBeGreaterThan(0);
    expect(layout.imageHeight).toBeGreaterThan(0);
    expect(layout.imageNaturalWidth).toBeGreaterThan(0);
    expect(layout.runtime).toBeUndefined();
    expect(dynamicRequests).toEqual([]);
    expect(browserErrors).toEqual([]);
  });
});
