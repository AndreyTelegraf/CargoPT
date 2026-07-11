from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.guide_publish_preflight import find_topic
from scripts.guide_publish_preflight import (
    validate_article_registry_contract,
)
from scripts.guide_registry_update import (
    registry_with_published_guide,
)
from scripts.guide_registry_update import serialize_registry
from scripts.guide_sitemap_update import add_guide_to_sitemap
from scripts.render_guide import output_path_for_article
from scripts.render_guide import public_url
from scripts.render_guide import render_guide


@dataclass(frozen=True)
class GuidePublicationPlan:
    article_id: str
    public_url: str
    output_path: Path
    rendered_html: str
    registry_text: str
    sitemap_text: str


def build_publication_plan(
    *,
    article: dict[str, Any],
    registry: dict[str, Any],
    sitemap_text: str,
    static_root: Path,
) -> GuidePublicationPlan:
    topic = find_topic(registry, article["id"])
    validate_article_registry_contract(article, topic)

    if topic["status"] not in {"planned", "draft"}:
        raise ValueError(
            "Guide publication requires planned or draft status, "
            f"got {topic['status']!r}: {article['id']}"
        )

    output_path = output_path_for_article(
        article,
        static_root,
    )

    if output_path.exists():
        raise ValueError(
            f"Guide output already exists before publication: "
            f"{output_path}"
        )

    updated_registry = registry_with_published_guide(
        registry,
        article_id=article["id"],
    )

    rendered_html = render_guide(
        article,
        updated_registry,
    )

    if not rendered_html.startswith("<!doctype html>\n"):
        raise ValueError(
            "Rendered guide does not start with doctype"
        )

    if not rendered_html.endswith("</html>\n"):
        raise ValueError(
            "Rendered guide does not end with closing html"
        )

    url = public_url(
        updated_registry["base_url"],
        article["path"],
    )

    updated_sitemap = add_guide_to_sitemap(
        sitemap_text,
        url=url,
        last_modified=article["date_modified"],
    )

    return GuidePublicationPlan(
        article_id=article["id"],
        public_url=url,
        output_path=output_path,
        rendered_html=rendered_html,
        registry_text=serialize_registry(updated_registry),
        sitemap_text=updated_sitemap,
    )
