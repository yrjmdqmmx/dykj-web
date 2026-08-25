#!/usr/bin/env python3
"""Static contracts for the dingyivac.com production-domain cutover."""

from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICP_NUMBER = "京ICP备2026049830号-1"
PRODUCTION_ORIGIN = "https://dingyivac.com"
CONTENT_PAGES = {
    "index.html": f"{PRODUCTION_ORIGIN}/",
    "about.html": f"{PRODUCTION_ORIGIN}/about.html",
    "business.html": f"{PRODUCTION_ORIGIN}/business.html",
    "brands.html": f"{PRODUCTION_ORIGIN}/brands.html",
    "cases.html": f"{PRODUCTION_ORIGIN}/cases.html",
    "contact.html": f"{PRODUCTION_ORIGIN}/contact.html",
}
ALL_PAGES = (*CONTENT_PAGES, "404.html")


class HtmlContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self._icp_link_depth = 0
        self.icp_link_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if tag == "a" and attributes.get("data-config") == "icp":
            self._icp_link_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._icp_link_depth:
            self._icp_link_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._icp_link_depth and data.strip():
            self.icp_link_text.append(data.strip())

    def find(self, tag: str, **attrs: str) -> list[dict[str, str | None]]:
        return [
            attributes
            for element_tag, attributes in self.elements
            if element_tag == tag
            and all(attributes.get(key) == value for key, value in attrs.items())
        ]


def parse_html(filename: str) -> HtmlContractParser:
    parser = HtmlContractParser()
    parser.feed((ROOT / filename).read_text(encoding="utf-8"))
    return parser


class DomainCutoverContractTest(unittest.TestCase):
    def test_all_seven_pages_declare_one_empty_favicon(self) -> None:
        for filename in ALL_PAGES:
            page = parse_html(filename)
            icon_links = [
                attributes
                for tag, attributes in page.elements
                if tag == "link"
                and "icon" in (attributes.get("rel") or "").split()
            ]
            with self.subTest(page=filename):
                self.assertEqual(1, len(icon_links))
                self.assertEqual("icon", icon_links[0].get("rel"))
                self.assertEqual("data:,", icon_links[0].get("href"))
                self.assertFalse(page.find("link", rel="apple-touch-icon"))

    def test_site_config_contains_the_approved_icp_number(self) -> None:
        source = (ROOT / "js/site-config.js").read_text(encoding="utf-8")
        match = re.search(r"\bicp\s*:\s*([\"'])(.*?)\1", source)
        self.assertIsNotNone(match, "site config must declare the ICP field")
        self.assertEqual(ICP_NUMBER, match.group(2))

    def test_each_content_page_has_one_canonical_and_open_graph_url(self) -> None:
        for filename, expected_url in CONTENT_PAGES.items():
            page = parse_html(filename)
            canonicals = page.find("link", rel="canonical")
            open_graph_urls = page.find("meta", property="og:url")
            with self.subTest(page=filename):
                self.assertEqual([expected_url], [item.get("href") for item in canonicals])
                self.assertEqual(
                    [expected_url], [item.get("content") for item in open_graph_urls]
                )

    def test_all_seven_footers_have_a_linked_static_icp_fallback(self) -> None:
        for filename in ALL_PAGES:
            page = parse_html(filename)
            links = page.find(
                "a",
                **{
                    "data-config": "icp",
                    "href": "https://beian.miit.gov.cn/",
                },
            )
            with self.subTest(page=filename):
                self.assertEqual(1, len(links))
                self.assertEqual([ICP_NUMBER], page.icp_link_text)

    def test_robots_and_sitemap_publish_only_production_urls(self) -> None:
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(f"Sitemap: {PRODUCTION_ORIGIN}/sitemap.xml", robots)
        self.assertNotIn("zdywrnm.github.io", robots)
        self.assertNotIn("启用正式域名后", robots)

        root = ET.parse(ROOT / "sitemap.xml").getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [element.text for element in root.findall("sm:url/sm:loc", namespace)]
        self.assertEqual(list(CONTENT_PAGES.values()), locations)

    def test_404_keeps_pages_mount_adaptation_with_production_no_js_fallbacks(self) -> None:
        page = parse_html("404.html")
        source = (ROOT / "404.html").read_text(encoding="utf-8")

        fallback_links = [
            attributes
            for attributes in page.find("a")
            if attributes.get("data-site-path") is not None
        ]
        self.assertGreater(len(fallback_links), 10)
        for link in fallback_links:
            with self.subTest(path=link.get("data-site-path")):
                self.assertTrue(
                    (link.get("href") or "").startswith(f"{PRODUCTION_ORIGIN}/")
                )

        styles = page.find("link", rel="stylesheet")
        self.assertEqual(1, len(styles))
        self.assertTrue((styles[0].get("href") or "").startswith(PRODUCTION_ORIGIN))
        self.assertEqual("css/style.css?v=20260714", styles[0].get("data-site-path"))
        self.assertIn('var projectRoot = "/dykj-web/"', source)
        self.assertIn("github\\.io", source)
        self.assertIn("window.__DINGYI_SITE_ROOT__", source)

    def test_cutover_placeholders_and_outdated_handover_copy_are_removed(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        handover = (ROOT / "docs/DEPLOY-HANDOVER.md").read_text(encoding="utf-8")

        self.assertNotIn("备案和正式域名启用后再补充 canonical", index)
        self.assertIn(ICP_NUMBER, readme)
        self.assertNotIn("icp` 字段替换为真实备案号", readme)
        self.assertIn(ICP_NUMBER, handover)
        self.assertNotIn("`icp`（备案号，当前为空字符串）", handover)
        self.assertNotIn("`icp` 填入真实备案号", handover)

    def test_github_pages_preview_uses_the_current_repository_owner(self) -> None:
        current_preview = "https://yrjmdqmmx.github.io/dykj-web/"
        retired_owner = "zdywrnm"
        checked_files = (
            "README.md",
            "docs/DEPLOY-HANDOVER.md",
            "tests/home_ui_contract_test.py",
            "tests/map_runtime_test.js",
            "tests/e2e/navigation-map.spec.js",
        )

        self.assertIn(current_preview, (ROOT / "README.md").read_text(encoding="utf-8"))
        for filename in checked_files:
            with self.subTest(file=filename):
                source = (ROOT / filename).read_text(encoding="utf-8")
                self.assertNotIn(retired_owner, source)

    def test_ecs_deploy_verifies_the_canonical_https_host(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        self.assertIn("--exclude='.well-known/acme-challenge/'", workflow)
        self.assertIn('https://dingyivac.com/index.html', workflow)
        self.assertIn('--resolve "dingyivac.com:443:${{ secrets.SERVER_HOST }}"', workflow)
        self.assertNotIn('http://${{ secrets.SERVER_HOST }}/index.html', workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
