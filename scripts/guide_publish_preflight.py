import argparse
import json
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from scripts.render_guide import (
    DEFAULT_REGISTRY_PATH,
    DEFAULT_STATIC_ROOT,
    output_path_for_article,
    public_url,
    render_guide,
)


DEFAULT_SITEMAP_PATH = DEFAULT_STATIC_ROOT / "sitemap.xml"
ALLOWED_SOURCE_STATUSES = {"planned", "draft", "published"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_topic(
    registry: dict[str, Any],
    article_id: str,
) -> dict[str, Any]:
    matches = [
        topic
        for topic in registry["topics"]
        if topic["id"] == article_id
    ]

    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one registry topic for "
            f"{article_id!r}, found {len(matches)}"
        )

    return matches[0]


def validate_article_registry_contract(
    article: dict[str, Any],
    topic: dict[str, Any],
) -> None:
    comparable_fields = (
        "id",
        "cluster",
        "path",
        "title",
        "primary_query",
        "intent",
    )

    for field in comparable_fields:
        if article.get(field) != topic.get(field):
            raise ValueError(
                f"Article and registry differ for {field}: "
                f"{article.get(field)!r} != {topic.get(field)!r}"
            )

    if topic["status"] not in ALLOWED_SOURCE_STATUSES:
        raise ValueError(
            f"Unsupported guide status: {topic['status']!r}"
        )

    if not article["path"].endswith("/"):
        raise ValueError(
            f"Guide path must end with /: {article['path']}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the publication state of one CargoPT guide "
            "without writing files."
        )
    )
    parser.add_argument(
        "article",
        type=Path,
        help="Structured guide article JSON file.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Guide topic registry path.",
    )
    parser.add_argument(
        "--sitemap",
        type=Path,
        default=DEFAULT_SITEMAP_PATH,
        help="Static sitemap path.",
    )
    parser.add_argument(
        "--static-root",
        type=Path,
        default=DEFAULT_STATIC_ROOT,
        help="Static output root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.article.is_file():
        raise FileNotFoundError(args.article)

    if not args.registry.is_file():
        raise FileNotFoundError(args.registry)

    if not args.sitemap.is_file():
        raise FileNotFoundError(args.sitemap)

    article = load_json(args.article)
    registry = load_json(args.registry)
    sitemap_text = args.sitemap.read_text(encoding="utf-8")

    ElementTree.fromstring(sitemap_text)

    topic = find_topic(registry, article["id"])
    validate_article_registry_contract(article, topic)

    rendered = render_guide(article, registry)

    if not rendered.startswith("<!doctype html>\n"):
        raise ValueError("Rendered guide does not start with doctype")

    if not rendered.endswith("</html>\n"):
        raise ValueError(
            "Rendered guide does not end with closing html"
        )

    output_path = output_path_for_article(
        article,
        args.static_root,
    )
    url = public_url(
        registry["base_url"],
        article["path"],
    )

    sitemap_count = sitemap_text.count(url)
    output_exists = output_path.is_file()
    status = topic["status"]

    if status == "published":
        if not output_exists:
            raise ValueError(
                f"Published guide HTML is missing: {output_path}"
            )

        if sitemap_count != 1:
            raise ValueError(
                "Published guide URL must appear exactly once "
                f"in sitemap, found {sitemap_count}: {url}"
            )

        existing_html = output_path.read_text(encoding="utf-8")

        if existing_html != rendered:
            raise ValueError(
                f"Published HTML differs from renderer output: "
                f"{output_path}"
            )
    else:
        if output_exists:
            raise ValueError(
                f"Unpublished guide already has public HTML: "
                f"{output_path}"
            )

        if sitemap_count != 0:
            raise ValueError(
                f"Unpublished guide URL is present in sitemap: {url}"
            )

    print(
        "GUIDE_PUBLISH_PREFLIGHT_OK",
        article["id"],
        status,
        url,
        output_path,
        len(rendered.encode("utf-8")),
    )


if __name__ == "__main__":
    main()
