#!/usr/bin/env python3
"""Build-output contract for the cinematic UI package."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_site"

REQUIRED = (
    "css/home.css",
    "js/company-scrolly.js",
    "assets/scrolly/v2/manifest.json",
    "assets/scrolly/v2/poster-desktop.webp",
    "assets/scrolly/v2/poster-mobile.webp",
    "assets/scrolly/v2/desktop/frame-0001.webp",
    "assets/scrolly/v2/desktop/frame-0048.webp",
    "assets/scrolly/v2/desktop/frame-0096.webp",
    "assets/scrolly/v2/mobile/frame-0001.webp",
    "assets/scrolly/v2/mobile/frame-0020.webp",
    "assets/scrolly/v2/mobile/frame-0040.webp",
)

EXCLUDED = (
    "source",
    "tests",
    "docs",
    "scripts",
    ".github",
    "node_modules",
    "assets/pump-seq",
    "js/pump-scrolly.js",
)


class BuildUiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        shutil.rmtree(OUTPUT, ignore_errors=True)
        subprocess.run(
            [str(ROOT / "scripts" / "build-site.sh"), str(OUTPUT)],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(OUTPUT, ignore_errors=True)

    def test_build_contains_home_runtime_and_cinematic_assets(self) -> None:
        missing = [relative for relative in REQUIRED if not (OUTPUT / relative).is_file()]
        self.assertEqual([], missing, f"missing deployable UI artifacts: {missing}")

    def test_build_excludes_source_and_development_inputs(self) -> None:
        leaked = [relative for relative in EXCLUDED if (OUTPUT / relative).exists()]
        self.assertEqual([], leaked, f"development inputs leaked into build: {leaked}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
