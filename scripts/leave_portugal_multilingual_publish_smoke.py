import json
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
        "path": ALTERNATES["en"],
    },
    "leave-portugal-ru": {
        "locale": "ru",
        "path": ALTERNATES["ru"],
    },
    "leave-portugal-pt-br": {
        "locale": "pt-BR",
        "path": ALTERNATES["pt-BR"],
    },
}

JOURNEY_REASONS = {
    "next_step",
    "dependency",
    "prerequisite",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
        ) == rendered

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
            assert expected_link in rendered

        assert (
            '<link rel="alternate" '
            'hreflang="x-default" '
            'href="https://cargopt.pt'
            '/en/guides/how-to-leave-portugal/">'
        ) in rendered

        related = article["related_links"]
        assert len(related) == 4
        assert related == [
            {
                "title": item["title"],
                "href": item["href"],
                "type": item["type"],
            }
            for item in related
        ]
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

    print(
        "LEAVE_PORTUGAL_MULTILINGUAL_PUBLISH_SMOKE_OK",
        len(loaded_articles),
    )


if __name__ == "__main__":
    main()
