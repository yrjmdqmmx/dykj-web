const { readFileSync, statSync } = require("node:fs");
const { extname, resolve } = require("node:path");
const { test, expect } = require("@playwright/test");
const { collectBrowserErrors } = require("./helpers");

const siteRoot = resolve(__dirname, "../../_site");
const publicPages = [
  "/index.html",
  "/about.html",
  "/business.html",
  "/brands.html",
  "/cases.html",
  "/contact.html",
  "/404.html"
];

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp"
};

async function mockAmapSuccess(page) {
  await page.route("https://webapi.amap.com/maps?**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `window.AMap = {
        Pixel: function Pixel() {},
        Marker: function Marker(options) { this.options = options; },
        Map: function Map() {
          this.add = function () {};
          this.destroy = function () {};
          this.on = function (event, callback) {
            if (event === "complete") setTimeout(callback, 0);
          };
        }
      };`
    });
  });
}

async function routeGitHubProjectSite(page) {
  await page.route("https://yrjmdqmmx.github.io/**", (route) => {
    const url = new URL(route.request().url());
    let relativePath = decodeURIComponent(url.pathname).replace(/^\/dykj-web\/?/, "");
    const candidate = resolve(siteRoot, relativePath || "index.html");
    const insideSite = candidate === siteRoot || candidate.startsWith(siteRoot + "/");
    let filePath = insideSite ? candidate : null;
    let status = 200;

    if (!filePath || !statIsFile(filePath)) {
      filePath = resolve(siteRoot, "404.html");
      status = 404;
    }

    route.fulfill({
      status,
      contentType: contentTypes[extname(filePath).toLowerCase()] || "application/octet-stream",
      body: readFileSync(filePath)
    });
  });
}

function statIsFile(path) {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

test.describe("navigation and deployment paths", () => {
  test("mobile menu is keyboard reachable and Escape restores focus", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chromium", "mobile navigation contract");
    await page.goto("/index.html");
    const toggle = page.locator("#navToggle");
    await toggle.focus();
    await page.keyboard.press("Enter");

    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".main-nav a").first()).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(toggle).toBeFocused();
  });

  test("all public pages have healthy internal links and no site console errors", async ({ page, request, baseURL }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one crawl covers shared markup");
    await mockAmapSuccess(page);
    const browserErrors = collectBrowserErrors(page);
    const internalUrls = new Set();
    const siteOrigin = new URL(baseURL).origin;

    for (const path of publicPages) {
      const response = await page.goto(path);
      expect(response.status(), `${path} should load`).toBe(200);
      const urls = await page.locator("a[href]").evaluateAll((links) => links.map((link) => link.href));
      for (const href of urls) {
        const url = new URL(href);
        if (url.origin === siteOrigin) {
          url.hash = "";
          internalUrls.add(url.href);
        }
      }
    }

    for (const href of internalUrls) {
      const response = await request.get(href);
      expect(response.status(), `broken internal link: ${href}`).toBeLessThan(400);
    }
    expect(browserErrors).toEqual([]);
  });

  test("deep 404 assets and links resolve at both ECS root and GitHub project root", async ({ page, baseURL }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one deployment-path contract");

    let response = await page.goto("/nested/missing/page");
    expect(response.status()).toBe(404);
    await expect.poll(() => page.locator("#siteStyles").evaluate((element) => {
      const url = new URL(element.href);
      return { origin: url.origin, pathname: url.pathname };
    })).toEqual({ origin: new URL(baseURL).origin, pathname: "/css/style.css" });
    await expect.poll(() => page.locator(".main-nav a").first().evaluate((element) => element.href)).toBe(
      new URL("/index.html", baseURL).href
    );
    await expect.poll(() => page.evaluate(() => window.SITE_CONFIG?.company)).toBe("北京鼎熠科技有限公司");

    await routeGitHubProjectSite(page);
    response = await page.goto("https://yrjmdqmmx.github.io/dykj-web/nested/missing/page");
    expect(response.status()).toBe(404);
    await expect.poll(() => page.locator("#siteStyles").evaluate((element) => element.href)).toMatch(
      /yrjmdqmmx\.github\.io\/dykj-web\/css\/style\.css/
    );
    await expect.poll(() => page.locator(".main-nav a").first().evaluate((element) => element.href)).toBe(
      "https://yrjmdqmmx.github.io/dykj-web/index.html"
    );
    await expect.poll(() => page.evaluate(() => window.SITE_CONFIG?.company)).toBe("北京鼎熠科技有限公司");
  });
});

test.describe("map progressive enhancement", () => {
  test("successful SDK initialization exposes the live map and keeps navigation links", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one map success contract");
    await mockAmapSuccess(page);
    await page.goto("/contact.html");
    await page.locator("#mapVisual").scrollIntoViewIfNeeded();

    await expect(page.locator("#mapVisual")).toHaveClass(/map-ready/);
    await expect(page.locator("#amapContainer")).toHaveAttribute("role", "region");
    await expect(page.locator("#amapContainer")).toHaveAttribute("aria-label", /高德地图/);
    await expect(page.getByRole("link", { name: "高德地图导航" })).toBeVisible();
    await expect(page.getByRole("link", { name: "百度地图导航" })).toBeVisible();
  });

  test("failed SDK initialization preserves the static address and navigation links", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "one map failure contract");
    await page.route("https://webapi.amap.com/maps?**", (route) => route.abort("failed"));
    await page.goto("/contact.html");
    await page.locator("#mapVisual").scrollIntoViewIfNeeded();
    await page.waitForTimeout(100);

    await expect(page.locator("#mapVisual")).not.toHaveClass(/map-ready/);
    await expect(page.locator("#mapVisual")).toHaveAttribute("aria-hidden", "true");
    await expect(page.locator(".map-card-body")).toContainText("中关村智造大街 D 座");
    await expect(page.getByRole("link", { name: "高德地图导航" })).toBeVisible();
    await expect(page.getByRole("link", { name: "百度地图导航" })).toBeVisible();
  });
});
