import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.guide_publish_apply import apply_publication_plan
from scripts.guide_publish_plan import build_publication_plan
from scripts.guide_publish_preflight import DEFAULT_SITEMAP_PATH
from scripts.render_guide import DEFAULT_REGISTRY_PATH
from scripts.render_guide import DEFAULT_STATIC_ROOT


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish one CargoPT guide by updating its HTML, "
            "registry status, and sitemap."
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
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build and validate the publication plan without writing.",
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

    plan = build_publication_plan(
        article=article,
        registry=registry,
        sitemap_text=sitemap_text,
        static_root=args.static_root,
    )

    if args.check:
        print(
            "GUIDE_PUBLISH_CHECK_OK",
            plan.article_id,
            plan.public_url,
            plan.output_path,
            len(plan.rendered_html.encode("utf-8")),
        )
        return

    apply_publication_plan(
        plan,
        registry_path=args.registry,
        sitemap_path=args.sitemap,
    )

    published_registry = load_json(args.registry)
    published_sitemap = args.sitemap.read_text(encoding="utf-8")
    published_html = plan.output_path.read_text(encoding="utf-8")

    matching_topics = [
        topic
        for topic in published_registry["topics"]
        if topic["id"] == plan.article_id
    ]

    if len(matching_topics) != 1:
        raise RuntimeError(
            "Published registry does not contain exactly one "
            f"topic for {plan.article_id!r}"
        )

    if matching_topics[0]["status"] != "published":
        raise RuntimeError(
            "Published registry topic status is not published"
        )

    if published_sitemap.count(plan.public_url) != 1:
        raise RuntimeError(
            "Published sitemap does not contain guide URL exactly once"
        )

    if published_html != plan.rendered_html:
        raise RuntimeError(
            "Published HTML differs from publication plan"
        )

    print(
        "GUIDE_PUBLISHED",
        plan.article_id,
        plan.public_url,
        plan.output_path,
        len(published_html.encode("utf-8")),
    )


if __name__ == "__main__":
    main()
