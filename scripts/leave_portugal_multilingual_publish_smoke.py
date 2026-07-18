import html
import json
import re
from pathlib import Path
from xml.etree import ElementTree

from scripts.guide_publish_preflight import (
    validate_article_registry_contract,
)
from scripts.guide_translation_contract import (
    validate_guide_translation_contract,
)
from scripts.render_guide import (
    output_path_for_article,
    public_url,
    render_guide,
)


ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content/guides/articles"
REGISTRY_PATH = ROOT / "content/guides/topics.json"
MAP_PATH = ROOT / "content/guides/internal-link-map.json"
STATIC_ROOT = ROOT / "app/static"
SITEMAP_PATH = STATIC_ROOT / "sitemap.xml"

GROUP = "leave-portugal"

ALTERNATES = {
    "en": "/en/guides/how-to-leave-portugal/",
    "ru": "/ru/guides/kak-pravilno-uehat-iz-portugalii/",
    "pt-BR": "/pt-br/guias/como-sair-de-portugal/",
}

EXPECTED = {
    "leave-portugal-en": {
        "locale": "en",
        "og_locale": "en_US",
        "path": ALTERNATES["en"],
        "footer_aria": "Legal information",
        "footer_links": {
            "/en/carriers/": "Carriers",
            "/en/privacy/": "Privacy",
            "/en/terms/": "Terms",
            "/en/cookies/": "Cookies",
            "mailto:hello@cargopt.pt": "Contact",
        },
    },
    "leave-portugal-ru": {
        "locale": "ru",
        "og_locale": "ru_RU",
        "path": ALTERNATES["ru"],
        "footer_aria": "Юридическая информация",
        "footer_links": {
            "/ru/carriers/": "Перевозчикам",
            "/ru/privacy/": "Конфиденциальность",
            "/ru/terms/": "Условия",
            "/ru/cookies/": "Cookies",
            "mailto:hello@cargopt.pt": "Контакты",
        },
    },
    "leave-portugal-pt-br": {
        "locale": "pt-BR",
        "og_locale": "pt_BR",
        "path": ALTERNATES["pt-BR"],
        "footer_aria": "Informações legais",
        "footer_links": {
            "/transportadores/": "Para transportadoras",
            "/privacy/": "Privacidade",
            "/terms/": "Termos",
            "/cookies/": "Cookies",
            "mailto:hello@cargopt.pt": "Contato",
        },
    },
}

JOURNEY_REASONS = {
    "next_step",
    "dependency",
    "prerequisite",
}

LOCALE_HOMEPAGES = {
    "/",
    "/en/",
    "/ru/",
    "/pt-br/",
}

APPROVED_IMAGE = (
    "https://cargopt.pt/assets/brand/og-image-v8.jpg"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_hreflang_paths(
    rendered: str,
    base_url: str,
) -> dict[str, str]:
    prefix = base_url.rstrip("/")

    return {
        locale: href.removeprefix(prefix)
        for locale, href in re.findall(
            (
                r'<link rel="alternate" '
                r'hreflang="([^"]+)" '
                r'href="([^"]+)">'
            ),
            rendered,
        )
        if locale != "x-default"
    }


def extract_switcher_paths(rendered: str) -> list[str]:
    match = re.search(
        (
            r'<span class="locale-menu">\s*'
            r'(.*?)'
            r'\s*</span>'
        ),
        rendered,
        flags=re.DOTALL,
    )

    assert match is not None, "MISSING_LOCALE_MENU"

    return re.findall(
        r'<a href="([^"]+)"(?: aria-current="page")?>',
        match.group(1),
    )


def main() -> None:
    registry = load_json(REGISTRY_PATH)
    link_map = load_json(MAP_PATH)
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    ElementTree.fromstring(sitemap)

    topics = {
        topic["id"]: topic
        for topic in registry["topics"]
    }

    loaded_articles = []

    for article_id, expected in EXPECTED.items():
        article_path = ARTICLES / f"{article_id}.json"

        assert article_path.is_file(), (
            "MISSING_ARTICLE_JSON",
            article_path,
        )

        article = load_json(article_path)
        loaded_articles.append(article)

        assert article["id"] == article_id
        assert article["locale"] == expected["locale"]
        assert article["path"] == expected["path"]
        assert article["translation_group"] == GROUP
        assert article["alternates"] == ALTERNATES

        validate_guide_translation_contract(article)

        assert article_id in topics, (
            "MISSING_TOPIC",
            article_id,
        )

        topic = topics[article_id]

        validate_article_registry_contract(article, topic)

        assert topic["status"] == "published"
        assert topic["cluster"] == "planning"

        relationships = link_map["links"].get(article_id)

        assert isinstance(relationships, list), (
            "MISSING_LINK_MAP_SOURCE",
            article_id,
        )
        assert len(relationships) == 4
        assert [
            item["priority"]
            for item in relationships
        ] == [1, 2, 3, 4]

        reasons = [
            item["reason"]
            for item in relationships
        ]
        targets = [
            item["target"]
            for item in relationships
        ]

        assert len(reasons) == len(set(reasons))
        assert len(targets) == len(set(targets))
        assert "same_cluster" in reasons
        assert JOURNEY_REASONS.intersection(reasons)
        assert reasons[-1] == "conversion"
        assert targets[-1] == "@request"
        assert article_id not in targets

        rendered = render_guide(article, registry)
        output_path = output_path_for_article(
            article,
            STATIC_ROOT,
        )

        assert output_path.is_file(), (
            "MISSING_RENDERED_HTML",
            output_path,
        )
        assert output_path.read_text(
            encoding="utf-8"
        ) == rendered, (
            "STALE_RENDERED_HTML",
            output_path,
        )

        url = public_url(
            registry["base_url"],
            article["path"],
        )

        assert sitemap.count(url) == 1, (
            "INVALID_SITEMAP_COUNT",
            url,
            sitemap.count(url),
        )

        for locale, alternate_path in ALTERNATES.items():
            alternate_url = public_url(
                registry["base_url"],
                alternate_path,
            )
            expected_link = (
                '<link rel="alternate" '
                f'hreflang="{locale}" '
                f'href="{alternate_url}">'
            )
            assert rendered.count(expected_link) == 1

        assert (
            '<link rel="alternate" '
            'hreflang="x-default" '
            'href="https://cargopt.pt'
            '/en/guides/how-to-leave-portugal/">'
        ) in rendered

        hreflang_paths = extract_hreflang_paths(
            rendered,
            registry["base_url"],
        )
        switcher_paths = extract_switcher_paths(rendered)

        assert hreflang_paths == ALTERNATES
        assert switcher_paths == list(ALTERNATES.values())
        assert set(switcher_paths) == set(hreflang_paths.values())
        assert not LOCALE_HOMEPAGES.intersection(switcher_paths)

        current_link = (
            f'<a href="{article["path"]}" '
            'aria-current="page">'
        )
        assert rendered.count(current_link) == 1

        footer = article["article_footer"]
        footer_cta = footer["cta"]

        site_footer_match = re.search(
            (
                r'<footer class="site-footer">\s*'
                r'.*?'
                r'<nav class="footer-links" '
                r'aria-label="([^"]+)">'
                r'(.*?)'
                r'</nav>\s*'
                r'</footer>'
            ),
            rendered,
            flags=re.DOTALL,
        )

        assert site_footer_match is not None, (
            "MISSING_SITE_FOOTER",
            article_id,
        )
        assert site_footer_match.group(1) == expected["footer_aria"]

        site_footer_links = {
            href: html.unescape(label)
            for href, label in re.findall(
                r'<a href="([^"]+)">([^<]+)</a>',
                site_footer_match.group(2),
            )
        }

        assert site_footer_links == expected["footer_links"], (
            "SITE_FOOTER_LOCALE_MISMATCH",
            article_id,
            site_footer_links,
            expected["footer_links"],
        )

        assert rendered.count(
            'class="section guide-article-footer"'
        ) == 1
        assert rendered.count(
            'class="guide-meta"'
        ) == 1
        assert rendered.count(
            'class="section guide-article-footer-cta"'
        ) == 1
        assert footer_cta["heading"] in rendered
        assert footer_cta["text"] in rendered
        assert footer_cta["label"] in rendered
        assert (
            f'href="{footer_cta["href"]}"'
            in rendered
        )

        preview = article["social_preview"]
        social_title = html.escape(
            preview["title"],
            quote=True,
        )
        social_description = html.escape(
            preview["description"],
            quote=True,
        )

        canonical = (
            registry["base_url"].rstrip("/")
            + article["path"]
        )

        assert rendered.count(
            '<meta property="og:title" '
            f'content="{social_title}">'
        ) == 1
        assert rendered.count(
            '<meta property="og:description" '
            f'content="{social_description}">'
        ) == 1
        assert rendered.count(
            '<meta property="og:locale" '
            f'content="{expected["og_locale"]}">'
        ) == 1
        assert rendered.count(
            '<meta property="og:image" '
            f'content="{APPROVED_IMAGE}">'
        ) == 1
        assert rendered.count(
            '<meta name="twitter:title" '
            f'content="{social_title}">'
        ) == 1
        assert rendered.count(
            '<meta name="twitter:description" '
            f'content="{social_description}">'
        ) == 1
        assert rendered.count(
            '<meta name="twitter:image" '
            f'content="{APPROVED_IMAGE}">'
        ) == 1
        assert rendered.count(
            f'"image":"{APPROVED_IMAGE}"'
        ) == 1

        canonical_match = re.search(
            r'<link rel="canonical" href="([^"]+)">',
            rendered,
        )
        og_url_match = re.search(
            r'<meta property="og:url" content="([^"]+)">',
            rendered,
        )

        assert canonical_match is not None
        assert og_url_match is not None
        assert canonical_match.group(1) == canonical
        assert og_url_match.group(1) == canonical

        assert "og-image-v1.png" not in rendered
        assert preview["title"] + " — CargoPT" not in rendered

        related = article["related_links"]

        assert len(related) == 4
        assert related[-1]["type"] == "service"
        assert related[-1]["href"] == "/#request"

    assert {
        article["locale"]
        for article in loaded_articles
    } == {"en", "ru", "pt-BR"}

    assert {
        article["translation_group"]
        for article in loaded_articles
    } == {GROUP}

    assert len({
        article["path"]
        for article in loaded_articles
    }) == 3

    print("ARTICLE_LOCALE_SWITCHER_TARGETS_OK")
    print("TRANSLATION_GROUP_NAVIGATION_OK")
    print("SWITCHER_HREFLANG_PARITY_OK")
    print("NO_LOCALE_HOMEPAGE_FALLBACK_OK")
    print("ARTICLE_FOOTER_RENDER_CONTRACT_OK")
    print("SITE_FOOTER_LOCALE_PARITY_OK")
    print("SOCIAL_PREVIEW_TITLE_OK")
    print("SOCIAL_PREVIEW_DESCRIPTION_OK")
    print("SOCIAL_PREVIEW_LOCALE_OK")
    print("SOCIAL_IMAGE_LOCALE_SAFE_OK")
    print("OG_CANONICAL_PARITY_OK")
    print(
        "LEAVE_PORTUGAL_MULTILINGUAL_PUBLISH_SMOKE_OK",
        len(loaded_articles),
    )


if __name__ == "__main__":
    main()
