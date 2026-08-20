from __future__ import annotations

from html.parser import HTMLParser
import os
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(os.environ.get("CARGOPT_ROOT", Path(__file__).resolve().parents[1]))
STATIC = ROOT / "app/static"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.span_depth = 0
        self.locale_menu_depth: int | None = None
        self.links: list[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "span":
            self.span_depth += 1
            if "locale-menu" in classes:
                self.locale_menu_depth = self.span_depth

        if tag == "a" and values.get("href"):
            self.links.append((values["href"] or "", self.locale_menu_depth is not None))

    def handle_endtag(self, tag: str) -> None:
        if tag != "span":
            return
        if self.locale_menu_depth == self.span_depth:
            self.locale_menu_depth = None
        self.span_depth = max(0, self.span_depth - 1)


def page_locale(source: str) -> str:
    marker = 'data-locale="'
    start = source.index(marker) + len(marker)
    locale = source[start:source.index('"', start)].lower()
    return "pt" if locale.startswith("pt") else locale


def internal_path(href: str) -> str | None:
    if href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlparse(href)
    if parsed.scheme and parsed.netloc != "cargopt.pt":
        return None
    return parsed.path or "/"


def is_shared_path(path: str) -> bool:
    return path.startswith(("/assets/", "/api/")) or path in {
        "/favicon.ico",
        "/site.webmanifest",
    }


def main() -> None:
    failures: list[tuple[Path, str, str]] = []
    checked = 0

    for html_path in sorted(STATIC.rglob("index.html")):
        relative = html_path.relative_to(STATIC)
        if relative == Path("meta-operations/index.html"):
            continue

        source = html_path.read_text(encoding="utf-8")
        locale = page_locale(source)
        is_guide_article = 'class="guide-page"' in source
        parser = LinkParser()
        parser.feed(source)

        for href, in_locale_menu in parser.links:
            path = internal_path(href)
            if path is None or is_shared_path(path) or in_locale_menu:
                continue
            checked += 1

            if is_guide_article:
                if locale in {"en", "ru"} and path == "/":
                    failures.append((relative, locale, href))
                continue

            if locale == "pt":
                wrong_locale = path.startswith(("/en/", "/ru/"))
            else:
                wrong_locale = not path.startswith(f"/{locale}/")

            if wrong_locale:
                failures.append((relative, locale, href))

    assert not failures, failures

    landing_js = (STATIC / "assets/js/landing.js").read_text(encoding="utf-8")
    track_js = (STATIC / "assets/js/track.js").read_text(encoding="utf-8")
    assert "tracking_url: localizedTrackingPath(entry.token)" in landing_js
    assert "window.location.href = localizedTrackingPath(body.tracking_token)" in landing_js
    assert "tracking_url: `${trackBasePath}/${encodeURIComponent(entry.token)}`" in track_js
    assert "entry.tracking_url\n      ||" not in track_js

    for relative in (Path("track/index.html"), Path("en/track/index.html"), Path("ru/track/index.html")):
        source = (STATIC / relative).read_text(encoding="utf-8")
        assert "/assets/js/track.js?v=short-lead-v1-locale-transition-v1" in source

    print("LOCALE_TRANSITION_STATIC_LINKS_OK", checked)
    print("LOCALE_TRANSITION_SAVED_REQUESTS_OK")


if __name__ == "__main__":
    main()
