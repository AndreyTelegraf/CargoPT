import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

PAGES = {
    "pt": {
        "path": STATIC / "parceiros/index.html",
        "canonical": "https://cargopt.pt/parceiros/",
        "home": "/",
        "partner_path": "/parceiros/",
        "marker": "Parcerias úteis",
    },
    "en": {
        "path": STATIC / "en/partners/index.html",
        "canonical": "https://cargopt.pt/en/partners/",
        "home": "/en/",
        "partner_path": "/en/partners/",
        "marker": "Useful partnerships",
    },
    "ru": {
        "path": STATIC / "ru/partners/index.html",
        "canonical": "https://cargopt.pt/ru/partners/",
        "home": "/ru/",
        "partner_path": "/ru/partners/",
        "marker": "Полезные партнёрства",
    },
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.canonicals: list[str] = []
        self.alternates: dict[str, str] = {}
        self.json_ld: list[str] = []
        self._json_buffer: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href", ""))
        if tag == "link" and values.get("rel") == "alternate":
            self.alternates[values.get("hreflang", "")] = values.get("href", "")
        if tag == "script" and values.get("type") == "application/ld+json":
            self._json_buffer = []

    def handle_data(self, data):
        if self._json_buffer is not None:
            self._json_buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json_buffer is not None:
            self.json_ld.append("".join(self._json_buffer))
            self._json_buffer = None


def check_page(locale: str, spec: dict[str, object]) -> None:
    path = spec["path"]
    text = path.read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(text)

    if parser.canonicals != [spec["canonical"]]:
        raise AssertionError(f"{locale}: canonical mismatch")
    expected_alternates = {
        "pt-PT": "https://cargopt.pt/parceiros/",
        "en": "https://cargopt.pt/en/partners/",
        "ru": "https://cargopt.pt/ru/partners/",
        "x-default": "https://cargopt.pt/parceiros/",
    }
    if parser.alternates != expected_alternates:
        raise AssertionError(f"{locale}: hreflang mismatch")
    if spec["marker"] not in text:
        raise AssertionError(f"{locale}: localized marker missing")
    if "partners@cargopt.pt" not in text:
        raise AssertionError(f"{locale}: partner contact missing")
    if '/assets/css/partners.css?v=partners-v2' not in text:
        raise AssertionError(f"{locale}: current partner stylesheet missing")
    if spec["home"] not in parser.links:
        raise AssertionError(f"{locale}: localized home link missing")
    if spec["partner_path"] not in parser.links:
        raise AssertionError(f"{locale}: self partner link missing")

    documents = [json.loads(value) for value in parser.json_ld]
    types = {document.get("@type") for document in documents}
    if types != {"CollectionPage", "BreadcrumbList"}:
        raise AssertionError(f"{locale}: structured data mismatch")

    for href in parser.links:
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https"} and parsed.netloc != "cargopt.pt":
            raise AssertionError(f"{locale}: unapproved external link {href}")

    forbidden = ("remodel.pt", "dofollow", "guaranteed referrals")
    lowered = text.lower()
    if any(value in lowered for value in forbidden):
        raise AssertionError(f"{locale}: unapproved partner claim")


def check_home_links() -> None:
    homes = {
        STATIC / "index.html": "/parceiros/",
        STATIC / "en/index.html": "/en/partners/",
        STATIC / "ru/index.html": "/ru/partners/",
    }
    for path, href in homes.items():
        text = path.read_text(encoding="utf-8")
        if f'href="{href}"' not in text:
            raise AssertionError(f"homepage partner link missing: {path}")


def check_sitemap() -> None:
    text = (STATIC / "sitemap.xml").read_text(encoding="utf-8")
    for value in (
        "https://cargopt.pt/parceiros/",
        "https://cargopt.pt/en/partners/",
        "https://cargopt.pt/ru/partners/",
    ):
        if text.count(f"<loc>{value}</loc>") != 1:
            raise AssertionError(f"sitemap entry mismatch: {value}")


def check_heading_tracking() -> None:
    text = (STATIC / "assets/css/partners.css").read_text(encoding="utf-8")
    match = re.search(r"\.partners-hero h1\s*\{(?P<body>[^}]*)\}", text)
    if match is None:
        raise AssertionError("partner hero title rule missing")
    expected = "letter-spacing: var(--letter-spacing-hero-title);"
    if expected not in match.group("body"):
        raise AssertionError("partner hero title uses legacy tight tracking")


def main() -> None:
    for locale, spec in PAGES.items():
        check_page(locale, spec)
    check_home_links()
    check_sitemap()
    check_heading_tracking()
    print("PARTNERS_STATIC_SMOKE_OK", len(PAGES))


if __name__ == "__main__":
    main()
