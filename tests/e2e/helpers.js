const { expect } = require("@playwright/test");

async function waitForScrolly(page) {
  await page.waitForFunction(() => window.__COMPANY_SCROLLY__?.enhanced === true);
  return page.evaluate(() => window.__COMPANY_SCROLLY__);
}

async function scrollScrollyTo(page, progress) {
  await page.evaluate((nextProgress) => {
    const section = document.getElementById("companyScrolly");
    const top = section.getBoundingClientRect().top + window.scrollY;
    const distance = Math.max(0, section.offsetHeight - window.innerHeight);
    window.scrollTo(0, top + distance * nextProgress);
  }, progress);
}

async function expectStaticScrollyFallback(page) {
  await expect(page.locator("#companyScrolly")).not.toHaveClass(/canvas-ready/);
  await expect(page.locator(".company-canvas")).toBeHidden();
  await expect(page.locator(".company-poster img")).toBeVisible();
  await expect(page.locator(".company-act[data-act]")).toHaveCount(5);
  await expect(page.locator(".company-act[data-act='5']")).toContainText("可靠交付");
}

function collectBrowserErrors(page) {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
  return errors;
}

module.exports = {
  collectBrowserErrors,
  expectStaticScrollyFallback,
  scrollScrollyTo,
  waitForScrolly
};
