import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLE_PATH = (
    PROJECT_ROOT
    / "content/guides/articles/quanto-custa-uma-mudanca.json"
)
REGISTRY_PATH = PROJECT_ROOT / "content/guides/topics.json"
RENDERER_PATH = PROJECT_ROOT / "scripts/render_guide.py"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "app/static/guias/precos/quanto-custa-uma-mudanca/index.html"
)


def load_renderer():
    sys.path.insert(0, str(PROJECT_ROOT))

    from scripts.render_guide import (  # noqa: PLC0415
        build_structured_data,
        output_path_for_article,
        render_guide,
    )

    return (
        build_structured_data,
        output_path_for_article,
        render_guide,
    )


def main() -> None:
    assert RENDERER_PATH.is_file()
    assert ARTICLE_PATH.is_file()
    assert REGISTRY_PATH.is_file()

    output_existed_before = OUTPUT_PATH.exists()
    output_bytes_before = (
        OUTPUT_PATH.read_bytes()
        if output_existed_before
        else None
    )

    article = json.loads(
        ARTICLE_PATH.read_text(encoding="utf-8")
    )
    registry = json.loads(
        REGISTRY_PATH.read_text(encoding="utf-8")
    )

    (
        build_structured_data,
        output_path_for_article,
        render_guide,
    ) = load_renderer()

    rendered = render_guide(article, registry)

    expected_output = output_path_for_article(
        article,
        PROJECT_ROOT / "app/static",
    )
    assert expected_output == OUTPUT_PATH

    required_html = [
        "<!doctype html>",
        '<html lang="pt-PT">',
        f"<title>{article['meta_title']}</title>",
        (
            '<link rel="canonical" href="'
            "https://cargopt.pt"
            f'{article["path"]}">'
        ),
        '<meta property="og:type" content="article">',
        '<link rel="stylesheet" href="/assets/css/guides.css?v=guides-v1">',
        '"@type":"Article"',
        '"@type":"BreadcrumbList"',
        '"@type":"FAQPage"',
        f"<h1>{article['title']}</h1>",
        article["direct_answer_heading"],
        article["key_points_heading"],
        article["faq_heading"],
        article["related_links_heading"],
        article["direct_answer"],
        article["sections"][0]["heading"],
        article["faq"][0]["question"],
        'href="/guias/"',
        f'<span aria-current="page">{article["title"]}</span>',
        'href="/#request"',
        'class="site-footer"',
    ]

    for expected in required_html:
        assert expected in rendered, expected

    assert rendered.count("<h1>") == 1
    assert rendered.count('"@type":"Article"') == 1
    assert rendered.count('"@type":"BreadcrumbList"') == 1
    assert rendered.count('"@type":"FAQPage"') == 1

    for section in article["sections"]:
        assert f'id="{section["id"]}"' in rendered
        assert f"<h2>{section['heading']}</h2>" in rendered

    for faq_item in article["faq"]:
        assert (
            f"<summary>{faq_item['question']}</summary>"
            in rendered
        )
        assert faq_item["answer"] in rendered

    for link in article["related_links"]:
        assert f'href="{link["href"]}"' in rendered
        assert link["title"] in rendered

    schemas = build_structured_data(article, registry)
    assert len(schemas) == 3

    article_schema, breadcrumb_schema, faq_schema = schemas

    assert article_schema["@type"] == "Article"
    assert article_schema["headline"] == article["title"]
    assert article_schema["datePublished"] == article["date_published"]
    assert article_schema["dateModified"] == article["date_modified"]
    assert article_schema["inLanguage"] == "pt-PT"

    assert breadcrumb_schema["@type"] == "BreadcrumbList"

    breadcrumb_items = breadcrumb_schema["itemListElement"]

    assert len(breadcrumb_items) == 3
    assert [item["position"] for item in breadcrumb_items] == [1, 2, 3]
    assert [item["name"] for item in breadcrumb_items] == [
        "CargoPT",
        "Guias",
        article["title"],
    ]
    assert breadcrumb_items[0]["item"] == "https://cargopt.pt/"
    assert breadcrumb_items[1]["item"] == "https://cargopt.pt/guias/"
    assert (
        breadcrumb_items[2]["item"]
        == "https://cargopt.pt"
        + article["path"]
    )

    assert faq_schema["@type"] == "FAQPage"
    assert len(faq_schema["mainEntity"]) == len(article["faq"])

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.render_guide",
            str(ARTICLE_PATH),
            "--registry",
            str(REGISTRY_PATH),
            "--check",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "GUIDE_RENDER_CHECK_OK" in result.stdout
    assert article["id"] in result.stdout
    assert OUTPUT_PATH.exists() is output_existed_before

    if output_existed_before:
        assert OUTPUT_PATH.read_bytes() == output_bytes_before

    assert rendered.endswith("</html>\n")

    print(
        "GUIDES_RENDERER_SMOKE_OK",
        article["id"],
        len(rendered),
        len(article["sections"]),
        len(article["faq"]),
    )


if __name__ == "__main__":
    main()
