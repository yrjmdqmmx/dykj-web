#!/usr/bin/env python3
"""Static contract for the browser QA toolchain.

This keeps deployment workflows and local commands from silently drifting away
from the checked-in Playwright setup.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PlaywrightToolchainContractTest(unittest.TestCase):
    def test_package_exposes_pinned_browser_qa_commands(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertTrue(package.get("private"), "browser QA package must not be publishable")
        self.assertEqual("npm run test:e2e", package["scripts"]["test:browser"])
        self.assertEqual("playwright test", package["scripts"]["test:e2e"])
        self.assertRegex(
            package["devDependencies"]["@playwright/test"],
            r"^\d+\.\d+\.\d+$",
            "@playwright/test must use an exact version",
        )

    def test_playwright_files_and_artifacts_follow_repository_conventions(self) -> None:
        required = (
            "playwright.config.js",
            "tests/e2e/site.spec.js",
            "tests/e2e/fallbacks.spec.js",
            "tests/e2e/navigation-map.spec.js",
            "tests/e2e/server.mjs",
            "tests/e2e/README.md",
            "package-lock.json",
        )
        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual([], missing)

        config = (ROOT / "playwright.config.js").read_text(encoding="utf-8")
        self.assertIn('outputDir: "output/playwright/test-results"', config)
        self.assertIn('["html", { outputFolder: "output/playwright/report"', config)
        self.assertIn("scripts/build-site.sh _site", config)

    def test_both_deploy_workflows_gate_release_on_browser_qa(self) -> None:
        for relative_path in (".github/workflows/pages.yml", ".github/workflows/deploy.yml"):
            with self.subTest(workflow=relative_path):
                workflow = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("actions/setup-node@v4", workflow)
                self.assertIn("npm ci", workflow)
                self.assertIn("npx playwright install --with-deps chromium", workflow)
                self.assertIn("npm run test:browser", workflow)
                self.assertNotIn("node tests/company_scrolly_runtime_test.js", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
