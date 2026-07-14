#!/usr/bin/env python3
"""Static contracts for the AMap proxy and documented fallback behavior."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MapContractTest(unittest.TestCase):
    def test_generic_amap_proxy_forces_jsonp_javascript_content_type(self) -> None:
        source = (ROOT / "docs/nginx-amap-proxy.conf.example").read_text(
            encoding="utf-8"
        )
        generic = source.split("location ^~ /_AMapService/ {", 1)[1]

        self.assertIn("proxy_hide_header Content-Type;", generic)
        self.assertIn(
            "add_header Content-Type application/javascript always;", generic
        )
        self.assertIn("add_header X-Content-Type-Options nosniff always;", generic)

    def test_docs_describe_navigation_links_as_present(self) -> None:
        sources = {
            filename: (ROOT / filename).read_text(encoding="utf-8")
            for filename in ("README.md", "docs/DEPLOY-HANDOVER.md")
        }

        for filename, source in sources.items():
            with self.subTest(filename=filename):
                self.assertNotIn("导航链接已按用户要求于 2026-07 移除", source)
                self.assertNotIn("导航链接已按用户要求移除（2026-07）", source)
                self.assertIn("高德/百度导航链接", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
