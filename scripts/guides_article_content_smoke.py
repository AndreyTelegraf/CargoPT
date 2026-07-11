import json
import re
from datetime import date
from pathlib import Path


REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "id",
    "locale",
    "cluster",
    "path",
    "title",
    "meta_title",
    "meta_description",
    "primary_query",
    "intent",
    "article_section",
    "eyebrow",
    "hero_description",
    "date_published",
    "date_modified",
    "review_owner",
    "direct_answer",
    "key_points",
    "sections",
    "mid_cta",
    "faq",
    "related_links",
    "final_cta",
}

ALLOWED_SECTION_CONTENT = {
    "paragraphs",
    "items",
    "checklist",
}

FORBIDDEN_CLAIMS = {
    "o mais barato",
    "o melhor transportador",
    "preço garantido",
    "resposta garantida",
    "primeiro agregador de portugal",
    "todos os transportadores são verificados",
}


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def public_file_for_path(static_root: Path, href: str) -> Path:
    return static_root / href.strip("/") / "index.html"


def main() -> None:
    article_path = Path(
        "content/guides/articles/quanto-custa-uma-mudanca.json"
    )
    registry_path = Path("content/guides/topics.json")
    static_root = Path("app/static")
    generated_page = (
        static_root
        / "guias/precos/quanto-custa-uma-mudanca/index.html"
    )
    sitemap_path = static_root / "sitemap.xml"

    assert article_path.is_file()
    assert registry_path.is_file()
    assert sitemap_path.is_file()

    article = json.loads(article_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    sitemap = sitemap_path.read_text(encoding="utf-8")

    assert REQUIRED_TOP_LEVEL_FIELDS <= article.keys()
    assert article["schema_version"] == 1
    assert article["locale"] == "pt-PT"

    topic = next(
        item
        for item in registry["topics"]
        if item["id"] == article["id"]
    )

    assert topic["status"] in {"planned", "draft", "published"}
    assert article["cluster"] == topic["cluster"]
    assert article["path"] == topic["path"]
    assert article["title"] == topic["title"]
    assert article["primary_query"] == topic["primary_query"]
    assert article["intent"] == topic["intent"]

    assert article["path"].startswith("/guias/")
    assert article["path"].endswith("/")
    assert article["meta_title"].endswith("— CargoPT")
    assert 50 <= len(article["meta_description"]) <= 170

    published = parse_iso_date(article["date_published"])
    modified = parse_iso_date(article["date_modified"])
    assert modified >= published

    direct_answer_words = article["direct_answer"].split()
    assert 60 <= len(direct_answer_words) <= 140, len(
        direct_answer_words
    )

    assert 3 <= len(article["key_points"]) <= 6
    assert all(
        isinstance(item, str) and item.strip()
        for item in article["key_points"]
    )

    sections = article["sections"]
    assert len(sections) >= 5

    section_ids = [section["id"] for section in sections]
    assert len(section_ids) == len(set(section_ids))

    for section in sections:
        assert {"id", "heading"} <= section.keys()
        assert section["heading"].strip()

        content_fields = ALLOWED_SECTION_CONTENT & section.keys()
        assert content_fields, section["id"]

        if "paragraphs" in section:
            assert section["paragraphs"]
            assert all(
                isinstance(paragraph, str) and paragraph.strip()
                for paragraph in section["paragraphs"]
            )

        if "items" in section:
            assert section["items"]
            for item in section["items"]:
                assert set(item) == {"title", "text"}
                assert item["title"].strip()
                assert item["text"].strip()

        if "checklist" in section:
            assert section["checklist"]
            assert all(
                isinstance(item, str) and item.strip()
                for item in section["checklist"]
            )

    for cta_name in ("mid_cta", "final_cta"):
        cta = article[cta_name]
        assert set(cta) == {
            "heading",
            "text",
            "label",
            "href",
        }
        assert cta["href"] == "/#request"

    assert 3 <= len(article["faq"]) <= 6

    questions = []
    for faq_item in article["faq"]:
        assert set(faq_item) == {"question", "answer"}
        assert faq_item["question"].endswith("?")
        assert faq_item["answer"].strip()
        questions.append(faq_item["question"])

    assert len(questions) == len(set(questions))

    related_links = article["related_links"]
    assert len(related_links) >= 3

    related_hrefs = [item["href"] for item in related_links]
    assert len(related_hrefs) == len(set(related_hrefs))
    assert "/guias/" in related_hrefs

    for link in related_links:
        assert set(link) == {"title", "href", "type"}
        assert link["type"] in {"parent", "guide", "landing"}
        assert link["href"].startswith("/")
        assert link["href"].endswith("/")

        expected_file = public_file_for_path(
            static_root,
            link["href"],
        )
        assert expected_file.is_file(), (
            link["href"],
            expected_file,
        )

    serialized = json.dumps(
        article,
        ensure_ascii=False,
    ).lower()

    for claim in FORBIDDEN_CLAIMS:
        assert claim not in serialized, claim

    numeric_price_pattern = re.compile(
        r"(?:€\s*\d+|\d+\s*€|\d+\s*(?:a|–|-)\s*\d+\s*€)",
        re.IGNORECASE,
    )
    assert not numeric_price_pattern.search(serialized)

    public_url = (
        registry["base_url"].rstrip("/")
        + article["path"]
    )

    if topic["status"] == "published":
        assert generated_page.is_file(), generated_page
        assert public_url in sitemap, public_url
    else:
        assert not generated_page.exists(), generated_page
        assert public_url not in sitemap, public_url

    assert article_path.read_text(
        encoding="utf-8"
    ).endswith("\n")

    print(
        "GUIDES_ARTICLE_CONTENT_SMOKE_OK",
        article["id"],
        len(sections),
        len(article["faq"]),
        len(direct_answer_words),
    )


if __name__ == "__main__":
    main()
