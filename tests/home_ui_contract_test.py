#!/usr/bin/env python3
"""Static contracts for the cinematic home page and shared site chrome.

This intentionally uses only the Python standard library so it can run in CI
before the later browser-test toolchain is installed.
"""

from __future__ import annotations

import unittest
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGE_FILES = (
    "index.html",
    "about.html",
    "business.html",
    "brands.html",
    "cases.html",
    "contact.html",
    "404.html",
)
PRIMARY_NAV = (
    "index.html",
    "about.html",
    "business.html",
    "brands.html",
    "cases.html",
    "contact.html",
)


class Element:
    def __init__(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag = tag
        self.attrs = dict(attrs)


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[Element] = []
        self.text_parts: list[str] = []
        self._nav_depth = 0
        self.primary_nav_links: list[dict[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        element = Element(tag, attrs)
        self.elements.append(element)

        classes = set((element.attrs.get("class") or "").split())
        if tag == "nav" and "main-nav" in classes:
            self._nav_depth += 1
        elif self._nav_depth and tag == "a":
            self.primary_nav_links.append(element.attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav" and self._nav_depth:
            self._nav_depth -= 1

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text_parts.append(data.strip())

    def find(self, tag: str, **attrs: str) -> list[Element]:
        matches: list[Element] = []
        for element in self.elements:
            if element.tag != tag:
                continue
            if all(element.attrs.get(key) == value for key, value in attrs.items()):
                matches.append(element)
        return matches


def parse_page(filename: str) -> DocumentParser:
    parser = DocumentParser()
    parser.feed((ROOT / filename).read_text(encoding="utf-8"))
    return parser


def path_without_query(value: str | None) -> str:
    if not value:
        return ""
    return urlsplit(value).path.lstrip("/").removeprefix("dykj-web/")


def version_for(value: str | None) -> str | None:
    if not value:
        return None
    versions = parse_qs(urlsplit(value).query).get("v", [])
    return versions[0] if len(versions) == 1 and versions[0].strip() else None


def css_declarations(source: str, selector: str, start: int = 0) -> dict[str, str]:
    """Return the first simple rule for *selector* after *start*."""
    match = re.search(
        re.escape(selector) + r"\s*\{([^}]*)\}", source[start:], flags=re.DOTALL
    )
    if not match:
        return {}

    declarations: dict[str, str] = {}
    for declaration in match.group(1).split(";"):
        if ":" not in declaration:
            continue
        property_name, value = declaration.split(":", 1)
        declarations[property_name.strip()] = value.strip()
    return declarations


def shared_stylesheet_references(page: DocumentParser) -> list[str | None]:
    """Return regular and mount-aware stylesheet references."""
    return [
        link.attrs.get("data-site-path") or link.attrs.get("href")
        for link in page.find("link", rel="stylesheet")
        if path_without_query(
            link.attrs.get("data-site-path") or link.attrs.get("href")
        )
        == "css/style.css"
    ]


def shared_runtime_references(page: DocumentParser) -> list[str]:
    """Return regular scripts plus 404's ordered mount-aware script list."""
    references = [
        script.attrs.get("src") or ""
        for script in page.find("script")
        if path_without_query(script.attrs.get("src")) == "js/main.js"
    ]
    for script in page.find("script"):
        references.extend(
            path
            for path in (script.attrs.get("data-site-scripts") or "").split()
            if path_without_query(path) == "js/main.js"
        )
    return references


class CinematicHomeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = parse_page("index.html")
        cls.source = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_home_loads_dedicated_stylesheet_and_runtime(self) -> None:
        stylesheet_paths = {
            path_without_query(link.attrs.get("href"))
            for link in self.page.find("link", rel="stylesheet")
        }
        script_paths = {
            path_without_query(script.attrs.get("src"))
            for script in self.page.find("script")
        }

        self.assertIn("css/home.css", stylesheet_paths)
        self.assertIn("js/company-scrolly.js", script_paths)

    def test_home_no_longer_loads_the_legacy_pump_experience(self) -> None:
        asset_references = [
            value
            for element in self.page.elements
            for key, value in element.attrs.items()
            if key in {"href", "src", "srcset", "data-src"} and value
        ]
        legacy = [
            value
            for value in asset_references
            if "pump-scrolly" in value or "assets/pump-seq/" in value
        ]
        self.assertEqual([], legacy, f"legacy pump references remain: {legacy}")
        self.assertNotIn("pump-scrolly", self.source)
        self.assertNotIn("assets/pump-seq/", self.source)

    def test_native_picture_contains_both_device_posters(self) -> None:
        references = {
            value.split()[0]
            for element in self.page.elements
            if element.tag in {"source", "img"}
            for key in ("srcset", "src")
            if (value := element.attrs.get(key))
        }

        self.assertTrue(
            any(ref.endswith("assets/scrolly/v2/poster-desktop.webp") for ref in references),
            "desktop poster is missing from native picture markup",
        )
        self.assertTrue(
            any(ref.endswith("assets/scrolly/v2/poster-mobile.webp") for ref in references),
            "mobile poster is missing from native picture markup",
        )
        self.assertTrue(self.page.find("picture"), "home needs a native <picture> fallback")

    def test_canvas_is_decorative_and_not_keyboard_focusable(self) -> None:
        canvases = self.page.find("canvas")
        self.assertEqual(1, len(canvases), "home should expose one decorative sequence canvas")
        canvas = canvases[0]
        self.assertEqual("true", canvas.attrs.get("aria-hidden"))
        self.assertNotIn("tabindex", canvas.attrs)

    def test_five_semantic_acts_remain_available_as_html(self) -> None:
        acts = [
            element
            for element in self.page.elements
            if element.tag == "article" and "data-act" in element.attrs
        ]
        self.assertEqual(5, len(acts), "the cinematic narrative must contain five HTML acts")
        self.assertEqual(
            {"1", "2", "3", "4", "5"},
            {act.attrs.get("data-act") for act in acts},
        )
        for act in acts:
            self.assertNotEqual("true", act.attrs.get("aria-hidden"))
            self.assertNotIn("hidden", act.attrs)

    def test_engineering_disclaimer_is_visible_html_copy(self) -> None:
        visible_copy = " ".join(self.page.text_parts)
        self.assertIn("结构与动画为工程示意", visible_copy)

    def test_five_copy_tracks_match_the_500svh_scrollable_distance(self) -> None:
        css = (ROOT / "css/home.css").read_text(encoding="utf-8")
        scrolly = css_declarations(css, ".company-scrolly")
        steps = css_declarations(css, ".company-steps")
        act = css_declarations(css, ".company-act")

        self.assertEqual("500svh", scrolly.get("height"))
        self.assertNotIn("min-height", scrolly)
        self.assertEqual("420svh", steps.get("height"))
        self.assertEqual("repeat(5, 80svh)", steps.get("grid-template-rows"))
        self.assertEqual("100svh", act.get("min-height"))

    def test_reduced_motion_restores_natural_copy_flow(self) -> None:
        css = (ROOT / "css/home.css").read_text(encoding="utf-8")
        reduced_start = css.index("@media (prefers-reduced-motion: reduce)")
        reduced_steps = css_declarations(css, ".company-steps", reduced_start)
        reduced_act = css_declarations(css, ".company-act", reduced_start)

        self.assertEqual("auto", reduced_steps.get("height"))
        self.assertEqual("0", reduced_act.get("min-height"))

    def test_noninteractive_labels_use_the_warm_industrial_accent(self) -> None:
        css = (ROOT / "css/home.css").read_text(encoding="utf-8")
        label_selectors = (
            ".act-number",
            ".home-section-head > p",
            ".capability-index",
            ".proof-metrics strong small",
            ".home-case > span",
            ".home-contact-panel p",
        )

        for selector in label_selectors:
            with self.subTest(selector=selector):
                self.assertEqual(
                    "var(--copper)",
                    css_declarations(css, selector).get("color"),
                )


class SharedChromeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pages = {filename: parse_page(filename) for filename in PAGE_FILES}

    def test_all_seven_pages_have_the_same_primary_navigation(self) -> None:
        for filename, page in self.pages.items():
            with self.subTest(page=filename):
                hrefs = tuple(
                    path_without_query(link.get("href"))
                    for link in page.primary_nav_links
                )
                self.assertEqual(PRIMARY_NAV, hrefs)

    def test_each_content_page_marks_exactly_its_current_navigation_item(self) -> None:
        for filename in PAGE_FILES[:-1]:
            page = self.pages[filename]
            current = [
                link for link in page.primary_nav_links if link.get("aria-current") == "page"
            ]
            with self.subTest(page=filename):
                self.assertEqual(1, len(current))
                self.assertEqual(filename, path_without_query(current[0].get("href")))

    def test_404_navigation_has_no_false_current_page(self) -> None:
        current = [
            link
            for link in self.pages["404.html"].primary_nav_links
            if link.get("aria-current") == "page"
        ]
        self.assertEqual([], current)

    def test_all_seven_pages_share_skip_target_and_footer_shell(self) -> None:
        for filename, page in self.pages.items():
            skip_links = [
                element
                for element in page.find("a")
                if "skip-link" in (element.attrs.get("class") or "").split()
            ]
            main_targets = page.find("main", id="main-content")
            footers = [
                element
                for element in page.find("footer")
                if "site-footer" in (element.attrs.get("class") or "").split()
            ]
            with self.subTest(page=filename):
                self.assertEqual(1, len(skip_links))
                self.assertEqual("#main-content", skip_links[0].attrs.get("href"))
                self.assertEqual(1, len(main_targets))
                self.assertEqual(1, len(footers))

    def test_shared_css_and_js_are_versioned_consistently(self) -> None:
        css_versions: set[str] = set()
        js_versions: set[str] = set()

        for filename, page in self.pages.items():
            styles = shared_stylesheet_references(page)
            scripts = shared_runtime_references(page)
            with self.subTest(page=filename):
                self.assertEqual(1, len(styles), "expected one shared stylesheet")
                self.assertEqual(1, len(scripts), "expected one shared runtime")
                self.assertIsNotNone(version_for(styles[0]))
                self.assertIsNotNone(version_for(scripts[0]))
                css_versions.add(version_for(styles[0]) or "")
                js_versions.add(version_for(scripts[0]) or "")

        self.assertEqual(1, len(css_versions), f"CSS versions diverged: {css_versions}")
        self.assertEqual(1, len(js_versions), f"JS versions diverged: {js_versions}")


class NotFoundPortabilityContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = parse_page("404.html")
        cls.source = (ROOT / "404.html").read_text(encoding="utf-8")

    def test_deep_404_never_uses_directory_relative_navigation(self) -> None:
        internal_links = [
            element
            for element in self.page.find("a")
            if (href := element.attrs.get("href"))
            and not href.startswith(("#", "mailto:", "tel:"))
            and element.attrs.get("data-site-path") is not None
        ]
        self.assertGreater(len(internal_links), 10, "expected the complete shared 404 chrome")

        for link in internal_links:
            href = link.attrs.get("href") or ""
            fallback = urlsplit(href)
            with self.subTest(href=href):
                self.assertEqual("https", fallback.scheme)
                self.assertEqual("dingyivac.com", fallback.netloc)
                self.assertTrue(
                    fallback.path.startswith("/"),
                    f"no-JS fallback must stay inside the production site: {href}",
                )
                self.assertIsNotNone(
                    link.attrs.get("data-site-path"),
                    "JavaScript deployments need a mount-relative path contract",
                )

    def test_mount_relative_paths_resolve_from_both_deployment_roots(self) -> None:
        links = [
            element
            for element in self.page.find("a")
            if element.attrs.get("data-site-path") is not None
        ]
        deployment_roots = (
            "https://yrjmdqmmx.github.io/dykj-web/",
            "https://dingyivac.com/",
        )

        for deployment_root in deployment_roots:
            expected_prefix = urlsplit(deployment_root).path
            for link in links:
                site_path = link.attrs.get("data-site-path") or ""
                resolved = urljoin(deployment_root, site_path)
                with self.subTest(root=deployment_root, path=site_path):
                    self.assertEqual(urlsplit(deployment_root).netloc, urlsplit(resolved).netloc)
                    self.assertTrue(urlsplit(resolved).path.startswith(expected_prefix))
                    self.assertNotIn("/missing/deep/", urlsplit(resolved).path)

    def test_404_bootstrap_declares_both_mounts_without_a_base_element(self) -> None:
        self.assertFalse(self.page.find("base"), "<base> would break the local skip link")
        self.assertIn('id="sitePathBootstrap"', self.source)
        self.assertIn('"/dykj-web/"', self.source)
        self.assertIn('window.location.hostname', self.source)
        self.assertIn('github\\.io', self.source)
        self.assertIn('window.__DINGYI_SITE_ROOT__', self.source)

        skip = [
            element
            for element in self.page.find("a")
            if "skip-link" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(1, len(skip))
        self.assertEqual("#main-content", skip[0].attrs.get("href"))
        self.assertIsNone(skip[0].attrs.get("data-site-path"))

    def test_shared_assets_are_mount_aware_and_keep_no_js_fallback(self) -> None:
        styles = self.page.find("link", rel="stylesheet")
        self.assertEqual(1, len(styles))
        self.assertEqual("css/style.css?v=20260714", styles[0].attrs.get("data-site-path"))
        self.assertEqual(
            "https://dingyivac.com/css/style.css?v=20260714",
            styles[0].attrs.get("href"),
        )

        loaders = self.page.find("script", id="siteRuntimeLoader")
        self.assertEqual(1, len(loaders))
        self.assertEqual(
            "js/site-config.js?v=20260714 js/main.js?v=20260714",
            loaders[0].attrs.get("data-site-scripts"),
        )

        return_links = [
            element
            for element in self.page.find("a")
            if "btn" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(1, len(return_links))
        self.assertEqual("", return_links[0].attrs.get("data-site-path"))
        self.assertEqual(
            "https://dingyivac.com/",
            return_links[0].attrs.get("href"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
