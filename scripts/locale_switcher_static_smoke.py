from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

CSS_VERSION = "locale-switcher-v1"
CSS_REFERENCE = (
    "/assets/css/components.css"
    f"?v={CSS_VERSION}"
)

pages = sorted(STATIC.rglob("index.html"))

assert len(pages) == 82, len(pages)

locale_counts = {
    "pt": 0,
    "en": 0,
    "ru": 0,
}

expected_active_label = {
    "pt": "PT",
    "en": "EN",
    "ru": "RU",
}

for path in pages:
    source = path.read_text(encoding="utf-8")

    relative = path.relative_to(STATIC)

    assert source.count(
        'class="site-header"'
    ) == 1, relative

    assert source.count(
        'class="logo"'
    ) == 1, relative

    assert source.count(
        'class="locale-switcher"'
    ) == 1, relative

    assert source.count(
        CSS_REFERENCE
    ) == 1, relative

    body = re.search(
        r'<body\b[^>]*\bdata-locale="([^"]+)"',
        source,
    )

    assert body is not None, relative

    locale = body.group(1)

    assert locale in locale_counts, (
        relative,
        locale,
    )

    locale_counts[locale] += 1

    switcher = re.search(
        r'<span class="locale-switcher">'
        r'.*?'
        r'<span class="locale-menu">'
        r'(.*?)'
        r'</span>\s*</span>',
        source,
        re.S,
    )

    assert switcher is not None, relative

    menu = switcher.group(1)

    links = re.findall(
        r'<a href="([^"]+)"'
        r'(?: aria-current="page")?>'
        r'(PT|EN|RU)</a>',
        menu,
    )

    assert len(links) == 3, (
        relative,
        links,
    )

    assert [
        label
        for _, label in links
    ] == [
        "PT",
        "EN",
        "RU",
    ], (
        relative,
        links,
    )

    active = re.findall(
        r'<a href="([^"]+)" '
        r'aria-current="page">'
        r'(PT|EN|RU)</a>',
        menu,
    )

    assert len(active) == 1, (
        relative,
        active,
    )

    assert active[0][1] == (
        expected_active_label[locale]
    ), (
        relative,
        locale,
        active,
    )

assert locale_counts == {
    "pt": 70,
    "en": 6,
    "ru": 6,
}, locale_counts

css = (
    STATIC / "assets/css/components.css"
).read_text(encoding="utf-8")

switcher_rule = re.search(
    r'\.locale-switcher\s*\{(.*?)\}',
    css,
    re.S,
)

assert switcher_rule is not None

switcher_body = switcher_rule.group(1)

assert "display: inline-flex;" in switcher_body
assert "display: none;" not in switcher_body
assert "position: relative;" in switcher_body
assert "align-items: center;" in switcher_body

menu_rule = re.search(
    r'\.locale-menu\s*\{(.*?)\}',
    css,
    re.S,
)

assert menu_rule is not None
assert "display: none;" in menu_rule.group(1)

assert (
    ".locale-switcher:hover .locale-menu,"
    in css
)

assert (
    ".locale-switcher:focus-within .locale-menu"
    in css
)

open_rule = re.search(
    r'\.locale-switcher:hover \.locale-menu,\s*'
    r'\.locale-switcher:focus-within '
    r'\.locale-menu\s*\{(.*?)\}',
    css,
    re.S,
)

assert open_rule is not None
assert "display: grid;" in open_rule.group(1)

renderer = (
    ROOT / "scripts/render_guide.py"
).read_text(encoding="utf-8")

assert CSS_REFERENCE in renderer

print("LOCALE_SWITCHER_ALL_82_PAGES_OK")
print("LOCALE_SWITCHER_ACTIVE_LANGUAGE_OK")
print("LOCALE_SWITCHER_VISIBLE_CSS_OK")
print("LOCALE_SWITCHER_MENU_INTERACTION_CSS_OK")
print("COMPONENT_CSS_CACHE_VERSION_UNIFIED_OK")
print("GUIDE_RENDERER_CACHE_VERSION_OK")
print("LOCALE_SWITCHER_STATIC_SMOKE_OK")
