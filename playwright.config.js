const { defineConfig } = require("@playwright/test");

const isCI = Boolean(process.env.CI);

module.exports = defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  workers: isCI ? 2 : undefined,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  outputDir: "output/playwright/test-results",
  reporter: [
    ["line"],
    ["html", { outputFolder: "output/playwright/report", open: "never" }]
  ],
  use: {
    baseURL: "http://127.0.0.1:4173",
    locale: "zh-CN",
    colorScheme: "dark",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off"
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { browserName: "chromium", viewport: { width: 1440, height: 900 } }
    },
    {
      name: "mobile-chromium",
      use: { browserName: "chromium", viewport: { width: 390, height: 844 } }
    }
  ],
  webServer: {
    command: "bash scripts/build-site.sh _site && node tests/e2e/server.mjs",
    url: "http://127.0.0.1:4173/index.html",
    reuseExistingServer: false,
    timeout: 120_000
  }
});
