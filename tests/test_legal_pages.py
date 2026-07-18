from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.canonical = []
        self.remote_assets = []
        self.script_count = 0
        self.main_count = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)

        if identifier := attributes.get("id"):
            self.ids.add(identifier)
        if tag == "a" and (href := attributes.get("href")):
            self.links.append(href)
        if tag == "link":
            href = attributes.get("href")
            if attributes.get("rel") == "canonical" and href:
                self.canonical.append(href)
            if (
                attributes.get("rel") == "stylesheet"
                and href
                and urlparse(href).scheme in {"http", "https"}
            ):
                self.remote_assets.append(href)
        if tag in {"img", "video", "audio", "iframe"}:
            source = attributes.get("src")
            if source and urlparse(source).scheme in {"http", "https"}:
                self.remote_assets.append(source)
        if tag == "script":
            self.script_count += 1
        if tag == "main":
            self.main_count += 1


def parse_page(relative_path):
    path = DOCS / relative_path
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return path, parser


class LegalPagesTests(unittest.TestCase):
    pages = {
        Path("index.html"): "https://meetingalarmo.github.io/",
        Path("privacy/index.html"): "https://meetingalarmo.github.io/privacy/",
        Path("terms/index.html"): "https://meetingalarmo.github.io/terms/",
    }

    def test_pages_have_canonical_urls_and_no_tracking_assets(self):
        for relative_path, expected_canonical in self.pages.items():
            with self.subTest(page=relative_path):
                _, parser = parse_page(relative_path)
                self.assertEqual(parser.main_count, 1)
                self.assertEqual(parser.canonical, [expected_canonical])
                self.assertEqual(parser.script_count, 0)
                self.assertEqual(parser.remote_assets, [])
                self.assertTrue(
                    any(
                        link.startswith("mailto:meetingalarmo@gmail.com")
                        for link in parser.links
                    )
                )

    def test_internal_links_resolve_to_published_files(self):
        for relative_path in self.pages:
            page_path, parser = parse_page(relative_path)
            for href in parser.links:
                parsed = urlparse(href)
                if parsed.scheme or href.startswith("#"):
                    continue

                target = (page_path.parent / unquote(parsed.path)).resolve()
                if parsed.path.endswith("/") or target.is_dir():
                    target /= "index.html"

                with self.subTest(page=relative_path, href=href):
                    self.assertTrue(
                        target.is_relative_to(DOCS.resolve()),
                        f"Link escapes the published docs directory: {href}",
                    )
                    self.assertTrue(target.is_file(), f"Broken link: {href}")

    def test_privacy_policy_covers_current_data_flows_and_choices(self):
        path, parser = parse_page(Path("privacy/index.html"))
        required_sections = {
            "data-we-handle",
            "on-device-data",
            "diagnostics",
            "purchases",
            "contact",
            "retention",
            "choices",
            "children",
            "changes",
            "contact-us",
        }
        content = " ".join(path.read_text(encoding="utf-8").split())

        self.assertTrue(required_sections.issubset(parser.ids))
        for disclosure in (
            "Firebase Crashlytics",
            "Firebase Analytics is not included",
            "90 days",
            "does not offer an in-app diagnostic collection switch",
            "do not sell personal information",
        ):
            with self.subTest(disclosure=disclosure):
                self.assertIn(disclosure, content)

    def test_terms_cover_products_safety_and_standard_eula_choice(self):
        path, parser = parse_page(Path("terms/index.html"))
        required_sections = {
            "eula",
            "app",
            "purchases",
            "subscriptions",
            "lifetime",
            "acceptable-use",
            "safety",
            "warranties",
            "liability",
            "changes",
            "support",
        }
        content = " ".join(path.read_text(encoding="utf-8").split())

        self.assertTrue(required_sections.issubset(parser.ids))
        for term in (
            "Standard End User License Agreement",
            "monthly and yearly auto-renewable",
            "at least 24 hours",
            "one-time, non-consumable purchase",
            "general-purpose utility",
        ):
            with self.subTest(term=term):
                self.assertIn(term, content)


if __name__ == "__main__":
    unittest.main()
