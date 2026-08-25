#!/usr/bin/env python3
"""Build-output contract for the static home UI package."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_site"

REQUIRED = (
    "css/home.css",
    "index.html",
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
    "assets/scrolly/v2",
    "js/company-scrolly.js",
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

    def test_build_contains_static_home_assets(self) -> None:
        missing = [relative for relative in REQUIRED if not (OUTPUT / relative).is_file()]
        self.assertEqual([], missing, f"missing deployable UI artifacts: {missing}")

    def test_build_excludes_source_and_development_inputs(self) -> None:
        leaked = [relative for relative in EXCLUDED if (OUTPUT / relative).exists()]
        self.assertEqual([], leaked, f"development inputs leaked into build: {leaked}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
